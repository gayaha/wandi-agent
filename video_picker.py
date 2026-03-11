"""Folder-aware video selection with round-robin diversity."""

import logging
import random

import supabase_client
import config

logger = logging.getLogger(__name__)


def _get_public_url(video_path: str) -> str:
    """Get public URL for a raw-media video path."""
    client = supabase_client._get_client()
    return client.storage.from_(config.SUPABASE_RAW_MEDIA_BUCKET).get_public_url(video_path)


def pick_videos_for_reels(
    user_id: str,
    folders: dict[str, str],
    reels: list[dict],
) -> list[str | None]:
    """Pick a source video for each reel based on folder_id with round-robin diversity.

    Args:
        user_id: Supabase user UUID.
        folders: Map of folder_id to display name.
        reels: List of reel dicts, each with a 'folder_id' field.

    Returns:
        List of public video URLs (or None) aligned with reels.
    """
    if not folders:
        return [None] * len(reels)

    valid_folder_ids = set(folders.keys())

    # Validate each reel's folder_id, fix invalid ones
    validated_folder_ids: list[str] = []
    for reel in reels:
        fid = reel.get("folder_id")
        if fid and fid in valid_folder_ids:
            validated_folder_ids.append(fid)
        else:
            # Fallback: pick a random valid folder
            validated_folder_ids.append(random.choice(list(valid_folder_ids)))

    # Fetch videos for all provided folders (not just referenced ones, for fallback)
    folder_videos: dict[str, list[str]] = {}
    for fid in valid_folder_ids:
        folder_videos[fid] = supabase_client.list_folder_videos(user_id, fid)

    # Collect all videos from all folders for fallback
    all_videos: list[str] = []
    for vids in folder_videos.values():
        all_videos.extend(vids)

    if not all_videos:
        logger.warning(f"No videos found in any folder for user {user_id}")
        return [None] * len(reels)

    # Round-robin counters per folder
    folder_counters: dict[str, int] = {fid: 0 for fid in folder_videos}
    # Shuffle videos per folder for variety
    for fid in folder_videos:
        random.shuffle(folder_videos[fid])

    urls: list[str | None] = []
    for fid in validated_folder_ids:
        vids = folder_videos.get(fid, [])
        if not vids:
            # Fallback: use videos from another folder
            vids = all_videos
            idx = folder_counters.get("_fallback", 0)
            folder_counters["_fallback"] = idx + 1
        else:
            idx = folder_counters[fid]
            folder_counters[fid] = idx + 1

        chosen_path = vids[idx % len(vids)]
        urls.append(_get_public_url(chosen_path))

    return urls
