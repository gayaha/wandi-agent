---
phase: 02-python-integration-layer
plan: 02
subsystem: render-pipeline
tags: [fastapi, async-job, polling, tdd, httpx, remotion]
dependency_graph:
  requires: [VideoRendererProtocol, RemotionRenderer, RenderRequest, JobStatus, renderer-package]
  provides: [POST-/render, GET-/render-status, _run_render-background-task, GET-/renders/:id/file]
  affects: [02-03]
tech_stack:
  added: [pytest-asyncio ASGITransport fixture, httpx.AsyncClient in-process testing]
  patterns: [202-async-job-pattern, polling-loop-with-backoff, task-set-for-gc-safety, TDD red-green]
key_files:
  created:
    - tests/test_render_routes.py
    - tests/test_renderer_remotion.py
  modified:
    - remotion-service/server/index.ts
    - main.py
    - renderer/remotion.py
    - tests/conftest.py
decisions:
  - "app_client fixture uses ASGITransport(app=app) so tests route through ASGI without real HTTP socket"
  - "_background_tasks module-level set prevents asyncio garbage-collecting in-flight tasks"
  - "MAX_POLL_ATTEMPTS=120 with sleep capped at 5s gives 10-minute max render wait"
  - "Wait formula min(2+attempt, 5) ramps from 2s to 5s cap rather than exponential growth"
  - "_run_render stores tmp_path as video_url — Plan 02-03 replaces with Supabase CDN URL"
metrics:
  duration: "4m 47s"
  completed_date: "2026-03-11"
  tasks_completed: 2
  files_created: 2
  files_modified: 4
  tests_added: 17
requirements_satisfied: [INTG-01, INTG-04, INTG-05]
---

# Phase 2 Plan 02: Async Render Routes + Background Task Summary

**One-liner:** FastAPI POST /render (202 + job_id) and GET /render-status with polling background task and Remotion file-download endpoint, fully tested with mocked renderer.

## What Was Built

### Task 1: GET /renders/:id/file (Remotion Express endpoint)

Added a file-serving endpoint to `remotion-service/server/index.ts`:

- Imports `path` from `node:path` for safe disk path construction
- `GET /renders/:id/file`: checks job is completed, streams MP4 via `res.download()`
- Returns 404 if job not found or not in `completed` state
- Returns 500 if file missing from disk but headers not yet sent
- Placed **after** `GET /renders/:id` to avoid Express path-matching conflicts

### Task 2: FastAPI render routes + background task (TDD)

**RED:** Wrote 17 failing tests across two new files and updated `conftest.py`.

**GREEN:** Implemented in `main.py` and fixed a bug in `renderer/remotion.py`.

#### `main.py` additions

- `_render_jobs: dict[str, dict[str, Any]]` — in-memory job store
- `_background_tasks: set` — module-level set prevents GC of in-flight tasks
- `POST /render` — validates `RenderRequest`, stores accepted job, fires `asyncio.create_task(_run_render(...))`; returns `{"job_id": ..., "status": "accepted"}` in under 1 second
- `GET /render-status/{job_id}` — returns job dict or 404
- `_run_render()` — submit → poll with `min(2+attempt, 5)s` backoff (MAX_POLL_ATTEMPTS=120) → download → mark completed → fire callback
- `_send_render_callback()` — 3-attempt retry with exponential backoff (1s, 2s, 4s)

#### `tests/conftest.py`

Added `app_client` async fixture using `httpx.ASGITransport(app=app)` — no real HTTP socket needed.

#### `tests/test_render_routes.py` (9 tests)

- POST /render returns 202 + job_id
- POST /render responds in under 1 second (non-blocking)
- POST /render with missing fields returns 422
- GET /render-status returns job state dict
- GET /render-status with invalid id returns 404
- Background task transitions to `completed`
- Background task marks `timed_out` when MAX_POLL_ATTEMPTS exceeded
- Background task marks `failed` when renderer returns failed state
- Callback URL notified on completion

#### `tests/test_renderer_remotion.py` (8 tests)

- `render()` sends `sourceVideoUrl` matching `source_video_url`
- `render()` sends all required payload keys
- `render()` omits `callbackUrl` when `callback_url` is None
- `render()` includes `callbackUrl` when provided
- `get_status()` maps `queued` → `accepted`
- `get_status()` maps `in-progress` → `rendering`
- `get_status()` maps `completed` → `completed`
- `get_status()` maps `failed` → `failed`

## Verification Results

```
48 passed in 0.57s
```

All plan success criteria met:
- POST /render returns 202 + job_id immediately
- GET /render-status returns current job state, 404 for unknown
- Background task polls MAX_POLL_ATTEMPTS=120 with capped backoff
- _background_tasks set prevents GC risk
- Callback URL notified on completion/failure
- source_video_url passed as sourceVideoUrl to Remotion
- GET /renders/:id/file endpoint serves completed renders
- 48 total tests passing (17 new + 31 existing)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| a6b8471 | feat | Add GET /renders/:id/file to Remotion Express service |
| 0549aba | test | Add failing tests for render routes and RemotionRenderer HTTP client (RED) |
| 7c08994 | feat | Implement FastAPI render routes and background render task (GREEN) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed missing `await` on `client.post()` in RemotionRenderer.render()**
- **Found during:** Task 2 GREEN implementation (spotted during code review before running tests)
- **Issue:** `renderer/remotion.py` line 44 had `resp = client.post(...)` without `await` — would have returned a coroutine object instead of an HTTP response, causing a runtime `AttributeError` on `.raise_for_status()` or `.json()`
- **Fix:** Changed to `resp = await client.post(...)`
- **Files modified:** renderer/remotion.py
- **Commit:** 7c08994 (included in the GREEN implementation commit)

No other deviations — plan executed as written.

## Self-Check: PASSED

Files exist:
- [x] remotion-service/server/index.ts (modified — GET /renders/:id/file added)
- [x] main.py (modified — render routes + background task added)
- [x] renderer/remotion.py (modified — await bug fixed)
- [x] tests/conftest.py (modified — app_client fixture added)
- [x] tests/test_render_routes.py (created)
- [x] tests/test_renderer_remotion.py (created)

Commits verified:
- [x] a6b8471 (feat Task 1)
- [x] 0549aba (test RED Task 2)
- [x] 7c08994 (feat GREEN Task 2)
