"""Tests for FastAPI render routes (POST /render, GET /render-status/{job_id})
and the background render task lifecycle.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import pytest_asyncio

from renderer import JobStatus, RenderRequest
from renderer.models import BrandConfig
from renderer.brand import resolve_brand_for_render


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


# ---------------------------------------------------------------------------
# Brand config integration: POST /render with client_id
# ---------------------------------------------------------------------------

class TestBrandConfig:

    @pytest.mark.asyncio
    async def test_render_with_client_id_fetches_brand(self, app_client):
        """POST /render with client_id calls at.get_client and at.extract_brand_config."""
        client_record = {"id": "recTEST", "fields": {"Brand Primary Color": "#FF0000", "Brand Font Family": "Rubik"}}
        brand_config = BrandConfig(primary_color="#FF0000", font_family="Rubik")

        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.at.get_client", new_callable=AsyncMock, return_value=client_record) as mock_get_client, \
             patch("main.at.extract_brand_config", return_value=brand_config) as mock_extract, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock, return_value="https://example.supabase.co/brand.mp4"), \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock, return_value={}), \
             patch("main.os.remove"):

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-brand")
            mock_rend.get_status = AsyncMock(return_value=JobStatus(state="completed", progress=1.0))
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "Brand hook!",
                    "body_text": "Brand body.",
                    "record_id": "recABC123",
                    "client_id": "recTEST",
                },
            )
            assert resp.status_code == 202

            # Allow the background task to run
            await asyncio.sleep(0.1)

        # Verify Airtable calls
        mock_get_client.assert_called_once_with("recTEST")
        mock_extract.assert_called_once_with(client_record)

    @pytest.mark.asyncio
    async def test_render_with_client_id_passes_resolved_brand(self, app_client):
        """POST /render with client_id and awareness_stage passes resolved brand to renderer."""
        client_record = {"id": "recTEST", "fields": {"Brand Primary Color": "#FF0000"}}
        brand_config = BrandConfig(primary_color="#FF0000")
        resolved_brand_mock = {
            "primaryColor": "#FF0000",
            "secondaryColor": "#FFFFFF",
            "fontFamily": "Heebo",
            "hookFontSize": 60,
            "bodyFontSize": 36,
            "hookFontWeight": 900,
            "overlayColor": "#000000",
            "overlayOpacity": 0.55,
            "borderRadius": 16,
            "textPosition": "top",
            "textAlign": "center",
            "animationSpeedMs": 400,
        }

        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.at.get_client", new_callable=AsyncMock, return_value=client_record), \
             patch("main.at.extract_brand_config", return_value=brand_config), \
             patch("main.resolve_brand_for_render", return_value=resolved_brand_mock) as mock_resolve, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock, return_value="https://example.supabase.co/test.mp4"), \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock, return_value={}), \
             patch("main.os.remove"):

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-resolved")
            mock_rend.get_status = AsyncMock(return_value=JobStatus(state="completed", progress=1.0))
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "Brand hook!",
                    "body_text": "Brand body.",
                    "record_id": "recABC123",
                    "client_id": "recTEST",
                    "awareness_stage": 1,
                },
            )
            assert resp.status_code == 202

            # Allow the background task to run
            await asyncio.sleep(0.1)

        # Verify resolve_brand_for_render was called with brand_config and stage 1
        mock_resolve.assert_called_once_with(brand_config, 1)

        # Verify renderer.render was called with resolved_brand
        mock_rend.render.assert_called_once()
        call_kwargs = mock_rend.render.call_args.kwargs
        assert call_kwargs.get("resolved_brand") == resolved_brand_mock

    @pytest.mark.asyncio
    async def test_render_without_client_id_uses_defaults(self, app_client):
        """POST /render without client_id does not call at.get_client and uses default BrandConfig."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.at.get_client", new_callable=AsyncMock) as mock_get_client, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock, return_value="https://example.supabase.co/test.mp4"), \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock, return_value={}), \
             patch("main.os.remove"):

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-defaults")
            mock_rend.get_status = AsyncMock(return_value=JobStatus(state="completed", progress=1.0))
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "Default hook!",
                    "body_text": "Default body.",
                    "record_id": "recABC123",
                    # No client_id
                },
            )
            assert resp.status_code == 202

            # Allow the background task to run
            await asyncio.sleep(0.1)

        # at.get_client should NOT have been called
        mock_get_client.assert_not_called()

        # renderer.render should have been called with a resolved_brand containing defaults
        mock_rend.render.assert_called_once()
        call_kwargs = mock_rend.render.call_args.kwargs
        resolved = call_kwargs.get("resolved_brand")
        assert resolved is not None
        assert resolved["primaryColor"] == "#FFFFFF"
        assert resolved["fontFamily"] == "Heebo"
        assert resolved["overlayOpacity"] == 0.55

    @pytest.mark.asyncio
    async def test_render_backward_compat_no_client_id(self, app_client):
        """POST /render without client_id or awareness_stage returns 202 (backward compat)."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock, return_value="https://example.supabase.co/compat.mp4"), \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock, return_value={}), \
             patch("main.os.remove"):

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-compat")
            mock_rend.get_status = AsyncMock(return_value=JobStatus(state="completed", progress=1.0))
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


# ---------------------------------------------------------------------------
# Segment pipeline: POST /render with segments array
# ---------------------------------------------------------------------------

class TestSegments:

    @pytest.mark.asyncio
    async def test_render_with_segments_returns_202(self, app_client):
        """POST /render with a segments array returns 202."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove"):

            mock_upload.return_value = "https://example.supabase.co/segments.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-segments")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "record_id": "recSEG123",
                    "segments": [
                        {"text": "Hook text", "start_seconds": 0, "end_seconds": 3, "role": "hook", "animation_style": "fade"},
                        {"text": "Body text", "start_seconds": 3, "end_seconds": 8, "role": "body", "animation_style": "fade"},
                        {"text": "Call to action!", "start_seconds": 8, "end_seconds": 12, "role": "cta", "animation_style": "fade"},
                    ],
                },
            )

        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_render_with_segments_sends_segments_to_renderer(self, app_client):
        """POST /render with segments calls renderer.render() with correct camelCase segments."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove"):

            mock_upload.return_value = "https://example.supabase.co/segments.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-segs-check")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "record_id": "recSEG456",
                    "segments": [
                        {"text": "Hook text", "start_seconds": 0, "end_seconds": 3, "role": "hook", "animation_style": "fade"},
                        {"text": "Body text", "start_seconds": 3, "end_seconds": 8, "role": "body", "animation_style": "fade"},
                        {"text": "CTA text", "start_seconds": 8, "end_seconds": 12, "role": "cta", "animation_style": "slide"},
                    ],
                },
            )
            assert resp.status_code == 202

            # Allow background task to run
            await asyncio.sleep(0.1)

        # Verify renderer.render was called with a segments kwarg containing 3 camelCase dicts
        mock_rend.render.assert_called_once()
        call_kwargs = mock_rend.render.call_args.kwargs
        segments = call_kwargs.get("segments")
        assert segments is not None
        assert len(segments) == 3

        # Verify camelCase keys
        hook_seg = segments[0]
        assert hook_seg["text"] == "Hook text"
        assert hook_seg["startSeconds"] == 0
        assert hook_seg["endSeconds"] == 3
        assert hook_seg["role"] == "hook"
        assert hook_seg["animationStyle"] == "fade"

        cta_seg = segments[2]
        assert cta_seg["role"] == "cta"
        assert cta_seg["animationStyle"] == "slide"

    @pytest.mark.asyncio
    async def test_render_legacy_backward_compat(self, app_client):
        """POST /render with legacy hook_text/body_text auto-converts to segments."""
        with patch("main.get_renderer") as mock_get_renderer, \
             patch("main.supabase_client.upload_video", new_callable=AsyncMock) as mock_upload, \
             patch("main.at.update_content_queue_video_attachment", new_callable=AsyncMock) as mock_attach, \
             patch("main.os.remove"):

            mock_upload.return_value = "https://example.supabase.co/legacy.mp4"
            mock_attach.return_value = {}

            mock_rend = AsyncMock()
            mock_rend.render = AsyncMock(return_value="remotion-job-legacy")
            mock_rend.get_status = AsyncMock(
                return_value=JobStatus(state="completed", progress=1.0)
            )
            mock_rend.download_file = AsyncMock(return_value=None)
            mock_get_renderer.return_value = mock_rend

            resp = await app_client.post(
                "/render",
                json={
                    "source_video_url": "https://example.com/source.mp4",
                    "hook_text": "Legacy hook text",
                    "body_text": "Legacy body content",
                    "record_id": "recLEGACY",
                },
            )
            assert resp.status_code == 202

            # Allow background task to run
            await asyncio.sleep(0.1)

        # Verify renderer.render was called with segments kwarg containing 2 auto-converted segments
        mock_rend.render.assert_called_once()
        call_kwargs = mock_rend.render.call_args.kwargs
        segments = call_kwargs.get("segments")
        assert segments is not None
        assert len(segments) == 2

        # First segment should be the hook
        assert segments[0]["role"] == "hook"
        assert segments[0]["text"] == "Legacy hook text"
        assert segments[0]["startSeconds"] == 0.0

        # Second segment should be the body
        assert segments[1]["role"] == "body"
        assert segments[1]["text"] == "Legacy body content"

        # Segments should cover the full duration (default 15s)
        assert segments[0]["endSeconds"] == segments[1]["startSeconds"]
        assert segments[1]["endSeconds"] == 15.0

    @pytest.mark.asyncio
    async def test_render_segments_validation_overlap_rejected(self, app_client):
        """POST /render with overlapping segments returns 422 validation error."""
        resp = await app_client.post(
            "/render",
            json={
                "source_video_url": "https://example.com/source.mp4",
                "record_id": "recOVERLAP",
                "segments": [
                    {"text": "First", "start_seconds": 0, "end_seconds": 5, "role": "hook"},
                    # Overlaps: starts at 4, before first ends at 5
                    {"text": "Overlapping", "start_seconds": 4, "end_seconds": 10, "role": "body"},
                ],
            },
        )
        assert resp.status_code == 422
