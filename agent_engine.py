"""Agentic engine for Wandi — the LLM decides what tools to call.

This replaces the hardcoded pipeline with a dynamic agent loop where
the LLM (via Ollama tool calling) decides which tools to invoke,
observes results, and iterates until the task is complete.

Sessions are persisted to Supabase via session_store.py.
In-memory message list is used during the agent loop for LLM context,
then saved to Supabase after each interaction.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import ollama_client as ollama
import session_store
import tool_registry

logger = logging.getLogger(__name__)

MAX_AGENT_STEPS = 20  # Safety limit to prevent infinite loops


@dataclass
class ToolCall:
    """Record of a single tool invocation."""
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    duration_ms: int


@dataclass
class AgentResult:
    """Result of running the agent loop."""
    session_id: str
    response: str
    steps: int
    tool_calls: list[ToolCall] = field(default_factory=list)
    error: bool = False
    total_duration_ms: int = 0


# ── Session Management (Supabase-backed) ─────────────────────────────────────


async def get_or_create_session(
    user_id: str, client_id: str, session_id: str | None = None
) -> dict:
    """Get existing session or create a new one in Supabase.

    Returns a session dict with keys: id, user_id, client_id, title, status.
    """
    if session_id:
        existing = await session_store.get_session(session_id)
        if existing:
            return existing

    # Create new session
    return await session_store.create_session(user_id, client_id)


async def get_session(session_id: str) -> dict | None:
    """Get an existing session by ID from Supabase."""
    return await session_store.get_session(session_id)


# ── Agent Loop ──────────────────────────────────────────────────────────────


async def run_agent(
    user_message: str,
    client_id: str,
    session: dict,
    system_prompt: str | None = None,
) -> AgentResult:
    """Run the agent loop — LLM decides what tools to call.

    Flow:
    1. Load conversation history from Supabase
    2. User message is added to conversation
    3. LLM sees conversation + available tools → decides next action
    4. If tool_calls → execute tools, add results, go to step 3
    5. If no tool_calls → LLM is done, return response to user
    6. All messages are saved to Supabase

    Args:
        user_message: The user's request in natural language.
        client_id: Airtable client record ID for context.
        session: Session dict from get_or_create_session().
        system_prompt: Optional custom system prompt override.
    """
    session_id = session["id"]

    # Use the agent system prompt from prompts.py, with client context injected
    if system_prompt is None:
        import prompts
        system_prompt = (
            prompts.AGENT_SYSTEM_PROMPT
            + f"\n\n## הקשר נוכחי:\n"
            f"client_id של הלקוחה הנוכחית: {client_id}\n"
            f"השתמשי ב-client_id הזה בכל קריאה לכלים שדורשים אותו."
        )

    # Load previous messages from Supabase for conversation continuity
    stored_messages = await session_store.get_messages(session_id)
    messages: list[dict[str, Any]] = []
    for msg in stored_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        entry: dict[str, Any] = {"role": role, "content": content}
        # Reconstruct tool_calls for assistant messages that triggered tools
        if role == "assistant" and msg.get("tool_name"):
            entry["tool_calls"] = [{
                "function": {
                    "name": msg["tool_name"],
                    "arguments": msg.get("tool_args", {}),
                }
            }]
        messages.append(entry)

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    # Persist user message to Supabase
    await session_store.save_message(session_id, "user", user_message)

    tool_schemas = tool_registry.get_all_tool_schemas()
    all_tool_calls: list[ToolCall] = []
    start_time = time.time()

    for step in range(MAX_AGENT_STEPS):
        logger.info(f"[Agent] Step {step + 1}/{MAX_AGENT_STEPS}")

        # Ask the LLM what to do next
        response = await ollama.chat(
            messages=messages,
            tools=tool_schemas,
            system=system_prompt,
        )

        content = response.get("content", "")
        tool_calls = response.get("tool_calls")

        # If no tool calls — the agent is done thinking and wants to respond
        if not tool_calls:
            total_ms = int((time.time() - start_time) * 1000)
            final_response = content or "סיימתי את המשימה."

            # Persist assistant response to Supabase
            await session_store.save_message(
                session_id, "assistant", final_response,
                duration_ms=total_ms,
            )

            logger.info(
                f"[Agent] Done after {step + 1} steps, "
                f"{len(all_tool_calls)} tool calls, {total_ms}ms"
            )
            return AgentResult(
                session_id=session_id,
                response=final_response,
                steps=step + 1,
                tool_calls=all_tool_calls,
                total_duration_ms=total_ms,
            )

        # The LLM wants to call tools — execute each one
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            fn = tc.get("function", {})
            tool_name = fn.get("name", "")
            tool_args = fn.get("arguments", {})

            logger.info(f"[Agent] Calling tool: {tool_name}({tool_args})")
            tool_start = time.time()

            result = await tool_registry.execute_tool(tool_name, tool_args)

            tool_duration = int((time.time() - tool_start) * 1000)
            tool_call_record = ToolCall(
                tool_name=tool_name,
                arguments=tool_args,
                result=result,
                duration_ms=tool_duration,
            )
            all_tool_calls.append(tool_call_record)

            # Add tool result to in-memory conversation for LLM context
            tool_result_str = json.dumps(result, ensure_ascii=False, default=str)
            messages.append({"role": "tool", "content": tool_result_str})

            # Persist tool call to Supabase
            await session_store.save_message(
                session_id, "tool", tool_result_str,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=result,
                duration_ms=tool_duration,
            )

            logger.info(
                f"[Agent] Tool {tool_name} completed in {tool_duration}ms"
            )

    # Safety limit reached
    total_ms = int((time.time() - start_time) * 1000)
    error_msg = f"הגעתי למגבלת הצעדים ({MAX_AGENT_STEPS}). המשימה לא הושלמה."

    # Persist error message
    await session_store.save_message(
        session_id, "assistant", error_msg, duration_ms=total_ms,
    )

    logger.warning(f"[Agent] Hit step limit after {MAX_AGENT_STEPS} steps")
    return AgentResult(
        session_id=session_id,
        response=error_msg,
        steps=MAX_AGENT_STEPS,
        tool_calls=all_tool_calls,
        error=True,
        total_duration_ms=total_ms,
    )
