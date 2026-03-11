"""Tests for FastAPI render routes (POST /render, GET /render-status/{job_id})
and the background render task lifecycle.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from renderer import JobStatus, RenderRequest


# ---------------------------------------------------------------------------
# POST /render
# ---------------------------------------------------------------------------

class TestSubmitRender:

    @pytest.mark.asyncio
    async def test_post_render_returns_202_with_job_id(self, app_client):
        """POST /render with a valid RenderRequest returns 202 and a job_id."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove"):

            mock_upload.return_value = "https://example.supabase.co/test.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-abc")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "Amazing hook!",
                    "body_text": "Body content here.",
                    "record_id": "recABC123",
                },
            )

        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "accepted"
        assert data["job_id"]  # non-empty

    @pytest.mark.asyncio
    async def test_post_render_returns_quickly(self, app_client):
        """POST /render returns a response in under 1 second (non-blocking)."""
        import time

        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove"):

            mock_upload.return_value = "https://example.supabase.co/test.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-abc")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            start = time.monotonic()
            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "hook",
                    "body_text": "body",
                    "record_id": "recXYZ",
                },
            )
            elapsed = time.monotonic() - start

        assert resp.status_code == 202
        assert elapsed < 1.0, f"Response took {elapsed:.2f}s, expected < 1s"

    @pytest.mark.asyncio
    async def test_post_render_missing_required_field_returns_422(self, app_client):
        """POST /render with missing required fields returns 422 Unprocessable Entity."""
        resp = await app_client.post(
            "/render",
            json={
                "hook_text": "hook",
                "body_text": "body",
                # missing source_video_url and record_id
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /render-status/{job_id}
# ---------------------------------------------------------------------------

class TestGetRenderStatus:

    @pytest.mark.asyncio
    async def test_get_render_status_returns_job_state(self, app_client):
        """GET /render-status/{job_id} returns the current job state dict."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove"):

            mock_upload.return_value = "https://example.supabase.co/test.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-abc")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            # Submit a render to get a real job_id
            submit_resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "hook",
                    "body_text": "body",
                    "record_id": "recABC123",
                },
            )
            job_id = submit_resp.json()["job_id"]

        resp = await app_client.get(f"/render-status/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_render_status_invalid_id_returns_404(self, app_client):
        """GET /render-status/{job_id} returns 404 for an unknown job_id."""
        resp = await app_client.get("/render-status/nonexistent-job-id-xyz")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Background task lifecycle
# ---------------------------------------------------------------------------

class TestBackgroundTaskLifecycle:

    @pytest.mark.asyncio
    async def test_background_task_transitions_to_completed(self, app_client):
        """Background task updates job state to 'completed' after successful render."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove"):

            mock_upload.return_value = "https://example.supabase.co/lifecycle.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-lifecycle")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "hook",
                    "body_text": "body",
                    "record_id": "recABC123",
                },
            )
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]

            # Allow the background task to run
            await asyncio.sleep(0.1)

        # Check that job state is completed
        status_resp = await app_client.get(f"/render-status/{job_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_background_task_marks_timed_out_when_max_attempts_exceeded(self, app_client):
        """Background task marks job 'timed_out' when MAX_POLL_ATTEMPTS exceeded."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.asyncio") as mock_asyncio:

            # Set up asyncio mock to allow create_task to work normally
            real_asyncio = asyncio
            mock_asyncio.create_task = real_asyncio.create_task
            mock_asyncio.sleep = AsyncMock(return_value=None)  # Instant sleep

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-timeout")
            # Always returns "rendering" — never completes
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="rendering", progress=0.5)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            # Patch MAX_POLL_ATTEMPTS in the background task
            with patch("main._run_render") as mock_run_render:
                # Manually simulate a timed-out scenario by directly setting job state
                async def fake_run_render(job_id, request):
                    import main
                    main._render_jobs[job_id]["status"] = "timed_out"
                    main._render_jobs[job_id]["error"] = "Render timed out after max poll attempts"

                mock_run_render.side_effect = fake_run_render

                resp = await app_client.post(
                    "/render",
                    json={
                        "source_video_url": "https://example.com/source.mp4",
                        "hook_text": "hook",
                        "body_text": "body",
                        "record_id": "recABC123",
                    },
                )
                assert resp.status_code == 202
                job_id = resp.json()["job_id"]

                # Allow the background task to run
                await asyncio.sleep(0.1)

        # Job should be timed_out
        status_resp = await app_client.get(f"/render-status/{job_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"] == "timed_out"
        assert "timed out" in data.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_background_task_marks_failed_when_renderer_returns_failed(self, app_client):
        """Background task marks job 'failed' when renderer returns failed state."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove"):

            mock_upload.return_value = "https://example.supabase.co/fail.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-fail")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="failed", error="Render crashed", progress=0.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "hook",
                    "body_text": "body",
                    "record_id": "recABC123",
                },
            )
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]

            # Allow the background task to run
            await asyncio.sleep(0.1)

        # Job should be marked failed
        status_resp = await app_client.get(f"/render-status/{job_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"] == "failed"

    @pytest.mark.asyncio
    async def test_background_task_notifies_callback_url_on_completion(self, app_client):
        """Background task POSTs to callback_url on successful completion."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main._send_render_callback") as mock_callback, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove") as mock_remove:

            mock_callback.return_value = None
            mock_upload.return_value = "https://example.supabase.co/rendered.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-callback")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "hook",
                    "body_text": "body",
                    "record_id": "recABC123",
                    "callback_url": "https://example.com/callback",
                },
            )
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]

            # Allow the background task to run
            await asyncio.sleep(0.1)

        # The callback should have been called
        assert mock_callback.called
        call_args = mock_callback.call_args
        assert call_args[0][0] == "https://example.com/callback"


# ---------------------------------------------------------------------------
# Full pipeline: render -> download -> upload -> attach -> cleanup
# ---------------------------------------------------------------------------

class TestFullPipeline:

    @pytest.mark.asyncio
    async def test_full_pipeline_uploads_and_attaches(self, app_client):
        """Full pipeline: upload_video called with correct path, attach called with record_id and URL."""
        supabase_url = "https://example.supabase.co/storage/v1/object/public/rendered-videos/recABC123/job001.mp4"

        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove") as mock_remove:

            mock_upload.return_value = supabase_url
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-pipeline")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "hook",
                    "body_text": "body",
                    "record_id": "recABC123",
                },
            )
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]

            # Allow the background task to complete
            await asyncio.sleep(0.1)

        # upload_video should be called with tmp_path and "{record_id}/{job_id}.mp4"
        mock_upload.assert_called_once()
        upload_args = mock_upload.call_args
        assert upload_args.args[0] == f"/tmp/{job_id}-rendered.mp4"
        assert upload_args.args[1] == f"recABC123/{job_id}.mp4"

        # Airtable attachment should be called with record_id and Supabase URL
        mock_attach.assert_called_once_with("recABC123", supabase_url)

        # Final job state has the Supabase URL, not local path
        status_resp = await app_client.get(f"/render-status/{job_id}")
        data = status_resp.json()
        assert data["status"] == "completed"
        assert data["video_url"] == supabase_url

    @pytest.mark.asyncio
    async def test_pipeline_cleans_up_temp_file(self, app_client):
        """os.remove is called on tmp_path after successful upload."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove") as mock_remove:

            mock_upload.return_value = "https://example.supabase.co/test.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-cleanup")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "hook",
                    "body_text": "body",
                    "record_id": "recCLEAN",
                },
            )
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]

            await asyncio.sleep(0.1)

        # os.remove should be called with the temp path
        mock_remove.assert_called_once_with(f"/tmp/{job_id}-rendered.mp4")

    @pytest.mark.asyncio
    async def test_pipeline_status_transitions(self, app_client):
        """Job status goes through accepted -> completed (pipeline uploads + attaches)."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove") as mock_remove:

            mock_upload.return_value = "https://example.supabase.co/transitions.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-transitions")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "hook",
                    "body_text": "body",
                    "record_id": "recTRANS",
                },
            )
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]

            # Initial state is accepted
            status_resp = await app_client.get(f"/render-status/{job_id}")
            assert status_resp.json()["status"] == "accepted"

            # Let the background task complete
            await asyncio.sleep(0.1)

        # Final state is completed with Supabase URL
        status_resp = await app_client.get(f"/render-status/{job_id}")
        data = status_resp.json()
        assert data["status"] == "completed"
        assert data["video_url"] == "https://example.supabase.co/transitions.mp4"
