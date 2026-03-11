# Architecture

**Analysis Date:** 2026-03-11

## Pattern Overview

**Overall:** Single-process async API service with a pipeline architecture

The wandi-agent is a FastAPI-based AI content generation service that orchestrates data retrieval from Airtable, prompt assembly, LLM inference via Ollama, and result persistence back to Airtable. It follows a linear pipeline pattern: fetch data, build prompt, generate content, save results.

**Key Characteristics:**
- Flat module structure (no packages, all `.py` files at root level)
- Async-first design using `httpx.AsyncClient` for all external I/O
- No ORM or database abstraction -- direct HTTP calls to Airtable REST API and Ollama API
- Configuration via environment variables loaded at import time
- Hebrew-language domain (Israeli Instagram marketing content generation)

## Layers

**API Layer (HTTP Interface):**
- Purpose: Accept generation requests, expose health/model endpoints, manage async task lifecycle
- Location: `main.py`
- Contains: FastAPI app, route handlers, Pydantic request/response models, CORS middleware, background task runner
- Depends on: `agent`, `airtable_client`, `ollama_client`, `config`
- Used by: External callers (Supabase Edge Functions, direct HTTP clients)

**Agent Layer (Business Logic / Orchestration):**
- Purpose: Coordinate the full reel generation pipeline -- fetch data, decide distribution, generate via LLM, save results
- Location: `agent.py`
- Contains: `generate_reels()` pipeline function, `_decide_distribution()` logic, `_build_queue_record()` mapper, `_fetch_all_data()` concurrent fetcher
- Depends on: `airtable_client`, `ollama_client`, `prompts`
- Used by: `main.py` route handlers

**Prompt Layer (LLM Prompt Engineering):**
- Purpose: Build structured Hebrew prompts for the Ollama LLM from client data and marketing context
- Location: `prompts.py`
- Contains: System prompt, batch generation template, data formatting functions (`format_magnets`, `format_hooks`, `format_viral_content`, `format_rtm_events`, `format_insights`, `format_style_examples`, `format_distribution`)
- Depends on: Nothing (pure functions operating on dicts)
- Used by: `agent.py`

**Data Access Layer (Airtable Client):**
- Purpose: Read from and write to Airtable tables (the primary data store)
- Location: `airtable_client.py`
- Contains: Generic CRUD helpers (`_fetch_all`, `_create_record`, `_create_records_batch`) and domain-specific query functions (`get_client`, `get_magnets_for_client`, `get_viral_hooks`, etc.)
- Depends on: `config`
- Used by: `agent.py`, `main.py` (for async callback data enrichment)

**LLM Client Layer (Ollama Client):**
- Purpose: Interface with the Ollama API for text generation and JSON extraction
- Location: `ollama_client.py`
- Contains: `generate()` for raw text, `generate_json()` with JSON extraction and markdown fence stripping, `check_health()`, `list_models()`
- Depends on: `config`
- Used by: `agent.py`, `main.py` (for health checks)

**Configuration Layer:**
- Purpose: Centralize environment variable loading and provide constants for table names, URLs, and server settings
- Location: `config.py`
- Contains: All env var lookups, Airtable table name constants, default values
- Depends on: `python-dotenv`
- Used by: All other modules

**Knowledge Base (Static Reference):**
- Purpose: Document the SDMF (Smart DM Funnel) marketing methodology that guides content generation
- Location: `SDMF_agent_knowledge.md`
- Contains: 5 awareness stages, magnet types, content taxonomy, hook types, weekly structure
- Used by: Developers/operators for understanding the domain; not loaded programmatically

**Stub Layer (Future):**
- Purpose: Placeholder for Supabase Storage video upload functionality
- Location: `supabase_client.py`
- Contains: Single `upload_video()` function that raises `NotImplementedError`
- Depends on: `config`
- Used by: Nothing currently

## Data Flow

**Synchronous Generation (`POST /generate`):**

1. Client sends `GenerateRequest` with `client_id`, `batch_type`, `quantity` to `main.py`
2. `main.py` calls `agent.generate_reels()` and awaits result
3. `agent.py` fetches client profile from Airtable via `at.get_client(client_id)`
4. `agent.py` extracts `niche` from client record, then concurrently fetches 6 data sets from Airtable (`_fetch_all_data`): magnets, viral hooks, viral content pool, RTM events, style examples, global insights
5. `agent.py` calls `_decide_distribution()` to compute reel counts per awareness stage based on `batch_type`
6. `agent.py` calls `prompts.build_generation_prompt()` to assemble the full Hebrew prompt with all fetched context
7. `agent.py` calls `ollama.generate_json()` which sends prompt + system message to Ollama `/api/generate`
8. `ollama_client.py` parses the response, strips markdown fences, extracts JSON
9. `agent.py` maps each generated reel to an Airtable record format via `_build_queue_record()`
10. `agent.py` saves each reel individually to the Content Queue table via `at.save_reels_to_queue()`
11. `agent.py` returns a `GenerateResponse` dict with reels, counts, and any errors
12. `main.py` returns the response to the caller

**Asynchronous Generation (`POST /generate-async`):**

1. Client sends `GenerateAsyncRequest` with `client_id`, `batch_type`, `quantity`, `callback_url`, `user_id`, `connection_id`, `webhook_secret`
2. `main.py` validates `batch_type`, creates an `asyncio.create_task()` for `_run_generation_and_callback()`, returns HTTP 202 immediately
3. Background task calls `agent.generate_reels()` (same pipeline as synchronous)
4. Background task maps generated reels to `content_projects` format (different field names than Airtable format)
5. Background task POSTs results to `callback_url` with retry (3 attempts, exponential backoff: 1s, 2s, 4s)
6. On failure, background task attempts to POST an error payload to the callback URL

**State Management:**
- No in-process state. All state lives in Airtable tables.
- No session management, no caching, no queuing system.
- Background tasks use `asyncio.create_task()` -- tasks are lost if the process crashes.

## Key Abstractions

**Airtable Record:**
- Purpose: Represents all domain entities (clients, magnets, hooks, content, events, templates, insights)
- Examples: Records fetched via `airtable_client.py` functions
- Pattern: Raw Airtable JSON format `{"id": "recXXX", "fields": {...}}` -- no domain model classes

**Content Distribution:**
- Purpose: Determines how many reels to generate per awareness stage
- Examples: `_decide_distribution()` in `agent.py`
- Pattern: Simple ratio-based allocation using batch_type and magnet availability

**Prompt Template:**
- Purpose: Structured Hebrew prompt that combines client data, marketing context, and generation instructions
- Examples: `BATCH_GENERATION_PROMPT` in `prompts.py`, `SYSTEM_PROMPT` in `prompts.py`
- Pattern: Python f-string template with named placeholders, filled by `build_generation_prompt()`

## Entry Points

**HTTP Server (`main.py`):**
- Location: `main.py` (line 298: `if __name__ == "__main__"`)
- Triggers: `python main.py` or `uvicorn main:app`
- Responsibilities: Start uvicorn server on `config.HOST`:`config.PORT` with reload enabled

**API Endpoints:**
- `GET /health` (line 231): Returns Ollama connectivity status and configured model name
- `GET /models` (line 241): Lists available Ollama models
- `POST /generate` (line 250): Synchronous reel generation -- blocks until complete
- `POST /generate-async` (line 271): Async reel generation -- returns 202, POSTs results to callback URL

## Error Handling

**Strategy:** Exception-based with HTTP status code mapping. No custom exception hierarchy.

**Patterns:**
- `ValueError` raised in `agent.py` for invalid inputs (bad `batch_type`, missing `niche`, `quantity` out of range) -- mapped to HTTP 400 in `main.py`
- Generic `Exception` caught in `main.py` route handlers -- mapped to HTTP 500 with error detail
- Individual reel save failures in `agent.py` are caught per-reel, logged, and collected into an `errors` list -- partial success is possible
- `ollama_client.py` `generate_json()` attempts multiple JSON extraction strategies before raising `ValueError`
- Async callback retries 3 times with exponential backoff; on total failure, attempts to send error payload to callback
- No structured error response format beyond FastAPI's default `HTTPException` detail

## Cross-Cutting Concerns

**Logging:**
- Standard Python `logging` module configured in `main.py` at startup
- Log level set via `config.LOG_LEVEL` (default: `info`)
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s` to stdout
- Each module creates its own `logger = logging.getLogger(__name__)`
- Extensive logging in `agent.py` (pipeline steps), `airtable_client.py` (record counts), `ollama_client.py` (prompt/response lengths)

**Validation:**
- Pydantic models validate API request bodies in `main.py` (`GenerateRequest`, `GenerateAsyncRequest`)
- `batch_type` validated against `BATCH_TYPES` set in `agent.py` and again in `main.py` `/generate-async` handler
- `quantity` constrained to 1-30 via Pydantic `Field(ge=1, le=30)` and runtime check in `agent.py`
- No validation on Airtable data shapes -- assumes correct structure

**Authentication:**
- No authentication on the API endpoints -- wide-open CORS (`allow_origins=["*"]`)
- Airtable authenticated via Bearer token in `AIRTABLE_API_KEY`
- Async callback optionally authenticated via `X-Webhook-Secret` header
- No API key, JWT, or OAuth for incoming requests

**CORS:**
- Fully permissive: all origins, all methods, all headers (configured in `main.py` line 54-59)

---

*Architecture analysis: 2026-03-11*
