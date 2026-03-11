# Wandi — Video Renderer Module

## What This Is

Wandi is a SaaS platform for Instagram content creation and scheduling, targeting business owners. The backend (this repo) generates weekly content plans using the SDMF marketing methodology, and the frontend (separate React/Lovable app) handles client UI, approval flows, and scheduling. The v1.0 milestone shipped a standalone video renderer module that takes generated text content + raw video footage and produces finished Instagram Reels with branded, animated Hebrew text overlays — multi-segment support (hook, body, CTA) with per-client styling.

## Core Value

Business owners get publish-ready Instagram Reels — text content rendered on video with their brand styling — without manual video editing.

## Requirements

### Validated

- ✓ Text content generation via Ollama using SDMF methodology — existing
- ✓ Airtable integration for client data, content queue, and storage — existing
- ✓ Async and sync API endpoints for content generation — existing
- ✓ Hebrew content generation with awareness stage targeting — existing
- ✓ Standalone video renderer (Remotion Node.js service, 1080x1920 MP4, H.264/AAC/30fps) — v1.0
- ✓ Hebrew RTL text rendering with mixed bidirectional support (Heebo font) — v1.0
- ✓ Text overlays in Instagram safe zone with fade/slide/spring animations — v1.0
- ✓ VideoRendererProtocol abstraction (swap renderer engine without changing callers) — v1.0
- ✓ FastAPI render endpoint with async job pattern (HTTP 202 + polling) — v1.0
- ✓ Rendered video saved as Airtable attachment via Supabase Storage upload — v1.0
- ✓ Source video fetched from Supabase Storage at render time — v1.0
- ✓ Per-client brand templates (colors, fonts, positioning, overlay style) — v1.0
- ✓ SDMF awareness stage styling (Stage 1 bold vs Stage 3 authoritative) — v1.0
- ✓ Multi-segment text (hook/body/CTA) with independent timing and animation — v1.0

### Active

(None — next milestone requirements to be defined via `/gsd:new-milestone`)

### Out of Scope

- Auto video selection (matching raw videos to content by tags) — future milestone
- Smart content generation agent (dynamic AI-driven content decisions) — future milestone
- Frontend changes — separate React/Lovable app, not in this repo
- Instagram publishing via Meta API — future milestone
- Modifications to existing content generation pipeline — must remain unchanged
- Audio mixing / background music — separate pipeline, licensing concerns
- Real-time browser preview — Remotion Studio covers dev preview
- Multiple output formats (4:5, 1:1) — only 9:16 validated; each format needs own safe-zone math
- Client self-service template editor — product in itself, exceeds scope

## Context

Shipped v1.0 with 2,060 LOC source (1,245 Python + 815 TypeScript) and 2,954 LOC tests (202 tests).
Tech stack: Python/FastAPI + Remotion/Node.js/React + Supabase Storage + Airtable.
All 15 v1 requirements complete. 4 phases, 10 plans executed in ~5 hours.

Current codebase:
- `renderer/` — Python package: VideoRendererProtocol, RemotionRenderer, BrandConfig, RenderRequest, TextSegment models
- `remotion-service/` — Node.js/Express: render queue, ReelTemplate, TextOverlay, SegmentOverlay, Heebo font, Zod schemas
- `main.py` — FastAPI app: render routes, background tasks, Supabase/Airtable wiring
- `airtable_client.py` / `supabase_client.py` — storage clients

Known deployment considerations:
- Supabase `rendered-videos` bucket must be public for Airtable URL-based attachment to work
- Airtable attachment URLs expire after ~2 hours — frontend should not cache them long-term

## Constraints

- **Isolation**: Renderer module does not touch any existing Python code — completely standalone
- **Swappability**: Renderer engine behind VideoRendererProtocol — can be replaced without changing callers
- **Tech stack**: Remotion (Node.js) for rendering, Python for API layer and abstraction
- **Video format**: Instagram Reels standard — 9:16, 1080x1920, MP4
- **Language**: Hebrew RTL text with Heebo font, mixed bidirectional support
- **Storage**: Raw videos from Supabase, rendered videos to Supabase then Airtable attachment
- **Existing system**: Continues working unchanged

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Remotion over FFmpeg | Need animated text overlays (fade, enter/exit) — FFmpeg limited for animation | ✓ Good — animations work cleanly |
| Separate Node.js service | Remotion is Node.js/React; keeps Python backend clean, communicates via HTTP | ✓ Good — clean separation |
| API endpoint trigger (HTTP 202 + polling) | Most flexible — frontend or pipeline can call it; handles 30-300s renders | ✓ Good — async pattern works |
| Per-client brand templates | Each client has brand identity; templates store colors, fonts, positioning | ✓ Good — stage modifiers add flexibility |
| VideoRendererProtocol abstraction | Swap renderer engine without changing calling code | ✓ Good — clean Protocol-based design |
| `node:22-bookworm-slim` Docker base | Alpine causes 35% slowdown and Chrome downgrade failures | ✓ Good — stable Chromium renders |
| Heebo font (narrow subset loading) | Full variant loading causes delayRender timeout; narrow to hebrew+400+700 | ✓ Good — fast font loading |
| URL-based Airtable attachment | Airtable downloads from Supabase URL and re-hosts; requires public bucket | ✓ Good — but verify bucket is public on deploy |
| Remotion Sequence for segments | Resets useCurrentFrame() per segment; independent timing naturally | ✓ Good — clean per-segment isolation |

---
*Last updated: 2026-03-11 after v1.0 milestone*
