"""Supabase Storage client — upload rendered videos and construct source video URLs."""

import logging
import os
import random

from supabase import create_client, Client

import config

logger = logging.getLogger(__name__)


def _get_client() -> Client:
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


async def upload_video(file_path: str, destination: str) -> str:
    """Upload rendered video to Supabase Storage. Returns public URL.

    Uses sync supabase-py client (acceptable in asyncio background task).
    The rendered-videos bucket MUST be public for Airtable URL-based attachment.

    Args:
        file_path: Local path to the rendered video file.
        destination: Path within the bucket (e.g. "record_id/job_id.mp4").

    Returns:
        Public URL of the uploaded video.
    """
    client = _get_client()
    with open(file_path, "rb") as f:
        client.storage.from_(config.SUPABASE_BUCKET).upload(
            path=destination,
            file=f,
            file_options={"content-type": "video/mp4", "upsert": "true"},
        )
    url = client.storage.from_(config.SUPABASE_BUCKET).get_public_url(destination)
    logger.info(f"Uploaded video to Supabase: {url}")
    return url


def get_source_video_url(video_path: str) -> str:
    """Construct public URL for a source video in Supabase Storage.

    Args:
        video_path: Path within the source-videos bucket (e.g., "client_id/video.mp4")
    Returns:
        Full public URL to the source video
    """
    client = _get_client()
    return client.storage.from_(config.SUPABASE_SOURCE_BUCKET).get_public_url(video_path)


def list_raw_videos(user_id: str) -> list[str]:
    """List all video files under raw-media/{user_id}/ recursively (one level of subfolders).

    Returns full paths like "{user_id}/{folder_id}/video.mov".
    """
    client = _get_client()
    bucket = client.storage.from_(config.SUPABASE_RAW_MEDIA_BUCKET)
    video_extensions = {".mp4", ".mov", ".webm", ".avi"}
    video_paths: list[str] = []

    try:
        items = bucket.list(path=user_id)
    except Exception as e:
        logger.warning(f"Failed to list raw-media/{user_id}/: {e}")
        return []

    for item in items:
        name = item.get("name", "")
        item_id = item.get("id")

        if item_id is None:
            # Subfolder — list files inside
            subfolder_path = f"{user_id}/{name}"
            try:
                files = bucket.list(path=subfolder_path)
            except Exception as e:
                logger.warning(f"Failed to list raw-media/{subfolder_path}/: {e}")
                continue
            for f in files:
                fname = f.get("name", "")
                if any(fname.lower().endswith(ext) for ext in video_extensions):
                    video_paths.append(f"{subfolder_path}/{fname}")
        else:
            # File directly under user_id/
            if any(name.lower().endswith(ext) for ext in video_extensions):
                video_paths.append(f"{user_id}/{name}")

    logger.info(f"Found {len(video_paths)} raw videos for user {user_id}")
    return video_paths


def list_folder_videos(user_id: str, folder_id: str) -> list[str]:
    """List video files in a specific folder under raw-media/{user_id}/{folder_id}/.

    Returns full paths like "{user_id}/{folder_id}/clip.mp4".
    """
    client = _get_client()
    bucket = client.storage.from_(config.SUPABASE_RAW_MEDIA_BUCKET)
    video_extensions = {".mp4", ".mov", ".webm", ".avi"}
    folder_path = f"{user_id}/{folder_id}"

    try:
        items = bucket.list(path=folder_path)
    except Exception as e:
        logger.warning(f"Failed to list raw-media/{folder_path}/: {e}")
        return []

    return [
        f"{folder_path}/{item['name']}"
        for item in items
        if any(item.get("name", "").lower().endswith(ext) for ext in video_extensions)
    ]


def pick_random_source_video(user_id: str) -> str | None:
    """Pick a random raw video for a user and return its public URL.

    Returns None if no videos found.
    """
    paths = list_raw_videos(user_id)
    if not paths:
        logger.warning(f"No raw videos found for user {user_id}")
        return None

    chosen_path = random.choice(paths)
    client = _get_client()
    url = client.storage.from_(config.SUPABASE_RAW_MEDIA_BUCKET).get_public_url(chosen_path)
    logger.info(f"Selected random source video: {chosen_path}")
    return url
