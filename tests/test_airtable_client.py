"""Tests for airtable_client — update_content_queue_video_attachment()."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

import config


class TestUpdateContentQueueVideoAttachment:

    @pytest.mark.asyncio
    async def test_update_video_attachment_patch_format(self):
        """update_content_queue_video_attachment() sends PATCH with correct Airtable attachment format."""
        record_id = "recABC123"
        video_url = "https://example.supabase.co/storage/v1/object/public/rendered-videos/recABC123/job001.mp4"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"id": record_id, "fields": {}})

        mock_http_client = AsyncMock()
        mock_http_client.patch = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            import airtable_client
            await airtable_client.update_content_queue_video_attachment(record_id, video_url)

        mock_http_client.patch.assert_called_once()
        call_kwargs = mock_http_client.patch.call_args
        json_body = call_kwargs.kwargs.get("json") or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
        assert json_body is not None, "PATCH request must include json body"
        assert "fields" in json_body
        assert "Final Video" in json_body["fields"]
        attachment_value = json_body["fields"]["Final Video"]
        assert isinstance(attachment_value, list), "Final Video must be a list"
        assert len(attachment_value) == 1
        assert attachment_value[0] == {"url": video_url}

    @pytest.mark.asyncio
    async def test_update_video_attachment_url(self):
        """update_content_queue_video_attachment() calls correct Airtable URL with TABLE_CONTENT_QUEUE and record_id."""
        record_id = "recXYZ789"
        video_url = "https://example.supabase.co/test.mp4"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"id": record_id})

        mock_http_client = AsyncMock()
        mock_http_client.patch = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            import airtable_client
            await airtable_client.update_content_queue_video_attachment(record_id, video_url)

        call_kwargs = mock_http_client.patch.call_args
        url = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("url")
        assert url is not None
        expected_url = f"https://api.airtable.com/v0/{config.AIRTABLE_BASE_ID}/{config.TABLE_CONTENT_QUEUE}/{record_id}"
        assert url == expected_url

    @pytest.mark.asyncio
    async def test_update_video_attachment_returns_response(self):
        """update_content_queue_video_attachment() returns the parsed JSON from Airtable."""
        record_id = "recRET001"
        video_url = "https://example.supabase.co/ret.mp4"
        expected_response = {"id": record_id, "fields": {"Rendered Video": [{"url": video_url}]}}

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=expected_response)

        mock_http_client = AsyncMock()
        mock_http_client.patch = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            import airtable_client
            result = await airtable_client.update_content_queue_video_attachment(record_id, video_url)

        assert result == expected_response
