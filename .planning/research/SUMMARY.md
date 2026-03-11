# Project Research Summary

**Project:** Wandi — Programmatic Instagram Reels Video Renderer
**Domain:** Automated video rendering microservice — Hebrew RTL text overlays on social media content
**Researched:** 2026-03-11
**Confidence:** HIGH

## Executive Summary

Wandi requires a two-component system: a Node.js microservice running Remotion (a React-to-video framework), and a Python abstraction layer inside the existing FastAPI backend. Remotion is the definitive choice for this use case — it renders React components to MP4 via headless Chromium, bundles FFmpeg internally, and handles Hebrew RTL text natively through CSS (no workarounds). The official render server template (`npx create-video@latest --render-server`) provides a working Express 5 + job queue + TypeScript baseline and should be the starting point, saving significant setup time.

The recommended architecture treats the Remotion service as a stateless, black-box HTTP service. The Python backend never calls Remotion directly — it communicates through a `VideoRendererProtocol` interface, which the `RemotionRenderer` concrete class implements. This abstraction is not optional: the project explicitly requires the ability to swap rendering engines, and coupling Python business logic to Remotion's HTTP schema makes that swap prohibitively expensive. Video rendering takes 30–300 seconds, so the job pattern must be asynchronous from day one: Python submits a render job and receives a `job_id` immediately, then polls for completion. Synchronous HTTP is not viable and will fail in production.

The highest-risk areas are all in Phase 1: Hebrew RTL text rendering, font loading in headless Chromium, and Supabase video sourcing via `OffthreadVideo`. These pitfalls are well-documented and preventable, but they are silent — the render succeeds while output is broken. The mitigation strategy is to build a comprehensive "hello world" render that validates RTL character order, brand font presence (not system fallback), and full-length video loading before any template or integration work begins.

---

## Key Findings

### Recommended Stack

The Node.js renderer service is built on Remotion 4.0.x (currently 4.0.434) with `@remotion/renderer` and `@remotion/bundler` at the same version. The official template targets React 19, TypeScript 5.8.x, Express 5.1.0, and Zod 3.22.x for props validation. The Docker base image must be `node:22-bookworm-slim` (Debian) — Alpine causes 35% render slowdowns due to musl libc incompatibilities and breaks Chrome version management. Hebrew fonts are loaded via `@remotion/google-fonts` (Noto Sans Hebrew, Heebo, or Assistant are all available) with local font file bundling as a fallback for offline environments.

The Python side adds three dependencies to the existing FastAPI service: `httpx` (async HTTP client for calling the render service — never `requests`, which blocks the event loop), `supabase-py` (already likely present), and `pyairtable` (for URL-based attachment upload). All Remotion packages must be pinned to the exact same version — version mismatches produce cryptic runtime errors with no clear diagnosis path.

**Core technologies:**
- `remotion@4.0.x` + `@remotion/renderer` + `@remotion/bundler`: Core rendering engine — Rust-powered, built-in FFmpeg, React-to-MP4 pipeline
- `node:22-bookworm-slim` Docker base: Official Remotion recommendation since Nov 2024; do not substitute Alpine
- `@remotion/google-fonts`: Type-safe Hebrew font loading with built-in render-readiness signaling
- `Express 5.1.0`: HTTP API layer from the official render server template
- `Zod 3.22.x`: Input props validation — prevents runtime shape mismatches between Python and Node.js
- `httpx.AsyncClient` (Python): Non-blocking async HTTP for submitting and polling render jobs
- `pyairtable`: URL-based Airtable attachment upload (Airtable fetches the file by URL, avoiding binary upload size limits)

### Expected Features

The MVP must deliver a rendered 1080x1920 MP4 with branded Hebrew text overlay, triggered via HTTP API and returned as a URL. All 11 P1 features are required for launch — there is no reasonable subset that produces a usable, publishable product.

**Must have (table stakes — v1):**
- Correct output format (1080x1920, H.264, AAC 256kbps, 30fps) — Instagram rejects off-spec video
- Safe-zone-aware text positioning (1080x1420px band) — Instagram UI covers ~250px top and bottom
- RTL Hebrew text direction with bidirectional Hebrew+English handling — mandatory per project constraints
- Hebrew-capable font (Heebo or Assistant) loaded and verified at render time
- Static text overlay with at minimum fade-in/fade-out animation — core reason Remotion was chosen over FFmpeg
- Per-client brand template (colors, font family, text position) — clients are businesses, generic styling is unacceptable
- HTTP render API with async job pattern (202 + job_id + polling)
- Python `VideoRendererProtocol` abstraction layer — must be in v1 to avoid coupling
- Output accessible via URL for Airtable attachment

**Should have (differentiators — v1.x):**
- Multiple independent text segments with per-segment timing (intro hook, body, CTA)
- Awareness-stage-aware text styling (maps SDMF awareness stage to visual weight/color)
- Render-time contrast enforcement (4.5:1 minimum check)

**Defer (v2+):**
- Multi-format output (4:5 feed, 1:1 square) — 9:16 Reels only for this milestone
- Audio mixing / background music — separate licensing and sync pipeline
- Auto video selection — next milestone per PROJECT.md
- Client self-service template editor — belongs in the React/Lovable frontend

### Architecture Approach

The system has three clear layers with hard boundaries between them. The Remotion Node.js service is a separate Docker process — Python treats it as a black-box HTTP service and never embeds or subprocess-calls it. Inside the Python backend, a `VideoRendererProtocol` (using `typing.Protocol`) defines the renderer contract; the `RemotionRenderer` concrete class is the only code that knows about Remotion's HTTP schema. Render jobs are serialized in the Node.js service via a Promise chain queue to prevent Chromium resource contention. Source video flows directly from Supabase Storage into Remotion via URL (no Python download step), and rendered output flows from the Node.js service to Airtable via Python (Node.js has no Airtable awareness).

**Major components:**
1. `remotion-service/` (Node.js) — Express HTTP API + serial render queue + Remotion composition definitions; deployed as Docker container
2. `renderer/` (Python module) — `VideoRendererProtocol`, `RemotionRenderer`, `RenderRequest`/`JobStatus` models; zero dependency on `app/` code
3. `api/render.py` (FastAPI) — thin endpoint that delegates to the protocol; returns job_id immediately, separate status endpoint for polling
4. `remotion/ReelTemplate.tsx` — React composition accepting `inputProps` (text, Supabase URL, brand config, animation style); Zod schema validates all inputs
5. Supabase Storage — read-only from renderer's perspective; source video URL passed as `inputProp`
6. Airtable — write-only from Python's perspective; Node.js service has no Airtable credentials

Build order is deterministic from the dependency graph: Zod schemas + React composition first, then Express server, then Docker packaging, then Python protocol + models, then `RemotionRenderer`, then FastAPI endpoint, then storage integration, then per-client brand template extensions.

### Critical Pitfalls

1. **Hebrew RTL text reversal from `unicode-bidi: bidi-override`** — Never use `bidi-override` on Hebrew containers; always use `direction: rtl` + `unicode-bidi: embed` (or `isolate` for mixed segments). Build a visual smoke test into Phase 1 that renders Hebrew + embedded English and verifies character order in the actual MP4, not just Studio preview.

2. **Font not loaded at render time (silent system font fallback)** — Call `loadFont()` at module top level with `delayRender()`/`continueRender()` blocking. Narrow the load to `{ subsets: ['hebrew'], weights: ['400', '700'] }` to prevent 28-58 second timeout from loading all font variants. Fail loudly (return error) rather than silently falling back to system fonts.

3. **`OffthreadVideo` timeout on long Supabase videos** — Signed URLs expire mid-render and raw video files can be 500MB+. Pre-download source video to the Node.js service's local disk before `renderMedia()` and pass a `staticFile()` reference. Never pass signed URLs directly to `OffthreadVideo` for videos over 30 seconds.

4. **Synchronous Python HTTP calls to the render service** — Renders take 30–300 seconds. Synchronous POST will time out at the HTTP client, nginx, or load balancer level, causing orphaned render jobs and retry duplication. Async job pattern (202 + polling) is non-negotiable and must be the first architectural decision.

5. **GPU-accelerated CSS effects causing 10x slowdowns in headless Chromium** — `text-shadow`, `filter: blur()`, and complex gradients fall back to software rendering without a GPU. Benchmark each template CSS on the actual server environment using `npx remotion benchmark` before finalizing design. Use pre-rendered image assets instead of real-time blur/shadow effects.

---

## Implications for Roadmap

Based on the dependency graph in ARCHITECTURE.md, the feature dependencies in FEATURES.md, and the phase-to-pitfall mapping in PITFALLS.md, the following phase structure is recommended:

### Phase 1: Remotion Service Foundation

**Rationale:** Everything downstream depends on a working, verified Remotion render with correct RTL output. The most critical and silent pitfalls (RTL reversal, font fallback, video timeout) all live here. Validating them first prevents discovering broken output after weeks of template work.

**Delivers:** A running Node.js Docker service that renders a verified Hebrew + English text overlay onto a source video from Supabase Storage and returns an accessible MP4 URL. This is the "hello world" render that proves the entire stack works.

**Addresses features:** Correct output format, safe-zone positioning, RTL Hebrew direction, bidirectional text, Hebrew font loading, static text overlay, async HTTP render API.

**Stack elements:** `node:22-bookworm-slim`, Remotion 4.0.x, `@remotion/renderer`, `@remotion/bundler`, Express 5, Zod, `@remotion/google-fonts`, `npx create-video@latest --render-server` bootstrap.

**Must avoid:**
- Alpine base image (35% slowdown, Chrome downgrade failures)
- `unicode-bidi: bidi-override` (reverses Hebrew characters silently)
- Synchronous render call (times out on any real video)
- Passing signed Supabase URLs directly to `OffthreadVideo` for long videos
- Loading all Google Font weights (causes `delayRender` timeout)

**Research flag:** Standard patterns — official Remotion render server template covers this phase. Skip `/gsd:research-phase`.

---

### Phase 2: Python Abstraction Layer and Integration

**Rationale:** The `VideoRendererProtocol` and `RemotionRenderer` must exist before any business logic can trigger renders. Defining the protocol boundary now prevents Remotion-specific coupling from spreading into calling code, which would make the mandatory engine-swap requirement impossible to honor.

**Delivers:** A `renderer/` Python module with `VideoRendererProtocol`, `RemotionRenderer` (calling Phase 1 service), `RenderRequest`/`JobStatus` models, and a FastAPI endpoint. Python can submit a render job, poll to completion, and receive a URL — end-to-end, without knowing any Remotion internals.

**Addresses features:** Python abstraction layer, render triggered via HTTP API, output accessible via URL.

**Stack elements:** `httpx.AsyncClient`, `typing.Protocol`, FastAPI dependency injection, `supabase-py`, `pyairtable.utils.attachment(url=...)`.

**Architecture components:** `VideoRendererProtocol`, `RemotionRenderer`, `api/render.py`, storage integration (download MP4, upload to Airtable).

**Must avoid:**
- Letting Remotion HTTP schema leak into business logic (breaks swappability)
- Synchronous `requests` library (blocks FastAPI event loop)
- Uploading MP4 bytes directly to Airtable (size limits; use URL-based attachment)
- Storing rendered video only on ephemeral Node.js container disk (data loss on restart)

**Research flag:** Python `typing.Protocol` and FastAPI DI patterns are well-documented. The Airtable URL-based attachment pattern is MEDIUM confidence — verify `pyairtable.utils.attachment(url=...)` behavior with a real Airtable record during implementation.

---

### Phase 3: Per-Client Brand Template System

**Rationale:** With the render pipeline proven end-to-end, template parameterization is the next highest-value delivery. Clients are businesses with brand identities — generic output is a regression. This phase extends the Zod schema with brand config and proves multi-client isolation.

**Delivers:** A `ReelTemplate.tsx` composition that accepts `brandColors`, `fontFamily`, `textPosition`, and `animationStyle` as `inputProps`. Per-client renders produce visually distinct output. Template data isolation between clients is verified.

**Addresses features:** Per-client brand template system, fade-in/fade-out animation, per-client font selection, text contrast legibility.

**Must avoid:**
- GPU-accelerated CSS effects (`text-shadow`, `filter: blur()`) — benchmark on server before finalizing
- Template data leaking between concurrent client render jobs
- Hardcoding font weights (locks out per-client bold/light brand fonts)

**Research flag:** Remotion `inputProps` and `interpolate()`/`spring()` patterns are well-documented. Skip `/gsd:research-phase` for animation primitives. If awareness-stage styling is added, a brief research spike on SDMF stage-to-style mapping may be warranted.

---

### Phase 4: Multi-Segment Text and Production Hardening

**Rationale:** Multiple independent text segments (intro hook, body, CTA) are a P2 feature that dramatically increases content quality. This phase also addresses production concerns: rate limiting, retry logic, performance benchmarking, and the full "looks done but isn't" checklist from PITFALLS.md.

**Delivers:** Render jobs accept an array of text segments with per-segment timing (`[{ text, startFrame, endFrame, animation }]`). Production readiness: rate limiting on the FastAPI endpoint, Airtable 429 retry backoff, concurrent render verification, service restart recovery, signed URL expiry handling.

**Addresses features:** Multiple text segments with independent timing, awareness-stage text styling hook, contrast enforcement at render time.

**Must avoid:**
- Concurrent render OOM (verify queue serialization handles concurrent submission correctly)
- Airtable rate limit (5 req/sec) — add retry with exponential backoff
- Rendered videos on ephemeral disk (must be resolved by this phase)

**Research flag:** May need a brief research spike on Airtable attachment rate limiting behavior and retry semantics. Otherwise standard patterns.

---

### Phase Ordering Rationale

- **Foundation before abstraction:** The Remotion service (Phase 1) must be running before the Python layer (Phase 2) can be tested. The build order from ARCHITECTURE.md is deterministic.
- **Pipeline before templates:** The end-to-end render path (Phases 1-2) must be proven before template complexity (Phase 3) is added. Debugging a broken render on top of brand config adds two variables.
- **RTL first, always:** Hebrew RTL issues are silent — they must be caught in Phase 1 before any other work depends on correct text rendering.
- **Async architecture is a Phase 1 concern:** The synchronous HTTP pitfall has HIGH recovery cost if caught late (requires redesign of Python endpoint, Node.js API, and any frontend polling). It must be the first architectural decision.
- **P2 features last:** Multi-segment timing and production hardening are deferred to Phase 4 because they require a stable end-to-end pipeline as a foundation.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2 (Airtable attachment):** The `pyairtable.utils.attachment(url=...)` pattern is MEDIUM confidence — verify behavior with a real Airtable record and confirm URL accessibility requirements before building the upload step.
- **Phase 4 (Airtable rate limits):** Rate limiting and retry behavior under production-like load should be validated empirically, not just from docs.

Phases with standard, well-documented patterns (skip `/gsd:research-phase`):
- **Phase 1:** Official Remotion render server template covers this entirely. Font loading, OffthreadVideo, and RTL are documented in official Remotion and MDN docs.
- **Phase 3:** Remotion `inputProps`, `interpolate()`, and `spring()` are well-documented. Brand template parameterization is a standard Remotion pattern.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core technologies verified against official Remotion docs, npm registry, and official template. Version compatibility confirmed. |
| Features | HIGH (core), MEDIUM (RTL specifics) | Rendering features are well-documented. BiDi edge cases in video context rely on community sources — verified consistent with MDN specs. |
| Architecture | HIGH | Official Remotion render server template and SSR docs provide canonical patterns. Python abstraction layer uses standard `typing.Protocol` patterns. |
| Pitfalls | HIGH (Remotion-specific), MEDIUM (RTL video context) | Remotion pitfalls sourced from official docs and GitHub issues. RTL in video context corroborated by multiple community sources but fewer authoritative references. |

**Overall confidence:** HIGH

### Gaps to Address

- **Airtable URL attachment behavior:** The `pyairtable.utils.attachment(url=...)` pattern is confirmed as the correct approach (MEDIUM confidence), but the exact URL accessibility requirements (must be public? signed URLs work? expiry window?) need verification with a real Airtable API call early in Phase 2.
- **Supabase signed URL strategy for source video:** The research recommends pre-downloading to local disk. The alternative (public Supabase bucket for raw source videos) may be simpler if data access policy permits — this is a product decision to confirm before Phase 1.
- **Concurrent render behavior at expected volume:** The serial queue handles concurrency correctly at low volume. If render volume exceeds ~10/hour, queue depth may require attention. Validate expected daily render volume before committing to single-container architecture.
- **Awareness-stage style definitions:** SDMF stage-to-style mappings are referenced as a Phase 2+ feature but the actual style definitions (what colors/weights correspond to each stage) require input from the product/content team, not additional technical research.

---

## Sources

### Primary (HIGH confidence)
- Remotion official docs (remotion.dev) — SSR, Docker, fonts, encoding, performance, OffthreadVideo, delayRender, GPU
- GitHub: remotion-dev/template-render-server — canonical render server architecture
- DeepWiki: remotion-dev/template-render-server — package versions (Express 5.1.0, React 19, TS 5.8.2, Zod 3.22.3)
- npmjs.com: remotion@4.0.434, @remotion/renderer@4.0.429 — current versions
- MDN: `unicode-bidi`, `direction` CSS properties — BiDi algorithm reference
- FastAPI docs — async/concurrency patterns
- Supabase docs — signed URL API

### Secondary (MEDIUM confidence)
- Instagram Reels dimensions 2026 (zeely.ai, outfy.com, socialrails.com) — format spec (consistent across multiple sources)
- Instagram safe zones (kreatli.com, zeely.ai) — safe zone dimensions
- pyairtable readthedocs — `attachment(url=...)` utility (community-confirmed pattern)
- RTL in video subtitling (artlangstv.com, rtlfixer.com) — BiDi edge cases in video context
- Community Docker deployment patterns (scotthavird.com, crepal.ai) — aligns with official Remotion recommendation

### Tertiary (LOW confidence)
- Airtable Hebrew/Arabic RTL community thread — mixed-direction alignment behavior in Airtable UI (not directly relevant to rendering)

---

*Research completed: 2026-03-11*
*Ready for roadmap: yes*
