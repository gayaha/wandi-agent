# Coding Conventions

**Analysis Date:** 2026-03-11

## Naming Patterns

**Files:**
- Use `snake_case` for all Python source files: `airtable_client.py`, `ollama_client.py`, `supabase_client.py`
- Client modules follow `{service}_client.py` naming pattern
- Single-word names for core modules: `agent.py`, `config.py`, `prompts.py`, `main.py`

**Functions:**
- Use `snake_case` for all functions: `generate_reels`, `check_health`, `build_generation_prompt`
- Prefix private/internal helpers with underscore: `_fetch_all`, `_create_record`, `_decide_distribution`, `_build_queue_record`, `_resolve_magnet_name`, `_run_generation_and_callback`
- Public API functions have no underscore prefix: `generate`, `generate_json`, `get_client`
- Async functions use the same naming convention (no `async_` prefix): `async def generate(...)`, `async def get_client(...)`

**Variables:**
- Use `snake_case` for local variables and parameters: `client_id`, `batch_type`, `response_text`
- Use `UPPER_SNAKE_CASE` for module-level constants: `BATCH_TYPES`, `CONTENT_TYPE_MAP`, `BASE_URL`, `HEADERS`
- Use `UPPER_SNAKE_CASE` for all config values: `AIRTABLE_API_KEY`, `OLLAMA_BASE_URL`, `TABLE_CLIENTS`

**Types:**
- Use `PascalCase` for Pydantic models: `GenerateRequest`, `GenerateAsyncRequest`, `GenerateResponse`
- Type hints use modern Python 3.10+ syntax: `str | None` (not `Optional[str]`), `list[dict]` (not `List[Dict]`)

## Code Style

**Formatting:**
- No formatter configuration detected (no black, ruff, yapf, or autopep8 config files)
- Consistent 4-space indentation throughout all files
- Use double quotes for strings universally
- f-strings for all string interpolation: `f"Fetched {len(records)} records from {table}"`
- Line length appears to be ~100-120 characters (no strict enforcement)

**Linting:**
- No linting configuration detected (no flake8, pylint, ruff, or mypy config files)
- No `pyproject.toml` or `setup.py` present
- No pre-commit hooks configured

**When adding new code:** Follow the existing double-quote, f-string, 4-space indent style. Use modern Python 3.10+ type hint syntax (`str | None`, `list[dict]`).

## Import Organization

**Order:**
1. Standard library imports (`import json`, `import asyncio`, `import logging`, `import sys`, `import uuid`)
2. Third-party imports (`import httpx`, `from fastapi import ...`, `from pydantic import ...`)
3. Local/project imports (`import config`, `import agent`, `import airtable_client as at`)

**Blank lines:** One blank line separates each import group.

**Import style:**
- Use `import module` for project modules: `import config`, `import agent`
- Use `from module import name` for specific items: `from typing import Any`, `from fastapi import FastAPI, HTTPException`
- Use aliases for verbose client modules: `import airtable_client as at`, `import ollama_client as ollama`
- Example from `agent.py`:
```python
import asyncio
import logging
from typing import Any

import airtable_client as at
import ollama_client as ollama
import prompts
```

**Path Aliases:**
- None. All imports are direct module references from the project root (flat structure).

## Error Handling

**Patterns:**
- Raise `ValueError` for invalid input with descriptive messages: `raise ValueError(f"Invalid batch_type '{batch_type}'. Must be one of: {BATCH_TYPES}")` in `agent.py`
- Raise `HTTPException` in FastAPI routes to translate errors to HTTP status codes: `raise HTTPException(status_code=400, detail=str(e))` in `main.py`
- Use `resp.raise_for_status()` on all httpx responses (Airtable, Ollama) -- lets httpx raise `HTTPStatusError` on non-2xx
- Catch broad `Exception` only for health checks and background tasks where failure should not crash the process:
```python
# ollama_client.py - health check
try:
    ...
    return resp.status_code == 200
except Exception:
    return False
```
- Background task (`_run_generation_and_callback` in `main.py`) catches all exceptions and attempts to notify the callback URL about the failure
- Retry pattern for callbacks in `main.py`: 3 attempts with exponential backoff (`2 ** attempt` seconds)
- `raise NotImplementedError(...)` for stub functions: `supabase_client.py`

**Error propagation:** Errors bubble up from client modules through `agent.py` and are caught at the route level in `main.py`. Routes convert `ValueError` to 400 and other exceptions to 500.

## Logging

**Framework:** Python `logging` standard library

**Setup:** Configured once in `main.py` with `logging.basicConfig()`:
```python
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
```

**Logger creation:** Each module creates its own logger:
```python
logger = logging.getLogger(__name__)
```
This pattern is used in: `main.py`, `agent.py`, `airtable_client.py`, `ollama_client.py`, `supabase_client.py`

**Patterns:**
- Use `logger.info()` for successful operations and progress tracking: `logger.info(f"Fetched {len(records)} records from {table}")`
- Use `logger.warning()` for degraded conditions: `logger.warning("Ollama is NOT reachable")`
- Use `logger.error()` for failures: `logger.error(f"Failed to save reel {i + 1}: {e}")`
- Use `logger.exception()` for errors with traceback: `logger.exception("Generation failed")`
- Use f-strings in log messages (not lazy % formatting)
- Prefix async background task logs with `[async]`: `logger.info(f"[async] Starting generation: ...")`

## Comments

**When to Comment:**
- Section dividers use Unicode box-drawing characters to separate logical groups in files:
```python
# -- Client ---------------------------------------------------------------
# -- Magnets ---------------------------------------------------------------
```
- Inline comments for non-obvious logic: `# Fallback: most hooks are untagged, fetch all`
- Step-by-step comments in pipeline functions (`agent.py`): `# Step 1: Fetch client profile`, `# Step 2: Decide distribution`, etc.

**Docstrings:**
- Use triple-quote docstrings on all public and private functions
- First line is a concise summary: `"""Fetch all records from an Airtable table, handling pagination."""`
- Multi-line docstrings include Args/Returns sections for stub functions (`supabase_client.py`)
- Module-level docstrings at the top of key files: `"""Core generation logic for the wandi-agent."""`, `"""FastAPI server for wandi-agent..."""`, `"""Prompt templates for Hebrew Instagram Reels content generation."""`

## Function Design

**Size:**
- Functions are focused and short. Most are 5-30 lines.
- The longest function is `_run_generation_and_callback` in `main.py` (~100 lines) which is a complete background task pipeline.
- `generate_reels` in `agent.py` is ~100 lines, following a clear 5-step pipeline pattern with comments.

**Parameters:**
- Use keyword-only arguments (`*`) for complex builder functions: `build_generation_prompt(*, quantity, client_name, ...)` in `prompts.py`
- Use typed parameters with defaults: `quantity: int = 10`, `limit: int = 5`
- Pydantic `Field(...)` for required API parameters, `Field(default=...)` for optional ones

**Return Values:**
- Return typed values: `-> list[dict[str, Any]]`, `-> dict[str, Any]`, `-> str`, `-> bool`
- Return `None` with explicit type: `-> dict[str, Any] | None` when a record may not exist (e.g., `get_global_insights`)
- Complex responses return dicts with consistent keys: `{"success": True, "reels": [...], "count": N, ...}`

## Module Design

**Exports:**
- No `__all__` definitions in any module
- All public functions are implicitly exported
- Private functions prefixed with `_` are not intended for external use

**Barrel Files:**
- None. Each module is imported directly by name.

**Module roles:**
- `config.py`: Pure configuration -- reads env vars, defines constants. No functions.
- `*_client.py`: External service wrappers. Contain only I/O functions for a single service.
- `prompts.py`: Pure data (prompt templates) + pure formatting functions. No I/O.
- `agent.py`: Orchestration logic. Coordinates between clients and prompts.
- `main.py`: HTTP layer. FastAPI app, routes, request/response models, startup.

## Async Patterns

**All I/O functions are async.** The codebase uses `async/await` throughout:
- `httpx.AsyncClient` for all HTTP calls (Airtable API, Ollama API, callback webhooks)
- `asyncio.gather()` for concurrent data fetching in `agent.py`:
```python
(magnets, hooks, viral_pool, rtm_events, style_examples, insights) = await asyncio.gather(
    at.get_magnets_for_client(...),
    at.get_viral_hooks(...),
    ...
)
```
- `asyncio.create_task()` for fire-and-forget background generation in `main.py`
- New `httpx.AsyncClient` created per-call with explicit timeouts (not shared/reused)

**Timeout values:**
- Health check: 5s
- List models: 15s
- Airtable reads: 30s
- Airtable batch writes: 60s
- Ollama generation: 300s (5 minutes)
- Callback webhook: 30s

## Pydantic Model Conventions

**Location:** Request/response models are defined in `main.py`, co-located with routes.

**Pattern:**
```python
class GenerateRequest(BaseModel):
    client_id: str = Field(..., description="Airtable record ID of the client (recXXX)")
    batch_type: str = Field(..., description="Content batch type")
    quantity: int = Field(default=10, ge=1, le=30, description="Number of reels to generate")
```

- Use `Field(...)` (ellipsis) for required fields
- Use `Field(default=...)` for optional fields with defaults
- Always include `description` in Field for API documentation
- Use `ge`/`le` validators for numeric constraints
- Use `str | None = None` for optional string fields

---

*Convention analysis: 2026-03-11*
