"""Usage quota management for Wandi agent.

Tracks daily message and generation limits per user plan.
Table: user_quotas(id UUID, user_id UUID, period_start DATE,
                   messages_used INT, generations_used INT, plan TEXT)

Fail-open policy: if Supabase is completely unreachable after both
SELECT + UPSERT attempts, we allow the request but log an ERROR
with full context for monitoring.
"""

from __future__ import annotations

import asyncio
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


FAIL_OPEN_LIMITS = {"messages_per_day": 5, "generations_per_day": 3}


def _fail_open_status(user_id: str = "unknown", reason: str = "") -> QuotaStatus:
    """Last-resort fallback when Supabase is completely unreachable.

    Allows the request to avoid blocking paying users during outages,
    but with a severely reduced cap (5 messages, 3 generations) so that
    abuse is limited even without real quota tracking.
    Logs at ERROR level so we can monitor and investigate.
    """
    logger.error(
        f"QUOTA FAIL-OPEN: user_id={user_id}, reason={reason}. "
        f"Request allowed with reduced limits "
        f"(msgs={FAIL_OPEN_LIMITS['messages_per_day']}, "
        f"gens={FAIL_OPEN_LIMITS['generations_per_day']}). "
        f"If this recurs, check Supabase connectivity and user_quotas table."
    )
    return QuotaStatus(
        allowed=True,
        plan=DEFAULT_PLAN,
        messages_used=0,
        messages_limit=FAIL_OPEN_LIMITS["messages_per_day"],
        generations_used=0,
        generations_limit=FAIL_OPEN_LIMITS["generations_per_day"],
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

    Raises:
        RuntimeError: If both SELECT and UPSERT fail (Supabase unreachable).
    """
    today = _today_utc().isoformat()
    fetch_error = None

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
        fetch_error = e
        logger.warning(f"Quota fetch failed for user {user_id} (will try upsert): {e}")

    # Row doesn't exist yet (or fetch failed) -- upsert with zeros
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
        if resp and resp.data:
            logger.info(
                f"Created quota row for user {user_id} (date={today})"
            )
            return resp.data[0]
        # Upsert returned empty data — log and raise so caller handles it
        raise RuntimeError(
            f"Upsert returned empty data for user {user_id}"
        )
    except RuntimeError:
        raise  # Re-raise our own error
    except Exception as e:
        logger.error(
            f"Quota upsert ALSO failed for user {user_id}: {e}. "
            f"Original fetch error: {fetch_error}"
        )
        raise RuntimeError(
            f"Both quota fetch and upsert failed for user {user_id}: "
            f"fetch={fetch_error}, upsert={e}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def check_quota(user_id: str) -> QuotaStatus:
    """Check if user has remaining quota for today.

    If no quota record exists for today, create one (UPSERT).
    Returns QuotaStatus with allowed=True/False.

    Retry policy: if Supabase fails on the first attempt, we wait 1 second
    and retry once. Only if the retry also fails do we fall back to a
    reduced-limit fail-open status (5 messages, 3 generations).
    """
    client = _get_client()

    # --- attempt helper (shared by first try + retry) ---
    def _build_status(row: dict) -> QuotaStatus:
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

    # --- first attempt ---
    try:
        row = _ensure_today_row(client, user_id)
        return _build_status(row)
    except (RuntimeError, Exception) as first_err:
        logger.warning(
            f"Quota check attempt 1 failed for {user_id}: {first_err}. "
            f"Retrying in 1s..."
        )

    # --- retry after 1 second ---
    await asyncio.sleep(1)
    try:
        row = _ensure_today_row(client, user_id)
        logger.info(f"Quota check retry succeeded for {user_id}")
        return _build_status(row)
    except (RuntimeError, Exception) as retry_err:
        # Both attempts failed — fall back to reduced limits
        return _fail_open_status(
            user_id=user_id,
            reason=f"2 attempts failed: first={first_err}, retry={retry_err}",
        )


async def consume_message(user_id: str) -> None:
    """Increment messages_used for today. Called after successful agent response."""
    try:
        client = _get_client()
        row = _ensure_today_row(client, user_id)
        row_id = row.get("id")
        if not row_id:
            logger.error(
                f"Quota row for {user_id} has no 'id' — cannot update count. "
                f"Row contents: {row}"
            )
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
            logger.error(
                f"Quota row for {user_id} has no 'id' — cannot update generation count. "
                f"Row contents: {row}"
            )
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
