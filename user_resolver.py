"""Resolve Supabase user_id to Airtable client_id.

Users register in Lovable with Supabase Auth (email/password).
The same email exists in Airtable's Clients table. This module bridges
the two identity systems by maintaining a cached mapping in Supabase's
user_client_map table, falling back to an Airtable email search on the
first call for any given user.

Supabase table schema:
    user_client_map(user_id UUID PK, client_id TEXT, client_email TEXT, mapped_at TIMESTAMPTZ)
"""

import logging
from urllib.parse import quote

import httpx
from supabase import create_client, Client

import config

logger = logging.getLogger(__name__)

# ── Supabase singleton ───────────────────────────────────────────────────────

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


# ── Airtable constants ───────────────────────────────────────────────────────

_AIRTABLE_BASE_URL = f"https://api.airtable.com/v0/{config.AIRTABLE_BASE_ID}"
_AIRTABLE_HEADERS = {
    "Authorization": f"Bearer {config.AIRTABLE_API_KEY}",
    "Content-Type": "application/json",
}


# ── Public API ───────────────────────────────────────────────────────────────


async def resolve_client_id(user_id: str, user_email: str | None = None) -> str | None:
    """Resolve Supabase user_id to Airtable client record ID.

    Strategy:
    1. Check user_client_map cache table in Supabase.
    2. If not found and email provided: search Airtable Clients by Client Email field.
    3. If not found: search Airtable by Client Name matching the email prefix (e.g. "gayahaelyon" → "גאיה").
    4. If still not found: look up email from Supabase auth, then repeat search.
    5. If found: cache in user_client_map for future calls.
    6. Returns client_id (recXXX) or None.
    """
    # Step 1 — check cache
    cached = await _lookup_cached_mapping(user_id)
    if cached:
        logger.debug(f"Cache hit: user {user_id} -> client {cached}")
        return cached

    # Step 2 — resolve email if not provided
    email = user_email
    if not email:
        email = await get_user_email_from_supabase(user_id)
    if not email:
        logger.warning(f"Cannot resolve client_id: no email for user {user_id}")
        return None

    # Step 3 — search Airtable by Client Email field
    client_id = await _search_airtable_client_by_email(email)

    # Step 4 — fallback: search by display_name in Supabase user metadata
    if not client_id:
        client_id = await _search_airtable_client_by_user_metadata(user_id)

    if not client_id:
        logger.warning(f"No Airtable client found for email {email}")
        return None

    # Step 5 — cache the mapping
    await _cache_mapping(user_id, client_id, email)
    logger.info(f"Resolved and cached: user {user_id} -> client {client_id}")
    return client_id


async def get_user_email_from_supabase(user_id: str) -> str | None:
    """Lookup user email from Supabase auth.users.

    Uses admin API: supabase.auth.admin.get_user_by_id(user_id).
    Returns the email string or None if the user is not found / on error.
    """
    try:
        client = _get_client()
        response = client.auth.admin.get_user_by_id(user_id)
        user = response.user
        if user and user.email:
            return user.email
        logger.warning(f"Supabase user {user_id} has no email")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch Supabase user {user_id}: {e}")
        return None


async def validate_supabase_token(token: str) -> dict | None:
    """Validate a Supabase JWT and return user info.

    Uses Supabase auth.get_user(token) to validate.
    Returns {"user_id": str, "email": str} or None if invalid.
    """
    try:
        client = _get_client()
        response = client.auth.get_user(token)
        user = response.user
        if user:
            return {
                "user_id": user.id,
                "email": user.email,
            }
        return None
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        return None


# ── Internal helpers ─────────────────────────────────────────────────────────


async def _search_airtable_client_by_email(email: str) -> str | None:
    """Search Airtable Clients table for a record matching the email.

    Uses filterByFormula with the Client Email field.
    Returns the record ID (recXXX) or None.
    """
    formula = f"{{Client Email}}='{_escape_airtable_string(email)}'"
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.get(
                f"{_AIRTABLE_BASE_URL}/{config.TABLE_CLIENTS}",
                headers=_AIRTABLE_HEADERS,
                params={
                    "filterByFormula": formula,
                    "maxRecords": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            records = data.get("records", [])
            if records:
                record_id = records[0]["id"]
                logger.info(f"Found Airtable client {record_id} for email {email}")
                return record_id
            return None
    except Exception as e:
        logger.error(f"Airtable client search failed for {email}: {e}")
        return None


async def _lookup_cached_mapping(user_id: str) -> str | None:
    """Check user_client_map in Supabase for an existing mapping."""
    try:
        client = _get_client()
        result = (
            client.table("user_client_map")
            .select("client_id")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if result.data:
            return result.data["client_id"]
        return None
    except Exception as e:
        logger.error(f"Cache lookup failed for user {user_id}: {e}")
        return None


async def _cache_mapping(user_id: str, client_id: str, email: str) -> None:
    """Insert a user_id -> client_id mapping into user_client_map."""
    try:
        client = _get_client()
        client.table("user_client_map").upsert(
            {
                "user_id": user_id,
                "client_id": client_id,
                "client_email": email,
            },
            on_conflict="user_id",
        ).execute()
        logger.debug(f"Cached mapping: {user_id} -> {client_id}")
    except Exception as e:
        # Non-fatal — next call will just search Airtable again
        logger.warning(f"Failed to cache mapping for user {user_id}: {e}")


async def _search_airtable_client_by_user_metadata(user_id: str) -> str | None:
    """Fallback: search Airtable by the user's display_name from Supabase metadata.

    When Client Email is not set in Airtable, we try matching the user's
    display_name (set during Lovable registration) against Client Name.

    ⚠️ This is a risky fallback — display_name can be generic (e.g. "Wendy")
    and may match the wrong client. We request maxRecords=2 to detect
    ambiguity: if 2+ records match, we refuse the match rather than
    pick the wrong client.
    """
    try:
        client = _get_client()
        response = client.auth.admin.get_user_by_id(user_id)
        user = response.user
        if not user:
            return None

        # Check user_metadata.display_name or user_metadata.full_name
        meta = user.user_metadata or {}
        display_name = meta.get("display_name") or meta.get("full_name") or ""
        if not display_name:
            return None

        # Also get the email for context in warning logs
        user_email = user.email or "unknown"

        logger.warning(
            f"CLIENT LOOKUP FALLBACK: email-based search failed, falling back to "
            f"display_name match. user_id={user_id}, email={user_email}, "
            f"display_name='{display_name}'. This may match the wrong client."
        )

        formula = f"{{Client Name}}='{_escape_airtable_string(display_name)}'"
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.get(
                f"{_AIRTABLE_BASE_URL}/{config.TABLE_CLIENTS}",
                headers=_AIRTABLE_HEADERS,
                params={"filterByFormula": formula, "maxRecords": 2},
            )
            resp.raise_for_status()
            records = resp.json().get("records", [])

            if len(records) > 1:
                # Ambiguous match — multiple clients share the same name
                record_ids = [r["id"] for r in records]
                logger.error(
                    f"AMBIGUOUS CLIENT MATCH: display_name='{display_name}' "
                    f"matched {len(records)} clients: {record_ids}. "
                    f"Refusing to pick one. user_id={user_id}, email={user_email}. "
                    f"Fix: set 'Client Email' in Airtable for this user."
                )
                return None

            if records:
                record_id = records[0]["id"]
                logger.warning(
                    f"Name-based match accepted (single result): "
                    f"'{display_name}' -> {record_id}. "
                    f"Consider setting 'Client Email' in Airtable to avoid this fallback."
                )
                return record_id

        return None
    except Exception as e:
        logger.error(f"Name-based client search failed for user {user_id}: {e}")
        return None


async def invalidate_client_mapping(user_id: str) -> bool:
    """Delete cached mapping so it gets re-resolved on next request.

    Use this when a user reports being linked to the wrong client.
    """
    try:
        client = _get_client()
        client.table("user_client_map").delete().eq("user_id", user_id).execute()
        logger.info(f"Invalidated client mapping for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to invalidate mapping for {user_id}: {e}")
        return False


def _escape_airtable_string(value: str) -> str:
    """Escape single quotes for use inside Airtable formula strings."""
    return value.replace("'", "\\'")
