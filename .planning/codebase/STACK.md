# Technology Stack

**Analysis Date:** 2026-03-11

## Languages

**Primary:**
- Python 3.14 - All application code (agent logic, API server, clients)

**Secondary:**
- None - Single-language project

## Runtime

**Environment:**
- Python 3.14.3 (CPython)
- Virtual environment at `.venv/` (venv module)

**Package Manager:**
- pip
- Lockfile: None (only `requirements.txt` with pinned versions, no `requirements.lock` or `poetry.lock`)

## Frameworks

**Core:**
- FastAPI 0.115.6 - HTTP API server (`main.py`)
- Pydantic 2.10.4 - Request/response validation and data models (`main.py`)

**Testing:**
- Not detected - No test framework in `requirements.txt`, no test files present

**Build/Dev:**
- uvicorn 0.34.0 (with `[standard]` extras) - ASGI server (`main.py`)

## Key Dependencies

**Critical (in `requirements.txt`):**
- `fastapi==0.115.6` - Web framework powering all API endpoints
- `uvicorn[standard]==0.34.0` - Production ASGI server with lifespan support
- `httpx==0.28.1` - Async HTTP client used for ALL external API calls (Ollama, Airtable)
- `pydantic==2.10.4` - Data validation for API request/response models
- `python-dotenv==1.0.1` - Environment variable loading from `.env` file

**Infrastructure:**
- No ORM, no database driver, no task queue - All external communication is via raw HTTP (`httpx`)

**Not in requirements.txt but referenced in code (future):**
- `supabase` Python SDK - Referenced in commented code in `supabase_client.py` but NOT installed

## Configuration

**Environment:**
- Configured via `.env` file loaded by `python-dotenv` in `config.py`
- `.env.example` provides template with all required variables
- All config values accessed via `config.py` module (single source of truth)

**Required Environment Variables:**
- `AIRTABLE_API_KEY` - Airtable personal access token (required, no default)
- `AIRTABLE_BASE_ID` - Airtable base identifier (has hardcoded default: `app8393BIwz7tRlR9`)
- `OLLAMA_BASE_URL` - Ollama API endpoint (default: `http://localhost:11434`)
- `OLLAMA_MODEL` - LLM model name (default: `glm4:latest`)
- `SUPABASE_URL` - Supabase project URL (required for future features, no default)
- `SUPABASE_KEY` - Supabase anon key (required for future features, no default)
- `SUPABASE_BUCKET` - Supabase storage bucket name (default: `rendered-videos`)
- `HOST` - Server bind address (default: `0.0.0.0`)
- `PORT` - Server port (default: `8000`)
- `LOG_LEVEL` - Logging level (default: `info`)

**Build:**
- No build step required - Pure Python, run directly
- Entry point: `python main.py` or `uvicorn main:app`
- Dev mode uses `uvicorn` with `reload=True`

## Application Metadata

**Version:** 1.1.0 (defined in `main.py` FastAPI app constructor)
**Title:** wandi-agent
**Description:** AI agent for generating Instagram Reels content

## Platform Requirements

**Development:**
- Python 3.14+ (uses `str | None` union syntax, `type[X]` lowercase generics)
- Ollama running locally on port 11434 (or remote instance)
- Airtable account with configured base and tables
- No Docker configuration detected

**Production:**
- ASGI-capable host (uvicorn included)
- Network access to Ollama instance and Airtable API
- `.env` file or environment variables configured

## Airtable Table Configuration

Airtable table identifiers are hardcoded as constants in `config.py`:
- `TABLE_CLIENTS` = `tblVUTKss5rnmH1P9`
- `TABLE_MAGNETS` = `Magnets`
- `TABLE_VIRAL_HOOKS` = `viral hooks`
- `TABLE_VIRAL_CONTENT_POOL` = `Viral Content Pool`
- `TABLE_RTM_EVENTS` = `RTM Events`
- `TABLE_REEL_TEMPLATES` = `Reel Templates`
- `TABLE_CONTENT_QUEUE` = `Content Queue`
- `TABLE_CLIENT_STYLE_BANK` = `Client Style Bank`
- `TABLE_GLOBAL_INSIGHTS` = `Global Insights`

---

*Stack analysis: 2026-03-11*
