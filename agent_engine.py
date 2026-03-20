"""Agentic engine for Wandi — the LLM decides what tools to call.

This replaces the hardcoded pipeline with a dynamic agent loop where
the LLM (via Ollama tool calling) decides which tools to invoke,
observes results, and iterates until the task is complete.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import ollama_client as ollama
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


@dataclass
class AgentSession:
    """Lightweight in-memory session for agent conversations.

    Future: persist to Supabase for cross-request continuity.
    """
    session_id: str
    client_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_history: list[ToolCall] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_call_message(self, tool_calls: list[dict]) -> None:
        """Add the assistant's tool call request to history."""
        self.messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls,
        })

    def add_tool_result(self, tool_name: str, result: Any) -> None:
        """Add a tool execution result to the conversation."""
        self.messages.append({
            "role": "tool",
            "content": json.dumps(result, ensure_ascii=False, default=str),
        })


# ── Session Store (in-memory for now) ───────────────────────────────────────

_sessions: dict[str, AgentSession] = {}


def get_or_create_session(
    client_id: str, session_id: str | None = None
) -> AgentSession:
    """Get existing session or create a new one."""
    if session_id and session_id in _sessions:
        return _sessions[session_id]

    new_id = session_id or str(uuid.uuid4())
    session = AgentSession(session_id=new_id, client_id=client_id)
    _sessions[new_id] = session
    return session


def get_session(session_id: str) -> AgentSession | None:
    """Get an existing session by ID."""
    return _sessions.get(session_id)


# ── Agent Loop ──────────────────────────────────────────────────────────────


async def run_agent(
    user_message: str,
    client_id: str,
    session: AgentSession | None = None,
    system_prompt: str | None = None,
) -> AgentResult:
    """Run the agent loop — LLM decides what tools to call.

    Flow:
    1. User message is added to conversation
    2. LLM sees conversation + available tools → decides next action
    3. If tool_calls → execute tools, add results, go to step 2
    4. If no tool_calls → LLM is done, return response to user

    Args:
        user_message: The user's request in natural language.
        client_id: Airtable client record ID for context.
        session: Optional existing session to continue conversation.
        system_prompt: Optional custom system prompt override.
    """
    if session is None:
        session = get_or_create_session(client_id)

    # Use the agent system prompt from prompts.py, with client context injected
    if system_prompt is None:
        import prompts
        system_prompt = (
            prompts.AGENT_SYSTEM_PROMPT
            + f"\n\n## הקשר נוכחי:\n"
            f"client_id של הלקוחה הנוכחית: {client_id}\n"
            f"השתמשי ב-client_id הזה בכל קריאה לכלים שדורשים אותו."
        )

    session.add_user_message(user_message)

    tool_schemas = tool_registry.get_all_tool_schemas()
    all_tool_calls: list[ToolCall] = []
    start_time = time.time()

    for step in range(MAX_AGENT_STEPS):
        logger.info(f"[Agent] Step {step + 1}/{MAX_AGENT_STEPS}")

        # Ask the LLM what to do next
        response = await ollama.chat(
            messages=session.messages,
            tools=tool_schemas,
            system=system_prompt,
        )

        content = response.get("content", "")
        tool_calls = response.get("tool_calls")

        # If no tool calls — the agent is done thinking and wants to respond
        if not tool_calls:
            if content:
                session.add_assistant_message(content)
            total_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"[Agent] Done after {step + 1} steps, "
                f"{len(all_tool_calls)} tool calls, {total_ms}ms"
            )
            return AgentResult(
                session_id=session.session_id,
                response=content or "סיימתי את המשימה.",
                steps=step + 1,
                tool_calls=all_tool_calls,
                total_duration_ms=total_ms,
            )

        # The LLM wants to call tools — execute each one
        session.add_tool_call_message(tool_calls)

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
            session.tool_history.append(tool_call_record)

            # Add tool result to conversation so LLM can see it
            session.add_tool_result(tool_name, result)

            logger.info(
                f"[Agent] Tool {tool_name} completed in {tool_duration}ms"
            )

    # Safety limit reached
    total_ms = int((time.time() - start_time) * 1000)
    error_msg = f"הגעתי למגבלת הצעדים ({MAX_AGENT_STEPS}). המשימה לא הושלמה."
    session.add_assistant_message(error_msg)

    logger.warning(f"[Agent] Hit step limit after {MAX_AGENT_STEPS} steps")
    return AgentResult(
        session_id=session.session_id,
        response=error_msg,
        steps=MAX_AGENT_STEPS,
        tool_calls=all_tool_calls,
        error=True,
        total_duration_ms=total_ms,
    )
