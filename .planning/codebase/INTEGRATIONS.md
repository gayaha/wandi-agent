# External Integrations

**Analysis Date:** 2026-03-11

## APIs & External Services

### Ollama (Local LLM Inference)
- **Purpose:** Generate Instagram Reels content (hooks, scripts, captions) as structured JSON
- **Client:** Custom async HTTP client via `httpx` in `ollama_client.py`
- **Auth:** None (local service, no authentication)
- **Base URL env var:** `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- **Model env var:** `OLLAMA_MODEL` (default: `glm4:latest`)

**Endpoints used:**
| Endpoint | Method | Used In | Purpose |
|----------|--------|---------|---------|
| `/api/tags` | GET | `ollama_client.check_health()`, `ollama_client.list_models()` | Health check and model listing |
| `/api/generate` | POST | `ollama_client.generate()` | Text/JSON generation with LLM |

**Generation parameters (hardcoded in `ollama_client.py`):**
- `temperature`: 0.8
- `top_p`: 0.9
- `num_predict`: 4096
- `stream`: False

**Timeouts:**
- Health check: 5 seconds
- Model listing: 15 seconds
- Generation: 300 seconds (5 minutes)

**JSON parsing:** `ollama_client.generate_json()` strips markdown code fences and attempts multiple JSON extraction strategies (direct parse, find `{...}`, find `[...]`).

### Airtable (Data Storage & CMS)
- **Purpose:** Primary data store for clients, content, magnets, hooks, templates, and generated output
- **Client:** Custom async HTTP client via `httpx` in `airtable_client.py`
- **Auth:** Bearer token via `AIRTABLE_API_KEY` env var
- **Base URL:** `https://api.airtable.com/v0/{AIRTABLE_BASE_ID}`
- **Base ID env var:** `AIRTABLE_BASE_ID` (hardcoded default: `app8393BIwz7tRlR9`)

**Tables accessed (9 total):**

| Table | Config Constant | Operations | Used In |
|-------|----------------|------------|---------|
| Clients (`tblVUTKss5rnmH1P9`) | `TABLE_CLIENTS` | Read (single record by ID) | `airtable_client.get_client()` |
| Magnets | `TABLE_MAGNETS` | Read (filtered by client) | `airtable_client.get_magnets_for_client()` |
| viral hooks | `TABLE_VIRAL_HOOKS` | Read (filtered by niche, fallback to all) | `airtable_client.get_viral_hooks()` |
| Viral Content Pool | `TABLE_VIRAL_CONTENT_POOL` | Read (filtered by Status='New', sorted by views) | `airtable_client.get_viral_content_pool()` |
| RTM Events | `TABLE_RTM_EVENTS` | Read (filtered by niche + Status='Active') | `airtable_client.get_active_rtm_events()` |
| Reel Templates | `TABLE_REEL_TEMPLATES` | Read (filtered by content type/stage) | `airtable_client.get_reel_templates()` |
| Content Queue | `TABLE_CONTENT_QUEUE` | Write (batch create, 10 records per batch) | `airtable_client.save_reels_to_queue()` |
| Client Style Bank | `TABLE_CLIENT_STYLE_BANK` | Read (filtered by client, top performers, limit 5) | `airtable_client.get_top_style_examples()` |
| Global Insights | `TABLE_GLOBAL_INSIGHTS` | Read (filtered by niche, returns first match) | `airtable_client.get_global_insights()` |

**Airtable API patterns used:**
- Pagination handling via `offset` parameter in `_fetch_all()`
- Filter formulas via `filterByFormula` (uses `FIND()`, `ARRAYJOIN()`, `AND()`)
- Sort via `sort[N][field]` and `sort[N][direction]` query params
- Batch record creation in groups of 10 (Airtable API limit) via `_create_records_batch()`
- Single record fetch by ID via direct URL: `/{table}/{record_id}`

**Timeouts:**
- Read operations: 30 seconds
- Batch write operations: 60 seconds

### Webhook Callbacks (Outgoing)
- **Purpose:** Notify external systems when async content generation completes
- **Client:** `httpx.AsyncClient` in `main.py` `_run_generation_and_callback()`
- **Auth:** Optional shared secret via `X-Webhook-Secret` header
- **Retry logic:** 3 attempts with exponential backoff (1s, 2s, 4s)
- **Timeout:** 30 seconds per attempt (success), 15 seconds (error notification)
- **Payload format:**
  ```json
  {
    "user_id": "supabase-user-uuid",
    "connection_id": "meta-connection-uuid",
    "batch_id": "generated-uuid",
    "projects": [
      {
        "title": "...",
        "caption": "...",
        "video_text": "...",
        "hook": "...",
        "hook_type": "...",
        "verbal_script": "...",
        "format": "...",
        "awareness_stage": "...",
        "content_goal": "exposure|sales|mixed",
        "magnet_name": "...",
        "airtable_record_id": "...",
        "client_airtable_id": "...",
        "client_name": "...",
        "batch_id": "...",
        "status": "draft"
      }
    ]
  }
  ```

## Data Storage

**Primary Database:**
- Airtable (cloud-hosted, accessed via REST API)
- No traditional SQL/NoSQL database
- All data lives in 9 Airtable tables (see table above)
- Connection: `AIRTABLE_API_KEY` + `AIRTABLE_BASE_ID`
- Client: Custom `httpx`-based client in `airtable_client.py`

**File Storage:**
- Supabase Storage (planned, NOT yet implemented)
- Bucket: `rendered-videos` (configured via `SUPABASE_BUCKET`)
- `supabase_client.py` is a stub - `upload_video()` raises `NotImplementedError`
- Connection: `SUPABASE_URL` + `SUPABASE_KEY`
- The `supabase` Python SDK is NOT installed (not in `requirements.txt`)

**Caching:**
- None - Every request fetches fresh data from Airtable

## Authentication & Identity

**API Auth:**
- None - The FastAPI server has no authentication middleware
- CORS is fully open: `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`
- Webhook callbacks use optional `X-Webhook-Secret` header for basic auth

**External Service Auth:**
- Airtable: Personal access token via `Authorization: Bearer {token}` header
- Ollama: No auth (local service)
- Supabase: Anon key (planned, not yet active)

## Monitoring & Observability

**Error Tracking:**
- None - No Sentry, DataDog, or similar service integrated

**Logs:**
- Python `logging` module with `basicConfig`
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- Output: `sys.stdout`
- Level: Configurable via `LOG_LEVEL` env var (default: `info`)
- Each module creates its own logger via `logging.getLogger(__name__)`

**Health Check:**
- `GET /health` endpoint checks Ollama connectivity
- Returns: `{"status": "ok", "ollama": "connected|disconnected", "model": "..."}`

## CI/CD & Deployment

**Hosting:**
- Not detected - No Dockerfile, docker-compose, Procfile, or cloud deployment config
- Designed to run as a standalone uvicorn process

**CI Pipeline:**
- Not detected - No GitHub Actions, GitLab CI, or similar configuration

## Environment Configuration

**Required env vars (must be set for the app to function):**
- `AIRTABLE_API_KEY` - Airtable personal access token

**Optional env vars (have working defaults):**
- `AIRTABLE_BASE_ID` - defaults to `app8393BIwz7tRlR9`
- `OLLAMA_BASE_URL` - defaults to `http://localhost:11434`
- `OLLAMA_MODEL` - defaults to `glm4:latest`
- `HOST` - defaults to `0.0.0.0`
- `PORT` - defaults to `8000`
- `LOG_LEVEL` - defaults to `info`

**Future env vars (configured but not yet used):**
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon/service key
- `SUPABASE_BUCKET` - defaults to `rendered-videos`

**Secrets location:**
- `.env` file in project root (present, gitignored status unknown)
- `.env.example` provides template with placeholder values

## Webhooks & Callbacks

**Incoming:**
- `POST /generate` - Synchronous content generation (blocks until complete)
- `POST /generate-async` - Async generation, returns 202 immediately

**Outgoing:**
- Callback URL provided in `/generate-async` request body
- Posts generated content projects to `callback_url` when generation completes
- Also sends error notifications to `callback_url` if generation fails

## Knowledge Base

**SDMF Framework:**
- `SDMF_agent_knowledge.md` - 397-line marketing methodology document
- Defines the "Smart DM Funnel" content strategy framework
- Covers 5 awareness stages, content taxonomy, magnet types, and weekly content structure
- Referenced conceptually in the prompt templates (`prompts.py`) but NOT loaded dynamically at runtime
- The agent's prompts in `prompts.py` implement this framework through Hebrew-language prompt templates

## Integration Data Flow

```
[Client Request] --> [FastAPI main.py]
                          |
                          v
                    [agent.py] -- generates reels pipeline
                     /       \
                    v         v
        [airtable_client.py]  [ollama_client.py]
         (fetch context data)  (LLM generation)
                    \         /
                     v       v
              [airtable_client.py]
               (save to Content Queue)
                          |
                          v
              [Webhook Callback] (if async)
```

**Concurrent data fetching:** `agent._fetch_all_data()` uses `asyncio.gather()` to fetch 6 Airtable tables in parallel:
1. Magnets for client
2. Viral hooks by niche
3. Viral content pool
4. Active RTM events
5. Top style examples
6. Global insights

---

*Integration audit: 2026-03-11*
