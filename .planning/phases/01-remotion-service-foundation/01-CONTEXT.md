# Phase 1: Remotion Service Foundation - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A running Node.js Docker service that renders Hebrew + English text overlaid on a Supabase source video and returns an accessible MP4 URL. This proves the entire render stack works correctly before any Python integration, brand templates, or multi-segment work begins.

This phase delivers the Remotion service ONLY. Python integration (Phase 2), brand templates (Phase 3), and multi-segment text (Phase 4) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Text Placement
- Hook text appears in the upper portion of the safe zone (top of the 1080x1420px visible area)
- Body text appears below the hook, within the safe zone — natural top-down reading flow
- Text uses a semi-transparent dark overlay/box behind it for readability on any video background
- Text is center-aligned by default (common in Reels, looks balanced on vertical video)

### Animation Timing & Style
- Default animation: fade-in/fade-out with medium speed (~0.5-1s transition)
- Additional animation option: slide-up from bottom as an alternative entrance
- Exit mirrors entrance (fade in → fade out, slide up → slide down)
- Brief clean gap between text segments (0.3-0.5s pause)

### Font & Text Sizing
- Default font: Heebo (clean, modern sans-serif, popular for Israeli marketing content)
- Font loading narrowed to `{ subsets: ['hebrew'], weights: ['400', '700'] }` (prevents delayRender timeout)
- Hook text is bold (700 weight) and larger than body text (~1.5x scale)
- Body text uses regular weight (400)

### Video Duration Handling
- If source video is longer than text content: trim to text duration + 1-2s outro
- If source video is shorter than text content: loop the video seamlessly
- Video plays at original speed, no distortion

### RTL & Hebrew (from research — locked)
- Use `direction: rtl` + `unicode-bidi: embed` on text containers
- NEVER use `unicode-bidi: bidi-override` (reverses Hebrew character order — silent failure)
- Hebrew + English mixed text handled by Chromium's native BiDi algorithm
- Pre-download Supabase source video to local disk before `renderMedia()` (signed URLs expire mid-render)

### Docker & Infrastructure (from research — locked)
- Base image: `node:22-bookworm-slim` (Debian, not Alpine — 35% faster renders)
- Official Remotion render server template as scaffold
- Express 5 + TypeScript + React 19 + Zod for schema validation
- Async job pattern: POST returns 202 + job ID, GET polls for status/result

### Claude's Discretion
- Exact pixel values for text positioning within safe zone
- Semi-transparent overlay opacity level
- Exact animation easing curves (spring constants, interpolation ranges)
- Video loop crossfade duration
- Error response format and HTTP status codes
- Docker multi-stage build optimization
- Remotion composition structure (component hierarchy)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `supabase_client.py`: Stub exists for Supabase Storage — confirms env vars (SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET) are already in config.py
- `config.py`: All environment variable patterns established — new Remotion service vars would follow the same pattern

### Established Patterns
- External service clients follow `{service}_client.py` naming pattern with async httpx
- All I/O is async with explicit timeouts per operation type
- Pydantic models for request/response validation
- Error propagation: specific errors bubble up, caught at route level

### Integration Points
- Phase 1 is a standalone Node.js service — no direct code integration with existing Python codebase
- The Remotion service runs as its own Docker container with its own HTTP API
- Phase 2 will create a `renderer/` Python module that calls this service via HTTP
- Supabase Storage credentials are already configured in `.env` — the Remotion service needs access to download raw videos

</code_context>

<specifics>
## Specific Ideas

- Content is primarily Hebrew (RTL) with occasional English words mixed in — this is the SDMF methodology style
- The rendered output must look professional enough for business owners to publish directly to Instagram
- Safe zone enforcement is critical — Instagram UI covers top ~250px and bottom ~250px of 1080x1920 frames

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-remotion-service-foundation*
*Context gathered: 2026-03-11*
