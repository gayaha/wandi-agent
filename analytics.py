"""Performance analytics tools for the Wandi agent.

Provides tools that analyze content performance from Airtable's Content Queue
and return structured insights the agent can use for data-driven decisions.

NOTE: Full analytics require the Learning Loop (n8n → Meta Insights → Content Queue)
to populate performance fields. Until then, tools return partial data with clear messages.
"""

import logging
from typing import Any

import httpx

import config

logger = logging.getLogger(__name__)

BASE_URL = f"https://api.airtable.com/v0/{config.AIRTABLE_BASE_ID}"
HEADERS = {
    "Authorization": f"Bearer {config.AIRTABLE_API_KEY}",
    "Content-Type": "application/json",
}

# Performance fields we expect in Content Queue (populated by Learning Loop)
_PERFORMANCE_FIELDS = [
    "hook", "Hook Type", "awareness_stage", "content_type",
    "Status", "Client Name", "Reach", "Saves", "Shares",
    "Engagement Rate", "Views", "created_at",
]


async def _fetch_content_queue(
    client_id: str | None = None,
    client_name: str | None = None,
    status: str | None = None,
    max_records: int = 100,
) -> list[dict[str, Any]]:
    """Fetch records from Content Queue with optional filters."""
    parts: list[str] = []

    if client_name:
        safe_name = client_name.replace("'", "\\'")
        parts.append(f"{{Client Name}}='{safe_name}'")
    if status:
        parts.append(f"{{Status}}='{status}'")

    formula = None
    if parts:
        formula = f"AND({','.join(parts)})" if len(parts) > 1 else parts[0]

    params: dict[str, Any] = {"maxRecords": max_records}
    if formula:
        params["filterByFormula"] = formula
    params["fields[]"] = _PERFORMANCE_FIELDS

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{BASE_URL}/{config.TABLE_CONTENT_QUEUE}",
                headers=HEADERS,
                params=params,
            )
            resp.raise_for_status()
            return resp.json().get("records", [])
    except Exception as e:
        logger.error(f"Failed to fetch Content Queue: {e}")
        return []


async def get_content_performance(client_id: str, days: int = 30) -> dict[str, Any]:
    """Analyze recent content performance for a client.

    Returns:
        - total_published: how many reels were published
        - avg_reach, avg_saves, avg_shares: average metrics
        - best_hooks: top performing hooks
        - best_stages: which SDMF stages performed best
        - has_data: whether performance data is actually available
    """
    import airtable_client as at

    # First get client name for filtering
    try:
        client_record = await at.get_client(client_id)
        client_name = client_record.get("fields", {}).get("Client Name", "")
    except Exception:
        client_name = ""

    records = await _fetch_content_queue(
        client_name=client_name,
        status="Published",
        max_records=50,
    )

    if not records:
        return {
            "has_data": False,
            "message": "אין עדיין נתוני ביצועים. הנתונים יתעדכנו אחרי שהLearning Loop יהיה פעיל.",
            "total_published": 0,
        }

    # Analyze performance
    total = len(records)
    reaches = []
    saves = []
    shares = []
    hooks_performance: list[dict] = []
    stage_stats: dict[str, dict] = {}

    for rec in records:
        f = rec.get("fields", {})
        reach = f.get("Reach", 0) or 0
        save = f.get("Saves", 0) or 0
        share = f.get("Shares", 0) or 0

        if reach:
            reaches.append(reach)
        if save:
            saves.append(save)
        if share:
            shares.append(share)

        hook = f.get("hook", "")
        if hook and (reach or save or share):
            hooks_performance.append({
                "hook": hook,
                "reach": reach,
                "saves": save,
                "shares": share,
                "score": reach + (save * 5) + (share * 10),  # weighted score
            })

        stage = f.get("awareness_stage", "Unknown")
        if stage not in stage_stats:
            stage_stats[stage] = {"count": 0, "total_reach": 0, "total_saves": 0}
        stage_stats[stage]["count"] += 1
        stage_stats[stage]["total_reach"] += reach
        stage_stats[stage]["total_saves"] += save

    # Sort hooks by score, return top 5
    hooks_performance.sort(key=lambda h: h["score"], reverse=True)
    best_hooks = hooks_performance[:5]

    # Calculate stage effectiveness
    best_stages = []
    for stage, stats in stage_stats.items():
        count = stats["count"]
        if count > 0:
            best_stages.append({
                "stage": stage,
                "count": count,
                "avg_reach": round(stats["total_reach"] / count),
                "avg_saves": round(stats["total_saves"] / count),
            })
    best_stages.sort(key=lambda s: s["avg_reach"], reverse=True)

    has_real_data = bool(reaches)

    return {
        "has_data": has_real_data,
        "total_published": total,
        "avg_reach": round(sum(reaches) / len(reaches)) if reaches else 0,
        "avg_saves": round(sum(saves) / len(saves)) if saves else 0,
        "avg_shares": round(sum(shares) / len(shares)) if shares else 0,
        "best_hooks": best_hooks,
        "best_stages": best_stages,
        "message": "" if has_real_data else "נתוני ביצועים חלקיים — ה-Learning Loop עדיין לא פעיל.",
    }


async def get_hook_performance(client_id: str) -> dict[str, Any]:
    """Analyze which hooks performed best for a client.

    Returns top hooks sorted by engagement score, with type breakdown.
    """
    import airtable_client as at

    try:
        client_record = await at.get_client(client_id)
        client_name = client_record.get("fields", {}).get("Client Name", "")
    except Exception:
        client_name = ""

    records = await _fetch_content_queue(
        client_name=client_name,
        status="Published",
        max_records=100,
    )

    if not records:
        return {
            "has_data": False,
            "message": "אין נתוני ביצועים להוקים עדיין.",
            "hooks": [],
            "type_breakdown": {},
        }

    # Analyze hooks
    hooks: list[dict] = []
    type_counts: dict[str, dict] = {}

    for rec in records:
        f = rec.get("fields", {})
        hook = f.get("hook", "")
        hook_type = f.get("Hook Type", "כללי")
        reach = f.get("Reach", 0) or 0
        saves = f.get("Saves", 0) or 0
        shares = f.get("Shares", 0) or 0
        score = reach + (saves * 5) + (shares * 10)

        if hook:
            hooks.append({
                "hook": hook,
                "type": hook_type,
                "reach": reach,
                "saves": saves,
                "shares": shares,
                "score": score,
            })

        # Type breakdown
        if hook_type not in type_counts:
            type_counts[hook_type] = {"count": 0, "total_score": 0}
        type_counts[hook_type]["count"] += 1
        type_counts[hook_type]["total_score"] += score

    hooks.sort(key=lambda h: h["score"], reverse=True)

    # Average score per type
    type_breakdown = {
        t: {
            "count": stats["count"],
            "avg_score": round(stats["total_score"] / stats["count"]) if stats["count"] else 0,
        }
        for t, stats in type_counts.items()
    }

    has_real_data = any(h["score"] > 0 for h in hooks)

    return {
        "has_data": has_real_data,
        "top_hooks": hooks[:10],
        "type_breakdown": type_breakdown,
        "total_analyzed": len(hooks),
        "message": "" if has_real_data else "נמצאו הוקים אבל בלי נתוני ביצועים — ה-Learning Loop עדיין לא פעיל.",
    }
