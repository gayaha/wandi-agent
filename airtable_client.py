import logging
from typing import Any

import httpx

import config
from renderer.models import BrandConfig

logger = logging.getLogger(__name__)

BASE_URL = f"https://api.airtable.com/v0/{config.AIRTABLE_BASE_ID}"
HEADERS = {
    "Authorization": f"Bearer {config.AIRTABLE_API_KEY}",
    "Content-Type": "application/json",
}


def _escape_airtable_string(value: str) -> str:
    """Escape single quotes for use inside Airtable FIND() formulas."""
    return value.replace("'", "\\'")


async def _fetch_all(
    table: str,
    formula: str | None = None,
    fields: list[str] | None = None,
    sort: list[dict] | None = None,
    max_records: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch records from an Airtable table, handling pagination.

    Args:
        max_records: If set, Airtable limits the total number of records
                     returned.  This avoids pagination for large tables
                     when only a sample is needed (e.g. viral hooks).
    """
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
            if max_records is not None:
                params["maxRecords"] = max_records
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

            # Stop early if we already have enough records
            if max_records is not None and len(records) >= max_records:
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
            if resp.status_code >= 400:
                logger.error(
                    f"Airtable API error {resp.status_code} for {table}: {resp.text}"
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
        safe = _escape_airtable_string(client_name)
        formula = f"FIND('{safe}', ARRAYJOIN({{Client Name}}))"
    else:
        safe = _escape_airtable_string(client_id)
        formula = f"FIND('{safe}', ARRAYJOIN({{Client}}))"
    return await _fetch_all(config.TABLE_MAGNETS, formula=formula)


# ── Viral Hooks ───────────────────────────────────────────────────────────────


async def get_viral_hooks(client_id: str, client_name: str = "", limit: int = 25) -> list[dict[str, Any]]:
    """Fetch viral hooks — filtered by client if tagged, otherwise fetch general (capped).

    The Viral Hooks table uses a "Clients" linked-record field (not "Client Name").
    FIND/ARRAYJOIN doesn't work reliably on linked records, so we fetch all hooks
    and filter in Python by checking if the client's record ID appears in the
    Clients field (which Airtable returns as a list of record IDs).

    Caps results to `limit` to avoid fetching 100+ hooks when only ~15 are used.
    """
    all_hooks = await _fetch_all(config.TABLE_VIRAL_HOOKS)
    # Filter hooks where this client's record ID is in the Clients linked-record list
    client_hooks = [
        r for r in all_hooks
        if client_id in (r.get("fields", {}).get("Clients") or [])
    ]
    if client_hooks:
        logger.info(f"Found {len(client_hooks)} client-specific hooks for {client_id}")
        return client_hooks[:limit]
    # Fallback: no client-specific hooks, fetch capped sample
    logger.info("No client-filtered hooks found, returning general hooks (capped)")
    return all_hooks[:limit]


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
    safe = _escape_airtable_string(niche)
    formula = (
        f"AND(FIND('{safe}', ARRAYJOIN({{Relevant Niches}})), {{Status}}='Active')"
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
        safe = _escape_airtable_string(client_name)
        client_filter = f"FIND('{safe}', ARRAYJOIN({{Client}}))"
    else:
        safe = _escape_airtable_string(client_id)
        client_filter = f"FIND('{safe}', ARRAYJOIN({{Client}}))"
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
    safe = _escape_airtable_string(niche)
    formula = f"{{Niche}}='{safe}'"
    records = await _fetch_all(config.TABLE_GLOBAL_INSIGHTS, formula=formula)
    if records:
        return records[0]
    return None


# ── Recent Hooks (deduplication) ─────────────────────────────────────────────


async def get_recent_hooks_for_client(
    client_id: str, client_name: str = "", limit: int = 20
) -> list[str]:
    """Fetch recent hook texts from Content Queue for deduplication."""
    try:
        if client_name:
            safe = _escape_airtable_string(client_name)
            client_filter = f"FIND('{safe}', ARRAYJOIN({{Client Name}}))"
        else:
            safe = _escape_airtable_string(client_id)
            client_filter = f"FIND('{safe}', ARRAYJOIN({{Client}}))"
        formula = f"AND({client_filter}, {{Source}}='wandi-agent')"
        records = await _fetch_all(
            config.TABLE_CONTENT_QUEUE,
            formula=formula,
            fields=["Hook"],
        )
        # No sort → Airtable returns oldest-first; take the tail for most recent
        return [
            r["fields"].get("Hook", "")
            for r in records[-limit:]
            if r.get("fields", {}).get("Hook")
        ]
    except Exception as e:
        logger.warning(f"Failed to fetch recent hooks for dedup: {e}")
        return []


# ── Content Queue ─────────────────────────────────────────────────────────────


async def save_reels_to_queue(
    reels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Save pre-mapped reel records to the Content Queue table.

    Expects records with Airtable field names (e.g. from agent._build_queue_record).
    Records are passed through directly without remapping.
    """
    return await _create_records_batch(config.TABLE_CONTENT_QUEUE, reels)


def extract_brand_config(client_record: dict[str, Any]) -> BrandConfig:
    """Extract and validate a BrandConfig from an Airtable client record.

    Maps Airtable field names to BrandConfig snake_case field names.
    Skips None and empty-string values (treats them as absent).
    Falls back to BrandConfig() all-defaults on any validation error.

    Args:
        client_record: Airtable record dict with {"id": ..., "fields": {...}}.

    Returns:
        BrandConfig populated from Airtable data, or all-defaults on error.
    """
    _FIELD_MAP = {
        "Brand Primary Color": "primary_color",
        "Brand Secondary Color": "secondary_color",
        "Brand Font Family": "font_family",
        "Brand Hook Font Size": "hook_font_size",
        "Brand Body Font Size": "body_font_size",
        "Brand Overlay Color": "overlay_color",
        "Brand Overlay Opacity": "overlay_opacity",
        "Brand Border Radius": "border_radius",
        "Brand Text Position": "text_position",
        "Brand Text Align": "text_align",
    }

    fields = client_record.get("fields", {})
    raw: dict[str, Any] = {}

    for airtable_field, model_field in _FIELD_MAP.items():
        value = fields.get(airtable_field)
        # Skip None and empty strings — treat as absent (use default)
        if value is None or value == "":
            continue
        raw[model_field] = value

    try:
        return BrandConfig(**raw)
    except Exception as e:
        record_id = client_record.get("id", "unknown")
        logger.warning(
            f"Failed to extract BrandConfig for client {record_id}: {e}. "
            "Using all defaults."
        )
        return BrandConfig()


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
            json={"fields": {"Final Video": [{"url": video_url}]}},
        )
        resp.raise_for_status()
        logger.info(f"Updated Content Queue {record_id} with video attachment")
        return resp.json()
