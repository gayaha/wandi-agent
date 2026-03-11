---
phase: 2
slug: python-integration-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (Wave 0 installs — no existing test infra) |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` — Wave 0 creates |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5-10 seconds (all mocked, no real renders) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q` (< 10s)
- **After every plan wave:** Run `python -m pytest tests/ -v` (full suite)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | INTG-02 | unit (isinstance check) | `python -m pytest tests/test_renderer_protocol.py -x` | W0 | pending |
| 2-01-02 | 01 | 1 | INTG-01 | unit (route returns 202) | `python -m pytest tests/test_render_routes.py -x` | W0 | pending |
| 2-02-01 | 02 | 2 | INTG-04, INTG-05 | unit (mock Remotion) | `python -m pytest tests/test_renderer_remotion.py -x` | W0 | pending |
| 2-02-02 | 02 | 2 | INTG-01, INTG-05 | integration (mock) | `python -m pytest tests/test_render_routes.py -x` | W0 | pending |
| 2-03-01 | 03 | 3 | INTG-04 | unit (mock Supabase) | `python -m pytest tests/test_supabase_client.py -x` | W0 | pending |
| 2-03-02 | 03 | 3 | INTG-03 | unit (mock Airtable) | `python -m pytest tests/test_airtable_client.py -x` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `pip install pytest pytest-asyncio` — test framework
- [ ] `tests/__init__.py` — makes tests a package
- [ ] `tests/conftest.py` — shared fixtures (FastAPI TestClient, mock renderer, mock httpx)
- [ ] `tests/test_renderer_protocol.py` — stubs for INTG-02
- [ ] `tests/test_render_routes.py` — stubs for INTG-01, INTG-05
- [ ] `tests/test_renderer_remotion.py` — stubs for INTG-04
- [ ] `tests/test_supabase_client.py` — stubs for INTG-04 (source video)
- [ ] `tests/test_airtable_client.py` — stubs for INTG-03

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Airtable attachment field name correct | INTG-03 | Need to verify actual Airtable base schema | PATCH a test record with attachment URL, check in Airtable UI |
| Supabase bucket public access | INTG-04 | Need to check actual Supabase dashboard | Verify source video URL is accessible without auth |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
