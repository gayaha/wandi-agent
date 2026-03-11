"""Core generation logic for the wandi-agent."""

import asyncio
import logging
from typing import Any

import airtable_client as at
import ollama_client as ollama
import prompts

logger = logging.getLogger(__name__)

# Valid values
BATCH_TYPES = {"חשיפה", "מכירה", "מעורב"}
CONTENT_TYPE_MAP = {
    "חשיפה": "חשיפה",
    "מכירה": "מכירה",
}


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


async def _fetch_all_data(
    client_id: str, niche: str, client_name: str = ""
) -> dict[str, Any]:
    """Fetch all required data from Airtable concurrently."""
    (
        magnets,
        hooks,
        viral_pool,
        rtm_events,
        style_examples,
        insights,
    ) = await asyncio.gather(
        at.get_magnets_for_client(client_id, client_name=client_name),
        at.get_viral_hooks(niche),
        at.get_viral_content_pool(niche),
        at.get_active_rtm_events(niche),
        at.get_top_style_examples(client_id, client_name=client_name),
        at.get_global_insights(niche),
    )
    return {
        "magnets": magnets,
        "hooks": hooks,
        "viral_pool": viral_pool,
        "rtm_events": rtm_events,
        "style_examples": style_examples,
        "insights": insights,
    }


def _build_queue_record(
    reel: dict[str, Any], client_id: str
) -> dict[str, Any]:
    """Convert a generated reel dict into an Airtable Content Queue record."""
    record: dict[str, Any] = {
        "Client": [client_id],
        "Hook": reel.get("hook", ""),
        "Hook Type": reel.get("hook_type", ""),
        "Text On Video": reel.get("text_on_video", ""),
        "Verbal Script": reel.get("verbal_script", ""),
        "Caption": reel.get("caption", ""),
        "Format": reel.get("format", ""),
        "Content Type": reel.get("content_type", ""),
        "Awareness Stage": reel.get("awareness_stage", ""),
        "Status": "Draft",
        "Source": "wandi-agent",
    }
    if reel.get("magnet_id"):
        record["Magnet"] = [reel["magnet_id"]]
    return record


async def generate_reels(
    client_id: str, batch_type: str, quantity: int = 10,
    folders: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Main generation pipeline.

    1. Fetch client + all related data from Airtable
    2. Decide content distribution
    3. Generate reels via Ollama
    4. Save to Content Queue
    5. Return results
    """
    if batch_type not in BATCH_TYPES:
        raise ValueError(f"Invalid batch_type '{batch_type}'. Must be one of: {BATCH_TYPES}")
    if quantity < 1 or quantity > 30:
        raise ValueError("quantity must be between 1 and 30")

    # Step 1: Fetch client profile
    logger.info(f"Fetching client {client_id}...")
    client_record = await at.get_client(client_id)
    client_fields = client_record["fields"]

    client_name = client_fields.get("Client Name", "")
    business_info = client_fields.get("Business Info", "")
    tone_of_voice = client_fields.get("Tone Of Voice", "")
    niche_raw = client_fields.get("Niche", "")
    niche = niche_raw[0] if isinstance(niche_raw, list) and niche_raw else niche_raw
    ig_username = client_fields.get("ig_username", "")

    if not niche:
        raise ValueError(f"Client {client_id} has no Niche defined")

    # Step 1b: Fetch all related data concurrently
    logger.info(f"Fetching data for niche '{niche}'...")
    data = await _fetch_all_data(client_id, niche, client_name=client_name)

    # Step 2: Decide distribution
    distribution = _decide_distribution(batch_type, quantity, data["magnets"])
    logger.info(f"Distribution plan: {distribution}")

    # Step 3: Generate via Ollama
    logger.info(f"Generating {quantity} reels via Ollama...")
    prompt = prompts.build_generation_prompt(
        quantity=quantity,
        client_name=client_name,
        business_info=business_info,
        tone_of_voice=tone_of_voice,
        niche=niche,
        ig_username=ig_username,
        distribution=distribution,
        magnets=data["magnets"],
        style_examples=data["style_examples"],
        hooks=data["hooks"],
        viral_content=data["viral_pool"],
        rtm_events=data["rtm_events"],
        insights=data["insights"],
        folders=folders,
    )

    result = await ollama.generate_json(prompt, system=prompts.SYSTEM_PROMPT)
    generated_reels = result.get("reels", []) if isinstance(result, dict) else []

    if not generated_reels:
        logger.error("Ollama returned no reels")
        raise ValueError("Model did not generate any reels")

    logger.info(f"Ollama generated {len(generated_reels)} reels")

    # Step 4: Save to Airtable Content Queue
    queue_records = [_build_queue_record(r, client_id) for r in generated_reels]

    saved: list[dict] = []
    errors: list[str] = []
    # Save in batches, handling individual failures
    for i, rec in enumerate(queue_records):
        try:
            result_records = await at.save_reels_to_queue([rec])
            saved.extend(result_records)
        except Exception as e:
            logger.error(f"Failed to save reel {i + 1}: {e}")
            errors.append(f"Reel {i + 1}: {str(e)}")

    logger.info(f"Saved {len(saved)}/{len(queue_records)} reels to Content Queue")

    # Step 5: Build response
    response_reels = []
    for i, reel_data in enumerate(generated_reels):
        reel_response = {
            **reel_data,
            "saved": i < len(saved),
            "record_id": saved[i]["id"] if i < len(saved) else None,
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
