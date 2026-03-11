# Architecture Research

**Domain:** Remotion video rendering service integrated with Python/FastAPI backend
**Researched:** 2026-03-11
**Confidence:** HIGH (Remotion architecture), MEDIUM (Python abstraction patterns), HIGH (data flow)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL CALLERS                             │
│  ┌──────────────────────────┐   ┌────────────────────────────────┐  │
│  │  Python/FastAPI Backend  │   │  Future: Frontend / Scheduler  │  │
│  │  (existing service)      │   │                                │  │
│  └────────────┬─────────────┘   └──────────────┬─────────────────┘  │
└───────────────┼──────────────────────────────── ┼ ────────────────────┘
                │ POST /render                     │
                ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│               PYTHON ABSTRACTION LAYER (new module)                  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  VideoRendererProtocol (ABC / typing.Protocol)               │    │
│  │  render(text, video_url, template_id) → render_job_id        │    │
│  │  get_status(job_id) → JobStatus                              │    │
│  │  get_result(job_id) → VideoResult                            │    │
│  └───────────────────────────┬──────────────────────────────────┘    │
│                              │ implements                            │
│  ┌───────────────────────────▼──────────────────────────────────┐    │
│  │  RemotionRenderer (concrete implementation)                  │    │
│  │  - HTTP client to Remotion Node.js service                   │    │
│  │  - POST /renders → polls GET /renders/:id                    │    │
│  │  - Downloads mp4 or receives URL on completion               │    │
│  └───────────────────────────┬──────────────────────────────────┘    │
└──────────────────────────────┼───────────────────────────────────────┘
                               │ HTTP (JSON over REST)
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│               REMOTION NODE.JS SERVICE (new service)                 │
│                                                                      │
│  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐  │
│  │   Express HTTP    │  │   Render Queue    │  │  Composition    │  │
│  │   API Layer       │  │   Manager         │  │  Layer          │  │
│  │                   │  │                   │  │                 │  │
│  │ POST /renders     │  │ makeRenderQueue() │  │ remotion/       │  │
│  │ GET  /renders/:id │  │ jobs: Map<id,     │  │ - ReelTemplate  │  │
│  │ DEL  /renders/:id │  │   JobState>       │  │   (React comp)  │  │
│  │ GET  /renders/*.  │  │ queue: Promise    │  │ - Zod schemas   │  │
│  │       mp4         │  │   chain (serial)  │  │ - inputProps    │  │
│  └────────┬──────────┘  └────────┬──────────┘  └────────┬────────┘  │
│           │                      │                       │           │
│           └──────────────────────▼───────────────────────┘           │
│                                  │                                   │
│                    @remotion/renderer (SSR APIs)                     │
│                    bundleOnLambda / bundle()                         │
│                    selectComposition()                               │
│                    renderMedia() → mp4 output                        │
│                    openBrowser() (reused instance)                   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
┌─────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│  SUPABASE STORAGE   │  │  LOCAL TEMP FS   │  │  AIRTABLE            │
│  (raw source video) │  │  (render output  │  │  (attachment URL     │
│                     │  │   before upload) │  │   persisted by       │
│  read via URL →     │  │  /tmp/*.mp4      │  │   Python backend)    │
│  passed as inputProp│  │                  │  │                      │
└─────────────────────┘  └──────────────────┘  └──────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| FastAPI render endpoint | Accept render requests from callers; delegate to abstraction layer; return job ID or result URL | Python FastAPI route, async |
| `VideoRendererProtocol` | Define the contract for any renderer engine; enable swappability | Python `typing.Protocol` or ABC |
| `RemotionRenderer` | Concrete implementation: talks to Remotion service over HTTP, polls for completion, returns URL | Python class using `httpx` async client |
| Express HTTP API layer | Expose REST endpoints; accept job parameters; serve status and file downloads | Node.js + Express, TypeScript |
| Render Queue Manager | Serialize renders to prevent Chromium resource contention; track job state machine | `makeRenderQueue()` factory, Promise chain |
| Composition Layer | Define video templates as React components; accept `inputProps` for text, source video URL, branding | Remotion `<Composition>` + React + Zod schemas |
| `@remotion/renderer` SSR APIs | Execute actual rendering: bundle, select composition, render frames, stitch video | `bundle()`, `selectComposition()`, `renderMedia()` |
| Supabase Storage | Persist raw source videos; serve via public URL passed as `inputProp` | Supabase bucket, read-only from renderer's perspective |
| Airtable | Store rendered video as attachment URL after Python backend uploads/registers it | Airtable attachment field, written by Python backend |

## Recommended Project Structure

```
wandi-agent/
├── app/                          # existing Python/FastAPI (do not modify)
│   └── ...
│
├── renderer/                     # NEW: Python abstraction layer (standalone module)
│   ├── __init__.py
│   ├── protocol.py               # VideoRendererProtocol (typing.Protocol)
│   ├── remotion.py               # RemotionRenderer (concrete implementation)
│   ├── models.py                 # RenderRequest, RenderJob, JobStatus dataclasses
│   └── exceptions.py             # RenderError, RenderTimeoutError
│
├── api/                          # NEW: FastAPI render endpoint
│   └── render.py                 # POST /render, GET /render/{job_id}
│
└── remotion-service/             # NEW: standalone Node.js service (separate process)
    ├── remotion/                 # Remotion composition definitions
    │   ├── index.ts              # Root — registers compositions
    │   ├── ReelTemplate.tsx      # Primary Instagram Reel composition
    │   ├── TextOverlay.tsx       # RTL-aware text overlay component
    │   └── schemas.ts            # Zod input prop schemas
    ├── server/                   # Express HTTP API
    │   ├── index.ts              # Server entrypoint, port 3000
    │   └── render-queue.ts       # makeRenderQueue() — job state + serial queue
    ├── Dockerfile                # node:22-bookworm-slim (NOT Alpine)
    ├── remotion.config.ts
    ├── package.json
    └── tsconfig.json
```

### Structure Rationale

- **`renderer/`:** Isolated Python module with zero dependency on existing `app/` code. The protocol lives here so future renderer engines (FFmpeg, RunwayML, etc.) implement the same contract without touching calling code.
- **`remotion-service/`:** Completely separate Node.js process. Deployed as a Docker container. Python side treats it as a black-box HTTP service.
- **`remotion/` inside service:** Separates composition definitions (what the video looks like) from server infrastructure (how renders are managed). Template changes don't require server changes.
- **`server/` inside service:** Encapsulates all job lifecycle logic. The Express layer is thin; business logic lives in `render-queue.ts`.

## Architectural Patterns

### Pattern 1: Async Submit-and-Poll (Job Queue)

**What:** Render requests are accepted synchronously (returns a `job_id` immediately), then rendered asynchronously. Callers poll for status.

**When to use:** Always — video rendering is CPU-intensive and takes seconds to minutes. Blocking HTTP is not viable.

**Trade-offs:** Adds polling complexity on the Python side; enables progress tracking, cancellation, and avoids HTTP timeouts. The Remotion render server template implements serial queue internally (one render at a time) — this prevents Chromium memory exhaustion on a single server.

**Example (Python caller):**
```python
async def render_and_wait(renderer: VideoRendererProtocol, req: RenderRequest) -> str:
    job_id = await renderer.submit(req)
    while True:
        status = await renderer.get_status(job_id)
        if status.state == "completed":
            return status.video_url
        if status.state == "failed":
            raise RenderError(status.error)
        await asyncio.sleep(3)  # poll interval
```

**Example (Remotion service — POST /renders returns immediately):**
```typescript
app.post("/renders", (req, res) => {
  const jobId = crypto.randomUUID();
  queue.add(jobId, req.body);     // enqueued, not yet running
  res.json({ jobId });            // respond immediately
});
```

### Pattern 2: Protocol / Strategy for Renderer Swappability

**What:** Define a `VideoRendererProtocol` in Python using `typing.Protocol` (structural subtyping). Concrete renderers implement it. The FastAPI endpoint and any business logic depends only on the protocol, never the concrete class.

**When to use:** Required here — project explicitly requires the ability to swap Remotion for another engine.

**Trade-offs:** Adds one layer of indirection; pays off as soon as a second engine is needed or when mocking for tests. `typing.Protocol` is preferable to ABC because it supports duck typing — no explicit `implements` declaration needed.

**Example:**
```python
from typing import Protocol

class VideoRendererProtocol(Protocol):
    async def submit(self, request: RenderRequest) -> str: ...
    async def get_status(self, job_id: str) -> JobStatus: ...
    async def cancel(self, job_id: str) -> None: ...

# FastAPI dependency injection
def get_renderer() -> VideoRendererProtocol:
    return RemotionRenderer(base_url=settings.REMOTION_SERVICE_URL)

@router.post("/render")
async def trigger_render(
    body: RenderRequestBody,
    renderer: VideoRendererProtocol = Depends(get_renderer),
):
    ...
```

### Pattern 3: inputProps-Driven Composition (Template Parameterization)

**What:** All per-render customization (text content, source video URL, brand colors, fonts, text positions) is passed as `inputProps` JSON to the Remotion composition. The React component is purely a rendering function of props. Templates are code, not files.

**When to use:** Always in Remotion — the composition is registered once at startup; rendering is parameterized at call time.

**Trade-offs:** All template behavior must be representable as JSON-serializable props. Large props (>194KB) auto-upload to S3 via Remotion Lambda — for a self-hosted service, keep props small (text + URLs, not video blobs).

**Example (Zod schema + TypeScript):**
```typescript
import { z } from "zod";

export const ReelInputSchema = z.object({
  sourceVideoUrl: z.string().url(),       // Supabase Storage public URL
  overlayText: z.string(),               // Hebrew or English
  textDirection: z.enum(["rtl", "ltr"]), // RTL for Hebrew
  brandColors: z.object({
    primary: z.string(),                 // hex
    secondary: z.string(),
  }),
  fontFamily: z.string(),
  textPosition: z.enum(["top", "center", "bottom"]),
  animationStyle: z.enum(["fade", "slide", "none"]),
});

export type ReelInput = z.infer<typeof ReelInputSchema>;
```

## Data Flow

### Render Request Flow (Happy Path)

```
Client (Python backend or frontend)
    │
    │  POST /render  { text, source_video_url, template_id, brand_config }
    ▼
FastAPI render endpoint (Python)
    │
    │  calls renderer.submit(RenderRequest)
    ▼
RemotionRenderer (Python)
    │
    │  POST http://remotion-service:3000/renders
    │  body: { compositionId, inputProps: { sourceVideoUrl, overlayText, ... } }
    ▼
Express API Layer (Node.js)
    │  → generates job_id, enqueues job
    │  ← returns { jobId }
    │
    ▼
Render Queue Manager (Node.js)
    │  waits for prior renders to complete (serial promise chain)
    │
    ▼
@remotion/renderer SSR APIs
    │  selectComposition("ReelTemplate", inputProps)
    │  renderMedia() → writes /tmp/{jobId}.mp4
    │  (Chromium renders frames, FFmpeg stitches)
    │
    │  reads source video from Supabase Storage URL during frame extraction
    │  (OffthreadVideo component fetches URL at render time)
    │
    ▼
Job state: completed → videoUrl = /renders/{jobId}.mp4

Python poller (RemotionRenderer.get_status())
    │  GET http://remotion-service:3000/renders/{jobId}
    │  ← { state: "completed", videoUrl: "/renders/abc.mp4" }
    │
    ▼
RemotionRenderer downloads mp4 (or streams it)
    │
    ▼
Python backend uploads mp4 to Airtable as attachment
    │  (Airtable attachment = URL-accessible, visible in frontend gallery)
    ▼
Return rendered video URL to original caller
```

### Job State Machine (Remotion Service)

```
[queued] → [in-progress] → [completed]
                 │
                 └──────────→ [failed]

queued:      job received, waiting in serial queue
in-progress: Chromium rendering frames, progress: 0.0–1.0
completed:   mp4 written to disk, videoUrl available
failed:      render error or cancellation signal received
```

### Key Data Flows

1. **Text + branding into Remotion:** Python serializes `RenderRequest` → JSON `inputProps` → HTTP POST to Remotion service → React composition receives props via `getInputProps()` and renders styled text overlay
2. **Source video into Remotion:** Supabase Storage public URL passed as `inputProp.sourceVideoUrl` → Remotion `<OffthreadVideo src={sourceVideoUrl}>` fetches at render time (no Python-side download needed)
3. **Rendered output to Airtable:** Remotion service writes mp4 to local `/tmp/` → Python downloads from `GET /renders/{jobId}.mp4` → Python backend uploads to Airtable as attachment field
4. **Job lifecycle tracking:** Python polls `GET /renders/{jobId}` every N seconds; Remotion returns JSON job state with progress float and eventual `videoUrl`

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 renders/day | Single Remotion container, serial queue, local file storage — no changes needed |
| 10-200 renders/day | Pre-warm browser instance (`openBrowser()` at startup, reuse across renders); increase /dev/shm in Docker |
| 200+ renders/day | Move to Remotion Lambda (distributed rendering); or horizontally scale Remotion containers behind a load balancer with a shared job queue (Redis) |

### Scaling Priorities

1. **First bottleneck:** Chromium startup time per render — fix with `openBrowser()` shared instance at service boot, reused for all renders
2. **Second bottleneck:** Serial queue depth (renders pile up) — fix by migrating to Remotion Lambda or multi-container setup with external queue

## Anti-Patterns

### Anti-Pattern 1: Blocking HTTP Render Request

**What people do:** POST to Remotion service and hold the HTTP connection open until render completes, using a long timeout.

**Why it's wrong:** Renders take 15-120+ seconds. Python HTTP clients time out. FastAPI workers are blocked. If the Remotion service crashes mid-render, the caller gets no result and has no job ID to retry with.

**Do this instead:** Submit returns a job ID immediately. Python polls or uses a background task (`asyncio.create_task`) to poll and then write the result to Airtable independently.

### Anti-Pattern 2: Coupling Python Business Logic to Remotion HTTP Schema

**What people do:** Python code directly constructs Remotion-specific JSON payloads with `compositionId`, Remotion field names, and service-specific URLs throughout the business layer.

**Why it's wrong:** When the renderer engine is swapped (the explicit goal of this project), every caller breaks. The Remotion schema leaks into code that should not know about Remotion.

**Do this instead:** Python business logic constructs a `RenderRequest` domain object (text, video_url, template_id, brand_config). The `RemotionRenderer` concrete class translates to Remotion's HTTP schema. The protocol boundary is the translation point.

### Anti-Pattern 3: Alpine Linux Base Image for Remotion Docker

**What people do:** Use `node:22-alpine` as the Remotion Docker base image to reduce image size.

**Why it's wrong:** Alpine's musl libc causes Rust component slowdowns and flaky Chromium compatibility. Remotion benchmarks show 35% longer render times on Alpine vs Debian.

**Do this instead:** Use `node:22-bookworm-slim` (Debian, slim variant). Pre-install Chromium system dependencies via the Dockerfile. This is Remotion's official recommendation as of November 2024.

### Anti-Pattern 4: Embedding Remotion Service Inside the Python Process

**What people do:** Try to call Node.js/Remotion directly from Python via subprocess or a subprocess-per-render pattern.

**Why it's wrong:** Remotion requires a persistent browser instance and bundle warm-up. Spawning a new Node.js process per render is extremely slow (10-30s overhead). The render queue and browser reuse are critical performance features that only work in a long-running Node.js server.

**Do this instead:** Run Remotion as a persistent Docker service. Python communicates over HTTP. The Node.js service manages its own lifecycle.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Supabase Storage | Remotion `<OffthreadVideo src={url}>` fetches source video URL at render time | URL must be publicly accessible or signed; no Python download step needed |
| Airtable | Python backend uploads rendered mp4 and registers as attachment field after render completes | Python handles this after polling completion; Remotion service is not Airtable-aware |
| Remotion service | Python `RemotionRenderer` calls `POST /renders`, polls `GET /renders/:id`, downloads mp4 from `GET /renders/*.mp4` | All communication is JSON + HTTP; language-agnostic |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| FastAPI endpoint ↔ `VideoRendererProtocol` | Direct Python method calls | The protocol is the seam; FastAPI never knows which renderer is concrete |
| `RemotionRenderer` ↔ Remotion Node.js service | HTTP REST (JSON) | Deployed as separate Docker containers; `REMOTION_SERVICE_URL` env var configures address |
| Remotion composition layer ↔ SSR renderer | In-process Node.js function calls (`renderMedia()`) | Same Node.js process; no network hop |
| Remotion service ↔ Supabase | HTTP (Remotion fetches video URL during rendering) | Remotion does not authenticate to Supabase; requires public or signed URLs |

## Build Order (Phase Dependencies)

The component dependency graph determines what must be built before what:

```
1. Zod schemas + ReelTemplate composition (no deps — pure React)
    ↓
2. Render Queue Manager + Express server (depends on composition being registered)
    ↓
3. Docker packaging of Remotion service (depends on working server)
    ↓
4. VideoRendererProtocol + RenderRequest models (Python, no deps)
    ↓
5. RemotionRenderer concrete class (depends on Remotion service running)
    ↓
6. FastAPI render endpoint (depends on protocol + renderer)
    ↓
7. Storage integration: download mp4 + upload to Airtable (depends on endpoint working)
    ↓
8. Per-client brand templates: extend inputProps schema (depends on baseline render working)
```

The Remotion composition (step 1) must be working before the server can be tested. The Python abstraction (step 4) can be written before the Node.js service is complete, but integration tests require both. Storage integration (step 7) is last because it requires end-to-end render success first.

## Sources

- [Remotion Render Server Template (DeepWiki)](https://deepwiki.com/remotion-dev/template-render-server) — HIGH confidence, canonical architecture
- [GitHub: remotion-dev/template-render-server](https://github.com/remotion-dev/template-render-server) — HIGH confidence, official template
- [Remotion SSR Node.js APIs](https://www.remotion.dev/docs/ssr-node) — HIGH confidence, official docs
- [Remotion Comparison of SSR Options](https://www.remotion.dev/docs/compare-ssr) — HIGH confidence, official docs
- [Remotion renderMedia() API](https://www.remotion.dev/docs/renderer/render-media) — HIGH confidence, official docs
- [Remotion Passing Props to Composition](https://www.remotion.dev/docs/passing-props) — HIGH confidence, official docs
- [Remotion Video Uploads (remote URLs)](https://www.remotion.dev/docs/video-uploads) — HIGH confidence, official docs
- [Remotion Python Integration (Lambda)](https://www.remotion.dev/docs/lambda/python) — HIGH confidence, official docs
- [Remotion + Supabase Storage](https://www.remotion.dev/docs/lambda/supabase) — HIGH confidence, official docs
- [Remotion Docker deployment patterns](https://www.scotthavird.com/blog/remotion-docker-template/) — MEDIUM confidence, community article, corroborated by official Docker docs
- [Remotion Docker base image recommendation (node:22-bookworm-slim)](https://crepal.ai/blog/aivideo/blog-how-to-run-remotion-in-docker/) — MEDIUM confidence, community, aligns with official recommendation

---
*Architecture research for: Remotion video rendering service + Python/FastAPI backend integration*
*Researched: 2026-03-11*
