---
phase: 4
slug: multi-segment-text
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **TypeScript Framework** | vitest ^3.0.0 |
| **TypeScript config file** | `remotion-service/vitest.config.ts` |
| **TypeScript quick run** | `cd remotion-service && npm test` |
| **Python Framework** | pytest + pytest-asyncio (asyncio_mode=auto) |
| **Python config file** | `pyproject.toml` (`testpaths = ["tests"]`) |
| **Python quick run** | `pytest tests/ -x` |
| **Full suite command** | `pytest tests/ -x && cd remotion-service && npm test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** `pytest tests/ -x && cd remotion-service && npm test`
- **After every plan wave:** `pytest tests/ && cd remotion-service && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01 | 01 | 1 | SEGM-01 | unit | `pytest tests/test_segments.py -x` | ❌ W0 | ⬜ pending |
| 04-02 | 01 | 1 | SEGM-01 | unit | `cd remotion-service && npm test -- segment` | ❌ W0 | ⬜ pending |
| 04-03 | 01 | 1 | SEGM-01 | unit | `cd remotion-service && npm test -- schema` | ✅ (extend) | ⬜ pending |
| 04-04 | 02 | 2 | SEGM-01 | integration | `pytest tests/test_render_routes.py::TestSegments -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_segments.py` — covers SEGM-01 Python-side tests (TextSegment model, RenderRequest validation, auto-conversion, overlap/duration checks)
- [ ] `remotion-service/src/__tests__/segment-overlay.test.ts` — covers SEGM-01 TypeScript-side tests (SegmentSchema, SegmentOverlay role styling, animation opacity)

*Existing `schema.test.ts` and `test_render_routes.py` will be extended.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual segment appearance/disappearance at correct times | SEGM-01 | Requires rendering actual video and visual inspection | Render a 15s video with 3 segments, play back and verify timing |
| Hebrew RTL rendering in segments | SEGM-01 | Font rendering is visual | Confirm Hebrew text renders correctly in each segment role |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
