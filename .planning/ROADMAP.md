# Roadmap: Wandi Video Renderer

## Overview

This milestone adds a standalone video renderer module to the Wandi platform. The build proceeds in four phases that follow the dependency graph of the system: first a verified Remotion Node.js service that proves Hebrew RTL rendering works correctly, then a Python abstraction layer that exposes the render capability via a swappable protocol and async HTTP API, then a brand template system that produces per-client styled output, and finally multi-segment text support for full content structure. Each phase delivers a verifiable capability before the next adds complexity.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Remotion Service Foundation** - Running Node.js Docker service that renders verified Hebrew + English text on Supabase video
- [ ] **Phase 2: Python Integration Layer** - FastAPI endpoint with VideoRendererProtocol, async job pattern, and Airtable output storage
- [ ] **Phase 3: Brand Template System** - Per-client brand templates with font, color, position, and animation parameters
- [ ] **Phase 4: Multi-Segment Text** - Multiple independent text segments with per-segment timing (hook, body, CTA)

## Phase Details

### Phase 1: Remotion Service Foundation
**Goal**: A running Node.js Docker service that renders Hebrew + English text overlaid on a Supabase source video and returns an accessible MP4 URL — proving the entire render stack works correctly before any integration or template work begins
**Depends on**: Nothing (first phase)
**Requirements**: REND-01, REND-02, REND-03, REND-04, HEBR-01, HEBR-02, HEBR-03
**Success Criteria** (what must be TRUE):
  1. Developer can POST a render request to the Node.js service and receive a job ID immediately (HTTP 202), then poll and receive a completed MP4 URL
  2. The rendered MP4 is 1080x1920, H.264 video, AAC audio, 30fps — passes Instagram Reels format spec
  3. Hebrew text in the rendered video displays right-to-left correctly, and embedded English words within Hebrew sentences appear in correct bidirectional order (verified by visual inspection of actual MP4 output, not Studio preview)
  4. Text overlays appear within the safe zone (not covered by Instagram UI top/bottom bars) and animate with at least fade-in and fade-out
  5. The Hebrew font (Heebo or Assistant) is confirmed loaded — not a system fallback — by inspecting rendered glyph shapes
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Bootstrap Remotion render server with Express 5, async job queue, Zod schema, Dockerfile, and vitest test infrastructure
- [x] 01-02-PLAN.md — Build ReelTemplate composition with Hebrew font loading, RTL text overlays, safe zone positioning, and fade/slide animations
- [ ] 01-03-PLAN.md — Smoke test render with Hebrew + English text, validate MP4 format, visual verification of RTL and font

### Phase 2: Python Integration Layer
**Goal**: A Python `renderer/` module with `VideoRendererProtocol`, `RemotionRenderer` implementation, and a FastAPI endpoint — so Python code can submit a render job, poll to completion, and receive a URL saved as an Airtable attachment, without any Remotion-specific coupling in business logic
**Depends on**: Phase 1
**Requirements**: INTG-01, INTG-02, INTG-03, INTG-04, INTG-05
**Success Criteria** (what must be TRUE):
  1. Calling the FastAPI render endpoint returns HTTP 202 with a job ID in under 1 second, regardless of how long the actual render takes
  2. Polling the status endpoint with the job ID eventually returns a completed status and an accessible MP4 URL
  3. The rendered MP4 URL is saved as an attachment on the correct Airtable content queue record and is accessible via that URL
  4. Source video is fetched from Supabase Storage at render time using the video URL in the request — no manual download step required from the caller
  5. Swapping the renderer engine (replacing `RemotionRenderer` with a different implementation of `VideoRendererProtocol`) requires zero changes to the FastAPI endpoint or any calling code
**Plans**: TBD

Plans:
- [ ] 02-01: Define VideoRendererProtocol, RenderRequest/JobStatus models, and RemotionRenderer skeleton
- [ ] 02-02: Implement async job pattern — FastAPI endpoint returns 202, status polling endpoint, httpx async client calling Phase 1 service
- [ ] 02-03: Wire Supabase source video fetch and Airtable attachment upload (URL-based)

### Phase 3: Brand Template System
**Goal**: The render pipeline accepts per-client brand configuration — primary/secondary colors, font family, text positioning, and awareness-stage styling — and produces visually distinct, branded output for each client
**Depends on**: Phase 2
**Requirements**: TMPL-01, TMPL-02
**Success Criteria** (what must be TRUE):
  1. Rendering the same text content with two different client brand configs produces visually distinct MP4 outputs (different fonts, colors, or text positions)
  2. Specifying an SDMF awareness stage in the render request changes the visual styling of the output (e.g., Stage 1 bold/high-contrast vs Stage 3 measured/authoritative) without requiring separate template files per stage
  3. Brand template data from one client render job does not appear in any other client's rendered output (isolation verified under concurrent submissions)
**Plans**: TBD

Plans:
- [ ] 03-01: Extend Zod schema and ReelTemplate composition with brand config inputProps (colors, font, position, animationStyle)
- [ ] 03-02: Implement awareness-stage style mapping and benchmark template CSS for GPU-fallback effects

### Phase 4: Multi-Segment Text
**Goal**: A single render request can include multiple independent text segments — hook, body, CTA — each appearing and disappearing at different times in the video with their own animation settings
**Depends on**: Phase 3
**Requirements**: SEGM-01
**Success Criteria** (what must be TRUE):
  1. A render request with three text segments (hook at seconds 0-3, body at seconds 3-8, CTA at seconds 8-12) produces a video where each segment appears and disappears at the specified times, confirmed by frame inspection
  2. Each segment can have independent animation style (e.g., hook fades in, CTA slides up) without affecting the other segments
  3. Removing, reordering, or adding segments in the request payload changes only the affected segments in the output — no global re-render required
**Plans**: TBD

Plans:
- [ ] 04-01: Extend render schema and ReelTemplate to accept segment array with per-segment timing and animation
- [ ] 04-02: End-to-end test with multi-segment Hebrew content (hook/body/CTA) through the full Python-to-Remotion pipeline

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Remotion Service Foundation | 2/3 | In progress | - |
| 2. Python Integration Layer | 0/3 | Not started | - |
| 3. Brand Template System | 0/2 | Not started | - |
| 4. Multi-Segment Text | 0/2 | Not started | - |
