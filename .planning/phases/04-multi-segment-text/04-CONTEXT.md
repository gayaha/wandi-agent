# Phase 4: Multi-Segment Text - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A single render request can include multiple independent text segments — hook, body, CTA — each appearing and disappearing at different times in the video with their own animation settings.

This phase delivers multi-segment text support ONLY. It builds on the existing brand template system (Phase 3) and render pipeline (Phase 2).

</domain>

<decisions>
## Implementation Decisions

### Segment Data Model
- New `segments` array replaces `hook_text` and `body_text` fields on the render request
- Auto-conversion for backward compatibility: if `hook_text`/`body_text` provided without `segments`, auto-convert to a 2-segment array internally. Single code path at render time, flexible input.
- Each segment object: `{ text, start_seconds, end_seconds, animation_style, role }`
- Timing in seconds (floats), not frames — consistent with `duration_in_seconds` on RenderRequest. Internal conversion to frames via `fps * seconds`.
- Segments must not overlap in time — sequential only. Validation rejects overlapping start/end times.
- Supported range: 1-5 segments per render. Validation at request time.
- Segment timing validated against video duration — reject if any segment's `end_seconds` > `duration_in_seconds`

### Segment Visual Layout
- Each segment gets its own independent overlay box that fades in/out on its own lifecycle
- All segments use the brand's `textPosition` (top/center/bottom) — no per-segment position override
- Gap between segments: clean video with no text. Previous segment exits, brief pause (0.3-0.5s), next segment enters.
- Safe zone constraints apply per segment within the existing SAFE_ZONE_TOP/SAFE_ZONE_BOTTOM bounds

### Segment Styling & Roles
- 3 fixed roles: `hook`, `body`, `cta` — enum restricted
- Role maps to brand config styling:
  - `hook` -> primary_color + hookFontSize + hookFontWeight (bold)
  - `body` -> secondary_color + bodyFontSize + regular weight (400)
  - `cta` -> primary_color + bodyFontSize + bold weight (same visual weight as hook, CTA-sized)
- SDMF stage modifiers apply to `hook` segments ONLY — body and cta unaffected. Matches Phase 3 pattern.
- Each segment specifies its own `animation_style` (fade/slide) — per-segment animation is required by the success criteria

### CTA Behavior
- CTA is just another role option — no special behavior beyond its styling
- No special persistence or positioning — same animation lifecycle as hook/body
- Caller decides content and timing; system just renders it with cta-role styling

### Claude's Discretion
- Exact Zod schema field names and nesting for the segments array
- How to implement the Remotion composition for multi-segment rendering (Sequence vs manual frame math)
- Auto-conversion logic from hook_text/body_text to segments array (Python-side or TypeScript-side)
- TypeScript component architecture: single SegmentOverlay component or separate per-segment compositions
- Error messages for validation failures (overlap, duration exceeded, role validation)
- How brand config's `animationSpeedMs` interacts with per-segment animation

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TextOverlay.tsx`: Has `hexToRgba()`, `getOverlayBoxStyle()`, `getTextContainerStyle()` — reusable for per-segment overlay rendering
- `ReelTemplate.tsx`: `POSITION_MAP` for text positioning — reuse for segment positioning
- `renderer/brand.py`: `resolve_brand_for_render()` produces resolved brand dict — extend to include segment-role-aware styling
- `renderer/models.py`: `BrandConfig` and `RenderRequest` — extend with segments model
- `remotion-service/remotion/schemas.ts`: `BrandConfigSchema` and `ReelInputSchema` — extend with segments schema
- `remotion-service/remotion/fonts.ts`: `getFontFamily()` — reuse for per-segment font resolution

### Established Patterns
- Zod schema validation at enqueue time in Remotion service (Phase 1 decision)
- Pydantic models for Python-side validation (renderer/models.py)
- Brand config computed in Python, Remotion receives explicit final values (dumb renderer pattern from Phase 3)
- TDD with vitest (TypeScript) and pytest (Python) — established in all prior phases
- Optional fields with defaults for backward compatibility

### Integration Points
- `renderer/models.py`: Add `TextSegment` model, add `segments` field to `RenderRequest`
- `remotion-service/remotion/schemas.ts`: Add `SegmentSchema` and `segments` array to `ReelInputSchema`
- `remotion-service/remotion/TextOverlay.tsx` or new `SegmentOverlay.tsx`: Render individual segments with independent timing
- `remotion-service/remotion/ReelTemplate.tsx`: Replace single TextOverlay with multiple segment overlays
- `renderer/brand.py`: Extend `resolve_brand_for_render()` to produce per-role styling dict
- `main.py _run_render()`: Auto-convert hook_text/body_text to segments if segments not provided

</code_context>

<specifics>
## Specific Ideas

- The auto-conversion from hook_text/body_text ensures all existing callers and tests continue to work without changes
- Each segment should feel like a standalone "moment" in the video — its own entrance, display, and exit
- The SDMF methodology uses hook to grab attention, body to deliver value, CTA to drive action — segment roles map directly to this flow
- Segment timing gives content creators precise control over pacing, which is critical for Instagram Reels engagement

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-multi-segment-text*
*Context gathered: 2026-03-11*
