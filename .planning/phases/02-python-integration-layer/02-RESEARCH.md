# Phase 2: Python Integration Layer - Research

**Researched:** 2026-03-11
**Domain:** Python/FastAPI async job pattern, Pydantic Protocol abstraction, httpx streaming, Supabase Storage upload, Airtable attachment API
**Confidence:** HIGH (core patterns); MEDIUM (Airtable URL attachment, Supabase upload API)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Rendered Video Storage Flow:**
- Remotion service renders MP4 to local disk, then Python downloads it and uploads to Supabase Storage
- Supabase Storage returns a public URL for the rendered video
- Python saves that public URL as an Airtable attachment on the existing Content Queue record
- Video URL only as attachment — no separate thumbnail (Airtable auto-generates preview)
- Rendered videos stored in a dedicated Supabase bucket (separate from raw source videos)

**Airtable Attachment:**
- Rendered video is added to the existing Content Queue record (the one created during text generation)
- Attachment field name on Content Queue table — Claude decides based on existing field naming patterns
- Use Airtable REST API directly (existing httpx pattern in `airtable_client.py`), NOT pyairtable library
- Airtable attachment API: PATCH the record with `[{"url": "https://..."}]` in the attachment field

**Render Trigger:**
- Separate explicit API endpoint (e.g., POST /render) — not auto-triggered after text generation
- Caller provides: Content Queue record ID + source video URL + optional overrides
- Caller is responsible for choosing which video to use (auto-selection is out of scope per PROJECT.md)
- Endpoint returns 202 + job ID immediately (async pattern, consistent with Remotion service and existing /generate-async)

**Notification Pattern:**
- Support both polling (GET /render-status/:id) AND callback webhook (caller provides callback_url)
- Matches the existing /generate-async callback pattern in main.py
- Default: polling. Callback is optional — provided by caller if they want push notification.

**Source Video Access:**
- Supabase raw source videos bucket access policy — Claude determines optimal approach (public bucket with direct URLs is simplest; signed URLs if bucket is private)
- Python generates the full Supabase Storage URL for the source video and passes it to the Remotion service
- Two separate Supabase buckets: one for raw source videos, one for rendered output videos
- Add `SUPABASE_SOURCE_BUCKET` env var to config.py (existing `SUPABASE_BUCKET` becomes the rendered output bucket)

**Protocol Abstraction (INTG-02):**
- `VideoRendererProtocol` defines the interface: `render()`, `get_status()`, `health_check()`
- `RemotionRenderer` implements the protocol by calling the Phase 1 HTTP service
- Any future renderer engine implements the same protocol — zero changes to FastAPI endpoint or calling code
- Protocol lives in `renderer/protocol.py`, implementation in `renderer/remotion.py`

**Module Structure:**
- New `renderer/` package at project root (follows existing flat structure pattern)
- `renderer/__init__.py` — exports protocol and factory
- `renderer/protocol.py` — VideoRendererProtocol definition
- `renderer/models.py` — Pydantic models for render requests/responses
- `renderer/remotion.py` — RemotionRenderer implementation (httpx async client)
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTG-01 | Python backend exposes an HTTP endpoint that accepts render requests (text segments + video URL + template config) and returns a job ID | FastAPI POST /render with 202 + UUID job_id; asyncio.create_task pattern from existing /generate-async |
| INTG-02 | Python backend defines a `VideoRendererProtocol` abstraction that can be implemented by any rendering engine | `typing.Protocol` with `@runtime_checkable`; protocol methods: render(), get_status(), health_check() |
| INTG-03 | Rendered MP4 is accessible via URL and saved as an Airtable attachment on the content queue record | Airtable PATCH record with `[{"url": "..."}]` in attachment field; Supabase public URL as the accessible URL |
| INTG-04 | Raw source video is fetched from Supabase Storage at render time using the video URL | Python passes Supabase public URL to Remotion service; Remotion pre-downloads it (already implemented in Phase 1 render-queue.ts) |
| INTG-05 | Render API uses async job pattern (HTTP 202 + polling/callback) to handle 30-300 second render times without timeout | Two-tier async: Python job tracks Remotion job_id; polling loop in background task; GET /render-status/:id returns Python job state |
</phase_requirements>

---

## Summary

Phase 2 builds the Python bridge between the FastAPI backend and the Phase 1 Remotion service. The architecture is a two-tier async job pattern: the Python FastAPI endpoint immediately returns a job ID (202), launches a background task that polls the Remotion service until completion, then downloads the rendered MP4 from the Remotion service, uploads it to Supabase Storage, and patches the Airtable record with the public URL.

The `VideoRendererProtocol` uses Python's `typing.Protocol` — structural subtyping that requires no inheritance and is verifiable at runtime via `@runtime_checkable`. The `RemotionRenderer` implementation wraps the Phase 1 HTTP API (POST /renders, GET /renders/:id) using the existing `httpx` library already in requirements.txt.

A critical architectural detail discovered during research: the Phase 1 Remotion service stores `videoUrl` as a **local disk path** (`/tmp/renders/{jobId}.mp4`), not an HTTP URL. To allow Python to download the rendered file, the Remotion service must expose a file-serving endpoint (e.g., GET /renders/:id/file or via `express.static` on `/tmp/renders`). This endpoint must be added in Plan 02-02 as part of the Remotion service integration work.

**Primary recommendation:** Use `typing.Protocol` + `asyncio.create_task` + `httpx.AsyncClient` with in-memory job dict. Implement Supabase upload via the `supabase` PyPI package (v2.28.0, already well-supported). Add a file-serving endpoint to the Remotion Express service so Python can stream the rendered MP4.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 (already installed) | All HTTP calls to Remotion service + download rendered file | Already in requirements.txt; native async support matches FastAPI's event loop |
| fastapi | 0.135.1 (already installed) | New POST /render and GET /render-status/:id routes | Already the project's web framework |
| pydantic | 2.12.5 (already installed) | RenderRequest, JobStatus, RenderResponse models | Already in use for all existing models in main.py |
| typing.Protocol | stdlib | VideoRendererProtocol definition — structural subtyping | Standard library; no dependencies; `@runtime_checkable` enables isinstance() checks |
| asyncio | stdlib | asyncio.create_task() for fire-and-forget background render task | Already used in main.py for /generate-async; identical pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| supabase | 2.28.0 (NOT yet installed) | Upload rendered MP4 to Supabase Storage after download | Use for implemented upload_video() in supabase_client.py; clean API with get_public_url() |
| aiofiles | 24.x (optional) | Async file writes when downloading rendered MP4 from Remotion | Use if streaming httpx download to disk needs async file I/O; otherwise sync write is acceptable in asyncio background task |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| supabase (PyPI) | Raw httpx to Supabase Storage REST API | Raw httpx avoids a dependency but requires manual auth header construction and URL building; supabase-py wraps this cleanly and get_public_url() is one-liner |
| typing.Protocol | ABC (Abstract Base Class) | ABC requires explicit inheritance; Protocol uses structural typing (duck typing) which fits "any renderer engine, zero code changes" constraint better |
| In-memory job dict | Redis/database | In-memory is sufficient for single-process MVP; loses state on restart (acceptable — renders are retriggerable) |
| asyncio.create_task | FastAPI BackgroundTasks | BackgroundTasks runs after response; asyncio.create_task() matches existing /generate-async pattern in the codebase; consistent approach |

**Installation:**
```bash
pip install supabase==2.28.0
```
Add to requirements.txt: `supabase==2.28.0`

---

## Architecture Patterns

### Recommended Project Structure
```
renderer/                    # New package — Python integration layer
├── __init__.py              # Exports VideoRendererProtocol, RemotionRenderer, get_renderer()
├── protocol.py              # VideoRendererProtocol (typing.Protocol), RenderJob dataclass
├── models.py                # Pydantic models: RenderRequest, JobStatus, RenderResponse
└── remotion.py              # RemotionRenderer implementation (httpx async client)

# Modified files:
main.py                      # Add POST /render, GET /render-status/:id routes
config.py                    # Add REMOTION_SERVICE_URL, SUPABASE_SOURCE_BUCKET env vars
airtable_client.py           # Add update_content_queue_video_attachment() function
supabase_client.py           # Implement upload_video() — was a stub

# Remotion service (Phase 1 — minor addition):
remotion-service/server/index.ts   # Add GET /renders/:id/file endpoint to serve rendered MP4
```

### Pattern 1: VideoRendererProtocol — Structural Typing
**What:** A `typing.Protocol` class defines the renderer interface. Any class with matching method signatures satisfies the protocol — no inheritance required.
**When to use:** Always. Enables INTG-02 (swap renderer engine without changing calling code).
**Example:**
```python
# renderer/protocol.py
# Source: Python docs — https://docs.python.org/3/library/typing.html#typing.Protocol
from typing import Protocol, runtime_checkable
from renderer.models import RenderRequest, JobStatus

@runtime_checkable
class VideoRendererProtocol(Protocol):
    async def render(self, request: RenderRequest) -> str:
        """Submit a render job. Returns job_id."""
        ...

    async def get_status(self, job_id: str) -> JobStatus:
        """Poll status by job_id."""
        ...

    async def health_check(self) -> bool:
        """Returns True if renderer service is reachable."""
        ...
```

### Pattern 2: Two-Tier Async Job — Python job wraps Remotion job
**What:** Python endpoint creates its own job_id, stores it in an in-memory dict, launches a background task that calls Remotion, polls until done, downloads/uploads, then updates the Python job dict. Caller polls Python's GET /render-status/:id endpoint.
**When to use:** Always — this is the mandatory async pattern for INTG-05.
**Example:**
```python
# In main.py — follows existing /generate-async pattern
import uuid
from typing import Any

# In-memory job store (module-level, single process)
_render_jobs: dict[str, dict[str, Any]] = {}

@app.post("/render", status_code=202)
async def submit_render(request: RenderRequest):
    job_id = str(uuid.uuid4())
    _render_jobs[job_id] = {"status": "accepted", "created_at": ..., "record_id": request.record_id}
    asyncio.create_task(_run_render(job_id, request))
    return {"job_id": job_id, "status": "accepted"}

@app.get("/render-status/{job_id}")
async def get_render_status(job_id: str):
    job = _render_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

### Pattern 3: RemotionRenderer — httpx Async Client
**What:** `RemotionRenderer` implements `VideoRendererProtocol` by calling the Phase 1 Remotion Express service via httpx. Uses per-call AsyncClient instances (matches existing airtable_client.py pattern).
**When to use:** Always — this is the concrete implementation for Remotion.
**Example:**
```python
# renderer/remotion.py
import httpx
import config

class RemotionRenderer:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.REMOTION_SERVICE_URL

    async def render(self, request: RenderRequest) -> str:
        payload = {
            "sourceVideoUrl": request.source_video_url,
            "hookText": request.hook_text,
            "bodyText": request.body_text,
            "textDirection": request.text_direction,
            "animationStyle": request.animation_style,
            "durationInSeconds": request.duration_in_seconds,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{self.base_url}/renders", json=payload)
            resp.raise_for_status()
            return resp.json()["jobId"]

    async def get_status(self, job_id: str) -> JobStatus:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/renders/{job_id}")
            resp.raise_for_status()
            data = resp.json()
            return JobStatus(
                state=data["state"],
                progress=data.get("progress", 0),
                video_url=data.get("videoUrl"),
                error=data.get("error"),
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
```

### Pattern 4: Polling Loop with Exponential Backoff in Background Task
**What:** Background task polls Remotion's GET /renders/:id in a loop until state is "completed" or "failed", with exponential backoff.
**When to use:** In the `_run_render()` background coroutine.
**Example:**
```python
# In _run_render() background coroutine
MAX_POLL_ATTEMPTS = 120   # 120 attempts × up to 5s backoff = up to 10 minutes
for attempt in range(MAX_POLL_ATTEMPTS):
    status = await renderer.get_status(remotion_job_id)
    if status.state == "completed":
        break
    elif status.state == "failed":
        raise RuntimeError(f"Remotion render failed: {status.error}")
    wait = min(2 + attempt, 5)   # ramp from 2s to 5s cap
    await asyncio.sleep(wait)
```

### Pattern 5: Downloading Rendered File from Remotion Service
**What:** After Remotion reports state="completed", Python downloads the rendered MP4 via an HTTP endpoint on the Remotion service (NOT from the local disk path in `videoUrl`).
**When to use:** Always — `videoUrl` in Remotion's job state is a local path, not accessible from Python.

**CRITICAL: Remotion service must expose a file-serving endpoint.** Add to `remotion-service/server/index.ts`:
```typescript
// In server/index.ts — add after the queue is initialized
import path from "node:path";

// Serve rendered files from /tmp/renders
app.get("/renders/:id/file", (req, res) => {
  const filePath = path.join("/tmp/renders", `${req.params.id}.mp4`);
  const job = queue.getJob(req.params.id);
  if (!job || job.state !== "completed") {
    res.status(404).json({ error: "Render not complete or not found" });
    return;
  }
  res.download(filePath, `${req.params.id}.mp4`);
});
```

Then Python downloads it:
```python
# Stream download rendered MP4 from Remotion service
import tempfile

async def _download_rendered_video(remotion_job_id: str) -> str:
    """Download rendered MP4 from Remotion service to a temp file. Returns local path."""
    url = f"{config.REMOTION_SERVICE_URL}/renders/{remotion_job_id}/file"
    tmp_path = f"/tmp/{remotion_job_id}-rendered.mp4"
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(tmp_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
    return tmp_path
```

### Pattern 6: Supabase Upload via supabase-py
**What:** Implement `supabase_client.upload_video()` stub using `supabase` library. Returns public URL constructed from SUPABASE_URL + bucket + path.
**When to use:** For rendered video upload; existing stub matches this signature.
**Example:**
```python
# supabase_client.py — implement the existing stub
from supabase import create_client, Client

async def upload_video(file_path: str, destination: str) -> str:
    """Upload a rendered video to Supabase Storage. Returns public URL."""
    client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    with open(file_path, "rb") as f:
        client.storage.from_(config.SUPABASE_BUCKET).upload(
            path=destination,
            file=f,
            file_options={"content-type": "video/mp4", "upsert": "true"},
        )
    return client.storage.from_(config.SUPABASE_BUCKET).get_public_url(destination)
```

### Pattern 7: Airtable URL-Based Attachment PATCH
**What:** PATCH the Content Queue record's attachment field with `[{"url": "https://..."}]`. Airtable fetches the file from that URL and stores its own copy.
**When to use:** After Supabase upload returns a public URL.
**Example:**
```python
# airtable_client.py — new function
async def update_content_queue_video_attachment(record_id: str, video_url: str) -> dict:
    """Add rendered video URL as attachment on a Content Queue record."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(
            f"{BASE_URL}/{config.TABLE_CONTENT_QUEUE}/{record_id}",
            headers=HEADERS,
            json={"fields": {"Rendered Video": [{"url": video_url}]}},
        )
        resp.raise_for_status()
        return resp.json()
```

Note: "Rendered Video" is the proposed attachment field name — follows the project's English field naming convention (e.g., "Content Queue" has fields like "Hook Text", "Body Text").

### Anti-Patterns to Avoid
- **Synchronous Remotion polling:** Never use `httpx.Client` (sync) inside an async background task — blocks the event loop. Always use `httpx.AsyncClient`.
- **Direct disk path access:** Never treat Remotion's `videoUrl` field as an accessible URL — it's a local path on the Node.js container. Always use the HTTP download endpoint.
- **Awaiting the background task in the route handler:** Never `await asyncio.create_task(...)` in the /render endpoint — defeats the 202 async pattern.
- **Storing job state on the task object:** Use a module-level dict for job state, not on the asyncio.Task object. Tasks can be garbage-collected.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Supabase file upload | Manual httpx POST to storage API with auth headers | `supabase` PyPI library v2.28.0 | Handles auth, multipart encoding, retry; get_public_url() is built-in |
| Protocol/interface definition | Custom abstract base class with inheritance | `typing.Protocol` + `@runtime_checkable` | Standard library; no inheritance needed; isinstance() works; mypy verifiable |
| Polling with backoff | Custom while loop with manual sleep math | Simple `asyncio.sleep()` loop with min(2+attempt, 5) cap | Sufficient at this scale; Remotion renders in 30-300s; 120 attempts × 5s = 10 min max |
| Airtable attachment format | File bytes upload to Airtable | PATCH with `[{"url": "..."}]` | Airtable fetches by URL; no size limits for caller; Airtable handles storage |
| Async background task | Thread pool / concurrent.futures | `asyncio.create_task()` | Already proven in /generate-async; FastAPI is async-native; no threading complexity |

**Key insight:** The entire Python side of this integration is "async wiring" — submitting jobs, polling, piping bytes between services. Use stdlib asyncio + existing httpx throughout. The only new dependency is `supabase` for the storage upload.

---

## Common Pitfalls

### Pitfall 1: Remotion videoUrl is a Local Disk Path, Not an HTTP URL
**What goes wrong:** Python tries to fetch `job.videoUrl` from Remotion's GET /renders/:id response and gets a local file path like `/tmp/renders/{jobId}.mp4`. Python cannot download from a file system path on a separate container.
**Why it happens:** Phase 1 implemented render-queue.ts to store `videoUrl: outputPath` where outputPath is a local path. This was correct for Phase 1 (smoke test reads the file directly) but does not expose an HTTP endpoint for Python to consume.
**How to avoid:** Add GET /renders/:id/file endpoint to the Remotion Express service using `res.download(filePath)`. This must be the first task of Plan 02-02.
**Warning signs:** Python's httpx receives a 404 when trying to fetch the "URL" from the status response, or the URL value starts with `/tmp/`.

### Pitfall 2: In-Memory Job Dict Lost on Process Restart
**What goes wrong:** Python process restarts; all in-progress render jobs are lost. Callers polling status get 404.
**Why it happens:** Module-level dict is ephemeral. `asyncio.create_task()` tasks are also cancelled on shutdown.
**How to avoid:** Accept this for MVP — renders are retriggerable. Document the limitation. Log job_id + Remotion job_id so lost jobs can be manually tracked. Add startup health check that verifies Remotion is reachable.
**Warning signs:** Only manifests after process restart; normal operations fine.

### Pitfall 3: asyncio.create_task() Reference Lost — Task Garbage Collected
**What goes wrong:** Background render task gets garbage collected before completing. The job status never transitions from "accepted" to a terminal state.
**Why it happens:** `asyncio.create_task()` returns a Task object. If no reference is kept, CPython may garbage-collect it mid-execution in some event loop implementations.
**How to avoid:** Store the task reference in a module-level set. Example:
```python
_background_tasks: set = set()

task = asyncio.create_task(_run_render(job_id, request))
_background_tasks.add(task)
task.add_done_callback(_background_tasks.discard)
```
FastAPI's official docs recommend this pattern.
**Warning signs:** Jobs that start but never complete, with no error logged.

### Pitfall 4: supabase-py Not Installed — Only httpx in requirements.txt
**What goes wrong:** `from supabase import create_client` raises ImportError at runtime. Current requirements.txt has no supabase entry.
**Why it happens:** supabase-py was never installed in this project — `supabase_client.py` was a stub that raised NotImplementedError.
**How to avoid:** Add `supabase==2.28.0` to requirements.txt as the first task of Plan 02-03.
**Warning signs:** ImportError on server startup if supabase_client.py is imported at module level.

### Pitfall 5: Airtable Attachment URL Must Be Publicly Accessible
**What goes wrong:** Airtable PATCH with a private Supabase signed URL succeeds (HTTP 200) but the attachment never appears in Airtable, or appears briefly then expires.
**Why it happens:** Airtable fetches the file from the provided URL server-side. If the URL is a Supabase signed URL that expires in 60 seconds, Airtable may not finish fetching before expiry. Private bucket URLs require auth headers Airtable cannot provide.
**How to avoid:** Store rendered videos in a **public** Supabase bucket. Use `get_public_url()` which returns a permanent public URL. Rendered videos are output artifacts — public access is acceptable for this use case.
**Warning signs:** Airtable attachment field shows URL that returns 403 when accessed in browser. Or the attachment shows in Airtable immediately but disappears later.

### Pitfall 6: Polling Timeout Without Upper Bound
**What goes wrong:** Remotion render hangs (service crash, disk full, etc.) and the Python background task polls forever, consuming memory and preventing job cleanup.
**Why it happens:** Render errors that don't update the job state (service crash) leave the job stuck in "queued" or "in-progress".
**How to avoid:** Enforce `MAX_POLL_ATTEMPTS` (e.g., 120 attempts × 5s = 10 minutes max). After exceeding, mark the Python job as "timed_out" and log the Remotion job_id for manual inspection.
**Warning signs:** Memory growth on the Python process; job IDs accumulating in _render_jobs dict indefinitely.

### Pitfall 7: Supabase Bucket Must Exist Before Upload
**What goes wrong:** `upload()` call raises a storage error because the rendered-videos bucket doesn't exist yet.
**Why it happens:** Supabase buckets must be created before use; the `supabase` library does not auto-create buckets.
**How to avoid:** Verify both `rendered-videos` and `SUPABASE_SOURCE_BUCKET` buckets exist in Supabase dashboard before running Phase 2. Add bucket validation to the startup health check.
**Warning signs:** StorageException with "bucket not found" on first upload attempt.

---

## Code Examples

Verified patterns from existing codebase and official sources:

### Existing Background Task Pattern (from main.py — replicate this)
```python
# Source: /Users/openclaw/wandi-agent/main.py (lines 110-226)
# This pattern is PROVEN in the codebase — Phase 2 replicates it for renders

@app.post("/generate-async", status_code=202)
async def generate_async(request: GenerateAsyncRequest):
    # Validate, then fire-and-forget
    asyncio.create_task(_run_generation_and_callback(request))
    return {"status": "accepted", "message": "..."}

async def _run_generation_and_callback(request: GenerateAsyncRequest):
    # Retry with exponential backoff: 3 attempts, 2**attempt seconds
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(request.callback_url, json=payload, headers=headers)
                resp.raise_for_status()
                return
        except Exception as e:
            await asyncio.sleep(2 ** attempt)
```

### Airtable PATCH with Attachment URL (from community docs, verified format)
```python
# Source: Airtable Web API — https://airtable.com/developers/web/api/update-record
# Attachment field: array of objects with "url" key. Airtable fetches by URL.
async with httpx.AsyncClient(timeout=30) as client:
    resp = await client.patch(
        f"https://api.airtable.com/v0/{base_id}/{table}/{record_id}",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"fields": {"Rendered Video": [{"url": video_url}]}},
    )
    resp.raise_for_status()
```

### Supabase Upload + Get Public URL
```python
# Source: https://supabase.com/docs/reference/python/storage-from-upload
# + https://supabase.com/docs/reference/python/storage-from-getpublicurl
from supabase import create_client

client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# Upload (synchronous — acceptable in async background task)
with open(local_path, "rb") as f:
    client.storage.from_(config.SUPABASE_BUCKET).upload(
        path=destination,      # e.g. "rec123/render_abc.mp4"
        file=f,
        file_options={"content-type": "video/mp4", "upsert": "true"},
    )

# Get public URL (permanent, no expiry — requires public bucket)
public_url = client.storage.from_(config.SUPABASE_BUCKET).get_public_url(destination)
# Returns: "https://{project}.supabase.co/storage/v1/object/public/{bucket}/{destination}"
```

### Express.js File Serving Endpoint (Remotion service addition)
```typescript
// Source: Express.js docs — https://expressjs.com/en/api.html#res.download
// Add to remotion-service/server/index.ts after queue initialization

app.get("/renders/:id/file", (req, res) => {
  const job = queue.getJob(req.params.id);
  if (!job || job.state !== "completed") {
    res.status(404).json({ error: "Render not complete" });
    return;
  }
  const filePath = path.join("/tmp/renders", `${req.params.id}.mp4`);
  res.download(filePath, `${req.params.id}.mp4`, (err) => {
    if (err) {
      res.status(500).json({ error: "File not found on disk" });
    }
  });
});
```

### Protocol with @runtime_checkable
```python
# Source: https://docs.python.org/3/library/typing.html#typing.Protocol
from typing import Protocol, runtime_checkable

@runtime_checkable
class VideoRendererProtocol(Protocol):
    async def render(self, request: "RenderRequest") -> str: ...
    async def get_status(self, job_id: str) -> "JobStatus": ...
    async def health_check(self) -> bool: ...

# Works with isinstance() at runtime:
renderer = RemotionRenderer()
assert isinstance(renderer, VideoRendererProtocol)  # True without inheritance
```

### Task Reference Safety Pattern
```python
# Source: FastAPI docs — https://fastapi.tiangolo.com/tutorial/background-tasks/
# Prevents garbage collection of asyncio tasks

_background_tasks: set = set()

def _submit_background_task(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ABC for interfaces | `typing.Protocol` (structural subtyping) | Python 3.8+ (PEP 544) | No inheritance needed; "satisfies protocol" by having matching methods |
| `requests` library (sync) | `httpx.AsyncClient` | FastAPI era (2019+) | Non-blocking; required for async route handlers |
| Synchronous Supabase calls | `supabase` client (sync acceptable in background tasks) | supabase-py v2.x | Sync storage calls acceptable within asyncio.create_task (not in route handlers) |
| Airtable direct byte upload | URL-based attachment via PATCH | Always preferred | No size limits for caller; Airtable handles storage |

**Deprecated/outdated:**
- `pyairtable` library: Not used (user decision — use httpx directly like existing airtable_client.py)
- `requests` library: Not in requirements.txt — httpx is the project's HTTP client

---

## Open Questions

1. **Airtable "Rendered Video" field — does it exist?**
   - What we know: CONTEXT.md says "Claude decides based on existing field naming patterns". The project's Airtable base has a "Content Queue" table with fields like "Hook Text", "Body Text".
   - What's unclear: The exact field name in the Airtable base. If the field doesn't exist, the PATCH will silently fail (Airtable ignores unknown fields) or create a new text field rather than an attachment field.
   - Recommendation: In Plan 02-03, add a test PATCH early and verify the Airtable API response confirms the attachment was stored. If needed, create the "Rendered Video" attachment field in Airtable dashboard before implementing.

2. **Supabase source bucket — public or private?**
   - What we know: CONTEXT.md says Claude determines optimal approach. Phase 1's render-queue.ts already downloads from a URL — so the source video URL must be accessible from the Node.js container.
   - What's unclear: Whether the raw source videos bucket is currently public or private.
   - Recommendation: Default to **public bucket URLs** for source videos (simplest; no expiry; Remotion service can download without auth). If security requires private, use 10-minute+ signed URLs. Document in config.py comment.

3. **Supabase upload — sync vs async client?**
   - What we know: `supabase-py` has a sync client; async uploads require `AsyncClient` which may have different API. The background task runs in asyncio context.
   - What's unclear: Whether async Supabase client (httpx-based) is the correct choice or sync within asyncio background task is acceptable.
   - Recommendation: Use **sync client** within the asyncio background task (wrapped in `asyncio.get_event_loop().run_in_executor(None, ...)` if needed, or just directly — sync file I/O in a background task does not block route handlers). Simpler; avoids async client API surface.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (NOT yet installed — Wave 0 gap) |
| Config file | None — needs `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` section |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTG-01 | POST /render returns 202 + job_id immediately | unit | `python -m pytest tests/test_render_routes.py::test_render_returns_202 -x` | Wave 0 |
| INTG-01 | GET /render-status/:id returns job state | unit | `python -m pytest tests/test_render_routes.py::test_render_status_polling -x` | Wave 0 |
| INTG-02 | RemotionRenderer satisfies VideoRendererProtocol (isinstance check) | unit | `python -m pytest tests/test_renderer_protocol.py::test_remotion_implements_protocol -x` | Wave 0 |
| INTG-02 | Protocol isolates: swap renderer without changing route | unit | `python -m pytest tests/test_renderer_protocol.py::test_protocol_swappability -x` | Wave 0 |
| INTG-03 | Airtable PATCH sends correct attachment format | unit (mock) | `python -m pytest tests/test_airtable_client.py::test_update_video_attachment -x` | Wave 0 |
| INTG-04 | RenderRequest passes source_video_url to RemotionRenderer | unit (mock) | `python -m pytest tests/test_renderer_remotion.py::test_render_passes_video_url -x` | Wave 0 |
| INTG-05 | POST /render responds in < 1 second regardless of render time | integration | `python -m pytest tests/test_render_routes.py::test_render_202_under_1_second -x` | Wave 0 |
| INTG-05 | Polling eventually returns completed status | integration (mock Remotion) | `python -m pytest tests/test_render_routes.py::test_polling_completes -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — makes tests a package
- [ ] `tests/conftest.py` — shared fixtures: FastAPI TestClient, mock RemotionRenderer, mock httpx responses
- [ ] `tests/test_render_routes.py` — covers INTG-01, INTG-05
- [ ] `tests/test_renderer_protocol.py` — covers INTG-02
- [ ] `tests/test_renderer_remotion.py` — covers INTG-04
- [ ] `tests/test_airtable_client.py` — covers INTG-03
- [ ] Framework install: `pip install pytest pytest-asyncio httpx[trio]` — no test framework detected in project

---

## Sources

### Primary (HIGH confidence)
- Existing codebase: `/Users/openclaw/wandi-agent/main.py` — asyncio.create_task pattern, httpx usage, error handling conventions
- Existing codebase: `/Users/openclaw/wandi-agent/airtable_client.py` — httpx PATCH pattern, HEADERS format
- Existing codebase: `/Users/openclaw/wandi-agent/remotion-service/server/render-queue.ts` — Phase 1 API contract; `videoUrl` is local path finding
- Python docs — https://docs.python.org/3/library/typing.html#typing.Protocol — Protocol + @runtime_checkable
- supabase PyPI — https://pypi.org/project/supabase/ — v2.28.0, Python >=3.9 requirement verified
- Supabase Python docs — https://supabase.com/docs/reference/python/storage-from-getpublicurl — get_public_url() pattern

### Secondary (MEDIUM confidence)
- Airtable Web API — https://airtable.com/developers/web/api/update-record — PATCH format verified; attachment `[{"url": "..."}]` structure confirmed by multiple community sources
- Airtable Community — https://community.airtable.com/development-apis-11/uploading-image-files-to-an-attachment-field-via-api-4954 — URL must be publicly accessible
- Supabase Storage docs — https://supabase.com/docs/reference/python/storage-from-upload — upload() method signature
- Express.js docs — https://expressjs.com/en/api.html#res.download — res.download() for file serving

### Tertiary (LOW confidence — verify with actual API calls)
- Airtable attachment field naming: "Rendered Video" — proposed, not verified against actual Airtable base. Verify with PATCH test early.
- Supabase bucket access policy (public vs signed URLs for raw source videos) — requires checking actual Supabase dashboard.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified; supabase v2.28.0 confirmed on PyPI; httpx already installed
- Architecture: HIGH — patterns derived from existing main.py code which is production; Protocol pattern from stdlib
- Pitfalls: HIGH (videoUrl path issue — confirmed by reading Phase 1 source code); MEDIUM (Airtable URL requirement — community-verified)
- Validation: MEDIUM — pytest not yet installed; test file structure is standard but no tests exist yet

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (30 days — supabase-py updates frequently but API is stable in v2.x)
