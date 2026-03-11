"""Tests for RemotionRenderer HTTP client behavior.

These tests verify that RemotionRenderer sends correctly-shaped payloads
to the Remotion service and maps state values correctly. All outgoing HTTP
is mocked via unittest.mock so no real Remotion service is needed.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from renderer import JobStatus, RenderRequest
from renderer.remotion import RemotionRenderer


# ---------------------------------------------------------------------------
# render() — payload construction
# ---------------------------------------------------------------------------

class TestRemotionRendererRender:

    @pytest.mark.asyncio
    async def test_render_passes_source_video_url_as_sourceVideoUrl(self, sample_render_request):
        """RemotionRenderer.render() sends source_video_url as sourceVideoUrl in POST payload."""
        renderer = RemotionRenderer("http://remotion:3000")

        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"jobId": "remotion-job-abc"})

        captured_payload = {}

        async def mock_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = mock_post

        with patch("httpx.AsyncClient", return_value=mock_client):
            job_id = await renderer.render(sample_render_request)

        assert job_id == "remotion-job-abc"
        assert "sourceVideoUrl" in captured_payload
        assert captured_payload["sourceVideoUrl"] == sample_render_request.source_video_url

    @pytest.mark.asyncio
    async def test_render_passes_all_required_keys(self, sample_render_request):
        """RemotionRenderer.render() sends all required payload keys to Remotion service."""
        renderer = RemotionRenderer("http://remotion:3000")

        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"jobId": "remotion-job-abc"})

        captured_payload = {}

        async def mock_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = mock_post

        with patch("httpx.AsyncClient", return_value=mock_client):
            await renderer.render(sample_render_request)

        required_keys = {
            "sourceVideoUrl",
            "hookText",
            "bodyText",
            "textDirection",
            "animationStyle",
            "durationInSeconds",
        }
        for key in required_keys:
            assert key in captured_payload, f"Missing payload key: {key}"

    @pytest.mark.asyncio
    async def test_render_does_not_include_callback_url_when_none(self, sample_render_request):
        """RemotionRenderer.render() omits callbackUrl when callback_url is None."""
        renderer = RemotionRenderer("http://remotion:3000")
        assert sample_render_request.callback_url is None  # pre-condition

        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"jobId": "remotion-job-abc"})

        captured_payload = {}

        async def mock_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = mock_post

        with patch("httpx.AsyncClient", return_value=mock_client):
            await renderer.render(sample_render_request)

        assert "callbackUrl" not in captured_payload

    @pytest.mark.asyncio
    async def test_render_includes_callback_url_when_provided(self):
        """RemotionRenderer.render() includes callbackUrl when callback_url is provided."""
        renderer = RemotionRenderer("http://remotion:3000")
        request = RenderRequest(
            source_video_url="https://example.com/source.mp4",
            hook_text="hook",
            body_text="body",
            record_id="rec123",
            callback_url="https://example.com/callback",
        )

        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"jobId": "remotion-job-abc"})

        captured_payload = {}

        async def mock_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = mock_post

        with patch("httpx.AsyncClient", return_value=mock_client):
            await renderer.render(request)

        assert "callbackUrl" in captured_payload
        assert captured_payload["callbackUrl"] == "https://example.com/callback"


# ---------------------------------------------------------------------------
# get_status() — state mapping
# ---------------------------------------------------------------------------

class TestRemotionRendererGetStatus:

    @pytest.mark.asyncio
    async def test_get_status_maps_queued_to_accepted(self):
        """RemotionRenderer.get_status() maps Remotion 'queued' state to 'accepted'."""
        renderer = RemotionRenderer("http://remotion:3000")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"state": "queued", "progress": 0.0})

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            status = await renderer.get_status("job-abc")

        assert status.state == "accepted"

    @pytest.mark.asyncio
    async def test_get_status_maps_in_progress_to_rendering(self):
        """RemotionRenderer.get_status() maps Remotion 'in-progress' state to 'rendering'."""
        renderer = RemotionRenderer("http://remotion:3000")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"state": "in-progress", "progress": 0.5})

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            status = await renderer.get_status("job-abc")

        assert status.state == "rendering"
        assert status.progress == 0.5

    @pytest.mark.asyncio
    async def test_get_status_maps_completed_to_completed(self):
        """RemotionRenderer.get_status() maps Remotion 'completed' state to 'completed'."""
        renderer = RemotionRenderer("http://remotion:3000")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={"state": "completed", "progress": 1.0, "videoUrl": "/tmp/renders/job-abc.mp4"}
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            status = await renderer.get_status("job-abc")

        assert status.state == "completed"
        assert status.progress == 1.0
        assert status.video_url == "/tmp/renders/job-abc.mp4"

    @pytest.mark.asyncio
    async def test_get_status_maps_failed_to_failed(self):
        """RemotionRenderer.get_status() maps Remotion 'failed' state to 'failed'."""
        renderer = RemotionRenderer("http://remotion:3000")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={"state": "failed", "progress": 0.0, "error": "OOM error"}
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            status = await renderer.get_status("job-abc")

        assert status.state == "failed"
        assert status.error == "OOM error"
