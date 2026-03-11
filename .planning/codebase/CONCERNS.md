# Codebase Concerns

**Analysis Date:** 2026-03-11

## Tech Debt

**Supabase client is a stub:**
- Issue: `supabase_client.py` is entirely unimplemented. The `upload_video` function raises `NotImplementedError`. Despite being imported nowhere currently, config vars (`SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_BUCKET`) are defined in `config.py` and `.env.example`, creating the impression of a functioning integration.
- Files: `supabase_client.py`, `config.py` (lines 26-28)
- Impact: Any future code that attempts to use Supabase storage will fail at runtime. Dead config pollutes the environment setup.
- Fix approach: Either implement the Supabase client or remove all Supabase references (`config.py` lines 26-28, `.env.example` lines 9-11, `supabase_client.py`) until the video rendering pipeline is ready.

**Hardcoded Airtable base ID fallback:**
- Issue: `config.py` line 8 has a hardcoded default value for `AIRTABLE_BASE_ID`: `"app8393BIwz7tRlR9"`. If the `.env` file is missing or the var is unset, the app silently connects to this specific base instead of failing fast. The `.env.example` shows a different base ID (`appdkeK15eNEijklB`), confirming confusion.
- Files: `config.py` (line 8)
- Impact: Silent data corruption — the agent could read/write to the wrong Airtable base without any error.
- Fix approach: Remove the default value. Use `os.getenv("AIRTABLE_BASE_ID", "")` and add startup validation that raises if empty.

**Hardcoded Airtable table IDs:**
- Issue: Table names and IDs are hardcoded directly in `config.py` (lines 11-19) with no override mechanism via environment variables. `TABLE_CLIENTS` uses an opaque ID (`tblVUTKss5rnmH1P9`) while other tables use human-readable names (`"Magnets"`, `"viral hooks"`, etc.). This inconsistency suggests organic growth without a plan.
- Files: `config.py` (lines 11-19)
- Impact: Changing any table name in Airtable requires a code change and redeployment. Mixing ID styles makes it unclear which form Airtable expects.
- Fix approach: Make all table references configurable via env vars with sensible defaults, and standardize on either table IDs or names consistently.

**Sequential reel saving instead of batch:**
- Issue: In `agent.py` lines 177-183, reels are saved to Airtable one at a time in a loop (`at.save_reels_to_queue([rec])`), even though `_create_records_batch` in `airtable_client.py` supports batches of 10. This was likely done to handle individual failures, but it makes N API calls instead of ceil(N/10).
- Files: `agent.py` (lines 177-183), `airtable_client.py` (lines 71-89)
- Impact: For a 30-reel batch, this makes 30 HTTP requests instead of 3. Slower and more prone to rate limiting.
- Fix approach: Save in batches of 10 using the existing batch function. Track which batch failed and retry or report individual failures within the batch.

**Response reel indexing assumes ordered success:**
- Issue: In `agent.py` lines 189-195, the response builder assumes `saved[i]` corresponds to `generated_reels[i]`. But if reel 3 fails to save, `saved` has fewer entries, and all subsequent `record_id` assignments are misaligned (reel 4 gets reel 3's record ID, etc.).
- Files: `agent.py` (lines 189-195)
- Impact: Clients receive wrong Airtable record IDs in the response, causing data integrity issues downstream.
- Fix approach: Track which reels were saved successfully by index, or match saved records back to generated reels by content.

## Known Bugs

**Retry backoff calculates wrong delays:**
- Symptoms: The comment in `main.py` line 194 says "1s, 2s, 4s" but `2 ** attempt` with `attempt` starting at 0 yields 1, 2, 4 — this is correct for the exponentiation but the first wait is actually 1s (2^0=1), not the stated intent of starting at 2s. Minor, but the comment is misleading.
- Files: `main.py` (line 194)
- Trigger: Any callback failure triggers this path.
- Workaround: Functional but the comment should match the code.

**`get_viral_content_pool` ignores niche parameter:**
- Symptoms: The function accepts a `niche` parameter but the filter formula only checks `{Status}='New'` — it never uses the niche value. All niches get the same viral content pool.
- Files: `airtable_client.py` (lines 136-143)
- Trigger: Every generation request.
- Workaround: None. All clients currently receive all viral content regardless of niche.

## Security Considerations

**CORS allows all origins:**
- Risk: `main.py` line 54-59 configures CORS with `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. This allows any website to make authenticated requests to the API.
- Files: `main.py` (lines 54-59)
- Current mitigation: None.
- Recommendations: Restrict `allow_origins` to known domains (e.g., the Supabase Edge Function URL, the frontend domain). At minimum, define allowed origins via an env var.

**No authentication on API endpoints:**
- Risk: The `/generate` and `/generate-async` endpoints have zero authentication. Anyone who discovers the server URL can trigger arbitrary content generation, consuming Ollama compute and writing records to Airtable.
- Files: `main.py` (lines 250-293)
- Current mitigation: None. The `/generate-async` endpoint accepts a `webhook_secret` field, but this is sent *to* the callback, not used to authenticate the *incoming* request.
- Recommendations: Add API key authentication (e.g., `X-API-Key` header validated against an env var). Consider rate limiting per client.

**Airtable formula injection:**
- Risk: Client-supplied values (`client_name`, `niche`) are interpolated directly into Airtable `filterByFormula` strings using f-strings without escaping. A client name containing a single quote (`'`) would break the formula; a crafted value could potentially manipulate the query.
- Files: `airtable_client.py` (lines 113, 115, 124, 151-153, 179, 181, 196)
- Current mitigation: None.
- Recommendations: Escape single quotes in user-supplied values before interpolation (replace `'` with `\\'`), or use a formula-building helper that handles escaping.

**No .gitignore file:**
- Risk: The project has no `.gitignore`. The `.env` file (containing API keys), `.venv/` directory, and `__pycache__/` could be accidentally committed to version control.
- Files: Project root (missing `.gitignore`)
- Current mitigation: The project is not currently a git repo, but if initialized, secrets would be committed.
- Recommendations: Create a `.gitignore` immediately with entries for `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `.planning/`.

**Webhook secret sent in plaintext header:**
- Risk: The `X-Webhook-Secret` in `main.py` lines 174-175 is sent as a raw header value. If the callback URL uses HTTP (not HTTPS), the secret is transmitted in cleartext.
- Files: `main.py` (lines 174-175)
- Current mitigation: None.
- Recommendations: Validate that `callback_url` uses HTTPS. Consider HMAC-based signing of the payload instead of a shared secret header.

**Airtable API key in module-level constant:**
- Risk: `HEADERS` in `airtable_client.py` line 11-14 is constructed at import time as a module-level constant. This means the API key is baked into the dictionary at startup. If the key were rotated at runtime, the old key would persist until restart. More importantly, this constant is accessible to any code that imports the module.
- Files: `airtable_client.py` (lines 11-14)
- Current mitigation: None needed for current scale, but not best practice.
- Recommendations: Build headers in a function or use a session/client factory pattern.

## Performance Bottlenecks

**Synchronous `/generate` endpoint blocks for minutes:**
- Problem: The `/generate` endpoint in `main.py` (line 250-268) is synchronous — it blocks the HTTP response until all reels are generated by Ollama AND saved to Airtable. With a 300-second Ollama timeout and up to 30 sequential Airtable writes, this could take 5+ minutes.
- Files: `main.py` (lines 250-268), `ollama_client.py` (line 40, 300s timeout)
- Cause: The endpoint awaits the full `agent.generate_reels()` pipeline before responding.
- Improvement path: The `/generate-async` endpoint already exists as the better pattern. Consider deprecating `/generate` or adding a timeout/progress mechanism.

**No Airtable response caching:**
- Problem: Every generation request fetches the full client profile, all magnets, all viral hooks, the viral content pool, RTM events, style examples, and global insights from Airtable. For repeated requests for the same client, this is redundant.
- Files: `agent.py` (lines 54-80), `airtable_client.py` (all fetch functions)
- Cause: No caching layer exists. Each call creates a new `httpx.AsyncClient`.
- Improvement path: Add a TTL cache (e.g., `cachetools` or simple dict with timestamp) for client data, hooks, and insights. Even a 5-minute cache would significantly reduce API calls.

**New httpx client created for every single request:**
- Problem: Every Airtable and Ollama call creates a new `httpx.AsyncClient` via `async with httpx.AsyncClient() as client:`. This means a new TCP connection (and TLS handshake for Airtable's HTTPS) for every request.
- Files: `airtable_client.py` (lines 27, 61, 76, 97), `ollama_client.py` (lines 14, 40, 91)
- Cause: No persistent client/connection pooling.
- Improvement path: Create a shared `httpx.AsyncClient` instance at module level or app startup and reuse it. This enables HTTP/2 multiplexing and connection reuse.

**Viral hooks fallback fetches entire table:**
- Problem: In `airtable_client.py` lines 126-130, if no niche-filtered hooks are found, the function falls back to fetching ALL hooks with no filter. This could return thousands of records.
- Files: `airtable_client.py` (lines 126-130)
- Cause: Fallback logic with no limit.
- Improvement path: Add a `maxRecords` parameter or limit the fallback to a reasonable number (e.g., 50 random hooks).

## Fragile Areas

**JSON parsing from LLM output:**
- Files: `ollama_client.py` (lines 53-85)
- Why fragile: The `generate_json` function attempts to parse JSON from raw LLM output. It handles markdown fences and tries to find JSON within arbitrary text, but LLMs can produce subtly broken JSON (trailing commas, unescaped quotes in Hebrew text, truncated output at `num_predict` limit).
- Safe modification: Add unit tests for edge cases. Consider using Ollama's native JSON mode (`"format": "json"` in the API payload) which constrains output to valid JSON.
- Test coverage: Zero — no tests exist in the project at all.

**Prompt template with Hebrew mixed formatting:**
- Files: `prompts.py` (lines 16-101)
- Why fragile: The `BATCH_GENERATION_PROMPT` uses Python `.format()` with double-brace escaping (`{{`, `}}`) for the JSON template example. Any new field added to the JSON example must use double braces. The mix of Hebrew RTL text with English field names and JSON creates rendering/encoding edge cases.
- Safe modification: Consider using `string.Template` or Jinja2 instead of `.format()` to avoid double-brace escaping. Always test prompt changes with actual Ollama calls.
- Test coverage: None.

**Niche field extraction:**
- Files: `agent.py` (line 130), `main.py` (line 124)
- Why fragile: The niche field is extracted with `niche_raw[0] if isinstance(niche_raw, list) and niche_raw else niche_raw`. This same logic is duplicated in two files. If Airtable's field type changes or the extraction logic needs updating, both must be changed.
- Safe modification: Extract to a shared utility function.
- Test coverage: None.

**Background task error handling:**
- Files: `main.py` (lines 110-226)
- Why fragile: `_run_generation_and_callback` runs as a fire-and-forget `asyncio.create_task()` (line 289). If it fails silently (e.g., the error callback also fails at line 225), there is no record of the failure — no database entry, no retry queue, no monitoring alert.
- Safe modification: Add a task registry or persistent job queue (e.g., Redis + Celery, or at minimum log to a file/table). Track background task status.
- Test coverage: None.

## Scaling Limits

**Single-process architecture:**
- Current capacity: One Uvicorn worker (default). One Ollama call at a time due to sequential processing within each request.
- Limit: A single long-running generation blocks the worker. With `reload=True` in production (line 306), the server restarts on file changes.
- Scaling path: Deploy with multiple Uvicorn workers (`--workers N`). Remove `reload=True` for production. Consider a task queue for generation jobs.

**Airtable API rate limits:**
- Current capacity: Airtable allows 5 requests per second per base. A single 30-reel generation makes ~36 API calls (6 fetch + 30 save).
- Limit: Two concurrent generation requests would hit rate limits. No retry-on-429 logic exists.
- Scaling path: Add rate limiting awareness (respect `Retry-After` headers), batch saves properly, and implement request queuing.

**Ollama as sole LLM backend:**
- Current capacity: Depends entirely on the local Ollama instance and the `glm4:latest` model.
- Limit: Ollama runs on a single machine. No failover, no load balancing, no cloud fallback.
- Scaling path: Abstract the LLM client behind an interface. Add support for cloud LLM providers (OpenAI, Anthropic) as fallback or primary.

## Dependencies at Risk

**No pinned transitive dependencies:**
- Risk: `requirements.txt` pins direct dependencies but there is no lockfile (`pip freeze > requirements.lock` or `pip-tools`). Transitive dependencies are unpinned and could change between installs.
- Impact: Builds may not be reproducible. A breaking change in a transitive dependency could silently break the app.
- Migration plan: Use `pip-tools` (`pip-compile`) or `poetry` to generate a lockfile with pinned transitive dependencies.

**httpx used for everything:**
- Risk: `httpx` is used as the HTTP client for both Airtable API calls and Ollama local calls. While httpx is well-maintained, there is no abstraction layer — switching HTTP clients would require changing every file.
- Impact: Low immediate risk, but tight coupling.
- Migration plan: Not urgent, but if abstracting LLM calls (see Ollama scaling concern above), create a client abstraction.

## Missing Critical Features

**No authentication or authorization:**
- Problem: The API has zero auth. Any network-reachable client can trigger generation, consuming resources and writing to Airtable.
- Blocks: Cannot deploy to a public network safely. Cannot track which user/system triggered which generation.

**No test suite:**
- Problem: The project has zero test files. No unit tests, no integration tests, no test configuration.
- Blocks: Cannot refactor safely. Cannot validate prompt changes. Cannot catch regressions. Every change is deployed on faith.

**No input validation beyond Pydantic models:**
- Problem: While `GenerateRequest` validates basic types, there is no validation that `client_id` is a real Airtable record format (`rec[A-Za-z0-9]{14}`), that `batch_type` is valid in the sync endpoint (only validated in async), or that `callback_url` is a valid HTTPS URL.
- Blocks: Malformed requests produce confusing Airtable errors instead of clear 400 responses.

**No request/generation logging to persistent storage:**
- Problem: All logging goes to stdout only. There is no audit trail of what was generated, for whom, or when — beyond what Airtable records show.
- Blocks: Cannot debug production issues after the fact. Cannot analyze generation quality over time.

**No health monitoring or alerting:**
- Problem: The `/health` endpoint exists but nothing polls it. If Ollama goes down, the only signal is a warning at startup.
- Blocks: Cannot detect and recover from failures automatically.

## Test Coverage Gaps

**Entire codebase is untested:**
- What's not tested: Every function in every module. Zero test files exist in the project.
- Files: `agent.py`, `airtable_client.py`, `ollama_client.py`, `prompts.py`, `config.py`, `main.py`, `supabase_client.py`
- Risk: Any change can introduce regressions undetected. The JSON parsing logic in `ollama_client.py` and the distribution logic in `agent.py` are especially risky — they contain branching logic that should have test coverage.
- Priority: High. Start with:
  1. `ollama_client.py` `generate_json` — test markdown fence stripping and JSON extraction edge cases
  2. `agent.py` `_decide_distribution` — test all batch types and edge cases (quantity=1, no magnets, etc.)
  3. `prompts.py` format functions — test with empty inputs, special characters, very long text
  4. `airtable_client.py` `_fetch_all` — test pagination handling
  5. `main.py` API endpoints — test with FastAPI `TestClient`

---

*Concerns audit: 2026-03-11*
