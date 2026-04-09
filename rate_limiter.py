"""In-memory rate limiter for wandi-agent.

Tracks request timestamps per user_id and enforces a per-minute cap.
Designed for a single-process deployment (pm2 with 1 instance).

The _request_log dict self-cleans on every check — entries older than
the window are pruned, so memory stays bounded even without an explicit
background cleanup task.
"""

import logging
import time

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

MAX_REQUESTS_PER_MINUTE = 10  # Generous for normal use (2-3 msgs/min)
WINDOW_SECONDS = 60

# ── State ──────────────────────────────────────────────────────────────────

# {user_id: [timestamp_1, timestamp_2, ...]}
_request_log: dict[str, list[float]] = {}


# ── Public API ─────────────────────────────────────────────────────────────

def check_rate_limit(user_id: str) -> None:
    """Enforce per-user rate limit.

    Call at the top of any endpoint that should be throttled.
    Raises HTTPException(429) if the user exceeds the limit.

    Service accounts (user_id="service") are exempt — they come from
    n8n/internal pipelines which have their own pacing.
    """
    # Exempt service accounts (n8n, internal pipeline)
    if user_id == "service":
        return

    now = time.time()
    cutoff = now - WINDOW_SECONDS

    # Prune old entries (self-cleaning)
    if user_id in _request_log:
        _request_log[user_id] = [t for t in _request_log[user_id] if t > cutoff]
    else:
        _request_log[user_id] = []

    # Check limit
    if len(_request_log[user_id]) >= MAX_REQUESTS_PER_MINUTE:
        logger.warning(
            f"[RateLimit] User {user_id} exceeded {MAX_REQUESTS_PER_MINUTE} "
            f"requests in {WINDOW_SECONDS}s — blocked"
        )
        raise HTTPException(
            status_code=429,
            detail="יותר מדי בקשות. נסי שוב בעוד דקה.",
        )

    # Record this request
    _request_log[user_id].append(now)
