"""Tests for video_picker — folder-aware video selection with diversity."""

from unittest.mock import patch, MagicMock
import pytest


class TestPickVideosForReels:

    def test_assigns_videos_from_matching_folders(self):
        """Each reel gets a video from its folder_id."""
        folders = {"folder-a": "תינוק ישן", "folder-b": "שותה קפה"}
        reels = [
            {"hook": "hook1", "folder_id": "folder-a"},
            {"hook": "hook2", "folder_id": "folder-b"},
        ]

        def mock_list(user_id, folder_id):
            return {
                "folder-a": ["uid/folder-a/vid1.mp4"],
                "folder-b": ["uid/folder-b/vid2.mp4"],
            }.get(folder_id, [])

        mock_bucket = MagicMock()
        mock_bucket.get_public_url = lambda path: f"https://storage.example.com/{path}"
        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_bucket)
        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.list_folder_videos", side_effect=mock_list), \
             patch("supabase_client.create_client", return_value=mock_client):
            from video_picker import pick_videos_for_reels
            urls = pick_videos_for_reels("uid", folders, reels)

        assert len(urls) == 2
        assert "folder-a/vid1.mp4" in urls[0]
        assert "folder-b/vid2.mp4" in urls[1]

    def test_round_robin_diversity(self):
        """Multiple reels in same folder get different videos before reuse."""
        folders = {"folder-a": "הרצאות"}
        reels = [
            {"hook": "h1", "folder_id": "folder-a"},
            {"hook": "h2", "folder_id": "folder-a"},
            {"hook": "h3", "folder_id": "folder-a"},
        ]

        def mock_list(user_id, folder_id):
            return ["uid/folder-a/vid1.mp4", "uid/folder-a/vid2.mp4"]

        mock_bucket = MagicMock()
        mock_bucket.get_public_url = lambda path: f"https://storage.example.com/{path}"
        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_bucket)
        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.list_folder_videos", side_effect=mock_list), \
             patch("supabase_client.create_client", return_value=mock_client):
            from video_picker import pick_videos_for_reels
            urls = pick_videos_for_reels("uid", folders, reels)

        # First two should be different videos, third reuses
        assert urls[0] != urls[1]
        assert len(urls) == 3

    def test_fallback_when_folder_empty(self):
        """Reel with empty folder falls back to another folder's videos."""
        folders = {"folder-a": "ריקה", "folder-b": "יש בה סרטונים"}
        reels = [
            {"hook": "h1", "folder_id": "folder-a"},
        ]

        def mock_list(user_id, folder_id):
            return {
                "folder-a": [],
                "folder-b": ["uid/folder-b/vid1.mp4"],
            }.get(folder_id, [])

        mock_bucket = MagicMock()
        mock_bucket.get_public_url = lambda path: f"https://storage.example.com/{path}"
        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_bucket)
        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.list_folder_videos", side_effect=mock_list), \
             patch("supabase_client.create_client", return_value=mock_client):
            from video_picker import pick_videos_for_reels
            urls = pick_videos_for_reels("uid", folders, reels)

        assert urls[0] is not None
        assert "folder-b/vid1.mp4" in urls[0]

    def test_invalid_folder_id_falls_back(self):
        """Reel with folder_id not in folders dict falls back to a valid folder."""
        folders = {"folder-a": "תינוק ישן"}
        reels = [
            {"hook": "h1", "folder_id": "nonexistent"},
        ]

        def mock_list(user_id, folder_id):
            return {"folder-a": ["uid/folder-a/vid1.mp4"]}.get(folder_id, [])

        mock_bucket = MagicMock()
        mock_bucket.get_public_url = lambda path: f"https://storage.example.com/{path}"
        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_bucket)
        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.list_folder_videos", side_effect=mock_list), \
             patch("supabase_client.create_client", return_value=mock_client):
            from video_picker import pick_videos_for_reels
            urls = pick_videos_for_reels("uid", folders, reels)

        assert urls[0] is not None
        assert "folder-a/vid1.mp4" in urls[0]

    def test_null_folder_id_falls_back(self):
        """Reel with folder_id=None falls back to a valid folder."""
        folders = {"folder-a": "תינוק ישן"}
        reels = [
            {"hook": "h1", "folder_id": None},
        ]

        def mock_list(user_id, folder_id):
            return {"folder-a": ["uid/folder-a/vid1.mp4"]}.get(folder_id, [])

        mock_bucket = MagicMock()
        mock_bucket.get_public_url = lambda path: f"https://storage.example.com/{path}"
        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_bucket)
        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.list_folder_videos", side_effect=mock_list), \
             patch("supabase_client.create_client", return_value=mock_client):
            from video_picker import pick_videos_for_reels
            urls = pick_videos_for_reels("uid", folders, reels)

        assert urls[0] is not None

    def test_no_videos_anywhere_returns_nones(self):
        """When no folder has videos, returns None for each reel."""
        folders = {"folder-a": "ריקה"}
        reels = [{"hook": "h1", "folder_id": "folder-a"}]

        mock_bucket = MagicMock()
        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_bucket)
        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.list_folder_videos", return_value=[]), \
             patch("supabase_client.create_client", return_value=mock_client):
            from video_picker import pick_videos_for_reels
            urls = pick_videos_for_reels("uid", folders, reels)

        assert urls == [None]
