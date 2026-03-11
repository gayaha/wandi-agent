# Phase 2: Python Integration Layer - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A Python `renderer/` module with `VideoRendererProtocol`, `RemotionRenderer` implementation, and a FastAPI endpoint — so Python code can submit a render job, poll to completion, and receive a URL saved as an Airtable attachment, without any Remotion-specific coupling in business logic.

This phase delivers the Python integration ONLY. Brand templates (Phase 3) and multi-segment text (Phase 4) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Rendered Video Storage Flow
- Remotion service renders MP4 to local disk, then Python downloads it and uploads to Supabase Storage
- Supabase Storage returns a public URL for the rendered video
- Python saves that public URL as an Airtable attachment on the existing Content Queue record
- Video URL only as attachment — no separate thumbnail (Airtable auto-generates preview)
- Rendered videos stored in a dedicated Supabase bucket (separate from raw source videos)

### Airtable Attachment
- Rendered video is added to the existing Content Queue record (the one created during text generation)
- Attachment field name on Content Queue table — Claude decides based on existing field naming patterns
- Use Airtable REST API directly (existing httpx pattern in `airtable_client.py`), not pyairtable library
- Airtable attachment API: PATCH the record with `[{"url": "https://..."}]` in the attachment field

### Render Trigger
- Separate explicit API endpoint (e.g., POST /render) — not auto-triggered after text generation
- Caller provides: Content Queue record ID + source video URL + optional overrides
- Caller is responsible for choosing which video to use (auto-selection is out of scope per PROJECT.md)
- Endpoint returns 202 + job ID immediately (async pattern, consistent with Remotion service and existing /generate-async)

### Notification Pattern
- Support both polling (GET /render-status/:id) AND callback webhook (caller provides callback_url)
- Matches the existing /generate-async callback pattern in main.py
- Default: polling. Callback is optional — provided by caller if they want push notification.

### Source Video Access
- Supabase raw source videos bucket access policy — Claude determines optimal approach (public bucket with direct URLs is simplest; signed URLs if bucket is private)
- Python generates the full Supabase Storage URL for the source video and passes it to the Remotion service
- Two separate Supabase buckets: one for raw source videos, one for rendered output videos
- Add `SUPABASE_SOURCE_BUCKET` env var to config.py (existing `SUPABASE_BUCKET` becomes the rendered output bucket)

### Protocol Abstraction (from INTG-02)
- `VideoRendererProtocol` defines the interface: `render()`, `get_status()`, `health_check()`
- `RemotionRenderer` implements the protocol by calling the Phase 1 HTTP service
- Any future renderer engine implements the same protocol — zero changes to FastAPI endpoint or calling code
- Protocol lives in `renderer/protocol.py`, implementation in `renderer/remotion.py`

### Module Structure
- New `renderer/` package at project root (follows existing flat structure pattern)
- `renderer/__init__.py` — exports protocol and factory
- `renderer/protocol.py` — VideoRendererProtocol definition
- `renderer/remotion.py` — RemotionRenderer implementation (httpx async client)
- `renderer/models.py` — Pydantic models for render requests/responses
- New route added to `main.py` (follows existing route pattern)
- `REMOTION_SERVICE_URL` env var added to config.py

### Claude's Discretion
- Exact Pydantic model field names and validation rules
- HTTP timeout values for Remotion service calls
- Error response format and status codes
- Retry strategy for Remotion service communication
- Supabase upload implementation details (client library vs raw httpx)
- Protocol method signatures (exact parameters and return types)
- Job state tracking implementation (in-memory dict vs persistent)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `airtable_client.py`: Full CRUD client with `_create_record()` and `_update_record()` — can add attachment update function
- `supabase_client.py`: Stub exists with `upload_video()` signature — needs implementation for rendered video upload
- `config.py`: Env var pattern established — add `REMOTION_SERVICE_URL`, `SUPABASE_SOURCE_BUCKET`
- `main.py`: Existing async background task pattern (`_run_generation_and_callback`) with retry and callback — reusable pattern

### Established Patterns
- External service clients: `{service}_client.py` with async httpx, per-call client instances, explicit timeouts
- Pydantic models co-located with routes in `main.py`
- `asyncio.create_task()` for fire-and-forget background work
- Error propagation: specific errors bubble up, caught at route level (ValueError→400, Exception→500)
- Retry with exponential backoff: 3 attempts, `2 ** attempt` seconds (from callback pattern)

### Integration Points
- `main.py`: Add POST /render and GET /render-status/:id routes
- `config.py`: Add REMOTION_SERVICE_URL, SUPABASE_SOURCE_BUCKET env vars
- `airtable_client.py`: Add function to update record with video attachment
- `supabase_client.py`: Implement upload_video() for rendered video storage
- Phase 1 Remotion service: POST /renders (input: sourceVideoUrl, hookText, bodyText) → 202 + jobId, GET /renders/:id → status + outputUrl

</code_context>

<specifics>
## Specific Ideas

- The existing /generate-async endpoint uses a callback pattern — the render endpoint should feel consistent with this
- Supabase bucket config already exists in config.py (`SUPABASE_BUCKET = "rendered-videos"`) — this becomes the output bucket
- The `supabase_client.py` stub already has the `upload_video()` signature with file_path and destination params
- Content Queue record ID ties text content to rendered video — keeps everything on one record

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-python-integration-layer*
*Context gathered: 2026-03-11*
