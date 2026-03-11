"""Supabase Storage client — upload rendered videos and construct source video URLs."""

import logging
import os

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
