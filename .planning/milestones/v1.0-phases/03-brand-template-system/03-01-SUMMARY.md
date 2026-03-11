---
phase: 03-brand-template-system
plan: 01
subsystem: brand-config
tags: [pydantic, zod, brand, fonts, airtable, remotion, tdd]
dependency_graph:
  requires: []
  provides: [BrandConfig, STAGE_MODIFIERS, resolve_brand_for_render, extract_brand_config, BrandConfigSchema, getFontFamily]
  affects: [renderer/remotion.py, main.py, remotion-service/remotion/schemas.ts]
tech_stack:
  added: [renderer/brand.py]
  patterns: [pydantic-field-validator, zod-optional-with-defaults, multi-font-loading, stage-modifier-pattern]
key_files:
  created:
    - renderer/brand.py
    - tests/test_brand_config.py
  modified:
    - renderer/models.py
    - renderer/__init__.py
    - airtable_client.py
    - renderer/remotion.py
    - main.py
    - remotion-service/remotion/schemas.ts
    - remotion-service/remotion/fonts.ts
    - remotion-service/src/__tests__/schema.test.ts
    - remotion-service/src/__tests__/font-loading.test.ts
decisions:
  - "BrandConfigSchema uses .optional() without .default({}) at top level — when brandConfig absent from payload, Remotion receives undefined and Zod does not auto-apply defaults; component handles fallback"
  - "STAGE_MODIFIERS uses relative scale (float) not absolute sizes — stage modifiers applied as brand.hook_font_size * scale, producing consistent visual hierarchy across all brand sizes"
  - "extract_brand_config() wraps entire BrandConfig(**raw) in try/except — any invalid combination (not just individual fields) falls back to all-defaults with warning log"
  - "fontFamily backward-compat export kept in fonts.ts — existing TextOverlay components continue working until Plan 02 updates them to use getFontFamily()"
metrics:
  duration: 5m 33s
  completed_date: 2026-03-11
  tasks_completed: 2
  files_changed: 9
---

# Phase 3 Plan 01: Brand Config + Stage Modifiers + Multi-Font Loading Summary

**One-liner:** Pydantic BrandConfig with SDMF stage modifiers, Zod BrandConfigSchema, and 4-font loading — threading per-client brand from Airtable through Python to Remotion.

## What Was Built

### Task 1: BrandConfig model, SDMF stage modifiers, Airtable extraction (TDD)

**renderer/models.py** extended with:
- `BrandConfig` Pydantic model — all fields optional with defaults matching current hardcoded look
- `@field_validator` for hex colors (validates `#RGB` and `#RRGGBB`, normalizes to uppercase)
- `@field_validator` for `font_family` — restricts to `{"Heebo", "Assistant", "Rubik", "Frank Ruhl Libre"}`
- `overlay_opacity` constrained to `[0.3, 0.8]`
- `RenderRequest` extended with: `client_id: str | None`, `awareness_stage: int | None (1-5)`, `brand_config: BrandConfig | None`

**renderer/brand.py** (new module):
- `STAGE_MODIFIERS` dict — stages 1-5 with `hook_size_scale`, `hook_font_weight`, `animation_speed_ms`
- Stage 1 (most emotional): scale=1.15, weight=900, speed=400ms
- Stage 3 (authority/default): scale=1.00, weight=700, speed=500ms
- `resolve_brand_for_render(brand, awareness_stage)` — returns camelCase dict for Remotion payload

**airtable_client.py** extended with:
- `extract_brand_config(client_record)` — maps 10 Airtable field names to BrandConfig fields, skips `None`/`""` values, falls back to `BrandConfig()` on validation error

**renderer/__init__.py** — added `BrandConfig` to exports and `__all__`

### Task 2: Remotion Zod schema, multi-font loading, Python pipeline wiring (TDD)

**remotion-service/remotion/schemas.ts** extended with:
- `BrandConfigSchema` — 12-field Zod object, all with defaults, `fontFamily` enum restricted to 4 curated fonts, `overlayOpacity` min/max enforcement
- `ReelInputSchema` — added `brandConfig: BrandConfigSchema.optional()`
- Backward compat: requests without `brandConfig` parse successfully, field remains `undefined`

**remotion-service/remotion/fonts.ts** replaced with:
- Loads all 4 fonts at module init: Heebo, Assistant, Rubik, Frank Ruhl Libre
- `FONT_MAP` mapping display names to CSS fontFamily strings
- `getFontFamily(name)` — lookup with fallback to `DEFAULT_FONT_FAMILY`
- `DEFAULT_FONT_FAMILY` and `fontFamily` backward-compat exports

**renderer/remotion.py** extended:
- `render()` now accepts optional `resolved_brand: dict[str, Any] | None = None`
- When provided, adds `payload["brandConfig"] = resolved_brand`

**main.py** `_run_render()` extended:
- Fetches brand config from Airtable when `request.client_id` is set
- Uses `BrandConfig()` (all defaults) when no `client_id`
- Calls `resolve_brand_for_render()` and passes result to `renderer.render()`

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| tests/test_brand_config.py | 30 new | All pass |
| tests/ (Python total) | 89 | All pass |
| remotion-service TS tests | 39 | All pass |

Zero regressions in existing tests.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 234fb75 | feat(03-01): BrandConfig model, SDMF stage modifiers, Airtable brand extraction |
| 2 | 8fb1a04 | feat(03-01): Extend Zod schema, multi-font loading, wire brand config through pipeline |

## Decisions Made

1. **BrandConfigSchema as bare optional (not `.default({})`):** When `brandConfig` is absent from the payload, it stays `undefined` at the Remotion component level. The component will handle the fallback. This avoids Zod silently converting absent fields to empty objects with defaults — keeping the data contract explicit.

2. **Stage modifiers as relative scale (not absolute):** `hook_font_size * scale` allows each brand to maintain its own proportions across stages. A brand with a large base font still scales correctly.

3. **extract_brand_config() full try/except:** Invalid individual fields could pass silently if only validated separately. Wrapping `BrandConfig(**raw)` catches cross-field constraint violations and logs the full error.

4. **Backward-compat fontFamily export in fonts.ts:** The existing `TextOverlay` component imports `{ fontFamily }`. Keeping this export as an alias for `DEFAULT_FONT_FAMILY` means no component changes are needed until Plan 02.

## Deviations from Plan

None — plan executed exactly as written.
