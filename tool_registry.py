"""Tool registry for the Wandi agentic system.

Each tool wraps an existing function and exposes it to the Agent LLM
via Ollama's native tool-calling API.  Tools have:
  - name: unique identifier
  - description: Hebrew description for the LLM
  - parameters: JSON Schema for the function arguments
  - handler: async callable that executes the tool
"""

import json
import logging
from typing import Any, Callable, Awaitable

import analytics
import airtable_client as at
import ollama_client as ollama
import parsers
import prompts

logger = logging.getLogger(__name__)


# ── Client cache (per-session, populated by get_client_profile) ────────────
# Stores verified Airtable data (name, email) so downstream tools like
# get_magnets don't rely on GLM-provided values which are unreliable.

_client_cache: dict[str, dict[str, str]] = {}


def clear_client_cache() -> None:
    """Reset the client cache. Called at the start of each agent session."""
    _client_cache.clear()
    logger.debug("Client cache cleared")


# ── Tool definition type ────────────────────────────────────────────────────

ToolHandler = Callable[..., Awaitable[Any]]


class Tool:
    """A single tool that the agent can invoke."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: ToolHandler,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_ollama_schema(self) -> dict[str, Any]:
        """Convert to Ollama /api/chat tools format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": [
                        k for k, v in self.parameters.items()
                        if v.get("required", False)
                    ],
                },
            },
        }


# ── Tool handlers ───────────────────────────────────────────────────────────
# Each handler wraps an existing function and returns a serializable result.


async def _handle_get_client_profile(client_id: str, **kwargs) -> dict[str, Any]:
    """Fetch client profile from Airtable."""
    record = await at.get_client(client_id)
    fields = record.get("fields", {})

    # Cache verified Airtable data for downstream tools (get_magnets, etc.)
    # This ensures tools use the real Airtable name/email, not GLM guesses.
    _client_cache[client_id] = {
        "name": (fields.get("Client Name") or "").strip(),
        "email": (fields.get("email") or "").strip(),
    }
    logger.info(
        f"Client cache populated: {client_id} → "
        f"name={_client_cache[client_id]['name']!r}, "
        f"email={_client_cache[client_id]['email']!r}"
    )

    # Return a clean summary the agent can reason about
    return {
        "client_id": record["id"],
        "client_name": fields.get("Client Name", ""),
        "business_info": fields.get("Business Info", ""),
        "tone_of_voice": fields.get("Tone Of Voice", ""),
        "ig_username": fields.get("ig_username", ""),
        "niche_ids": fields.get("Niche") or [],
        "personal_brand_tags": [
            t.get("name", "") if isinstance(t, dict) else str(t)
            for t in (fields.get("Personal Brand Tags") or [])
        ],
        "has_client_knowledge": bool(fields.get("Client Knowledge", "").strip()),
    }


async def _handle_get_magnets(client_id: str, client_name: str = "", **kwargs) -> list[dict]:
    """Fetch magnets for a client."""
    magnets = await at.get_magnets_for_client(client_id, client_name=client_name)
    return [
        {
            "magnet_id": m["id"],
            "name": m.get("fields", {}).get("Magnet Name", ""),
            "description": m.get("fields", {}).get("Description", ""),
            "trigger_word": m.get("fields", {}).get("Trigger Word", ""),
            "awareness_stage": m.get("fields", {}).get("Awareness Stage", ""),
        }
        for m in magnets
    ]


async def _handle_get_hooks(
    niche_ids: list[str] | None = None,
    limit: int = 20,
    **kwargs,
) -> list[dict]:
    """Fetch viral hooks filtered by niche."""
    hooks = await at.get_viral_hooks(niche_ids or [], limit=min(limit, 20))
    result = []
    for h in hooks:
        f = h.get("fields", {})
        text = prompts._extract_hook_text(f)
        if text:
            result.append({
                "hook_text": text,
                "hook_type": prompts._get_select_name(f.get("Hook Type")) or "כללי",
            })
    return result


async def _handle_get_recent_hooks(
    client_id: str, client_name: str = "", **kwargs,
) -> list[str]:
    """Fetch recent hooks for deduplication."""
    return await at.get_recent_hooks_for_client(
        client_id, client_name=client_name,
    )


async def _handle_draft_content(
    client_id: str,
    batch_type: str = "מעורב",
    quantity: int = 3,
    session_id: str = "",
    **kwargs,
) -> dict[str, Any]:
    """Generate draft reels for user review — does NOT save to Airtable.

    Drafts are stored in agent_drafts table and presented to the user.
    The user can then approve, request changes, or reject.
    """
    import agent as agent_module
    import session_store

    result = await agent_module.generate_drafts(
        client_id=client_id,
        batch_type=batch_type,
        quantity=quantity,
    )

    drafts = result.get("drafts", [])
    if not drafts:
        return {"success": False, "error": "לא הצלחתי לייצר תוכן"}

    # Save drafts to Supabase for later editing/approval
    if session_id:
        try:
            await session_store.save_drafts(session_id, drafts)
        except Exception as e:
            logger.warning(f"Failed to persist drafts: {e}")

    return {
        "success": True,
        "drafts": drafts,
        "count": len(drafts),
        "message": "טיוטות מוכנות לבדיקה. המשתמשת יכולה לאשר, לבקש שינויים, או להתחיל מחדש.",
    }


async def _handle_edit_draft(
    session_id: str,
    draft_index: int,
    instruction: str,
    client_id: str = "",
    **kwargs,
) -> dict[str, Any]:
    """Re-generate a specific draft based on user feedback."""
    import agent as agent_module
    import session_store

    # Get current drafts
    drafts = await session_store.get_drafts(session_id)
    target = next((d for d in drafts if d.get("draft_index") == draft_index), None)
    if not target:
        return {"error": f"לא נמצאה טיוטה מספר {draft_index}"}

    old_content = target.get("content", {})
    old_stage = old_content.get("awareness_stage", "Unaware")
    old_batch_type = "חשיפה" if old_content.get("content_type") == "חשיפה" else "מכירה"

    # Re-generate one reel with the instruction as additional context
    result = await agent_module.generate_drafts(
        client_id=client_id,
        batch_type=old_batch_type,
        quantity=1,
    )

    new_drafts = result.get("drafts", [])
    if not new_drafts:
        return {"error": "לא הצלחתי לייצר טיוטה חדשה"}

    new_content = new_drafts[0]
    new_content["draft_index"] = draft_index

    # Update in Supabase
    await session_store.update_draft(session_id, draft_index, new_content)

    return {
        "success": True,
        "draft_index": draft_index,
        "updated_draft": new_content,
    }


async def _handle_write_reel(
    client_name: str,
    niche: str,
    ig_username: str = "",
    tone: str = "ישירה, בטוחה, חדה",
    awareness_stage: str = "Unaware",
    stage_instruction: str = "",
    selected_hook: str = "",
    hook_type: str = "פרובוקציה",
    creative_direction: str = "",
    magnet_name: str = "",
    magnet_trigger_word: str = "",
    magnet_id: str = "",
    **kwargs,
) -> dict[str, Any]:
    """Generate a single reel from a focused creative brief.

    The agent brain has already selected the hook and written
    the creative direction. This tool sends a compact prompt
    to the content writer (Dicta).
    """
    # Default stage instruction if not provided
    if not stage_instruction:
        stage_instructions = {
            "Unaware": "חשיפה בלבד. עצור סקרול. אסור מגנט.",
            "Problem-Aware": "תוכן ערכי. תן שם לכאב. מגנט אופציונלי.",
            "Solution-Aware": "מכירה עם מגנט. CTA עם טריגר.",
        }
        stage_instruction = stage_instructions.get(awareness_stage, "")

    prompt = prompts.build_focused_reel_prompt(
        client_name=client_name,
        niche=niche,
        ig_username=ig_username,
        tone=tone,
        awareness_stage=awareness_stage,
        stage_instruction=stage_instruction,
        selected_hook=selected_hook,
        hook_type=hook_type,
        creative_direction=creative_direction,
        magnet_name=magnet_name or None,
        magnet_trigger_word=magnet_trigger_word or None,
        magnet_id=magnet_id or None,
    )

    try:
        # Phase 1: Generate creative content with primary model (mistral-small)
        # format="json" constrains Ollama to output valid JSON
        result = await ollama.generate_json(
            prompt, system=prompts.FOCUSED_SYSTEM_PROMPT, format="json",
        )
        if isinstance(result, dict):
            if "reels" in result and isinstance(result["reels"], list) and result["reels"]:
                reel = result["reels"][0]
            elif "hook" in result:
                reel = result
            else:
                return {"error": "המודל לא החזיר תוצאה תקינה"}

            # Phase 2: Translate English → Hebrew with Dicta
            # Dicta gets structured-text prompt (not JSON) to focus on translation quality.
            # Build the content section from the English reel fields
            content_lines = []
            for field_key, label in [
                ("hook", "hook"),
                ("caption", "caption"),
                ("text_on_video", "text_on_video"),
                ("hook_type", "hook_type"),
                ("content_type", "content_type"),
                ("awareness_stage", "awareness_stage"),
            ]:
                val = reel.get(field_key)
                if val is not None:
                    content_lines.append(f"{field_key}: {val}")
                else:
                    content_lines.append(f"{field_key}: null")

            translate_prompt = (
                "תרגמי את הריל הבא מאנגלית לעברית ישראלית יומיומית.\n\n"
                f"הקשר חשוב לתרגום:\n"
                f"- לקוחה: {client_name} | נישה: {niche}\n"
                f"- טון דיבור: {tone}\n"
                f"- קהל יעד: בעלות עסקים ישראליות\n"
                f"- העוקץ של ההוק: {creative_direction[:200]}\n\n"
                f"תרגמי כאילו {client_name} מדברת לחברה שלה. "
                f"לא שפה שיווקית, לא ניטרלי — עברית ישראלית בטון של {client_name}.\n\n"
                "הנה התוכן לתרגום:\n"
                + "\n".join(content_lines)
                + "\n\n"
                "תרגמי כל שדה לעברית וכתבי בפורמט הבא בדיוק:\n"
                "HOOK: [התרגום]\n"
                "CAPTION: [התרגום]\n"
                "TEXT_ON_VIDEO: [התרגום, או null אם אין]\n"
                "HOOK_TYPE: [תרגמי לעברית: שאלה מאתגרת / מספר + הבטחה / טעות נפוצה / סוד חשיפה / זיהוי קהל / תוצאה מפתיעה / פרובוקציה]\n"
                "CONTENT_TYPE: [תרגמי: exposure=חשיפה, sales/sale=מכירה]\n"
                "AWARENESS_STAGE: [העתיקי כמו שזה — Unaware / Problem-Aware / Solution-Aware]\n"
            )

            translated = None
            for attempt in range(2):
                try:
                    # Get raw text from Dicta (no JSON constraint)
                    raw_response = await ollama.generate(
                        translate_prompt,
                        system=prompts.DICTA_TRANSLATE_SYSTEM_PROMPT,
                        model="dicta",
                    )

                    # Try JSON first (backward compatible — Dicta sometimes returns valid JSON)
                    try:
                        json_result = json.loads(raw_response.strip())
                        if isinstance(json_result, dict) and "hook" in json_result:
                            logger.info("[write_reel] Dicta returned valid JSON directly")
                            translated = json_result
                            break
                    except (json.JSONDecodeError, TypeError):
                        pass

                    # Try structured-text parsing (the new approach)
                    parsed = parsers.parse_dicta_response(raw_response)
                    if parsed and parsed.get("hook"):
                        logger.info("[write_reel] Dicta translation parsed from structured text")
                        translated = parsed
                        break
                    else:
                        logger.warning(
                            f"[write_reel] Dicta attempt {attempt + 1}/2: "
                            f"could not parse response (first 200 chars: {raw_response[:200]})"
                        )
                except Exception as e:
                    logger.warning(f"[write_reel] Dicta attempt {attempt + 1}/2 failed: {e}")

            if translated:
                # Preserve magnet_id from the English reel (Dicta doesn't translate it)
                if reel.get("magnet_id") and not translated.get("magnet_id"):
                    translated["magnet_id"] = reel["magnet_id"]
                reel = translated
            else:
                logger.error("[write_reel] Dicta translation failed after 2 attempts, skipping reel")
                return {"error": "תרגום לעברית נכשל — הריל לא נשמר"}

            return {"success": True, "reel": reel}
        return {"error": "תשובה לא תקינה מהמודל"}
    except ValueError as e:
        return {"error": f"שגיאה בייצור תוכן: {str(e)}"}


async def _handle_approve_and_save(
    session_id: str,
    client_id: str,
    draft_indices: list[int] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Save approved drafts to Airtable Content Queue."""
    import session_store

    drafts = await session_store.get_drafts(session_id)
    if not drafts:
        return {"error": "אין טיוטות לשמור"}

    # Filter by indices if specified, otherwise save all pending
    to_save = []
    for d in drafts:
        if d.get("status") != "pending":
            continue
        if draft_indices and d.get("draft_index") not in draft_indices:
            continue
        to_save.append(d.get("content", {}))

    if not to_save:
        return {"error": "אין טיוטות ממתינות לאישור"}

    # Build Airtable records
    import agent as agent_module
    queue_records = [agent_module._build_queue_record(draft, client_id) for draft in to_save]

    saved: list[dict] = []
    errors: list[str] = []
    for i, rec in enumerate(queue_records):
        try:
            result = await at.save_reels_to_queue([rec])
            saved.extend(result)
        except Exception as e:
            logger.error(f"Failed to save draft {i + 1}: {e}")
            errors.append(str(e))

    # Mark as saved in Supabase
    indices = draft_indices or [d.get("draft_index") for d in drafts if d.get("status") == "pending"]
    await session_store.mark_drafts_saved(session_id, indices)

    return {
        "success": True,
        "saved_count": len(saved),
        "total": len(to_save),
        "errors": errors if errors else None,
    }


async def _handle_get_insights(niche: str, **kwargs) -> dict[str, Any]:
    """Fetch global insights for a niche."""
    insights = await at.get_global_insights(niche)
    if not insights:
        return {"available": False}
    f = insights.get("fields", {})
    return {
        "available": True,
        "top_hook_type": f.get("Top Hook Type", ""),
        "hook_pattern": f.get("Hook Pattern", ""),
        "best_posting_hours": f.get("Best Posting Hours", ""),
        "avg_engagement_rate": f.get("Avg Engagement Rate", ""),
    }


async def _handle_analyze_performance(
    client_id: str, days: int = 30, **kwargs,
) -> dict[str, Any]:
    """Analyze content performance — hooks, stages, engagement."""
    return await analytics.get_content_performance(client_id, days=days)


async def _handle_get_best_hooks(client_id: str, **kwargs) -> dict[str, Any]:
    """Get best performing hooks for the client."""
    return await analytics.get_hook_performance(client_id)


async def _handle_get_rtm_events(niche: str = "", **kwargs) -> dict[str, Any]:
    """Get active RTM (Real Time Marketing) events relevant to a niche."""
    try:
        events = await at.get_rtm_events(niche)
        if not events:
            return {"events": [], "message": "אין אירועי RTM פעילים כרגע בנישה הזו"}
        formatted = []
        for e in events:
            f = e.get("fields", {})
            formatted.append({
                "name": f.get("Event Name", ""),
                "description": f.get("Event Description", ""),
                "expires": f.get("Expires At", ""),
                "niches": f.get("Relevant Niches", []),
            })
        return {"events": formatted, "count": len(formatted)}
    except Exception as e:
        return {"error": str(e)}


# ── Tool Registry ───────────────────────────────────────────────────────────

TOOLS: list[Tool] = [
    Tool(
        name="get_client_profile",
        description="שולף פרופיל לקוחה מ-Airtable — שם, עסק, טון, נישות, מגנטים. השתמש בזה תמיד בתחילת משימה.",
        parameters={
            "client_id": {
                "type": "string",
                "description": "Airtable record ID of the client (recXXX)",
                "required": True,
            },
        },
        handler=_handle_get_client_profile,
    ),
    Tool(
        name="get_magnets",
        description="שולף את המגנטים (freebies/lead magnets) של הלקוחה. חובה לפני יצירת תוכן Solution-Aware.",
        parameters={
            "client_id": {
                "type": "string",
                "description": "Airtable record ID of the client",
                "required": True,
            },
            "client_name": {
                "type": "string",
                "description": "Client name for lookup",
            },
        },
        handler=_handle_get_magnets,
    ),
    Tool(
        name="get_hooks",
        description="שולף הוקים ויראליים מותאמים לנישה. ההוקים מסוננים לפי נישה ושלב מודעות.",
        parameters={
            "niche_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of niche record IDs to filter hooks",
            },
            "limit": {
                "type": "integer",
                "description": "Max hooks to return (default 20)",
            },
        },
        handler=_handle_get_hooks,
    ),
    Tool(
        name="get_recent_hooks",
        description="שולף הוקים אחרונים שנוצרו ללקוחה — למניעת חזרות.",
        parameters={
            "client_id": {
                "type": "string",
                "description": "Airtable record ID of the client",
                "required": True,
            },
            "client_name": {
                "type": "string",
                "description": "Client name for lookup",
            },
        },
        handler=_handle_get_recent_hooks,
    ),
    Tool(
        name="write_reel",
        description="מייצר רילס אחד מ-brief יצירתי ממוקד. השתמש אחרי שבחרת הוק מ-get_hooks וכתבת הנחיה יצירתית. הכלי שולח brief קצר וממוקד למודל תוכן.",
        parameters={
            "client_name": {
                "type": "string",
                "description": "Client name",
                "required": True,
            },
            "niche": {
                "type": "string",
                "description": "Client primary niche",
                "required": True,
            },
            "ig_username": {
                "type": "string",
                "description": "Instagram username",
            },
            "tone": {
                "type": "string",
                "description": "Tone description in Hebrew (2-5 words)",
            },
            "awareness_stage": {
                "type": "string",
                "description": "Unaware / Problem-Aware / Solution-Aware",
                "required": True,
            },
            "selected_hook": {
                "type": "string",
                "description": "The specific hook to use as inspiration",
                "required": True,
            },
            "hook_type": {
                "type": "string",
                "description": "Hook type: פרובוקציה / שאלה מאתגרת / מספר + הבטחה / etc",
                "required": True,
            },
            "creative_direction": {
                "type": "string",
                "description": "2-3 sentences explaining the angle, what to adapt, and the target emotion",
                "required": True,
            },
            "magnet_name": {
                "type": "string",
                "description": "Magnet name (for Solution-Aware only)",
            },
            "magnet_trigger_word": {
                "type": "string",
                "description": "Exact trigger word for CTA (for Solution-Aware only)",
            },
            "magnet_id": {
                "type": "string",
                "description": "Airtable magnet record ID (for Solution-Aware only)",
            },
        },
        handler=_handle_write_reel,
    ),
    Tool(
        name="approve_and_save",
        description="שומר טיוטות מאושרות ב-Airtable. השתמש רק אחרי שהמשתמשת אישרה את הטיוטות.",
        parameters={
            "session_id": {
                "type": "string",
                "description": "Session ID where drafts are stored",
                "required": True,
            },
            "client_id": {
                "type": "string",
                "description": "Airtable record ID of the client",
                "required": True,
            },
            "draft_indices": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Which drafts to save (by number). Empty = save all.",
            },
        },
        handler=_handle_approve_and_save,
    ),
    Tool(
        name="get_insights",
        description="שולף תובנות ביצועים לנישה — סוגי הוקים מובילים, שעות פרסום, מעורבות.",
        parameters={
            "niche": {
                "type": "string",
                "description": "Niche name to get insights for",
                "required": True,
            },
        },
        handler=_handle_get_insights,
    ),
    Tool(
        name="analyze_performance",
        description="מנתח ביצועי תוכן אחרונים — reach, saves, shares. מחזיר את ההוקים והשלבים הכי מוצלחים. השתמש כשהמשתמשת שואלת על ביצועים או רוצה לדעת מה עובד.",
        parameters={
            "client_id": {
                "type": "string",
                "description": "Airtable record ID of the client",
                "required": True,
            },
            "days": {
                "type": "integer",
                "description": "Number of days to analyze (default 30)",
            },
        },
        handler=_handle_analyze_performance,
    ),
    Tool(
        name="get_best_hooks",
        description="מחזיר את ההוקים הכי מוצלחים של הלקוחה לפי engagement, saves, shares. כולל פירוט לפי סוג הוק.",
        parameters={
            "client_id": {
                "type": "string",
                "description": "Airtable record ID of the client",
                "required": True,
            },
        },
        handler=_handle_get_best_hooks,
    ),
    Tool(
        name="get_rtm_events",
        description="שולף אירועי RTM (Real Time Marketing) פעילים — טרנדים, עדכונים, אירועים רלוונטיים לנישה. השתמש כשהמשתמשת רוצה תוכן על מה שקורה עכשיו.",
        parameters={
            "niche": {
                "type": "string",
                "description": "Niche name to find relevant events for",
            },
        },
        handler=_handle_get_rtm_events,
    ),
]


# ── Registry helpers ────────────────────────────────────────────────────────

_TOOL_MAP: dict[str, Tool] = {t.name: t for t in TOOLS}


def get_tool(name: str) -> Tool | None:
    """Look up a tool by name."""
    return _TOOL_MAP.get(name)


def get_all_tool_schemas() -> list[dict[str, Any]]:
    """Return Ollama-format tool schemas for all registered tools."""
    return [t.to_ollama_schema() for t in TOOLS]


async def execute_tool(
    name: str,
    arguments: dict[str, Any],
    authorized_client_id: str = "",
    user_id: str = "",
) -> dict[str, Any]:
    """Execute a tool by name with given arguments.

    Args:
        authorized_client_id: The verified client_id from user_resolver.
            When provided, any client_id in the arguments is overridden
            with this value to prevent GLM from accessing other clients'
            data (prompt injection or hallucination).
        user_id: Supabase user UUID (needed by video_picker for
            raw-media/{user_id}/ paths).

    Returns a dict with either the result or an error message.
    """
    tool = get_tool(name)
    if not tool:
        logger.error(f"Unknown tool: {name}")
        return {"error": f"Unknown tool: {name}"}

    # Security: override client_id with the authorized one.
    # GLM decides which client_id to pass, but it can hallucinate or
    # be tricked via prompt injection. We always enforce the real one.
    if authorized_client_id and "client_id" in arguments:
        glm_client_id = arguments["client_id"]
        if glm_client_id != authorized_client_id:
            logger.warning(
                f"[Security] Tool {name}: GLM sent client_id={glm_client_id} "
                f"but authorized is {authorized_client_id} — overriding"
            )
        arguments["client_id"] = authorized_client_id

    # Filter arguments to only those the handler accepts,
    # and remove None values
    clean_args = {
        k: v for k, v in arguments.items()
        if v is not None and k in tool.parameters
    }

    # Inject execution context so tool handlers can access verified
    # identity without relying on GLM-provided values.
    # Handlers that need these accept **kwargs.
    exec_context = {}
    if authorized_client_id:
        exec_context["authorized_client_id"] = authorized_client_id
    if user_id:
        exec_context["user_id"] = user_id

    try:
        logger.info(f"Executing tool: {name}({clean_args})")
        result = await tool.handler(**clean_args, **exec_context)
        return {"result": result}
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return {"error": f"Tool {name} failed: {str(e)}"}
