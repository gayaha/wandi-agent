---
phase: 04-multi-segment-text
plan: "01"
subsystem: data-models
tags: [pydantic, zod, segments, tdd, python, typescript]
dependency_graph:
  requires: []
  provides: [TextSegment model, SegmentSchema, updated ReelInputSchema, _build_segments auto-conversion, segments payload in RemotionRenderer]
  affects: [renderer/models.py, remotion-service/remotion/schemas.ts, main.py, renderer/remotion.py]
tech_stack:
  added: []
  patterns: [pydantic model_validator cross-field validation, Zod .refine() for either/or fields, auto-conversion from legacy fields to segment dicts]
key_files:
  created:
    - tests/test_segments.py
  modified:
    - renderer/models.py
    - remotion-service/remotion/schemas.ts
    - remotion-service/src/__tests__/schema.test.ts
    - main.py
    - renderer/remotion.py
    - renderer/__init__.py
    - remotion-service/remotion/ReelTemplate.tsx
    - remotion-service/server/render-queue.ts
decisions:
  - "TextSegment uses model_validator(mode='after') for end_seconds > start_seconds — cross-field constraint cannot be expressed as a simple Field constraint"
  - "RenderRequest hook_text/body_text changed to optional with None default — model_validator enforces either/or, existing callers unaffected"
  - "_build_segments splits duration in half for legacy auto-conversion — equal halves is the simplest deterministic split"
  - "RemotionRenderer.render() sends segments param when provided, falls back to hookText/bodyText defensively"
  - "ReelTemplate.tsx uses hookText ?? '' / bodyText ?? '' — Plan 04-02 will add segment-aware rendering; this keeps TS clean meanwhile"
  - "render-queue.ts runRender parameter typed as ReelInput (not inline object) — keeps in sync with schema changes automatically"
metrics:
  duration: "5m 11s"
  completed_date: "2026-03-11"
  tasks_completed: 2
  files_modified: 8
  files_created: 1
  tests_added: 40
  total_tests_passing: 191
---

# Phase 4 Plan 1: TextSegment Model and Segment Schemas Summary

**One-liner:** Pydantic TextSegment with cross-field timing validation + Zod SegmentSchema + ReelInputSchema either/or refine + _build_segments auto-conversion from legacy hook/body fields.

## What Was Built

### TextSegment Pydantic Model (`renderer/models.py`)

New `TextSegment(BaseModel)` with:
- `text: str`
- `start_seconds: float = Field(ge=0.0)` — rejects negative values
- `end_seconds: float`
- `animation_style: Literal["fade", "slide"] = "fade"`
- `role: Literal["hook", "body", "cta"]`
- `@model_validator(mode='after')` enforcing `end_seconds > start_seconds`

### Updated RenderRequest (`renderer/models.py`)

- Changed `hook_text: str` to `hook_text: str | None = None`
- Changed `body_text: str` to `body_text: str | None = None`
- Added `segments: list[TextSegment] | None = None`
- Added `@model_validator(mode='after')` enforcing:
  - Either `segments` or (`hook_text` + `body_text`) must be present
  - When segments: count 1-5, no overlap, all end within `duration_in_seconds`

### Zod SegmentSchema (`remotion-service/remotion/schemas.ts`)

New `SegmentSchema` with `text`, `startSeconds (min 0)`, `endSeconds (positive)`, `animationStyle (default "fade")`, `role (hook/body/cta)`. Exports `Segment` type.

### Updated ReelInputSchema (`remotion-service/remotion/schemas.ts`)

- `hookText`/`bodyText` changed from required to `.optional()`
- Added `segments: z.array(SegmentSchema).min(1).max(5).optional()`
- Added `.refine()` enforcing either segments or hookText+bodyText

### Auto-Conversion Function (`main.py`)

`_build_segments(request: RenderRequest) -> list[dict[str, Any]]`:
- When `request.segments` is set: returns camelCase dicts directly
- Legacy path: splits `duration_in_seconds` in half, hook gets 0-mid, body gets mid-duration

### Updated RemotionRenderer (`renderer/remotion.py`)

`render()` now accepts `segments: list[dict[str, Any]] | None = None`:
- When segments provided: `payload["segments"] = segments` (no hookText/bodyText)
- When segments is None (defensive): falls back to legacy hookText/bodyText

## Test Coverage

| File | Tests | What It Covers |
|------|-------|----------------|
| `tests/test_segments.py` | 27 | TextSegment validation, RenderRequest with segments, legacy mode |
| `remotion-service/src/__tests__/schema.test.ts` | +13 new | SegmentSchema, ReelInputSchema segments-only + legacy paths |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed TypeScript compilation errors from schema changes**
- **Found during:** Task 2, after updating ReelInputSchema to make hookText/bodyText optional
- **Issue:** `ReelTemplate.tsx` passed `hookText` and `bodyText` (now `string | undefined`) to `TextOverlay` which expects `string`. `render-queue.ts` had inline type annotation with `hookText: string` that no longer matched parsed schema type.
- **Fix:** In `ReelTemplate.tsx`, used `hookText ?? ""` / `bodyText ?? ""` fallbacks. In `render-queue.ts`, replaced inline type annotation with `ReelInput` type import from schemas.
- **Files modified:** `remotion-service/remotion/ReelTemplate.tsx`, `remotion-service/server/render-queue.ts`
- **Commit:** `4f5c652`
- **Note:** This is a minimal fix for type safety; Plan 04-02 will replace the hookText/bodyText rendering with actual segment-aware components.

## Self-Check: PASSED

All files exist:
- tests/test_segments.py: FOUND
- renderer/models.py: FOUND (contains TextSegment class)
- remotion-service/remotion/schemas.ts: FOUND (contains SegmentSchema)
- main.py: FOUND (contains _build_segments)
- renderer/remotion.py: FOUND
- .planning/phases/04-multi-segment-text/04-01-SUMMARY.md: FOUND

All commits exist:
- 6dc55bd: Task 1 commit FOUND
- 4f5c652: Task 2 commit FOUND
