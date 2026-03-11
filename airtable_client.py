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


async def _fetch_all(
    table: str,
    formula: str | None = None,
    fields: list[str] | None = None,
    sort: list[dict] | None = None,
) -> list[dict[str, Any]]:
    """Fetch all records from an Airtable table, handling pagination."""
    records: list[dict[str, Any]] = []
    offset: str | None = None

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params: dict[str, Any] = {}
            if formula:
                params["filterByFormula"] = formula
            if fields:
                for f in fields:
                    params.setdefault("fields[]", [])
                if fields:
                    params["fields[]"] = fields
            if sort:
                for i, s in enumerate(sort):
                    params[f"sort[{i}][field]"] = s["field"]
                    params[f"sort[{i}][direction]"] = s.get("direction", "asc")
            if offset:
                params["offset"] = offset

            resp = await client.get(
                f"{BASE_URL}/{table}", headers=HEADERS, params=params
            )
            resp.raise_for_status()
            data = resp.json()

            records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break

    logger.info(f"Fetched {len(records)} records from {table}")
    return records


async def _create_record(table: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Create a single record in an Airtable table."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/{table}",
            headers=HEADERS,
            json={"fields": fields},
        )
        resp.raise_for_status()
        return resp.json()


async def _create_records_batch(
    table: str, records_fields: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Create records in batches of 10 (Airtable limit)."""
    created: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=60) as client:
        for i in range(0, len(records_fields), 10):
            batch = records_fields[i : i + 10]
            payload = {"records": [{"fields": f} for f in batch]}
            resp = await client.post(
                f"{BASE_URL}/{table}",
                headers=HEADERS,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            created.extend(data.get("records", []))
            logger.info(f"Created batch of {len(batch)} records in {table}")
    return created


# ── Client ────────────────────────────────────────────────────────────────────


async def get_client(client_id: str) -> dict[str, Any]:
    """Fetch a single client by record ID."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/{config.TABLE_CLIENTS}/{client_id}", headers=HEADERS
        )
        resp.raise_for_status()
        record = resp.json()
    logger.info(f"Fetched client: {record['fields'].get('Client Name', client_id)}")
    return record


# ── Magnets ───────────────────────────────────────────────────────────────────


async def get_magnets_for_client(client_id: str, client_name: str = "") -> list[dict[str, Any]]:
    """Fetch all magnets linked to a client."""
    if client_name:
        formula = f"FIND('{client_name}', ARRAYJOIN({{Client Name}}))"
    else:
        formula = f"FIND('{client_id}', ARRAYJOIN({{Client}}))"
    return await _fetch_all(config.TABLE_MAGNETS, formula=formula)


# ── Viral Hooks ───────────────────────────────────────────────────────────────


async def get_viral_hooks(niche: str) -> list[dict[str, Any]]:
    """Fetch viral hooks — filtered by niche if tagged, otherwise fetch all."""
    formula = f"FIND('{niche}', ARRAYJOIN({{Relevant Niches}}))"
    records = await _fetch_all(config.TABLE_VIRAL_HOOKS, formula=formula)
    if records:
        return records
    # Fallback: most hooks are untagged, fetch all
    logger.info("No niche-filtered hooks found, fetching all hooks")
    return await _fetch_all(config.TABLE_VIRAL_HOOKS)


# ── Viral Content Pool ───────────────────────────────────────────────────────


async def get_viral_content_pool(niche: str) -> list[dict[str, Any]]:
    """Fetch viral content pool filtered by status=New."""
    formula = "{Status}='New'"
    return await _fetch_all(
        config.TABLE_VIRAL_CONTENT_POOL,
        formula=formula,
        sort=[{"field": "Views Count", "direction": "desc"}],
    )


# ── RTM Events ───────────────────────────────────────────────────────────────


async def get_active_rtm_events(niche: str) -> list[dict[str, Any]]:
    """Fetch active RTM events for a niche."""
    formula = (
        f"AND(FIND('{niche}', ARRAYJOIN({{Relevant Niches}})), {{Status}}='Active')"
    )
    return await _fetch_all(config.TABLE_RTM_EVENTS, formula=formula)


# ── Reel Templates ────────────────────────────────────────────────────────────


async def get_reel_templates(
    content_type: str | None = None, awareness_stage: str | None = None
) -> list[dict[str, Any]]:
    """Fetch reel templates, optionally filtered."""
    parts: list[str] = []
    if content_type:
        parts.append(f"{{Content Type}}='{content_type}'")
    if awareness_stage:
        parts.append(f"{{Awareness Stage}}='{awareness_stage}'")
    formula = f"AND({','.join(parts)})" if len(parts) > 1 else (parts[0] if parts else None)
    return await _fetch_all(config.TABLE_REEL_TEMPLATES, formula=formula)


# ── Client Style Bank ────────────────────────────────────────────────────────


async def get_top_style_examples(client_id: str, client_name: str = "", limit: int = 5) -> list[dict[str, Any]]:
    """Fetch top-performing style examples for a client."""
    if client_name:
        client_filter = f"FIND('{client_name}', ARRAYJOIN({{Client}}))"
    else:
        client_filter = f"FIND('{client_id}', ARRAYJOIN({{Client}}))"
    formula = f"AND({client_filter}, {{Is Top Performer}}=TRUE())"
    records = await _fetch_all(
        config.TABLE_CLIENT_STYLE_BANK,
        formula=formula,
        sort=[{"field": "Performance Score", "direction": "desc"}],
    )
    return records[:limit]


# ── Global Insights ───────────────────────────────────────────────────────────


async def get_global_insights(niche: str) -> dict[str, Any] | None:
    """Fetch global insights for a niche."""
    formula = f"{{Niche}}='{niche}'"
    records = await _fetch_all(config.TABLE_GLOBAL_INSIGHTS, formula=formula)
    if records:
        return records[0]
    return None


# ── Content Queue ─────────────────────────────────────────────────────────────


async def save_reels_to_queue(
    reels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Save generated reels to the Content Queue table."""
    return await _create_records_batch(config.TABLE_CONTENT_QUEUE, reels)


async def update_content_queue_video_attachment(record_id: str, video_url: str) -> dict[str, Any]:
    """Add rendered video URL as attachment on a Content Queue record.

    Airtable fetches the file from the URL and stores its own copy.
    The URL must be publicly accessible (no auth required).

    Args:
        record_id: Airtable record ID (e.g. "recXXX").
        video_url: Public URL of the rendered video.

    Returns:
        Updated Airtable record as a dict.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(
            f"{BASE_URL}/{config.TABLE_CONTENT_QUEUE}/{record_id}",
            headers=HEADERS,
            json={"fields": {"Rendered Video": [{"url": video_url}]}},
        )
        resp.raise_for_status()
        logger.info(f"Updated Content Queue {record_id} with video attachment")
        return resp.json()
