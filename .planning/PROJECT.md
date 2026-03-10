# Wandi — Video Renderer Module

## What This Is

Wandi is a SaaS platform for Instagram content creation and scheduling, targeting business owners. The backend (this repo) generates weekly content plans using the SDMF marketing methodology, and the frontend (separate React/Lovable app) handles client UI, approval flows, and scheduling. This milestone adds a standalone video renderer module that takes generated text content + raw video footage and produces finished Instagram Reels with styled text overlays.

## Core Value

Business owners get publish-ready Instagram Reels — text content rendered on video with their brand styling — without manual video editing.

## Requirements

### Validated

- ✓ Text content generation via Ollama using SDMF methodology — existing
- ✓ Airtable integration for client data, content queue, and storage — existing
- ✓ Async and sync API endpoints for content generation — existing
- ✓ Hebrew content generation with awareness stage targeting — existing

### Active

- [ ] Standalone video renderer module (Remotion-based, separate Node.js service)
- [ ] Abstraction layer allowing renderer engine to be swapped (Remotion today, others tomorrow)
- [ ] Render API endpoint on Python backend (receives text + video URL + template → returns rendered mp4)
- [ ] Per-client brand templates (colors, fonts, positioning) for text overlays
- [ ] RTL Hebrew text support with occasional English
- [ ] Static and animated text overlays (fade in/out, enter/exit animations)
- [ ] Instagram Reels format output (9:16 vertical, 1080x1920, up to 90 seconds)
- [ ] Raw video sourcing from Supabase Storage
- [ ] Rendered video saved as Airtable attachment (URL-accessible)

### Out of Scope

- Auto video selection (matching raw videos to content by tags) — future milestone
- Smart content generation agent (dynamic AI-driven content decisions) — future milestone
- Frontend changes — separate React/Lovable app, not in this repo
- Instagram publishing via Meta API — future milestone
- Modifications to existing content generation pipeline — must remain unchanged

## Context

- The existing backend is a Python/FastAPI service that generates text content via Ollama and saves to Airtable
- The SDMF methodology drives content strategy (5 awareness stages, magnets, hooks)
- All content is primarily Hebrew (RTL) with occasional English
- Raw source videos are stored in Supabase Storage
- Rendered videos must be accessible via URL for Airtable attachment and frontend display
- The frontend displays rendered videos from Airtable in a content gallery
- The renderer must be a standalone module — zero changes to existing code
- Remotion (Node.js/React) is the chosen rendering engine, running as a separate service
- Python backend communicates with Remotion service via HTTP API

## Constraints

- **Isolation**: Renderer module must not touch any existing Python code — completely standalone
- **Swappability**: Renderer engine must be behind an abstraction layer (interface/protocol) so it can be replaced
- **Tech stack**: Remotion (Node.js) for rendering, Python for the backend API layer and abstraction
- **Video format**: Instagram Reels standard — 9:16, 1080x1920, mp4
- **Language**: Hebrew RTL text support is mandatory
- **Storage**: Raw videos from Supabase, rendered videos to Airtable attachments
- **Existing system**: Must continue working unchanged during and after this build

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Remotion over FFmpeg | Need animated text overlays (fade, enter/exit) — FFmpeg limited for animation | — Pending |
| Separate Node.js service | Remotion is Node.js/React; keeps Python backend clean, communicates via HTTP | — Pending |
| API endpoint trigger | Most flexible — frontend or pipeline can call it; decoupled from both | — Pending |
| Per-client templates | Each client has brand identity; templates store colors, fonts, positioning | — Pending |
| Abstraction layer | User wants ability to swap renderer engine without changing calling code | — Pending |

---
*Last updated: 2026-03-11 after initialization*
