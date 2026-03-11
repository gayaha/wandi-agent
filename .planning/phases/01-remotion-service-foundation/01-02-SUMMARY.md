---
phase: 01-remotion-service-foundation
plan: 02
subsystem: remotion-service
tags: [remotion, composition, rtl, hebrew, animation, heebo, safe-zone]
dependency_graph:
  requires: [remotion-service-skeleton, render-queue, zod-schema]
  provides: [reel-template-composition, text-overlay-component, heebo-font, safe-zone-constants, animation-system]
  affects: [01-03-PLAN]
tech_stack:
  added: []
  patterns: [interpolate-fade-animation, spring-slide-animation, module-level-font-loading, rtl-embed-bidi, safe-zone-positioning]
key_files:
  created:
    - remotion-service/remotion/constants.ts
    - remotion-service/remotion/fonts.ts
    - remotion-service/remotion/ReelTemplate.tsx
    - remotion-service/remotion/TextOverlay.tsx
    - remotion-service/src/__tests__/safe-zone.test.ts
    - remotion-service/src/__tests__/animation.test.ts
    - remotion-service/src/__tests__/rtl-styles.test.ts
    - remotion-service/src/__tests__/font-loading.test.ts
  modified:
    - remotion-service/remotion/Root.tsx
    - remotion-service/remotion/schemas.ts
decisions:
  - Used getTextContainerStyle() exported helper for testable RTL style assertions without rendering full React component
  - Added sourceVideoLocalPath as optional field in ReelInputSchema (injected by render-queue at render time)
  - Exit slide animation uses interpolate (not reverse spring) for predictable frame-based control
metrics:
  duration: 3m 53s
  completed: "2026-03-11T00:54:35Z"
  tasks_completed: 2
  tasks_total: 2
  tests_passing: 21
  files_created: 8
  files_modified: 2
---

# Phase 01 Plan 02: ReelTemplate Composition with Hebrew RTL and Animations Summary

Remotion composition with ReelTemplate (OffthreadVideo + safe-zone TextOverlay), Heebo font loading at module level with hebrew subset, fade/slide animations via interpolate()/spring(), and RTL text styling with direction:rtl + unicodeBidi:embed.

## Tasks Completed

### Task 1: Create constants, font loading, and unit test scaffolds
**Commit:** ae67129

Created:
- **constants.ts**: Safe zone constants (SAFE_ZONE_TOP=250, SAFE_ZONE_BOTTOM=250, SAFE_ZONE_HEIGHT=1420), animation timing (FADE_IN_FRAMES=15, FADE_OUT_FRAMES=15 at 30fps), video dimensions (1080x1920)
- **fonts.ts**: Heebo font loaded at module level via `@remotion/google-fonts/Heebo` with weights 400/700 and hebrew subset only (prevents delayRender timeout per locked decision)
- **safe-zone.test.ts**: 4 tests for REND-03 safe zone positioning (all constants verified, Instagram UI overlap check)
- **animation.test.ts**: 4 tests for REND-04 fade interpolation (opacity at frame 0, FADE_IN_FRAMES, pre-fade-out, last frame)
- **rtl-styles.test.ts**: 3 tests for HEBR-01 RTL properties (direction:rtl, unicodeBidi:embed, never bidi-override) — intentionally RED at this point (TDD)
- **font-loading.test.ts**: 1 test for HEBR-03 font family is Heebo

### Task 2: Build ReelTemplate and TextOverlay compositions with full animation and RTL support
**Commit:** 3f1183d

Created:
- **ReelTemplate.tsx**: Main composition component rendering OffthreadVideo (or black fallback) with TextOverlay positioned within the safe zone (top=250, height=1420). Uses AbsoluteFill layers for video and text overlay.
- **TextOverlay.tsx**: RTL-aware animated text overlay with:
  - Fade animation using `interpolate()` with keyframes [0, FADE_IN_FRAMES, durationInFrames-FADE_OUT_FRAMES, durationInFrames] mapped to [0,1,1,0]
  - Slide animation using `spring()` for entrance (translateY 80->0) combined with interpolate for exit (0->80)
  - Semi-transparent dark overlay box (rgba(0,0,0,0.55), borderRadius 16)
  - Hook text: bold 700 weight, 52px; Body text: regular 400, 36px
  - `getTextContainerStyle()` helper exported for testable RTL assertions

Modified:
- **Root.tsx**: Replaced placeholder composition with real ReelTemplate component, Hebrew sample defaultProps
- **schemas.ts**: Added optional `sourceVideoLocalPath` field for render-queue injection

## Verification Results

- All 21 tests pass (6 test files, vitest 3.2.4)
- TypeScript compiles with zero errors
- ReelTemplate uses OffthreadVideo (not Video) for source video
- Safe zone constants enforce 250px top/bottom margins
- RTL styles use embed, never bidi-override
- Heebo font loaded at module level with hebrew subset and weights 400/700
- Animation is frame-based (interpolate/spring), not CSS transitions

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Exported getTextContainerStyle() helper**: Rather than trying to render TextOverlay in tests (which requires React/Remotion context), exported a pure function that returns the RTL style object. Tests import and assert on the returned CSS properties directly.
2. **sourceVideoLocalPath as optional schema field**: Added directly to ReelInputSchema rather than as a separate type. The render-queue already spreads this field into inputProps, and making it optional means the HTTP validation schema still works without it.
3. **Exit slide via interpolate, not reverse spring**: The slide-out animation at the end uses `interpolate()` mapping the last FADE_OUT_FRAMES to translateY 0->80, rather than a reverse spring. This gives predictable, frame-exact timing that matches the fade-out duration.

## Self-Check: PASSED

- All 8 created files verified to exist on disk
- Both 2 modified files verified to exist on disk
- Commit ae67129 verified in git log
- Commit 3f1183d verified in git log
- 01-02-SUMMARY.md verified to exist
