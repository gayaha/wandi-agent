---
phase: 3
slug: brand-template-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-asyncio (Python) + vitest ^3.0.0 (TypeScript) |
| **Config file** | `pyproject.toml` (Python) + `remotion-service/vitest.config.ts` (TS) |
| **Quick run command** | `python -m pytest tests/test_brand_config.py -x && cd remotion-service && npm test -- src/__tests__/brand-styles.test.ts` |
| **Full suite command** | `python -m pytest tests/ -x && cd remotion-service && npm test` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_brand_config.py -x && cd remotion-service && npm test -- src/__tests__/brand-styles.test.ts`
- **After every plan wave:** Run `python -m pytest tests/ -x && cd remotion-service && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TMPL-01 | unit (Python) | `python -m pytest tests/test_brand_config.py::test_brand_config_defaults -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | TMPL-01 | unit (Python) | `python -m pytest tests/test_brand_config.py::test_invalid_hex_rejected -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | TMPL-01 | unit (Python) | `python -m pytest tests/test_brand_config.py::test_invalid_font_rejected -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | TMPL-01 | unit (Python) | `python -m pytest tests/test_brand_config.py::test_extract_brand_config_empty_strings -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | TMPL-01 | unit (TS) | `cd remotion-service && npm test -- src/__tests__/schema.test.ts` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | TMPL-01 | unit (TS) | `cd remotion-service && npm test -- src/__tests__/font-loading.test.ts` | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 1 | TMPL-01 | unit (TS) | `cd remotion-service && npm test -- src/__tests__/brand-styles.test.ts` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | TMPL-02 | unit (Python) | `python -m pytest tests/test_brand_config.py::test_stage_1_larger_than_stage_3 -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | TMPL-02 | unit (Python) | `python -m pytest tests/test_brand_config.py::test_stage_modifier_weights -x` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | TMPL-02 | unit (Python) | `python -m pytest tests/test_brand_config.py::test_stage_modifiers_relative_to_brand -x` | ❌ W0 | ⬜ pending |
| 03-02-04 | 02 | 2 | TMPL-01 | integration (Python) | `python -m pytest tests/test_render_routes.py::TestBrandConfig -x` | ❌ W0 | ⬜ pending |
| 03-02-05 | 02 | 2 | TMPL-01 | integration (Python) | `python -m pytest tests/test_brand_config.py::test_concurrent_brand_isolation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_brand_config.py` — stubs for TMPL-01 (BrandConfig model, extract_brand_config, merge, isolation) and TMPL-02 (stage modifiers)
- [ ] `remotion-service/src/__tests__/brand-styles.test.ts` — stubs for TMPL-01 (position map, textAlign, style helpers)
- [ ] Extend `remotion-service/src/__tests__/schema.test.ts` — brandConfig optional fields + defaults
- [ ] Extend `remotion-service/src/__tests__/font-loading.test.ts` — getFontFamily() with all curated fonts
- [ ] `renderer/brand.py` — new module (stdlib only, no new packages)
- [ ] No new package installs required

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual distinction between two brand configs in rendered MP4 | TMPL-01 | Requires human visual comparison of rendered video | Render same text with Brand A (Rubik, blue, center) and Brand B (Heebo, red, bottom); compare MP4 outputs side-by-side |
| Stage styling perceptibly changes visual tone | TMPL-02 | Numeric modifier values (1.15x) need visual judgment | Render same text/brand with stage 1 vs stage 3; verify stage 1 is noticeably bolder/larger |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 8s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
