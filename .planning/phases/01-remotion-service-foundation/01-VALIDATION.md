---
phase: 1
slug: remotion-service-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (Wave 0 installs — no existing test infra) |
| **Config file** | `remotion-service/vitest.config.ts` — Wave 0 creates |
| **Quick run command** | `cd remotion-service && npm test -- --testNamePattern "unit"` |
| **Full suite command** | `cd remotion-service && npm test` |
| **Estimated runtime** | ~60-90 seconds (includes one smoke render) |

---

## Sampling Rate

- **After every task commit:** Run `cd remotion-service && npm test -- --testNamePattern "unit"` (< 5s)
- **After every plan wave:** Run `cd remotion-service && npm test` (full suite ~60-90s)
- **Before `/gsd:verify-work`:** Full suite must be green + visual MP4 inspection
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | REND-01 | integration (smoke render) | `npm test -- --testNamePattern "REND-01"` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | REND-02 | manual (visual inspection) | visual only — open MP4 in player | N/A | ⬜ pending |
| 1-02-01 | 02 | 1 | REND-03 | unit (CSS position constants) | `npm test -- --testNamePattern "REND-03"` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | REND-04 | unit (interpolate output) | `npm test -- --testNamePattern "REND-04"` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | HEBR-01 | unit (component style props) | `npm test -- --testNamePattern "HEBR-01"` | ❌ W0 | ⬜ pending |
| 1-02-04 | 02 | 1 | HEBR-03 | unit (font module import) | `npm test -- --testNamePattern "HEBR-03"` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | HEBR-02 | manual (visual inspection) | visual only — inspect actual MP4 | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `remotion-service/vitest.config.ts` — vitest configuration
- [ ] `remotion-service/src/__tests__/safe-zone.test.ts` — stubs for REND-03
- [ ] `remotion-service/src/__tests__/animation.test.ts` — stubs for REND-04
- [ ] `remotion-service/src/__tests__/rtl-styles.test.ts` — stubs for HEBR-01
- [ ] `remotion-service/src/__tests__/font-loading.test.ts` — stubs for HEBR-03
- [ ] `remotion-service/src/__tests__/smoke-render.test.ts` — stubs for REND-01
- [ ] Framework install: `npm install -D vitest` inside `remotion-service/`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Text content appears visibly in rendered output | REND-02 | Cannot verify pixel-level text in MP4 without frame-diffing infra | Open rendered MP4 in video player, verify hook and body text are readable |
| Mixed Hebrew+English word order correct | HEBR-02 | Cannot verify bidi character order in rendered video without visual inspection | Render sentence with embedded English words, open MP4, verify word order matches expected RTL flow |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
