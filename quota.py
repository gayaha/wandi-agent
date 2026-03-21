"""Usage quota management for Wandi agent.

Tracks daily message and generation limits per user plan.
Table: user_quotas(id UUID, user_id UUID, period_start DATE,
                   messages_used INT, generations_used INT, plan TEXT)

Fail-open: if Supabase is unreachable, users are never blocked.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from supabase import create_client, Client

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Plan limits
# ---------------------------------------------------------------------------

PLAN_LIMITS: dict[str, dict[str, int]] = {
    "basic":     {"messages_per_day": 30,  "generations_per_day": 10},
    "pro":       {"messages_per_day": 100, "generations_per_day": 30},
    "unlimited": {"messages_per_day": 500, "generations_per_day": 100},
}

DEFAULT_PLAN = "basic"
TABLE = "user_quotas"

# ---------------------------------------------------------------------------
# Supabase singleton (mirrors supabase_client.py)
# ---------------------------------------------------------------------------

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _next_reset_iso() -> str:
    """ISO timestamp of next UTC midnight (quota reset boundary)."""
    tomorrow = _today_utc() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc).isoformat()


def _limits_for_plan(plan: str) -> dict[str, int]:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[DEFAULT_PLAN])


def _fail_open_status() -> QuotaStatus:
    """Default status when Supabase is unreachable -- allow the request."""
    limits = _limits_for_plan(DEFAULT_PLAN)
    return QuotaStatus(
        allowed=True,
        plan=DEFAULT_PLAN,
        messages_used=0,
        messages_limit=limits["messages_per_day"],
        generations_used=0,
        generations_limit=limits["generations_per_day"],
        reset_time=_next_reset_iso(),
    )


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class QuotaStatus:
    allowed: bool
    plan: str
    messages_used: int
    messages_limit: int
    generations_used: int
    generations_limit: int
    reset_time: str  # ISO timestamp of next day start


# ---------------------------------------------------------------------------
# Core: ensure a quota row exists for today (upsert)
# ---------------------------------------------------------------------------

def _ensure_today_row(client: Client, user_id: str) -> dict:
    """Return the quota row for today, creating one via upsert if needed.

    Uses ON CONFLICT (user_id, period_start) so concurrent calls are safe.
    """
    today = _today_utc().isoformat()

    # Try fetching first (fast path -- avoids upsert overhead on every call)
    try:
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("period_start", today)
            .maybe_single()
            .execute()
        )
        if resp and resp.data:
            return resp.data
    except Exception as e:
        logger.debug(f"Quota fetch failed (will upsert): {e}")

    # Row doesn't exist yet -- upsert with zeros
    row = {
        "user_id": user_id,
        "period_start": today,
        "messages_used": 0,
        "generations_used": 0,
        "plan": DEFAULT_PLAN,
    }
    try:
        resp = (
            client.table(TABLE)
            .upsert(row, on_conflict="user_id,period_start")
            .execute()
        )
        return resp.data[0] if resp and resp.data else row
    except Exception as e:
        logger.warning(f"Quota upsert failed: {e}")
        return row


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def check_quota(user_id: str) -> QuotaStatus:
    """Check if user has remaining quota for today.

    If no quota record exists for today, create one (UPSERT).
    Returns QuotaStatus with allowed=True/False.
    """
    try:
        client = _get_client()
        row = _ensure_today_row(client, user_id)

        plan = row.get("plan") or DEFAULT_PLAN
        limits = _limits_for_plan(plan)
        messages_used = row.get("messages_used", 0)
        generations_used = row.get("generations_used", 0)

        allowed = (
            messages_used < limits["messages_per_day"]
            and generations_used < limits["generations_per_day"]
        )

        return QuotaStatus(
            allowed=allowed,
            plan=plan,
            messages_used=messages_used,
            messages_limit=limits["messages_per_day"],
            generations_used=generations_used,
            generations_limit=limits["generations_per_day"],
            reset_time=_next_reset_iso(),
        )
    except Exception as exc:
        logger.error(f"Quota check failed for {user_id}, defaulting to allow: {exc}")
        return _fail_open_status()


async def consume_message(user_id: str) -> None:
    """Increment messages_used for today. Called after successful agent response."""
    try:
        client = _get_client()
        row = _ensure_today_row(client, user_id)
        row_id = row.get("id")
        if not row_id:
            logger.warning(f"No quota row ID for {user_id}, skipping consume")
            return
        new_count = row.get("messages_used", 0) + 1
        (
            client.table(TABLE)
            .update({"messages_used": new_count})
            .eq("id", row_id)
            .execute()
        )
        logger.debug(f"User {user_id} messages_used -> {new_count}")
    except Exception as exc:
        logger.error(f"Failed to consume message quota for {user_id}: {exc}")


async def consume_generation(user_id: str, count: int = 1) -> None:
    """Increment generations_used. Called when generate_reel/batch tool runs."""
    try:
        client = _get_client()
        row = _ensure_today_row(client, user_id)
        row_id = row.get("id")
        if not row_id:
            logger.warning(f"No quota row ID for {user_id}, skipping generation consume")
            return
        new_count = row.get("generations_used", 0) + count
        (
            client.table(TABLE)
            .update({"generations_used": new_count})
            .eq("id", row_id)
            .execute()
        )
        logger.debug(f"User {user_id} generations_used -> {new_count}")
    except Exception as exc:
        logger.error(f"Failed to consume generation quota for {user_id}: {exc}")


async def get_quota_status(user_id: str) -> dict:
    """Return quota info as dict for API response (frontend display)."""
    status = await check_quota(user_id)
    return {
        "allowed": status.allowed,
        "plan": status.plan,
        "messages": {
            "used": status.messages_used,
            "limit": status.messages_limit,
            "remaining": max(0, status.messages_limit - status.messages_used),
        },
        "generations": {
            "used": status.generations_used,
            "limit": status.generations_limit,
            "remaining": max(0, status.generations_limit - status.generations_used),
        },
        "reset_time": status.reset_time,
    }
