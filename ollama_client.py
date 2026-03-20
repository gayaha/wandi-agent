import json
import logging
import re
from typing import Any

import httpx

import config

logger = logging.getLogger(__name__)


async def list_models() -> list[dict[str, Any]]:
    """List all available Ollama models."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
        resp.raise_for_status()
        return resp.json().get("models", [])


async def generate(prompt: str, system: str | None = None) -> str:
    """Generate text using the configured Ollama model.

    Uses the /api/generate endpoint with stream=false for simplicity.
    """
    payload: dict[str, Any] = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.8,
            "top_p": 0.9,
            "num_predict": 8192,
        },
    }
    if system:
        payload["system"] = system

    logger.info(f"Calling Ollama ({config.OLLAMA_MODEL}) — prompt length: {len(prompt)}")

    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    response_text = data.get("response", "")
    logger.info(f"Ollama response length: {len(response_text)}")
    return response_text


def _fix_hebrew_quotes_in_json(text: str) -> str:
    """Replace Hebrew gershayim (״ or ASCII \" inside Hebrew context) with the
    Hebrew punctuation character GERSHAYIM (U+05F4) so they don't break JSON
    string parsing.

    The problem: a model returns  "hook": "לאסוף 100 ש"ח נוספים"
    The inner " before ח is meant as Hebrew gershayim but breaks JSON parsing.

    Strategy: inside JSON string values, find a double-quote that sits between
    two Hebrew characters (with optional digits/spaces) and replace it with ״
    (U+05F4, Hebrew punctuation gershayim).
    """
    # Match a double quote surrounded by Hebrew letter context.
    # Look-behind: Hebrew letter or digit; look-ahead: Hebrew letter.
    # This catches patterns like ש"ח where " is gershayim.
    hebrew_letter = r'[\u0590-\u05FF]'
    pattern = rf'({hebrew_letter})"({hebrew_letter})'
    return re.sub(pattern, '\\1\u05F4\\2', text)


def _extract_json_substring(text: str) -> str | None:
    """Try to extract a JSON object or array substring from text.

    When there is non-JSON text surrounding the JSON (e.g. model commentary),
    prefer finding '{"' over bare '{' to avoid matching Hebrew braces like
    {שיווק} that aren't actual JSON.
    """
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        end = text.rfind(end_char)
        if end == -1 or end <= start:
            continue

        # If there's non-JSON text before the first brace and we're looking
        # for an object, prefer '{"' to skip false positives like {שיווק}
        if start_char == "{" and start > 0:
            better = text.find('{"')
            if better != -1 and better <= end:
                start = better

        return text[start : end + 1]
    return None


_REEL_FIELD_NAMES = {"hook", "caption", "video_text", "verbal_script", "cta", "magnet"}


def _regex_extract_fields(text: str) -> dict[str, Any] | None:
    """Last-resort: extract key-value pairs from JSON-like text using regex.

    If the extracted fields look like a single reel (contain hook/caption/etc.),
    wraps them in {"reels": [fields]} so the pipeline receives the expected
    structure instead of a flat dict.

    Returns a dict or None if nothing found.
    """
    # Match "key": "value" pairs, allowing for escaped quotes in value
    pairs = re.findall(
        r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"',
        text,
    )
    if pairs:
        flat = {k: v for k, v in pairs}
        # If it looks like a single reel, wrap it
        if flat.keys() & _REEL_FIELD_NAMES:
            return {"reels": [flat]}
        return flat

    # Also try unquoted/numeric values
    numeric_pairs = re.findall(
        r'"([^"]+)"\s*:\s*(\d+(?:\.\d+)?|true|false|null)',
        text,
    )
    if numeric_pairs:
        result: dict[str, Any] = {}
        for k, v in numeric_pairs:
            if v == "true":
                result[k] = True
            elif v == "false":
                result[k] = False
            elif v == "null":
                result[k] = None
            elif "." in v:
                result[k] = float(v)
            else:
                result[k] = int(v)
        if result.keys() & _REEL_FIELD_NAMES:
            return {"reels": [result]}
        return result
    return None


def _try_parse(text: str) -> Any:
    """Attempt json.loads, returning None on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _try_parse_with_hebrew_fix(text: str) -> Any:
    """Try parsing raw, then with Hebrew gershayim fix."""
    result = _try_parse(text)
    if result is not None:
        return result
    fixed = _fix_hebrew_quotes_in_json(text)
    if fixed != text:
        return _try_parse(fixed)
    return None


def _parse_json_robust(cleaned: str) -> Any:
    """Try multiple strategies to parse a JSON string.

    1. Direct parse (raw + Hebrew fix)
    2. Find first { … last } and parse
    3. Find ```json … ``` fenced blocks and parse content
    4. Find {"reels" specifically and parse from there
    5. Regex field extraction as last resort (wraps flat reel fields)

    If any strategy yields a dict with a non-empty "reels" list, use it
    immediately.
    """

    def _has_reels(obj: Any) -> bool:
        return isinstance(obj, dict) and isinstance(obj.get("reels"), list) and len(obj["reels"]) > 0

    # Strategy 1: direct parse (raw + Hebrew fix)
    result = _try_parse_with_hebrew_fix(cleaned)
    if result is not None:
        return result

    # Strategy 2: first { … last } bracket extraction
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        substring = cleaned[start : end + 1]
        result = _try_parse_with_hebrew_fix(substring)
        if result is not None:
            return result

    # Strategy 3: ```json ... ``` fenced code blocks
    fence_pattern = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)
    for match in fence_pattern.finditer(cleaned):
        block = match.group(1).strip()
        result = _try_parse_with_hebrew_fix(block)
        if result is not None:
            return result

    # Strategy 4: find {"reels" specifically — model may have prose around it
    reels_idx = cleaned.find('{"reels"')
    if reels_idx == -1:
        reels_idx = cleaned.find("{\"reels\"")
    if reels_idx != -1:
        tail = cleaned[reels_idx:]
        end = tail.rfind("}")
        if end != -1:
            result = _try_parse_with_hebrew_fix(tail[: end + 1])
            if _has_reels(result):
                return result

    # Strategy 5: regex extraction as last resort
    source = _fix_hebrew_quotes_in_json(cleaned)
    substring = _extract_json_substring(source) or source
    result = _regex_extract_fields(substring)
    if result:
        logger.warning("Used regex fallback to extract JSON fields from Ollama response")
        return result

    return None


async def generate_json(prompt: str, system: str | None = None) -> Any:
    """Generate and parse JSON from Ollama.

    Attempts to extract a JSON object or array from the model response,
    even if the model wraps it in markdown code fences. Handles Hebrew
    gershayim characters that look like double quotes inside string values.
    """
    raw = await generate(prompt, system)

    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove first line (```json or ```) and last ```
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Strip <think>...</think> blocks only if present (thinking models)
    if "<think>" in cleaned:
        cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
        logger.info("Stripped <think> block from model response")

    logger.debug(f"Cleaned text for JSON parsing (first 500 chars): {cleaned[:500]}")

    result = _parse_json_robust(cleaned)
    if result is not None:
        return result

    logger.error(f"Failed to parse JSON from Ollama response: {raw[:500]}")
    raise ValueError(f"Could not parse JSON from model response: {raw[:200]}")


async def chat(
    messages: list[dict[str, Any]],
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    system: str | None = None,
) -> dict[str, Any]:
    """Chat completion with optional tool calling via /api/chat.

    This is the core method for the agent engine — it sends a conversation
    with tool definitions and returns the model's response, which may include
    tool_calls that the agent loop should execute.

    Returns a dict with:
      - content: str (the model's text response, may be empty if tool call)
      - tool_calls: list[dict] | None (tool calls the model wants to make)
    """
    resolved_model = model or config.OLLAMA_AGENT_MODEL or config.OLLAMA_MODEL

    payload: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.3,  # Lower temp for tool-calling decisions
            "num_predict": 4096,
        },
    }
    if system:
        # Prepend system message
        payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]
    if tools:
        payload["tools"] = tools

    logger.info(
        f"Calling Ollama chat ({resolved_model}) — "
        f"{len(messages)} messages, {len(tools or [])} tools"
    )

    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    message = data.get("message", {})
    content = message.get("content", "")
    tool_calls = message.get("tool_calls")

    logger.info(
        f"Ollama chat response: content={len(content)} chars, "
        f"tool_calls={len(tool_calls) if tool_calls else 0}"
    )

    return {
        "content": content,
        "tool_calls": tool_calls,
    }


async def check_health() -> bool:
    """Check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
