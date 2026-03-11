---
phase: 02-python-integration-layer
plan: 03
subsystem: render-pipeline
tags: [supabase, airtable, upload, attachment, tdd, httpx, python]
dependency_graph:
  requires: [POST-/render, _run_render-background-task, RenderRequest, VideoRendererProtocol]
  provides: [supabase_client.upload_video, supabase_client.get_source_video_url, airtable_client.update_content_queue_video_attachment, full-render-pipeline]
  affects: [INTG-03, INTG-04]
tech_stack:
  added: [supabase==2.28.0, supabase-py storage3 client]
  patterns: [sync-supabase-in-async-task, url-based-airtable-attachment, temp-file-cleanup-try-except]
key_files:
  created:
    - tests/test_supabase_client.py
    - tests/test_airtable_client.py
  modified:
    - supabase_client.py
    - airtable_client.py
    - main.py
    - requirements.txt
    - tests/test_render_routes.py
decisions:
  - "Patch supabase_client.create_client (not supabase.create_client) in tests — module imports create_client directly so patch must be on the module's binding"
  - "sync supabase-py client acceptable inside asyncio background task — IO is fast (upload) and does not block the event loop significantly"
  - "os.remove wrapped in try/except OSError to handle missing tmp file without crashing the pipeline"
  - "destination path pattern is {record_id}/{job_id}.mp4 — groups videos by Airtable record for easy browsing in Supabase Storage"
  - "Remotion health check added to lifespan startup — warns early if service unreachable"
metrics:
  duration: "5m 45s"
  completed_date: "2026-03-11"
  tasks_completed: 2
  files_created: 2
  files_modified: 5
  tests_added: 11
requirements_satisfied: [INTG-03, INTG-04]
---

# Phase 2 Plan 03: Supabase Upload + Airtable Attachment Pipeline Summary

**One-liner:** supabase_client.upload_video() uploads MP4 to Supabase Storage and returns a public URL, which is saved as an Airtable attachment via update_content_queue_video_attachment(), completing the full render -> download -> upload -> attach pipeline in main.py.

## What Was Built

### Task 1: supabase_client.upload_video() and Airtable attachment function (TDD)

**RED:** Wrote 8 failing tests across `tests/test_supabase_client.py` and `tests/test_airtable_client.py`.

**GREEN:** Implemented both functions.

#### `supabase_client.py` (replaced stub with working implementation)

- `_get_client() -> Client`: creates a `supabase-py` client from `config.SUPABASE_URL` and `config.SUPABASE_KEY`
- `upload_video(file_path, destination) -> str`: opens file in binary mode, calls `storage.from_(SUPABASE_BUCKET).upload(path=destination, file=f, file_options={"content-type": "video/mp4", "upsert": "true"})`, then returns `get_public_url(destination)`
- `get_source_video_url(video_path) -> str`: calls `storage.from_(SUPABASE_SOURCE_BUCKET).get_public_url(video_path)` to construct a public URL for source videos

#### `airtable_client.py` (new function appended to Content Queue section)

- `update_content_queue_video_attachment(record_id, video_url) -> dict`: sends `PATCH {BASE_URL}/{TABLE_CONTENT_QUEUE}/{record_id}` with `{"fields": {"Rendered Video": [{"url": video_url}]}}` — the format Airtable expects for URL-based attachment ingestion

#### `requirements.txt`

- Added `supabase==2.28.0`

#### `tests/test_supabase_client.py` (5 tests)

- `test_upload_video_calls_storage_upload`: verifies `storage.from_(SUPABASE_BUCKET).upload()` called with correct `path`
- `test_upload_video_passes_file_options`: verifies `file_options={"content-type": "video/mp4", "upsert": "true"}`
- `test_upload_video_returns_public_url`: verifies function returns result of `get_public_url()`
- `test_upload_video_uses_rendered_bucket`: verifies `from_()` called with `config.SUPABASE_BUCKET`
- `test_get_source_video_url_uses_source_bucket`: verifies `from_()` called with `config.SUPABASE_SOURCE_BUCKET` and correct path

#### `tests/test_airtable_client.py` (3 tests)

- `test_update_video_attachment_patch_format`: verifies `{"fields": {"Rendered Video": [{"url": "..."}]}}` body
- `test_update_video_attachment_url`: verifies PATCH URL is `{BASE_URL}/{TABLE_CONTENT_QUEUE}/{record_id}`
- `test_update_video_attachment_returns_response`: verifies parsed JSON returned

### Task 2: Wire upload and attachment into the render pipeline

Updated `main.py` to complete the full pipeline and added pipeline integration tests.

#### `main.py` changes

- Added `import supabase_client` and `import os`
- Updated `lifespan()` to health-check the Remotion service on startup (warns if unreachable)
- Updated `_run_render()` — after `download_file()`:
  1. Sets status to `"uploading"`
  2. Calls `supabase_client.upload_video(tmp_path, f"{record_id}/{job_id}.mp4")`
  3. Calls `at.update_content_queue_video_attachment(record_id, video_url)`
  4. Cleans up `tmp_path` with `os.remove()` in try/except
  5. Sets status to `"completed"` with `video_url` = Supabase public URL (not local path)

#### `tests/test_render_routes.py` (3 new tests in `TestFullPipeline`)

- `test_full_pipeline_uploads_and_attaches`: verifies `upload_video` called with `(tmp_path, "recABC123/{job_id}.mp4")` and `update_content_queue_video_attachment` called with `(record_id, supabase_url)`, and final job state has Supabase URL
- `test_pipeline_cleans_up_temp_file`: verifies `os.remove()` called on `tmp_path`
- `test_pipeline_status_transitions`: verifies job starts `accepted` and ends `completed` with Supabase URL

## Verification Results

```
59 passed in 1.08s
```

All plan success criteria met:
- `supabase_client.upload_video()` implemented — uploads to Supabase Storage, returns public URL
- `supabase_client.get_source_video_url()` constructs public URL from source bucket
- `airtable_client.update_content_queue_video_attachment()` PATCHes with `[{"url": "..."}]` format
- `main.py _run_render()` pipeline: render -> download -> upload -> attach -> cleanup
- Job `video_url` holds Supabase public URL on completion (not local tmp path)
- Temp rendered file cleaned up after upload
- `supabase==2.28.0` in `requirements.txt`
- Remotion service health checked on startup
- All 59 tests passing (11 new + 48 existing)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 4b5f5e7 | test | Add failing tests for supabase upload and airtable attachment (RED) |
| 7fdc3a0 | feat | Implement supabase_client.upload_video() and airtable attachment PATCH (GREEN) |
| b199763 | feat | Wire supabase upload and airtable attachment into render pipeline |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mock patch target for supabase.create_client in tests**
- **Found during:** Task 1 GREEN phase — first test run after writing RED tests showed incorrect patch path
- **Issue:** Tests patched `supabase.create_client` but `supabase_client.py` imports `create_client` directly with `from supabase import create_client`. The patch was hitting the supabase module instead of the local binding, so `_get_client()` used the real Supabase client (which failed with no URL configured)
- **Fix:** Changed all test patches from `supabase.create_client` to `supabase_client.create_client`
- **Files modified:** tests/test_supabase_client.py
- **Commit:** 7fdc3a0

**2. [Rule 1 - Bug] Updated pre-existing render route tests to mock new pipeline steps**
- **Found during:** Task 2 implementation — `test_background_task_transitions_to_completed` and 3 other existing tests failed because they didn't mock `supabase_client.upload_video` and `at.update_content_queue_video_attachment`, which are now called in `_run_render()`
- **Issue:** Pre-existing tests from Plan 02-02 assumed the pipeline ended at `download_file()` — the new upload step tried to create a real Supabase client with empty URL and raised `SupabaseException: supabase_url is required`
- **Fix:** Added `patch("main.supabase_client.upload_video")`, `patch("main.at.update_content_queue_video_attachment")`, and `patch("main.os.remove")` to the 4 affected tests
- **Files modified:** tests/test_render_routes.py
- **Commit:** b199763

## Self-Check: PASSED

Files exist:
- [x] supabase_client.py (replaced stub with working implementation)
- [x] airtable_client.py (update_content_queue_video_attachment added)
- [x] main.py (upload/attach pipeline wired in _run_render, Remotion health check in lifespan)
- [x] requirements.txt (supabase==2.28.0 added)
- [x] tests/test_supabase_client.py (created, 5 tests)
- [x] tests/test_airtable_client.py (created, 3 tests)
- [x] tests/test_render_routes.py (updated, 3 new TestFullPipeline tests)

Commits verified:
- [x] 4b5f5e7 (test RED)
- [x] 7fdc3a0 (feat GREEN Task 1)
- [x] b199763 (feat Task 2)
