---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: [INTG-03]

must_haves:
  truths:
    - "After a render completes and the MP4 is uploaded to Supabase Storage, the video URL is saved as an Airtable attachment on the content queue record"
    - "The Airtable attachment uses the record_id from the render request to identify the correct record"
    - "The attachment format uses Airtable's URL-based attachment API ({url: publicUrl})"
  artifacts:
    - path: "airtable_client.py"
      provides: "update_content_queue_video_attachment(record_id, video_url) function"
      contains: "update_content_queue_video_attachment"
    - path: "main.py"
      provides: "Call to update_content_queue_video_attachment in _run_render pipeline"
      contains: "update_content_queue_video_attachment"
    - path: "tests/test_airtable_client.py"
      provides: "Unit tests for Airtable attachment PATCH format and URL"
      contains: "TestUpdateContentQueueVideoAttachment"
    - path: "tests/test_render_routes.py"
      provides: "Integration test for full pipeline upload + attach"
      contains: "test_full_pipeline_uploads_and_attaches"
  key_links:
    - from: "main.py::_run_render"
      to: "airtable_client.py::update_content_queue_video_attachment"
      via: "await at.update_content_queue_video_attachment(request.record_id, video_url)"
      pattern: "at\\.update_content_queue_video_attachment"
    - from: "airtable_client.py::update_content_queue_video_attachment"
      to: "Airtable REST API"
      via: "httpx PATCH to /Content Queue/{record_id} with Rendered Video attachment"
      pattern: "client\\.patch.*Rendered Video"
---

<objective>
Verify that INTG-03 (save rendered video URL as Airtable attachment) is fully implemented and tested.

Purpose: INTG-03 requires that after a render completes and the MP4 is uploaded to Supabase Storage, the video URL is saved as an Airtable attachment on the content queue record using the record_id from the render request. This functionality already exists in the codebase -- this plan verifies completeness.

Output: Confirmation that all code paths and tests are in place, no new files needed.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@airtable_client.py
@main.py
@tests/test_airtable_client.py
@tests/test_render_routes.py

<interfaces>
<!-- Key functions the executor needs to verify -->

From airtable_client.py (lines 261-282):
```python
async def update_content_queue_video_attachment(record_id: str, video_url: str) -> dict[str, Any]:
    """Add rendered video URL as attachment on a Content Queue record.
    Airtable fetches the file from the URL and stores its own copy.
    The URL must be publicly accessible (no auth required).
    """
    # PATCH /Content Queue/{record_id} with {"fields": {"Rendered Video": [{"url": video_url}]}}
```

From main.py _run_render() (lines 355-356):
```python
# Save as Airtable attachment
await at.update_content_queue_video_attachment(request.record_id, video_url)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify INTG-03 implementation completeness</name>
  <files>airtable_client.py, main.py, tests/test_airtable_client.py, tests/test_render_routes.py</files>
  <action>
INTG-03 is already implemented. Verify completeness by running the full test suite to confirm all code paths work:

1. Run `tests/test_airtable_client.py` -- 3 tests covering:
   - PATCH body format: `{"fields": {"Rendered Video": [{"url": video_url}]}}` (test_update_video_attachment_patch_format)
   - Correct Airtable API URL with TABLE_CONTENT_QUEUE and record_id (test_update_video_attachment_url)
   - Return value is parsed JSON from Airtable (test_update_video_attachment_returns_response)

2. Run `tests/test_render_routes.py::TestFullPipeline` -- 3 tests covering:
   - Full pipeline calls upload_video then update_content_queue_video_attachment with correct args (test_full_pipeline_uploads_and_attaches)
   - Temp file cleanup after upload (test_pipeline_cleans_up_temp_file)
   - Status transitions end at "completed" with Supabase URL (test_pipeline_status_transitions)

3. Verify the wiring in main.py _run_render():
   - Line 352-353: uploads to Supabase and gets video_url
   - Line 356: calls at.update_content_queue_video_attachment(request.record_id, video_url)
   - This is AFTER Supabase upload and BEFORE marking job completed

No code changes needed. This is a verification-only task.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/test_airtable_client.py tests/test_render_routes.py -v</automated>
  </verify>
  <done>All 23 tests pass. INTG-03 pipeline is confirmed: _run_render() uploads to Supabase, saves URL as Airtable attachment using record_id, then marks job completed. The Airtable PATCH uses the correct attachment format [{"url": publicUrl}] against the Content Queue table.</done>
</task>

</tasks>

<verification>
- All tests in test_airtable_client.py pass (3 tests)
- All tests in test_render_routes.py pass (20 tests)
- airtable_client.py contains update_content_queue_video_attachment function
- main.py _run_render() calls at.update_content_queue_video_attachment(request.record_id, video_url) after Supabase upload
</verification>

<success_criteria>
- 23/23 tests pass confirming INTG-03 is fully implemented
- No code changes required -- feature was already built in Phase 2 milestone
</success_criteria>

<output>
After completion, create `.planning/quick/1-implement-intg-03-save-rendered-video-ur/1-SUMMARY.md`
</output>
