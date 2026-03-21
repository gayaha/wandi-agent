"""Tool registry for the Wandi agentic system.

Each tool wraps an existing function and exposes it to the Agent LLM
via Ollama's native tool-calling API.  Tools have:
  - name: unique identifier
  - description: Hebrew description for the LLM
  - parameters: JSON Schema for the function arguments
  - handler: async callable that executes the tool
"""

import logging
from typing import Any, Callable, Awaitable

import analytics
import airtable_client as at
import ollama_client as ollama
import prompts

logger = logging.getLogger(__name__)


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


async def _handle_get_client_profile(client_id: str) -> dict[str, Any]:
    """Fetch client profile from Airtable."""
    record = await at.get_client(client_id)
    fields = record.get("fields", {})
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


async def _handle_get_magnets(client_id: str, client_name: str = "") -> list[dict]:
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
) -> list[dict]:
    """Fetch viral hooks filtered by niche."""
    hooks = await at.get_viral_hooks(niche_ids or [], limit=limit)
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
    client_id: str, client_name: str = "",
) -> list[str]:
    """Fetch recent hooks for deduplication."""
    return await at.get_recent_hooks_for_client(
        client_id, client_name=client_name,
    )


async def _handle_generate_reel(
    client_id: str,
    awareness_stage: str,
    batch_type: str = "מעורב",
    content_category: str = "niche",
) -> dict[str, Any]:
    """Generate a single reel using the existing pipeline.

    This wraps the full single-reel generation flow: fetch data, build
    prompt, call content LLM, validate, and save to Airtable.
    """
    # Import here to avoid circular imports at module level
    import agent as agent_module

    result = await agent_module.generate_reels(
        client_id=client_id,
        batch_type=batch_type,
        quantity=1,
        content_mix={content_category: 1.0},
    )
    reels = result.get("reels", [])
    if reels:
        return {
            "success": True,
            "reel": reels[0],
            "saved": reels[0].get("saved", False),
            "record_id": reels[0].get("record_id"),
        }
    return {"success": False, "error": "Failed to generate reel"}


async def _handle_generate_batch(
    client_id: str,
    batch_type: str = "מעורב",
    quantity: int = 5,
    content_mix: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Generate a batch of reels using the existing pipeline."""
    import agent as agent_module

    return await agent_module.generate_reels(
        client_id=client_id,
        batch_type=batch_type,
        quantity=quantity,
        content_mix=content_mix or {"niche": 1.0},
    )


async def _handle_get_insights(niche: str) -> dict[str, Any]:
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
    client_id: str, days: int = 30,
) -> dict[str, Any]:
    """Analyze content performance — hooks, stages, engagement."""
    return await analytics.get_content_performance(client_id, days=days)


async def _handle_get_best_hooks(client_id: str) -> dict[str, Any]:
    """Get best performing hooks for the client."""
    return await analytics.get_hook_performance(client_id)


async def _handle_get_rtm_events(niche: str = "") -> dict[str, Any]:
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
        name="generate_reel",
        description="מייצר רילס אחד — כולל הוק, טקסט, קפשן — ושומר אוטומטית ב-Airtable.",
        parameters={
            "client_id": {
                "type": "string",
                "description": "Airtable record ID of the client",
                "required": True,
            },
            "awareness_stage": {
                "type": "string",
                "description": "SDMF stage: Unaware / Problem-Aware / Solution-Aware",
                "required": True,
            },
            "batch_type": {
                "type": "string",
                "description": "חשיפה / מכירה / מעורב (default: מעורב)",
            },
            "content_category": {
                "type": "string",
                "description": "niche / personal brand (default: niche)",
            },
        },
        handler=_handle_generate_reel,
    ),
    Tool(
        name="generate_batch",
        description="מייצר באצ' של רילסים (1-30) ושומר ב-Airtable. השתמש כשהמשתמשת מבקשת כמות.",
        parameters={
            "client_id": {
                "type": "string",
                "description": "Airtable record ID of the client",
                "required": True,
            },
            "batch_type": {
                "type": "string",
                "description": "חשיפה / מכירה / מעורב",
                "required": True,
            },
            "quantity": {
                "type": "integer",
                "description": "Number of reels to generate (1-30)",
                "required": True,
            },
            "content_mix": {
                "type": "object",
                "description": 'Content category ratio, e.g. {"niche": 0.6, "personal brand": 0.4}',
            },
        },
        handler=_handle_generate_batch,
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


async def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool by name with given arguments.

    Returns a dict with either the result or an error message.
    """
    tool = get_tool(name)
    if not tool:
        logger.error(f"Unknown tool: {name}")
        return {"error": f"Unknown tool: {name}"}

    # Filter arguments to only those the handler accepts,
    # and remove None values
    clean_args = {
        k: v for k, v in arguments.items()
        if v is not None and k in tool.parameters
    }

    try:
        logger.info(f"Executing tool: {name}({clean_args})")
        result = await tool.handler(**clean_args)
        return {"result": result}
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return {"error": f"Tool {name} failed: {str(e)}"}
