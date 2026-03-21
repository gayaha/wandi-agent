"""Supabase-backed session and message storage for the Wandi agent.

Replaces the in-memory _sessions dict in agent_engine.py with persistent
storage in Supabase (agent_sessions + agent_messages tables).

Uses the same singleton client pattern as supabase_client.py.
All functions are async for API compatibility, wrapping the sync
supabase-py client under the hood.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Any

from supabase import create_client, Client

import config

logger = logging.getLogger(__name__)

# ── Singleton Client ─────────────────────────────────────────────────────────

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


# ── Helpers ──────────────────────────────────────────────────────────────────

def _generate_title(content: str) -> str:
    """Auto-generate a session title from the first user message (first 50 chars)."""
    title = content.strip().replace("\n", " ")
    if len(title) > 50:
        title = title[:50] + "..."
    return title


async def _run_sync(func, *args, **kwargs) -> Any:
    """Run a sync supabase-py call in the default executor to avoid blocking."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


# ── Sessions ─────────────────────────────────────────────────────────────────

async def create_session(
    user_id: str,
    client_id: str,
    title: str | None = None,
) -> dict:
    """Create a new agent session.

    Returns:
        Dict with keys: id, user_id, client_id, title, status, created_at.
    """
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    row = {
        "id": session_id,
        "user_id": user_id,
        "client_id": client_id,
        "title": title or "",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }

    try:
        client = _get_client()
        result = await _run_sync(
            lambda: client.table("agent_sessions").insert(row).execute()
        )
        logger.info(f"Created session {session_id} for user {user_id}")
        return result.data[0]
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise


async def get_session(session_id: str) -> dict | None:
    """Get a session by ID.

    Returns:
        Session dict or None if not found.
    """
    try:
        client = _get_client()
        result = await _run_sync(
            lambda: (
                client.table("agent_sessions")
                .select("*")
                .eq("id", session_id)
                .single()
                .execute()
            )
        )
        return result.data
    except Exception as e:
        # supabase-py raises on .single() when no row is found
        logger.debug(f"Session {session_id} not found: {e}")
        return None


async def list_sessions(user_id: str, limit: int = 20) -> list[dict]:
    """List a user's sessions, newest first.

    Intended for sidebar/session-picker display.

    Args:
        user_id: The user whose sessions to list.
        limit: Maximum number of sessions to return.

    Returns:
        List of session dicts ordered by created_at descending.
    """
    try:
        client = _get_client()
        result = await _run_sync(
            lambda: (
                client.table("agent_sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        )
        return result.data
    except Exception as e:
        logger.error(f"Failed to list sessions for user {user_id}: {e}")
        return []


async def update_session_title(session_id: str, title: str) -> None:
    """Update a session's title.

    Typically called once when the first user message arrives,
    to auto-generate a descriptive title.
    """
    try:
        client = _get_client()
        now = datetime.now(timezone.utc).isoformat()
        await _run_sync(
            lambda: (
                client.table("agent_sessions")
                .update({"title": title, "updated_at": now})
                .eq("id", session_id)
                .execute()
            )
        )
        logger.debug(f"Updated title for session {session_id}: {title}")
    except Exception as e:
        logger.error(f"Failed to update session title: {e}")


async def close_session(session_id: str) -> None:
    """Mark a session as complete."""
    try:
        client = _get_client()
        now = datetime.now(timezone.utc).isoformat()
        await _run_sync(
            lambda: (
                client.table("agent_sessions")
                .update({"status": "complete", "updated_at": now})
                .eq("id", session_id)
                .execute()
            )
        )
        logger.info(f"Closed session {session_id}")
    except Exception as e:
        logger.error(f"Failed to close session: {e}")


# ── Messages ─────────────────────────────────────────────────────────────────

async def save_message(
    session_id: str,
    role: str,
    content: str,
    tool_name: str | None = None,
    tool_args: dict | None = None,
    tool_result: dict | None = None,
    tokens_used: int = 0,
    duration_ms: int = 0,
) -> dict:
    """Save a message to the session.

    Also auto-generates the session title from the first user message
    if the session has no title yet.

    Args:
        session_id: The session this message belongs to.
        role: One of 'user', 'assistant', 'tool', 'system'.
        content: The message text.
        tool_name: Tool name (for role='tool' or tool-call messages).
        tool_args: Tool arguments as a dict.
        tool_result: Tool execution result as a dict.
        tokens_used: Token count for this interaction.
        duration_ms: Wall-clock duration in milliseconds.

    Returns:
        The created message dict.
    """
    message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    row: dict[str, Any] = {
        "id": message_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "tokens_used": tokens_used,
        "duration_ms": duration_ms,
        "created_at": now,
    }

    if tool_name is not None:
        row["tool_name"] = tool_name
    if tool_args is not None:
        row["tool_args"] = tool_args
    if tool_result is not None:
        row["tool_result"] = tool_result

    try:
        client = _get_client()
        result = await _run_sync(
            lambda: client.table("agent_messages").insert(row).execute()
        )
        saved = result.data[0]
        logger.debug(
            f"Saved {role} message {message_id} to session {session_id}"
        )
    except Exception as e:
        logger.error(f"Failed to save message: {e}")
        raise

    # Auto-generate session title from first user message
    if role == "user":
        try:
            session = await get_session(session_id)
            if session and not session.get("title"):
                title = _generate_title(content)
                await update_session_title(session_id, title)
        except Exception as e:
            # Non-critical — don't fail the save over a title update
            logger.warning(f"Failed to auto-generate session title: {e}")

    return saved


async def get_messages(session_id: str) -> list[dict]:
    """Get all messages for a session, ordered by created_at ascending.

    Returns:
        List of message dicts in chronological order.
    """
    try:
        client = _get_client()
        result = await _run_sync(
            lambda: (
                client.table("agent_messages")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .execute()
            )
        )
        return result.data
    except Exception as e:
        logger.error(
            f"Failed to get messages for session {session_id}: {e}"
        )
        return []
