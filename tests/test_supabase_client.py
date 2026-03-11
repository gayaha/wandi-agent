"""Tests for supabase_client — upload_video() and get_source_video_url()."""

from unittest.mock import MagicMock, patch, mock_open
import pytest

import config


class TestUploadVideo:

    @pytest.mark.asyncio
    async def test_upload_video_calls_storage_upload(self):
        """upload_video() calls storage.from_(bucket).upload() with correct path and file content."""
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload = MagicMock(return_value={"Key": "rendered-videos/rec123/job456.mp4"})
        mock_storage_bucket.get_public_url = MagicMock(return_value="https://example.supabase.co/storage/v1/object/public/rendered-videos/rec123/job456.mp4")

        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_storage_bucket)

        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.create_client", return_value=mock_client), \
             patch("builtins.open", mock_open(read_data=b"fake video content")):
            import supabase_client
            await supabase_client.upload_video("/tmp/job456-rendered.mp4", "rec123/job456.mp4")

        mock_storage.from_.assert_called_with(config.SUPABASE_BUCKET)
        mock_storage_bucket.upload.assert_called_once()
        call_kwargs = mock_storage_bucket.upload.call_args
        assert call_kwargs.kwargs.get("path") == "rec123/job456.mp4" or \
               (call_kwargs.args and call_kwargs.args[0] == "rec123/job456.mp4")

    @pytest.mark.asyncio
    async def test_upload_video_passes_file_options(self):
        """upload_video() passes content-type 'video/mp4' and upsert 'true' in file_options."""
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload = MagicMock(return_value={})
        mock_storage_bucket.get_public_url = MagicMock(return_value="https://example.supabase.co/storage/v1/object/public/rendered-videos/dest.mp4")

        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_storage_bucket)

        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.create_client", return_value=mock_client), \
             patch("builtins.open", mock_open(read_data=b"fake")):
            import supabase_client
            await supabase_client.upload_video("/tmp/test.mp4", "dest.mp4")

        call_kwargs = mock_storage_bucket.upload.call_args
        assert call_kwargs is not None, "upload() should have been called"
        file_options = call_kwargs.kwargs.get("file_options")
        if file_options is None and len(call_kwargs.args) >= 3:
            file_options = call_kwargs.args[2]
        assert file_options is not None
        assert file_options.get("content-type") == "video/mp4"
        assert file_options.get("upsert") == "true"

    @pytest.mark.asyncio
    async def test_upload_video_returns_public_url(self):
        """upload_video() returns the public URL from get_public_url()."""
        expected_url = "https://example.supabase.co/storage/v1/object/public/rendered-videos/rec123/job456.mp4"

        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload = MagicMock(return_value={})
        mock_storage_bucket.get_public_url = MagicMock(return_value=expected_url)

        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_storage_bucket)

        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.create_client", return_value=mock_client), \
             patch("builtins.open", mock_open(read_data=b"fake")):
            import supabase_client
            result = await supabase_client.upload_video("/tmp/job456-rendered.mp4", "rec123/job456.mp4")

        assert result == expected_url

    @pytest.mark.asyncio
    async def test_upload_video_uses_rendered_bucket(self):
        """upload_video() calls storage.from_() with config.SUPABASE_BUCKET (rendered-videos bucket)."""
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.upload = MagicMock(return_value={})
        mock_storage_bucket.get_public_url = MagicMock(return_value="https://example.supabase.co/test.mp4")

        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_storage_bucket)

        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.create_client", return_value=mock_client), \
             patch("builtins.open", mock_open(read_data=b"fake")):
            import supabase_client
            await supabase_client.upload_video("/tmp/test.mp4", "dest/test.mp4")

        # storage.from_ called with the rendered-videos bucket
        from_calls = mock_storage.from_.call_args_list
        assert any(call.args[0] == config.SUPABASE_BUCKET for call in from_calls)


class TestGetSourceVideoUrl:

    def test_get_source_video_url_uses_source_bucket(self):
        """get_source_video_url() calls get_public_url() on SOURCE_BUCKET with correct path."""
        expected_url = "https://example.supabase.co/storage/v1/object/public/source-videos/client123/video.mp4"

        mock_storage_bucket = MagicMock()
        mock_storage_bucket.get_public_url = MagicMock(return_value=expected_url)

        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_storage_bucket)

        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.create_client", return_value=mock_client):
            import supabase_client
            result = supabase_client.get_source_video_url("client123/video.mp4")

        assert result == expected_url
        mock_storage.from_.assert_called_with(config.SUPABASE_SOURCE_BUCKET)
        mock_storage_bucket.get_public_url.assert_called_with("client123/video.mp4")
