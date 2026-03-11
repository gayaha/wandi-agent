# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Video Renderer

**Shipped:** 2026-03-11
**Phases:** 4 | **Plans:** 10

### What Was Built
- Remotion Node.js render service (1080x1920 MP4, Hebrew RTL, animated text overlays)
- Python integration layer (FastAPI async API, VideoRendererProtocol, Supabase + Airtable pipeline)
- Per-client brand template system with SDMF awareness stage styling
- Multi-segment text support (hook/body/CTA with independent timing via Remotion Sequence)
- 202 tests (124 Python + 78 TypeScript) across 2,954 LOC test code

### What Worked
- TDD throughout all phases — tests caught integration issues early (e.g., snake_case/camelCase conversion between Python and TypeScript)
- Pure function exports for testability — `resolveRoleStyle()`, `hexToRgba()`, `getOverlayBoxStyle()` all testable without React context
- Research-first planning with gsd-phase-researcher — identified Remotion Sequence as the right primitive before writing code
- Stable velocity (~4-5 min/plan) across all 10 plans

### What Was Inefficient
- REQUIREMENTS.md tracking lagged behind implementation (TMPL-01, TMPL-02, INTG-03 all complete but not checked off)
- Context resets mid-workflow required extra recovery time
- Airtable URL-based attachment pattern was flagged as MEDIUM confidence but never verified with real API until late in milestone

### Patterns Established
- `renderer/` Python package with Protocol-based abstraction — clean swappability
- `remotion-service/` as standalone Node.js service with Express 5 + Zod validation
- Background task set (`_background_tasks`) for asyncio GC safety
- Narrowed font loading (`subsets: ['hebrew'], weights: ['400', '700']`) to avoid delayRender timeout
- Auto-conversion functions (e.g., `_build_segments()`) for backward compatibility

### Key Lessons
1. Always check requirement tracking after each phase verification — do not defer to milestone completion
2. URL-based Airtable attachments work (Airtable downloads and re-hosts) but require public Supabase bucket — verify infrastructure config during deployment
3. Remotion Sequence component is the right abstraction for timed text segments — each segment gets its own frame counter
4. `node:22-bookworm-slim` is the only viable Docker base for Remotion — Alpine breaks Chrome

### Cost Observations
- Model mix: ~30% opus, ~70% sonnet (executor and verifier agents used sonnet)
- Notable: Parallel wave execution (2 plans per wave) was efficient — most plans took 4-5 minutes

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 4 | 10 | First milestone — established TDD, Protocol abstraction, research-first planning |

### Cumulative Quality

| Milestone | Tests | LOC Source | LOC Tests |
|-----------|-------|------------|-----------|
| v1.0 | 202 | 2,060 | 2,954 |

### Top Lessons (Verified Across Milestones)

1. TDD prevents integration bugs across language boundaries (Python ↔ TypeScript)
2. Research before planning identifies the right primitives (Sequence, Protocol, etc.)
