# Phase 4: Multi-Segment Text - Research

**Researched:** 2026-03-11
**Domain:** Multi-segment timed text rendering — Pydantic/Zod data models, Remotion Sequence component, per-role brand styling, auto-conversion layer
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Segment Data Model**
- New `segments` array replaces `hook_text` and `body_text` fields on the render request
- Auto-conversion for backward compatibility: if `hook_text`/`body_text` provided without `segments`, auto-convert to a 2-segment array internally. Single code path at render time, flexible input.
- Each segment object: `{ text, start_seconds, end_seconds, animation_style, role }`
- Timing in seconds (floats), not frames — consistent with `duration_in_seconds` on RenderRequest. Internal conversion to frames via `fps * seconds`.
- Segments must not overlap in time — sequential only. Validation rejects overlapping start/end times.
- Supported range: 1-5 segments per render. Validation at request time.
- Segment timing validated against video duration — reject if any segment's `end_seconds` > `duration_in_seconds`

**Segment Visual Layout**
- Each segment gets its own independent overlay box that fades in/out on its own lifecycle
- All segments use the brand's `textPosition` (top/center/bottom) — no per-segment position override
- Gap between segments: clean video with no text. Previous segment exits, brief pause (0.3-0.5s), next segment enters.
- Safe zone constraints apply per segment within the existing SAFE_ZONE_TOP/SAFE_ZONE_BOTTOM bounds

**Segment Styling & Roles**
- 3 fixed roles: `hook`, `body`, `cta` — enum restricted
- Role maps to brand config styling:
  - `hook` -> primary_color + hookFontSize + hookFontWeight (bold)
  - `body` -> secondary_color + bodyFontSize + regular weight (400)
  - `cta` -> primary_color + bodyFontSize + bold weight (same visual weight as hook, CTA-sized)
- SDMF stage modifiers apply to `hook` segments ONLY — body and cta unaffected. Matches Phase 3 pattern.
- Each segment specifies its own `animation_style` (fade/slide) — per-segment animation is required by the success criteria

**CTA Behavior**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEGM-01 | Render request can specify multiple text segments (hook, body, CTA) each with independent start/end timing and animation | Remotion `Sequence` component provides frame-accurate per-segment timing; Zod + Pydantic validation enables strict segment constraints; per-role styling maps directly to existing brand config fields |
</phase_requirements>

---

## Summary

Phase 4 adds multi-segment text support to the existing render pipeline. The core technical approach is well-understood: Remotion's `Sequence` component handles per-segment timing natively by resetting `useCurrentFrame()` to 0 within each sequence's window, which is exactly what is needed for independent per-segment animations. The data layer is straightforward extensions to existing Pydantic (`TextSegment` model on `RenderRequest`) and Zod schemas (`SegmentSchema` added to `ReelInputSchema`).

The most consequential design decision (left to Claude's Discretion) is where to perform auto-conversion from the legacy `hook_text`/`body_text` fields to `segments`. The codebase currently builds the Remotion payload in `renderer/remotion.py::render()`. The cleanest single code path is Python-side conversion inside `_run_render()` in `main.py` — before the payload is built — so `RemotionRenderer.render()` always receives a request with a populated `segments` list. The TypeScript side then needs no awareness of the legacy fields.

The second key decision is the `SegmentOverlay` component architecture. A single `SegmentOverlay` component that accepts per-segment props (text, role, animation style, brand config) and uses `useCurrentFrame()` relative to its `Sequence` container is the correct pattern. `ReelTemplate` maps over the segments array and renders each as a `<Sequence from={startFrame} durationInFrames={segmentDuration}>` wrapping a `<SegmentOverlay>`.

**Primary recommendation:** Use `Sequence` for segment timing, create a single `SegmentOverlay` component for rendering, do auto-conversion Python-side in `_run_render()`, and validate all constraints (overlap, duration, count) at Pydantic model level with a `model_validator`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| remotion | ^4.0.0 | `Sequence` component for per-segment frame windowing | Already in use; `Sequence` resets frame context per segment — exactly what independent animations need |
| zod | 4.3.6 | `SegmentSchema` + array validation in Remotion service | Already used for `ReelInputSchema`; `.array().min(1).max(5)` handles count validation |
| pydantic v2 | (from requirements.txt) | `TextSegment` model + `model_validator` on `RenderRequest` | Already used; `model_validator(mode='after')` handles cross-field validation (overlap, duration bounds) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| vitest | ^3.0.0 | TypeScript unit tests for schema + component logic | Already configured in `vitest.config.ts`; all TypeScript tests run with `npm test` |
| pytest + pytest-asyncio | (pyproject.toml: asyncio_mode=auto) | Python unit + integration tests | Already configured; `asyncio_mode = "auto"` means no `@pytest.mark.asyncio` needed for async tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Remotion `Sequence` | Manual `useCurrentFrame()` math with frame offset subtraction | Manual math works but Sequence is idiomatic, resets frame to 0 inside each window, cleaner per-segment animation code |
| Python-side auto-conversion | TypeScript-side conversion in render-queue.ts | TypeScript side is further from the request entry point; Python side keeps conversion with validation, single code path, aligns with existing brand resolution pattern |
| Single `SegmentOverlay` component | Separate component per role | Per-role components duplicate animation logic; a single component parameterized by role props is DRY and testable |

---

## Architecture Patterns

### Recommended Project Structure

New and modified files for this phase:

```
renderer/
├── models.py          # ADD: TextSegment model, add segments field to RenderRequest,
│                      #      add model_validator for overlap/duration/count checks
├── brand.py           # EXTEND: resolve_brand_for_render returns per-role styling dict
remotion-service/remotion/
├── schemas.ts         # ADD: SegmentSchema, add segments array to ReelInputSchema,
│                      #      make hookText/bodyText optional (backward compat)
├── SegmentOverlay.tsx # NEW: per-segment rendering component
├── ReelTemplate.tsx   # MODIFY: replace single TextOverlay with Sequence+SegmentOverlay loop
main.py                # MODIFY: _run_render adds auto-conversion hook_text/body_text -> segments
                       #         render() in remotion.py sends segments in payload
```

### Pattern 1: Remotion Sequence for Per-Segment Timing

**What:** `Sequence` wraps each segment rendering. It accepts `from` (start frame) and `durationInFrames`. Within the `Sequence`, `useCurrentFrame()` returns 0 at the segment's start — enabling each segment to run its own entrance/exit animation independent of absolute video position.

**When to use:** Any time a composition contains multiple independently-timed elements.

**Example:**
```typescript
// Source: Remotion official docs — https://www.remotion.dev/docs/sequence
import { Sequence, useCurrentFrame, useVideoConfig } from "remotion";

// In ReelTemplate, iterating over validated segments:
const { fps } = useVideoConfig();

return (
  <AbsoluteFill>
    {/* video layer */}
    {segments.map((seg, i) => {
      const startFrame = Math.round(seg.startSeconds * fps);
      const endFrame = Math.round(seg.endSeconds * fps);
      const durationInFrames = endFrame - startFrame;
      return (
        <Sequence key={i} from={startFrame} durationInFrames={durationInFrames}>
          <SegmentOverlay
            text={seg.text}
            role={seg.role}
            animationStyle={seg.animationStyle}
            brandConfig={brandConfig}
            textDirection={textDirection}
          />
        </Sequence>
      );
    })}
  </AbsoluteFill>
);
```

Inside `SegmentOverlay`, `useCurrentFrame()` returns `0` at the segment's logical start and `durationInFrames - 1` at its end — the existing fade/slide animation interpolation logic from `TextOverlay.tsx` works unchanged.

### Pattern 2: Per-Role Styling Resolution

**What:** A role-to-style lookup table (or function) that maps `hook | body | cta` to the correct brand config fields. Lives in the TypeScript `SegmentOverlay` component, not in Python — because the component already receives the full `brandConfig` object and applies styles directly.

**When to use:** Inside `SegmentOverlay` when computing text color, font size, and font weight.

**Example:**
```typescript
// Source: based on CONTEXT.md role->styling mapping
type SegmentRole = "hook" | "body" | "cta";

function resolveRoleStyle(
  role: SegmentRole,
  brand: BrandConfig
): { color: string; fontSize: number; fontWeight: number } {
  switch (role) {
    case "hook":
      return {
        color: brand.primaryColor,
        fontSize: brand.hookFontSize,
        fontWeight: brand.hookFontWeight,
      };
    case "body":
      return {
        color: brand.secondaryColor,
        fontSize: brand.bodyFontSize,
        fontWeight: 400,
      };
    case "cta":
      return {
        color: brand.primaryColor,
        fontSize: brand.bodyFontSize,
        fontWeight: 700,
      };
  }
}
```

### Pattern 3: Python-Side Auto-Conversion (Backward Compatibility)

**What:** `_run_render()` in `main.py` converts `hook_text`/`body_text` to a `segments` list before passing to the renderer. All existing callers that send `hook_text`/`body_text` without `segments` continue to work without changes.

**When to use:** `RenderRequest` arrives with `hook_text` and `body_text` set but `segments` is `None`.

**Example:**
```python
# In main.py _run_render() — before building the Remotion payload
def _build_segments(request: RenderRequest) -> list[dict]:
    """Return segments list — auto-converts legacy hook_text/body_text if needed."""
    if request.segments:
        return [s.model_dump() for s in request.segments]
    # Legacy auto-conversion: hook occupies first half, body second half
    mid = request.duration_in_seconds / 2
    return [
        {
            "text": request.hook_text,
            "start_seconds": 0.0,
            "end_seconds": mid,
            "animation_style": request.animation_style,
            "role": "hook",
        },
        {
            "text": request.body_text,
            "start_seconds": mid,
            "end_seconds": float(request.duration_in_seconds),
            "animation_style": request.animation_style,
            "role": "body",
        },
    ]
```

### Pattern 4: Pydantic model_validator for Segment Constraints

**What:** A `model_validator(mode='after')` on `RenderRequest` validates all cross-field constraints after individual field validation: segment count (1-5), no overlap (each segment's `start_seconds >= previous segment's end_seconds`), and timing bounds (`end_seconds <= duration_in_seconds`).

**When to use:** Any validation that requires comparing multiple fields — Pydantic v2 model validators run after all field validators.

**Example:**
```python
# In renderer/models.py
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal

class TextSegment(BaseModel):
    text: str
    start_seconds: float = Field(ge=0.0)
    end_seconds: float
    animation_style: Literal["fade", "slide"] = "fade"
    role: Literal["hook", "body", "cta"]

    @model_validator(mode='after')
    def end_after_start(self) -> "TextSegment":
        if self.end_seconds <= self.start_seconds:
            raise ValueError(
                f"end_seconds ({self.end_seconds}) must be greater than "
                f"start_seconds ({self.start_seconds})"
            )
        return self


class RenderRequest(BaseModel):
    source_video_url: str
    hook_text: str | None = None       # optional — present for backward compat
    body_text: str | None = None       # optional — present for backward compat
    segments: list[TextSegment] | None = None
    record_id: str
    # ... existing fields unchanged ...

    @model_validator(mode='after')
    def validate_segments_or_legacy(self) -> "RenderRequest":
        has_legacy = self.hook_text and self.body_text
        has_segments = self.segments is not None

        if not has_legacy and not has_segments:
            raise ValueError(
                "Provide either 'segments' or both 'hook_text' and 'body_text'"
            )
        if has_segments:
            segs = self.segments
            # Count constraint
            if not (1 <= len(segs) <= 5):
                raise ValueError(f"segments must have 1-5 items, got {len(segs)}")
            # No-overlap constraint (segments must be sequential)
            for i in range(1, len(segs)):
                if segs[i].start_seconds < segs[i-1].end_seconds:
                    raise ValueError(
                        f"Segment {i} start ({segs[i].start_seconds}s) overlaps "
                        f"with segment {i-1} end ({segs[i-1].end_seconds}s)"
                    )
            # Duration bounds
            for seg in segs:
                if seg.end_seconds > self.duration_in_seconds:
                    raise ValueError(
                        f"Segment end_seconds ({seg.end_seconds}s) exceeds "
                        f"video duration ({self.duration_in_seconds}s)"
                    )
        return self
```

### Pattern 5: SDMF Stage Modifiers — Hook Segments Only

**What:** `resolve_brand_for_render()` currently modifies hook font size and weight globally. For segments, the stage modifier output is used for `hook`-role segments; `body` and `cta` segments use the base brand config directly.

**When to use:** When building the `brandConfig` dict sent to Remotion. The current single `brandConfig` dict is still correct — the component side (TypeScript) uses role to pick which fields apply. The stage modifier's `hookFontSize` and `hookFontWeight` flow to hook segments; `bodyFontSize` flows to body and cta.

**No change needed to `resolve_brand_for_render()`** — it already outputs `hookFontSize`, `bodyFontSize`, `hookFontWeight` separately. The `SegmentOverlay` component picks the right subset based on role.

### Anti-Patterns to Avoid

- **Putting segment timing in CSS `display: none` toggling:** This is not how Remotion works. Use `Sequence` — it correctly handles frame counting and video thumbnail generation.
- **Computing per-segment frame offsets in the component using `useVideoConfig().durationInFrames`:** That gives the total video duration, not the segment duration. Inside `Sequence`, `useCurrentFrame()` is relative — use it directly.
- **Validating segment overlap in TypeScript only:** Overlap validation must be in Python (Pydantic model validator) so the `/render` endpoint rejects bad requests with 422 before the Remotion service ever receives them. TypeScript Zod schema should mirror this but the Python side is the authoritative rejection point.
- **Making `hookText`/`bodyText` required in the updated Zod schema:** These must become optional (or removed) to allow segment-only payloads. The Zod schema should accept either `segments` OR `hookText`+`bodyText` via `.refine()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-segment time windowing | Manual frame offset math in component | Remotion `Sequence` | Sequence resets `useCurrentFrame()` to 0 at segment start — no offset subtraction needed; animation interpolation code from TextOverlay reuses unchanged |
| Segment timing validation | Custom overlap-detection algorithm | Pydantic `model_validator` | Pydantic v2 model validators run after field validation, have access to all fields; `model_validator(mode='after')` is the established project pattern |
| Font weight outside loaded range | Loading weights 100-900 | Stick to loaded weights 400 and 700 | `fonts.ts` loads only `weights: ["400", "700"]` — requesting other weights causes `delayRender` timeout or falls back to wrong weight |

**Key insight:** Remotion `Sequence` is purpose-built for this exact use case — independent timed compositions within a single video. It handles all the frame-offset math internally.

---

## Common Pitfalls

### Pitfall 1: Font Weight 900 for CTA Not Loaded

**What goes wrong:** `cta` role styling uses `fontWeight: 700` (bold, same visual weight as hook). If someone sets CTA to weight 900 it will fail — only 400 and 700 are loaded.
**Why it happens:** `fonts.ts` intentionally loads only `weights: ["400", "700"]` to prevent `delayRender` timeout (established decision from pre-Phase 1).
**How to avoid:** CTA role uses `fontWeight: 700` — the same as the hook weight at non-stage-1. Never introduce 900 for CTA.
**Warning signs:** Chrome hanging during render; Remotion log showing font not found.

### Pitfall 2: Sequence `from` Must Be Non-Negative

**What goes wrong:** If `start_seconds` is negative or `end_seconds <= start_seconds`, Remotion throws at render time with a cryptic error.
**Why it happens:** `Sequence` prop `from` must be >= 0 and `durationInFrames` must be > 0.
**How to avoid:** `TextSegment` validates `start_seconds >= 0` (Field constraint) and `end_seconds > start_seconds` (model_validator). These are caught at request time, not render time.
**Warning signs:** Remotion render failing with "Sequence durationInFrames must be a positive number."

### Pitfall 3: `hookText`/`bodyText` Still Required in Zod Schema

**What goes wrong:** If the existing Zod `ReelInputSchema` keeps `hookText` and `bodyText` as required fields, all-segments-only requests fail validation in the Remotion service.
**Why it happens:** Current schema has `hookText: z.string()` (required). New payloads from the Python side send `segments` only.
**How to avoid:** Make `hookText` and `bodyText` optional in the Zod schema: `hookText: z.string().optional()`. Add `.refine()` that requires either `segments` or both `hookText`+`bodyText`.
**Warning signs:** 422 from Remotion service on valid segment-only requests.

### Pitfall 4: animationSpeedMs Applied Globally vs Per-Segment

**What goes wrong:** The brand's `animationSpeedMs` controls fade/slide speed. Currently it's a single brand config value. For multi-segment, each segment's `SegmentOverlay` receives the same `animationSpeedMs`. The decision from CONTEXT.md is that `animationSpeedMs` is a brand-level property, not per-segment. However, SDMF stage modifiers may change `animationSpeedMs` (stage 1 = 400ms, stage 5 = 600ms). Since SDMF modifiers apply to hook only, the `animationSpeedMs` from the modifier could reasonably apply to all segments or just hook.
**Why it happens:** `resolve_brand_for_render()` returns a single `animationSpeedMs` derived from stage modifiers.
**How to avoid:** Apply the stage-modified `animationSpeedMs` uniformly across all segments — it controls the brand's "energy level" not a per-segment property. This matches the existing architecture where `animationSpeedMs` is brand config, not segment config.
**Warning signs:** Inconsistent animation energy between segments at same awareness stage.

### Pitfall 5: Auto-Conversion Timing for Legacy Requests

**What goes wrong:** Auto-conversion splits `duration_in_seconds` into two equal halves. If the video is 15 seconds, hook gets 0-7.5s, body gets 7.5-15s. This may feel too long for hook and too long for body.
**Why it happens:** There is no "natural" split point in legacy data.
**How to avoid:** Equal halving is the simplest defensible choice. Document in code that this is the fallback behavior. The success criteria do not require particular timing for legacy requests — only that they continue to work.
**Warning signs:** No warning signs — this is a design choice, not an error.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Remotion Sequence — Frame Reset Behavior
```typescript
// Source: https://www.remotion.dev/docs/sequence
// Inside a <Sequence from={30} durationInFrames={60}>, useCurrentFrame() returns:
// - 0 when the absolute frame is 30
// - 59 when the absolute frame is 89
// - The sequence is invisible outside its from..from+durationInFrames window

import { Sequence, useCurrentFrame } from "remotion";

// In ReelTemplate with segment array:
const { fps } = useVideoConfig();
return (
  <AbsoluteFill>
    {segments.map((seg, i) => (
      <Sequence
        key={i}
        from={Math.round(seg.startSeconds * fps)}
        durationInFrames={Math.round((seg.endSeconds - seg.startSeconds) * fps)}
      >
        <SegmentOverlay {...seg} brandConfig={brandConfig} textDirection={textDirection} />
      </Sequence>
    ))}
  </AbsoluteFill>
);
```

### SegmentSchema in Zod (TypeScript)
```typescript
// Source: project pattern from schemas.ts + CONTEXT.md locked decisions
export const SegmentSchema = z.object({
  text: z.string(),
  startSeconds: z.number().min(0),
  endSeconds: z.number().positive(),
  animationStyle: z.enum(["fade", "slide"]).default("fade"),
  role: z.enum(["hook", "body", "cta"]),
});

export type Segment = z.infer<typeof SegmentSchema>;

// Updated ReelInputSchema — hookText/bodyText become optional, segments is new
export const ReelInputSchema = z.object({
  sourceVideoUrl: z.string(),
  hookText: z.string().optional(),           // legacy — kept for backward compat
  bodyText: z.string().optional(),           // legacy — kept for backward compat
  segments: z.array(SegmentSchema).min(1).max(5).optional(),
  textDirection: z.enum(["rtl", "ltr"]).default("rtl"),
  // note: top-level animationStyle kept for legacy payloads; segments override per-segment
  animationStyle: z.enum(["fade", "slide"]).default("fade"),
  durationInSeconds: z.number().min(3).max(90).default(15),
  sourceVideoLocalPath: z.string().optional(),
  brandConfig: BrandConfigSchema.optional(),
}).refine(
  (data) => data.segments || (data.hookText && data.bodyText),
  { message: "Provide either 'segments' or both 'hookText' and 'bodyText'" }
);
```

### TextSegment Pydantic Model (Python)
```python
# Source: project pattern from renderer/models.py + CONTEXT.md decisions
from pydantic import BaseModel, Field, model_validator
from typing import Literal

class TextSegment(BaseModel):
    text: str
    start_seconds: float = Field(ge=0.0)
    end_seconds: float
    animation_style: Literal["fade", "slide"] = "fade"
    role: Literal["hook", "body", "cta"]

    @model_validator(mode='after')
    def end_after_start(self) -> "TextSegment":
        if self.end_seconds <= self.start_seconds:
            raise ValueError(
                f"end_seconds ({self.end_seconds}) must be > start_seconds ({self.start_seconds})"
            )
        return self
```

### RemotionRenderer.render() — Segments in Payload (Python)
```python
# Source: project pattern from renderer/remotion.py — extends existing render() method
# Segment dicts are camelCased for Remotion service (matches Zod schema field names)
payload: dict[str, Any] = {
    "sourceVideoUrl": request.source_video_url,
    "textDirection": request.text_direction,
    "animationStyle": request.animation_style,
    "durationInSeconds": request.duration_in_seconds,
    "segments": [
        {
            "text": seg["text"],
            "startSeconds": seg["start_seconds"],
            "endSeconds": seg["end_seconds"],
            "animationStyle": seg["animation_style"],
            "role": seg["role"],
        }
        for seg in segments  # pre-built list from auto-conversion or direct
    ],
}
# hookText/bodyText omitted from payload — Remotion schema accepts segments-only
```

### SegmentOverlay Component (TypeScript)
```typescript
// Source: project pattern based on TextOverlay.tsx + Remotion docs
import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { getTextContainerStyle, getOverlayBoxStyle, hexToRgba } from "./TextOverlay.js";
import type { BrandConfig } from "./schemas.js";

type SegmentOverlayProps = {
  text: string;
  role: "hook" | "body" | "cta";
  animationStyle: "fade" | "slide";
  textDirection: "rtl" | "ltr";
  brandConfig?: BrandConfig;
};

export const SegmentOverlay: React.FC<SegmentOverlayProps> = ({
  text, role, animationStyle, textDirection, brandConfig,
}) => {
  const frame = useCurrentFrame();        // 0-relative inside Sequence window
  const { fps, durationInFrames } = useVideoConfig();

  const fadeFrames = Math.round(((brandConfig?.animationSpeedMs ?? 500) / 1000) * fps);

  const opacity = interpolate(
    frame,
    [0, fadeFrames, durationInFrames - fadeFrames, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Role-based styling
  const { color, fontSize, fontWeight } = resolveRoleStyle(role, brandConfig);

  // ... slide logic same as TextOverlay.tsx ...
};
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `hookText` + `bodyText` fields | `segments` array with role/timing per entry | Phase 4 | Enables arbitrary number of independently-timed text blocks |
| Single `TextOverlay` for whole video | `SegmentOverlay` per segment inside `Sequence` | Phase 4 | Each segment gets its own animation lifecycle |
| Global animation style on request | Per-segment `animation_style` field | Phase 4 | Hook can fade, CTA can slide — CONTEXT.md requirement |

**Deprecated/outdated after this phase:**
- `hookText` and `bodyText` as required fields: become optional legacy fields maintained for backward compat only
- Single `TextOverlay` component in `ReelTemplate`: replaced by a loop over `SegmentOverlay` components inside `Sequence` wrappers

---

## Open Questions

1. **`animationSpeedMs` interaction with per-segment animation**
   - What we know: Brand config has a single `animationSpeedMs`; SDMF stage modifiers may change it (400-600ms range). This is a brand-level speed setting.
   - What's unclear: Should hook segments use the stage-modified speed (matching current behavior) while body/cta use the base brand speed? Or should all segments use the stage-modified speed?
   - Recommendation: Use the stage-modified `animationSpeedMs` for all segments. The brand config sent to Remotion is already fully resolved by `resolve_brand_for_render()` — the `animationSpeedMs` in it already reflects the stage modifier. All segments receive the same `brandConfig`, so all get the same animation speed. This is the simplest and most consistent approach.

2. **Gap enforcement between segments**
   - What we know: CONTEXT.md says "clean video with no text, previous segment exits, brief pause (0.3-0.5s), next segment enters." The gap is enforced by the caller specifying non-overlapping `start_seconds`/`end_seconds` with space between them.
   - What's unclear: Should the system enforce a minimum gap (0.3s)? Or is that the caller's responsibility?
   - Recommendation: Do not enforce minimum gap at the API level. The "brief pause" is the caller's design decision. Validation rejects overlaps (`seg[i].start_seconds < seg[i-1].end_seconds`) but allows adjacent segments with zero gap.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| TypeScript Framework | vitest ^3.0.0 |
| TypeScript config file | `remotion-service/vitest.config.ts` |
| TypeScript quick run | `cd remotion-service && npm test` |
| TypeScript full suite | `cd remotion-service && npm test` |
| Python Framework | pytest + pytest-asyncio (asyncio_mode=auto) |
| Python config file | `pyproject.toml` (`testpaths = ["tests"]`) |
| Python quick run | `pytest tests/ -x` |
| Python full suite | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEGM-01 | `TextSegment` model accepts valid segment fields | unit | `pytest tests/test_segments.py::test_text_segment_valid -x` | Wave 0 |
| SEGM-01 | `TextSegment` rejects `end_seconds <= start_seconds` | unit | `pytest tests/test_segments.py::test_text_segment_end_before_start -x` | Wave 0 |
| SEGM-01 | `RenderRequest` with `segments` array validates count 1-5 | unit | `pytest tests/test_segments.py::test_render_request_segment_count -x` | Wave 0 |
| SEGM-01 | `RenderRequest` rejects overlapping segment times | unit | `pytest tests/test_segments.py::test_render_request_no_overlap -x` | Wave 0 |
| SEGM-01 | `RenderRequest` rejects `end_seconds > duration_in_seconds` | unit | `pytest tests/test_segments.py::test_render_request_exceeds_duration -x` | Wave 0 |
| SEGM-01 | Legacy `hook_text`/`body_text` auto-converts to 2 segments | unit | `pytest tests/test_segments.py::test_legacy_auto_conversion -x` | Wave 0 |
| SEGM-01 | `ReelInputSchema` accepts segment-only payload | unit | `cd remotion-service && npm test -- schema` | Wave 0 (extend schema.test.ts) |
| SEGM-01 | `ReelInputSchema` rejects payload with neither legacy nor segments | unit | `cd remotion-service && npm test -- schema` | Wave 0 (extend schema.test.ts) |
| SEGM-01 | `SegmentOverlay` opacity is 0 at frame 0 and at durationInFrames | unit | `cd remotion-service && npm test -- segment` | Wave 0 |
| SEGM-01 | Per-role styling: hook uses primaryColor+hookFontSize | unit | `cd remotion-service && npm test -- segment` | Wave 0 |
| SEGM-01 | Per-role styling: body uses secondaryColor+bodyFontSize | unit | `cd remotion-service && npm test -- segment` | Wave 0 |
| SEGM-01 | Per-role styling: cta uses primaryColor+bodyFontSize+bold | unit | `cd remotion-service && npm test -- segment` | Wave 0 |
| SEGM-01 | `_run_render()` sends segments in Remotion payload | integration | `pytest tests/test_render_routes.py::TestSegments -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x && cd remotion-service && npm test`
- **Per wave merge:** `pytest tests/ && cd remotion-service && npm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_segments.py` — covers SEGM-01 Python-side tests (TextSegment model, RenderRequest validation, auto-conversion, render route integration)
- [ ] `remotion-service/src/__tests__/segment-overlay.test.ts` — covers SEGM-01 TypeScript-side tests (SegmentSchema, SegmentOverlay role styling, animation opacity)

---

## Sources

### Primary (HIGH confidence)
- Remotion official docs: https://www.remotion.dev/docs/sequence — `Sequence` component API, `from` / `durationInFrames` props, frame reset behavior
- Existing codebase: `remotion-service/remotion/TextOverlay.tsx` — animation interpolation pattern reused in `SegmentOverlay`
- Existing codebase: `remotion-service/remotion/schemas.ts` — Zod schema pattern for extending with new fields
- Existing codebase: `renderer/models.py` — Pydantic v2 `model_validator` not yet used but `field_validator` pattern established; Pydantic v2 docs confirm `model_validator(mode='after')` is correct approach
- Existing codebase: `renderer/brand.py` — `resolve_brand_for_render()` outputs separate `hookFontSize`, `bodyFontSize`, `hookFontWeight` — SegmentOverlay role resolution uses these directly

### Secondary (MEDIUM confidence)
- Remotion official docs: https://www.remotion.dev/docs/use-current-frame — confirms `useCurrentFrame()` returns frame relative to `Sequence` container
- Pydantic v2 docs: https://docs.pydantic.dev/latest/concepts/validators/#model-validators — `model_validator(mode='after')` receives the full model instance with all fields validated

### Tertiary (LOW confidence)
- None — all findings are HIGH or MEDIUM confidence based on existing codebase patterns and official documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use with confirmed versions
- Architecture: HIGH — Remotion `Sequence` is well-documented, existing codebase patterns are clear
- Pitfalls: HIGH — derived from existing codebase decisions (font weight loading, Zod required fields) and Remotion API constraints
- Validation architecture: HIGH — test framework fully configured in both Python and TypeScript sides

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable — Remotion 4.x, Pydantic v2, Zod 4 all stable releases)
