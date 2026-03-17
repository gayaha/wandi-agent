"""Core generation logic for the wandi-agent."""

import asyncio
import logging
import re
from typing import Any

import airtable_client as at
import ollama_client as ollama
import prompts

logger = logging.getLogger(__name__)

# Valid values
BATCH_TYPES = {"חשיפה", "מכירה", "מעורב"}

# ── Normalisation maps (lowercase key → Airtable value) ──────────────
# The AI model and the website may return English values, but Airtable
# Select fields expect specific strings.  These maps ensure both sources
# always produce the correct Airtable option.

_HOOK_TYPE_MAP: dict[str, str] = {
    # Hebrew pass-through
    "שאלה מאתגרת": "שאלה מאתגרת",
    "מספר + הבטחה": "מספר + הבטחה",
    "טעות נפוצה": "טעות נפוצה",
    "סוד חשיפה": "סוד חשיפה",
    "זיהוי קהל": "זיהוי קהל",
    "תוצאה מפתיעה": "תוצאה מפתיעה",
    "פרובוקציה": "פרובוקציה",
    # Hebrew variants the model may produce
    "דעה לא פופולרית": "פרובוקציה",
    # English variants the model / website may produce
    "provocative": "פרובוקציה",
    "provocation": "פרובוקציה",
    "challenging question": "שאלה מאתגרת",
    "challenging_question": "שאלה מאתגרת",
    "number + promise": "מספר + הבטחה",
    "number_plus_promise": "מספר + הבטחה",
    "number plus promise": "מספר + הבטחה",
    "common mistake": "טעות נפוצה",
    "common_mistake": "טעות נפוצה",
    "secret reveal": "סוד חשיפה",
    "secret_reveal": "סוד חשיפה",
    "audience identification": "זיהוי קהל",
    "audience_identification": "זיהוי קהל",
    "surprising result": "תוצאה מפתיעה",
    "surprising_result": "תוצאה מפתיעה",
    "call to action": "פרובוקציה",
    "call_to_action": "פרובוקציה",
    "cta": "פרובוקציה",
    # Irrelevant types → map to closest valid type
    "unpopular opinion": "פרובוקציה",
    "unpopular_opinion": "פרובוקציה",
    "talking_head": "פרובוקציה",
    "talking head": "פרובוקציה",
}

_VALID_HOOK_TYPES: set[str] = {
    "שאלה מאתגרת", "מספר + הבטחה", "טעות נפוצה", "סוד חשיפה",
    "זיהוי קהל", "תוצאה מפתיעה", "פרובוקציה",
}

_CONTENT_TYPE_AIRTABLE: dict[str, str] = {
    "חשיפה": "חשיפה",
    "מכירה": "מכירה",
    "exposure": "חשיפה",
    "sales": "מכירה",
    "sale": "מכירה",
}

_AWARENESS_MAP: dict[str, str] = {
    # English
    "unaware": "Unaware",
    "problem-aware": "Problem-Aware",
    "problem aware": "Problem-Aware",
    "problem_aware": "Problem-Aware",
    "solution-aware": "Solution-Aware",
    "solution aware": "Solution-Aware",
    "solution_aware": "Solution-Aware",
    # Hebrew — model sometimes returns Hebrew stage names
    "לא מודע": "Unaware",
    "לא מודעים": "Unaware",
    "לא מודעת": "Unaware",
    "מודעות לבעיה": "Problem-Aware",
    "מודע לבעיה": "Problem-Aware",
    "מודעת לבעיה": "Problem-Aware",
    "מודעות לפתרון": "Solution-Aware",
    "מודע לפתרון": "Solution-Aware",
    "מודעת לפתרון": "Solution-Aware",
}

# Recommended hook types per awareness stage (for validation — not strict rejection)
_STAGE_HOOK_TYPES: dict[str, set[str]] = {
    "Unaware": {"פרובוקציה", "תוצאה מפתיעה", "שאלה מאתגרת"},
    "Problem-Aware": {"טעות נפוצה", "זיהוי קהל", "שאלה מאתגרת", "מספר + הבטחה"},
    "Solution-Aware": {"סוד חשיפה", "מספר + הבטחה", "תוצאה מפתיעה"},
}

# Stage → required content_type
_STAGE_CONTENT_TYPE: dict[str, str] = {
    "Unaware": "חשיפה",
    "Problem-Aware": "חשיפה",
    "Solution-Aware": "מכירה",
}


def _normalize(value: str, mapping: dict[str, str]) -> str:
    """Map a value to the canonical Airtable option (case-insensitive).

    Strips whitespace and surrounding quotes that the LLM sometimes adds.
    """
    if not value:
        return value
    cleaned = value.strip().strip('"').strip("'").strip().lower()
    result = mapping.get(cleaned)
    if result:
        return result
    logger.warning(f"Unmapped select value '{value}' (cleaned: '{cleaned}')")
    return value


# ── Hook quality helpers ─────────────────────────────────────────────────────


def count_hebrew_words(text: str) -> int:
    """Count words in *text*, where a 'word' is any whitespace-delimited token
    that contains at least one Hebrew character (\\u0590-\\u05FF)."""
    if not text:
        return 0
    return sum(1 for w in text.split() if re.search(r'[\u0590-\u05FF]', w))


def _count_words(text: str) -> int:
    """Count total whitespace-delimited words in *text*."""
    return len(text.split()) if text else 0


def _has_consecutive_english(text: str, threshold: int = 3) -> bool:
    """Return True if *text* contains *threshold* or more consecutive
    whitespace-delimited tokens that are purely ASCII-letter words."""
    if not text:
        return False
    consecutive = 0
    for token in text.split():
        if re.fullmatch(r'[A-Za-z]+', token):
            consecutive += 1
            if consecutive >= threshold:
                return True
        else:
            consecutive = 0
    return False


async def _validate_hook(
    hook: str,
    prompt: str,
    reel_index: int,
) -> tuple[str | None, bool]:
    """Validate a hook for word count and language.

    Returns (validated_hook, should_skip).
    - validated_hook is the (possibly fixed) hook text, or None if skipped.
    - should_skip is True when the reel should be dropped entirely.
    """
    tag = f"Reel {reel_index + 1}"

    # ── Rule 1: Hook over 12 words → retry once, then truncate ──
    word_count = _count_words(hook)
    if word_count > 12:
        logger.warning(
            f"[HookValidation] {tag}: hook has {word_count} words (>12), retrying..."
        )
        retry_prompt = prompt + "\n\nהוק חייב להיות עד 10 מילים בדיוק"
        try:
            result = await ollama.generate_json(
                retry_prompt, system=prompts.FULL_SYSTEM_PROMPT
            )
            retry_reel = None
            if isinstance(result, dict):
                if "reels" in result and isinstance(result["reels"], list) and result["reels"]:
                    retry_reel = result["reels"][0]
                elif "hook" in result:
                    retry_reel = result
            if retry_reel:
                new_hook = retry_reel.get("hook", "")
                new_count = _count_words(new_hook)
                if new_count <= 12:
                    logger.info(f"[HookValidation] {tag}: retry succeeded ({new_count} words)")
                    return new_hook, False
                logger.warning(
                    f"[HookValidation] {tag}: retry still {new_count} words, truncating to 12"
                )
                hook = " ".join(new_hook.split()[:12])
            else:
                logger.warning(f"[HookValidation] {tag}: retry returned empty, truncating original")
                hook = " ".join(hook.split()[:12])
        except Exception as e:
            logger.warning(f"[HookValidation] {tag}: retry failed ({e}), truncating original")
            hook = " ".join(hook.split()[:12])

    # ── Rule 2: 3+ consecutive English words → retry once, then skip ──
    if _has_consecutive_english(hook):
        logger.warning(
            f"[HookValidation] {tag}: hook contains 3+ consecutive English words, retrying..."
        )
        retry_prompt = prompt + "\n\nכתוב אך ורק בעברית"
        try:
            result = await ollama.generate_json(
                retry_prompt, system=prompts.FULL_SYSTEM_PROMPT
            )
            retry_reel = None
            if isinstance(result, dict):
                if "reels" in result and isinstance(result["reels"], list) and result["reels"]:
                    retry_reel = result["reels"][0]
                elif "hook" in result:
                    retry_reel = result
            if retry_reel:
                new_hook = retry_reel.get("hook", "")
                if not _has_consecutive_english(new_hook):
                    logger.info(f"[HookValidation] {tag}: retry succeeded (Hebrew only)")
                    # Also enforce word count on the retried hook
                    if _count_words(new_hook) > 12:
                        new_hook = " ".join(new_hook.split()[:12])
                    return new_hook, False
        except Exception as e:
            logger.warning(f"[HookValidation] {tag}: Hebrew retry failed ({e})")

        logger.warning(f"[HookValidation] {tag}: still English after retry → SKIPPING reel")
        return None, True

    return hook, False


# ── Post-generation validation ───────────────────────────────────────────────


def _validate_and_fix_reel(
    reel: dict[str, Any],
    magnets: list[dict],
    valid_magnet_ids: set[str],
    folders: dict[str, str] | None,
    reel_index: int,
) -> dict[str, Any]:
    """Validate a single reel against SDMF rules and auto-fix violations.

    Returns the (possibly modified) reel dict.
    """
    tag = f"Reel {reel_index + 1}"

    # 1. Normalize awareness_stage
    raw_stage = reel.get("awareness_stage") or ""
    stage = _normalize(raw_stage, _AWARENESS_MAP)
    if stage not in ("Unaware", "Problem-Aware", "Solution-Aware"):
        logger.warning(f"[Validation] {tag}: invalid awareness_stage '{raw_stage}' → defaulting to Problem-Aware")
        stage = "Problem-Aware"
    reel["awareness_stage"] = stage

    # 2. Enforce content_type per stage
    expected_ct = _STAGE_CONTENT_TYPE[stage]
    raw_ct = _normalize(reel.get("content_type") or "", _CONTENT_TYPE_AIRTABLE)
    if raw_ct != expected_ct:
        logger.warning(f"[Validation] {tag}: content_type '{raw_ct}' → fixed to '{expected_ct}' (stage={stage})")
        reel["content_type"] = expected_ct
    else:
        reel["content_type"] = raw_ct

    # 3. Enforce magnet rules per stage
    magnet_id = reel.get("magnet_id")
    if stage == "Unaware":
        if magnet_id:
            logger.warning(f"[Validation] {tag}: Unaware reel had magnet_id '{magnet_id}' → removed")
            reel["magnet_id"] = None
    elif stage == "Solution-Aware":
        if not magnet_id or magnet_id not in valid_magnet_ids:
            if valid_magnet_ids:
                fallback = next(iter(valid_magnet_ids))
                logger.warning(f"[Validation] {tag}: Solution-Aware missing/invalid magnet → assigned '{fallback}'")
                reel["magnet_id"] = fallback
            else:
                logger.warning(f"[Validation] {tag}: Solution-Aware but no magnets available → downgrading to Problem-Aware")
                reel["awareness_stage"] = "Problem-Aware"
                reel["content_type"] = "חשיפה"
                reel["magnet_id"] = None
    elif stage == "Problem-Aware":
        if magnet_id and magnet_id not in valid_magnet_ids:
            logger.warning(f"[Validation] {tag}: Problem-Aware had invalid magnet_id '{magnet_id}' → removed")
            reel["magnet_id"] = None

    # 3b. Solution-Aware: validate trigger word in caption
    if reel["awareness_stage"] == "Solution-Aware" and reel.get("magnet_id"):
        magnet = next((m for m in magnets if m["id"] == reel.get("magnet_id")), None)
        if magnet:
            trigger = magnet.get("fields", {}).get("Trigger Word", "")
            caption = reel.get("caption", "")
            if trigger and trigger not in caption:
                logger.warning(f"[Validation] {tag}: missing trigger word '{trigger}' — appending CTA")
                reel["caption"] = caption.rstrip() + f"\n\nתגיבו '{trigger}' ותקבלו את זה בהודעה 👇"

    # 4. Validate and normalize hook_type
    raw_ht = _normalize(reel.get("hook_type") or "", _HOOK_TYPE_MAP)
    if raw_ht not in _VALID_HOOK_TYPES:
        recommended = _STAGE_HOOK_TYPES.get(reel["awareness_stage"], set())
        fallback_ht = next(iter(recommended)) if recommended else "שאלה מאתגרת"
        logger.warning(f"[Validation] {tag}: invalid hook_type '{raw_ht}' → fixed to '{fallback_ht}'")
        reel["hook_type"] = fallback_ht
    else:
        reel["hook_type"] = raw_ht

    # 5. Unaware → hook_only (text_on_video should be null)
    if reel["awareness_stage"] == "Unaware" and reel.get("text_on_video"):
        logger.info(f"[Validation] {tag}: Unaware reel had text_on_video → cleared (hook_only)")
        reel["text_on_video"] = None

    # 6. Validate folder_id
    if reel.get("folder_id") and folders and reel["folder_id"] not in folders:
        logger.warning(f"[Validation] {tag}: invalid folder_id '{reel['folder_id']}' → removed")
        reel["folder_id"] = None

    return reel


def _validate_distribution_compliance(
    reels: list[dict], distribution: dict[str, int]
) -> None:
    """Log warnings if actual stage counts don't match the requested distribution."""
    actual: dict[str, int] = {}
    for r in reels:
        stage = r.get("awareness_stage", "Unknown")
        actual[stage] = actual.get(stage, 0) + 1

    for stage, expected in distribution.items():
        got = actual.get(stage, 0)
        if got != expected:
            logger.warning(
                f"[Distribution] Requested {expected} {stage} reels, got {got}"
            )


# ── Distribution ─────────────────────────────────────────────────────────────


def _decide_distribution(
    batch_type: str, quantity: int, magnets: list[dict]
) -> dict[str, int]:
    """Decide how many reels per Awareness Stage based on batch_type."""
    has_magnets = len(magnets) > 0

    if batch_type == "חשיפה":
        # Mostly unaware/problem-aware content
        unaware = max(1, int(quantity * 0.6))
        problem = quantity - unaware
        return {"Unaware": unaware, "Problem-Aware": problem}

    if batch_type == "מכירה":
        # Mostly solution-aware with CTA
        if not has_magnets:
            logger.warning("מכירה batch but no magnets — shifting to Problem-Aware")
            problem = max(1, int(quantity * 0.6))
            solution = quantity - problem
            return {"Problem-Aware": problem, "Solution-Aware": solution}
        solution = max(1, int(quantity * 0.6))
        problem = quantity - solution
        return {"Problem-Aware": problem, "Solution-Aware": solution}

    # מעורב — balanced mix
    if quantity <= 2:
        return {"Unaware": 1, "Problem-Aware": max(0, quantity - 1)}

    unaware = max(1, int(quantity * 0.3))
    solution = max(1, int(quantity * 0.3)) if has_magnets else 0
    problem = quantity - unaware - solution
    return {"Unaware": unaware, "Problem-Aware": problem, "Solution-Aware": solution}


# ── Data fetching ────────────────────────────────────────────────────────────


async def _fetch_all_data(
    client_id: str, niche: str, client_name: str = "",
    content_sources: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch required data from Airtable concurrently.

    Args:
        content_sources: Optional list of data sources to fetch.
            Possible values: "hooks", "viral_pool", "rtm_events",
            "style_examples", "insights".
            Magnets + recent_hooks are always fetched.
            Empty/None = fetch everything.
    """
    # Magnets + recent_hooks are always needed
    tasks: dict[str, Any] = {
        "magnets": at.get_magnets_for_client(client_id, client_name=client_name),
        "recent_hooks": at.get_recent_hooks_for_client(client_id, client_name=client_name),
    }

    # Conditionally add other sources
    fetch_all = not content_sources
    if fetch_all or "hooks" in content_sources:
        tasks["hooks"] = at.get_viral_hooks(client_id, client_name=client_name)
    if fetch_all or "viral_pool" in content_sources:
        tasks["viral_pool"] = at.get_viral_content_pool(niche)
    if fetch_all or "rtm_events" in content_sources:
        tasks["rtm_events"] = at.get_active_rtm_events(niche)
    if fetch_all or "style_examples" in content_sources:
        tasks["style_examples"] = at.get_top_style_examples(client_id, client_name=client_name)
    if fetch_all or "insights" in content_sources:
        tasks["insights"] = at.get_global_insights(niche)

    keys = list(tasks.keys())
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    defaults: dict[str, Any] = {
        "magnets": [], "hooks": [], "viral_pool": [], "rtm_events": [],
        "style_examples": [], "insights": None, "recent_hooks": [],
    }
    data = dict(defaults)
    for key, result in zip(keys, results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to fetch {key}: {result}")
        else:
            data[key] = result

    skipped = set(defaults.keys()) - set(keys)
    if skipped:
        logger.info(f"Skipped fetching: {', '.join(sorted(skipped))}")

    return data


# ── Record building ──────────────────────────────────────────────────────────


def _build_queue_record(
    reel: dict[str, Any], client_id: str
) -> dict[str, Any]:
    """Convert a generated reel dict into an Airtable Content Queue record."""
    record: dict[str, Any] = {
        "Client": [client_id],
        "Hook": reel.get("hook") or "",
        "Hook Type": _normalize(reel.get("hook_type") or "", _HOOK_TYPE_MAP),
        "text on video": reel.get("text_on_video") or "",
        "Caption": reel.get("caption") or "",
        "Content Type": _normalize(reel.get("content_type") or "", _CONTENT_TYPE_AIRTABLE),
        "Awareness Stage": _normalize(reel.get("awareness_stage") or "", _AWARENESS_MAP),
        "Status": "Draft",
        "Source": "wandi-agent",
    }
    if reel.get("magnet_id"):
        record["Selected Magnet"] = [reel["magnet_id"]]
    return record


# ── Main pipeline ────────────────────────────────────────────────────────────


async def generate_reels(
    client_id: str, batch_type: str, quantity: int = 10,
    folders: dict[str, str] | None = None,
    content_sources: list[str] | None = None,
) -> dict[str, Any]:
    """Main generation pipeline.

    1. Fetch client + all related data from Airtable
    2. Decide content distribution
    3. Generate reels via Ollama
    4. Validate and fix each reel
    5. Save to Content Queue
    6. Return results
    """
    if batch_type not in BATCH_TYPES:
        raise ValueError(f"Invalid batch_type '{batch_type}'. Must be one of: {BATCH_TYPES}")
    if quantity < 1 or quantity > 30:
        raise ValueError("quantity must be between 1 and 30")

    # Step 1: Fetch client profile
    logger.info(f"Fetching client {client_id}...")
    client_record = await at.get_client(client_id)
    client_fields = client_record["fields"]

    client_name = (client_fields.get("Client Name") or "").strip()
    business_info = client_fields.get("Business Info", "")
    tone_of_voice = client_fields.get("Tone Of Voice", "")
    niche_raw = client_fields.get("Niche", "")
    niche = niche_raw[0] if isinstance(niche_raw, list) and niche_raw else niche_raw
    ig_username = client_fields.get("ig_username", "")
    client_knowledge = client_fields.get("Client Knowledge", "")

    if not niche:
        logger.warning(f"Client {client_id} has no Niche defined — defaulting to 'כללי'")
        niche = "כללי"

    # Step 1b: Fetch all related data concurrently
    logger.info(f"Fetching data for niche '{niche}'...")
    data = await _fetch_all_data(client_id, niche, client_name=client_name, content_sources=content_sources)

    # Step 2: Decide distribution
    distribution = _decide_distribution(batch_type, quantity, data["magnets"])
    logger.info(f"Distribution plan: {distribution}")

    # Step 3: Generate via Ollama — one reel per call to avoid model degradation
    logger.info(f"Generating {quantity} reels via Ollama (one per call)...")

    # Build the reel list from distribution: e.g. {Unaware: 2, Problem-Aware: 1} → [Unaware, Unaware, Problem-Aware]
    stage_sequence: list[str] = []
    for stage, count in distribution.items():
        stage_sequence.extend([stage] * count)

    # Track hooks generated so far to pass as recent_hooks for dedup
    all_recent = list(data["recent_hooks"])
    generated_reels: list[dict] = []

    for reel_idx, stage in enumerate(stage_sequence):
        prompt = prompts.build_single_reel_prompt(
            awareness_stage=stage,
            client_name=client_name,
            business_info=business_info,
            tone_of_voice=tone_of_voice,
            niche=niche,
            ig_username=ig_username,
            client_knowledge=client_knowledge,
            magnets=data["magnets"],
            style_examples=data["style_examples"],
            hooks=data["hooks"],
            rtm_events=data["rtm_events"],
            insights=data["insights"],
            folders=folders,
            recent_hooks=all_recent,
            reel_index=reel_idx,
        )

        max_attempts = 2
        reel: dict | None = None
        for attempt in range(max_attempts):
            try:
                result = await ollama.generate_json(prompt, system=prompts.FULL_SYSTEM_PROMPT)
                # Handle both {"reels": [...]} wrapper and flat reel dict
                if isinstance(result, dict):
                    if "reels" in result and isinstance(result["reels"], list) and result["reels"]:
                        reel = result["reels"][0]
                    elif "hook" in result:
                        reel = result
                if reel:
                    break
                logger.warning(f"Reel {reel_idx + 1} attempt {attempt + 1}/{max_attempts}: empty result")
            except ValueError as e:
                logger.warning(f"Reel {reel_idx + 1} attempt {attempt + 1}/{max_attempts} failed: {e}")
                if attempt == max_attempts - 1:
                    logger.error(f"Skipping reel {reel_idx + 1} after {max_attempts} failures")

        if reel:
            # ── Hook validation (word count + language) ──
            raw_hook = reel.get("hook", "")
            validated_hook, should_skip = await _validate_hook(
                raw_hook, prompt, reel_idx
            )
            if should_skip:
                logger.warning(
                    f"Reel {reel_idx + 1}/{len(stage_sequence)} ({stage}): "
                    f"SKIPPED — hook failed language validation"
                )
                continue
            if validated_hook is not None:
                reel["hook"] = validated_hook

            generated_reels.append(reel)
            # Track this hook so the next reel won't repeat it
            hook_text = reel.get("hook", "")
            if hook_text:
                all_recent.append(hook_text)
            logger.info(
                f"Reel {reel_idx + 1}/{len(stage_sequence)} ({stage}): "
                f"{hook_text[:60]} [{_count_words(hook_text)}w]"
            )
        else:
            logger.error(f"Reel {reel_idx + 1}/{len(stage_sequence)} ({stage}): FAILED — skipped")

    if not generated_reels:
        logger.error("Ollama returned no reels after all attempts")
        raise ValueError("Model did not generate any reels")

    logger.info(f"Ollama generated {len(generated_reels)} reels")

    # Step 4: Validate and fix each reel
    valid_magnet_ids = {m["id"] for m in data["magnets"]}
    for i, reel in enumerate(generated_reels):
        generated_reels[i] = _validate_and_fix_reel(
            reel, data["magnets"], valid_magnet_ids, folders, i
        )
    _validate_distribution_compliance(generated_reels, distribution)

    # Step 5: Save to Airtable Content Queue (batch first, fallback to individual)
    queue_records = [_build_queue_record(r, client_id) for r in generated_reels]

    saved: list[dict] = []
    errors: list[str] = []
    try:
        saved = await at.save_reels_to_queue(queue_records)
    except Exception as e:
        logger.warning(f"Batch save failed: {e}, falling back to individual saves")
        for i, rec in enumerate(queue_records):
            try:
                result_records = await at.save_reels_to_queue([rec])
                saved.extend(result_records)
            except Exception as e2:
                logger.error(f"Failed to save reel {i + 1}: {e2}")
                errors.append(f"Reel {i + 1}: {str(e2)}")

    logger.info(f"Saved {len(saved)}/{len(queue_records)} reels to Content Queue")

    # Step 6: Build response — resolve magnet names so callers don't need
    # to re-fetch the magnets list.
    magnet_names = {m["id"]: m.get("fields", {}).get("Magnet Name", "") for m in data["magnets"]}
    response_reels = []
    for i, reel_data in enumerate(generated_reels):
        reel_response = {
            **reel_data,
            "saved": i < len(saved),
            "record_id": saved[i]["id"] if i < len(saved) else None,
            "magnet_name": magnet_names.get(reel_data.get("magnet_id", ""), ""),
        }
        response_reels.append(reel_response)

    return {
        "success": True,
        "client_name": client_name,
        "batch_type": batch_type,
        "distribution": distribution,
        "reels": response_reels,
        "count": len(generated_reels),
        "saved_count": len(saved),
        "errors": errors if errors else None,
    }
