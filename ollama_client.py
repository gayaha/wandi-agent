import json
import logging
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
            "num_predict": 4096,
        },
    }
    if system:
        payload["system"] = system

    logger.info(f"Calling Ollama ({config.OLLAMA_MODEL}) — prompt length: {len(prompt)}")

    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    response_text = data.get("response", "")
    logger.info(f"Ollama response length: {len(response_text)}")
    return response_text


async def generate_json(prompt: str, system: str | None = None) -> Any:
    """Generate and parse JSON from Ollama.

    Attempts to extract a JSON object or array from the model response,
    even if the model wraps it in markdown code fences.
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

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON within the response
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = cleaned.find(start_char)
            end = cleaned.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    continue
        logger.error(f"Failed to parse JSON from Ollama response: {raw[:500]}")
        raise ValueError(f"Could not parse JSON from model response: {raw[:200]}")


async def check_health() -> bool:
    """Check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
