# End-to-End Generate + Render Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/generate-async` an end-to-end pipeline that generates content, picks relevant source videos by folder name, renders videos with hooks overlaid, and returns finished video URLs in the callback.

**Architecture:** The LLM generates reels and picks a `folder_id` per reel from a provided folder map. A new `video_picker` module assigns actual video URLs with round-robin diversity. The async generation background task then renders each reel in parallel (max 5 concurrent) and includes rendered URLs in the callback.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, Supabase Storage (sync client), asyncio, pytest

**Spec:** `docs/superpowers/specs/2026-03-11-e2e-generate-render-design.md`

---

## Chunk 1: Supabase folder listing + Video picker

### Task 1: Add `list_folder_videos` to supabase_client

**Files:**
- Modify: `supabase_client.py:55-93` (add new function after existing `list_raw_videos`)
- Test: `tests/test_supabase_client.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_supabase_client.py`, add:

```python
class TestListFolderVideos:

    def test_list_folder_videos_returns_video_paths(self):
        """list_folder_videos() returns paths of video files in a specific folder."""
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.list = MagicMock(return_value=[
            {"name": "clip1.mp4", "id": "file-id-1"},
            {"name": "clip2.mov", "id": "file-id-2"},
            {"name": "thumbnail.jpg", "id": "file-id-3"},
        ])

        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_storage_bucket)

        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.create_client", return_value=mock_client):
            import supabase_client
            result = supabase_client.list_folder_videos("user-123", "folder-abc")

        assert result == ["user-123/folder-abc/clip1.mp4", "user-123/folder-abc/clip2.mov"]
        mock_storage_bucket.list.assert_called_once_with(path="user-123/folder-abc")

    def test_list_folder_videos_empty_folder(self):
        """list_folder_videos() returns empty list when folder has no videos."""
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.list = MagicMock(return_value=[])

        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_storage_bucket)

        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.create_client", return_value=mock_client):
            import supabase_client
            result = supabase_client.list_folder_videos("user-123", "empty-folder")

        assert result == []

    def test_list_folder_videos_handles_exception(self):
        """list_folder_videos() returns empty list on Supabase error."""
        mock_storage_bucket = MagicMock()
        mock_storage_bucket.list = MagicMock(side_effect=Exception("network error"))

        mock_storage = MagicMock()
        mock_storage.from_ = MagicMock(return_value=mock_storage_bucket)

        mock_client = MagicMock()
        mock_client.storage = mock_storage

        with patch("supabase_client.create_client", return_value=mock_client):
            import supabase_client
            result = supabase_client.list_folder_videos("user-123", "bad-folder")

        assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_supabase_client.py::TestListFolderVideos -v`
Expected: FAIL with `AttributeError: module 'supabase_client' has no attribute 'list_folder_videos'`

- [ ] **Step 3: Implement `list_folder_videos`**

In `supabase_client.py`, add after `list_raw_videos` (after line 93):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_supabase_client.py::TestListFolderVideos -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add supabase_client.py tests/test_supabase_client.py
git commit -m "feat: add list_folder_videos to supabase_client"
```

---

### Task 2: Create `video_picker.py`

**Files:**
- Create: `video_picker.py`
- Test: `tests/test_video_picker.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_video_picker.py`:

```python
"""Tests for video_picker — folder-aware video selection with diversity."""

from unittest.mock import patch, MagicMock
import pytest

import config


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_video_picker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_picker'`

- [ ] **Step 3: Implement `video_picker.py`**

Create `video_picker.py` in the project root:

```python
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
        folders: Map of folder_id → display name.
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

    # Fetch videos for each unique folder (one Supabase call per folder)
    folder_videos: dict[str, list[str]] = {}
    for fid in set(validated_folder_ids):
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_video_picker.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add video_picker.py tests/test_video_picker.py
git commit -m "feat: add video_picker with folder-aware round-robin selection"
```

---

## Chunk 2: Prompt + Agent changes (folder_id in LLM output)

### Task 3: Add folders section to prompt

**Files:**
- Modify: `prompts.py:217-248` (add `folders` param and `format_folders` function)

- [ ] **Step 1: Add `format_folders()` function**

In `prompts.py`, add after `format_insights` (after line 201):

```python
def format_folders(folders: dict[str, str]) -> str:
    """Format folders map for prompt insertion."""
    if not folders:
        return ""

    lines = []
    for folder_id, display_name in folders.items():
        lines.append(f"- {folder_id}: {display_name}")
    return "\n".join(lines)
```

- [ ] **Step 2: Add folders section to `BATCH_GENERATION_PROMPT`**

In `prompts.py`, add a new section in the template string after the insights section (after line 60) and before the instructions section:

```
═══════════════════════════════════════
תיקיות סרטונים זמינות (בחר תיקיה רלוונטית לכל רילס):
═══════════════════════════════════════
{folders_text}
```

- [ ] **Step 3: Add `folder_id` to the JSON output schema in the prompt**

In the JSON example in `BATCH_GENERATION_PROMPT` (around line 88-100), add `folder_id` field:

```
{{
  "reels": [
    {{
      "hook": "...",
      "hook_type": "...",
      "text_on_video": "...",
      "verbal_script": "...",
      "caption": "...",
      "format": "...",
      "content_type": "...",
      "awareness_stage": "...",
      "magnet_id": "..." או null,
      "folder_id": "..." או null
    }}
  ]
}}
```

And add instruction #10 to the numbered list:

```
10. folder_id — ה-ID של התיקיה הכי רלוונטית להוק מרשימת התיקיות הזמינות (אם אין תיקיות — null). נסה לגוון בין התיקיות ולא לבחור באותה תיקיה כל הזמן.
```

- [ ] **Step 4: Update `build_generation_prompt()` signature and call**

In `prompts.py`, update `build_generation_prompt`:

```python
def build_generation_prompt(
    *,
    quantity: int,
    client_name: str,
    business_info: str,
    tone_of_voice: str,
    niche: str,
    ig_username: str,
    distribution: dict[str, int],
    magnets: list[dict],
    style_examples: list[dict],
    hooks: list[dict],
    viral_content: list[dict],
    rtm_events: list[dict],
    insights: dict | None,
    folders: dict[str, str] | None = None,
) -> str:
    """Build the full generation prompt with all context."""
    return BATCH_GENERATION_PROMPT.format(
        quantity=quantity,
        client_name=client_name,
        business_info=business_info,
        tone_of_voice=tone_of_voice,
        niche=niche,
        ig_username=ig_username,
        distribution_text=format_distribution(distribution),
        magnets_text=format_magnets(magnets),
        style_examples_text=format_style_examples(style_examples),
        hooks_text=format_hooks(hooks),
        viral_content_text=format_viral_content(viral_content),
        rtm_text=format_rtm_events(rtm_events),
        insights_text=format_insights(insights),
        folders_text=format_folders(folders or {}),
    )
```

- [ ] **Step 5: Commit**

```bash
git add prompts.py
git commit -m "feat: add folder selection to LLM prompt and output schema"
```

---

### Task 4: Pass `folders` through `agent.generate_reels()`

**Files:**
- Modify: `agent.py:105-107` (add `folders` param)
- Modify: `agent.py:146-160` (pass to `build_generation_prompt`)

- [ ] **Step 1: Update `generate_reels()` signature**

In `agent.py`, change line 105-107:

```python
async def generate_reels(
    client_id: str, batch_type: str, quantity: int = 10,
    folders: dict[str, str] | None = None,
) -> dict[str, Any]:
```

- [ ] **Step 2: Pass `folders` to prompt builder**

In `agent.py`, update the `prompts.build_generation_prompt()` call (around line 146) to include:

```python
    prompt = prompts.build_generation_prompt(
        quantity=quantity,
        client_name=client_name,
        business_info=business_info,
        tone_of_voice=tone_of_voice,
        niche=niche,
        ig_username=ig_username,
        distribution=distribution,
        magnets=data["magnets"],
        style_examples=data["style_examples"],
        hooks=data["hooks"],
        viral_content=data["viral_pool"],
        rtm_events=data["rtm_events"],
        insights=data["insights"],
        folders=folders,
    )
```

- [ ] **Step 3: Commit**

```bash
git add agent.py
git commit -m "feat: pass folders through agent to prompt builder"
```

---

## Chunk 3: End-to-end async pipeline in main.py

### Task 5: Add `folders` to `GenerateAsyncRequest`

**Files:**
- Modify: `main.py:132-143`

- [ ] **Step 1: Add `folders` field**

In `main.py`, add to `GenerateAsyncRequest` class (after line 143):

```python
    folders: dict[str, str] = Field(
        default_factory=dict,
        description="Map of folder_id → display name for video selection",
    )
```

- [ ] **Step 2: Commit**

```bash
git add main.py
git commit -m "feat: add folders field to GenerateAsyncRequest"
```

---

### Task 6: Wire up end-to-end render in `_run_generation_and_callback`

**Files:**
- Modify: `main.py:169-286` (the `_run_generation_and_callback` function)

This is the core change. Add imports at top of main.py:

```python
import video_picker
```

- [ ] **Step 1: Update `_run_generation_and_callback` to pass folders to generate_reels**

In `main.py`, update the `agent.generate_reels()` call (around line 191-194):

```python
        result = await agent.generate_reels(
            client_id=request.client_id,
            batch_type=request.batch_type,
            quantity=request.quantity,
            folders=request.folders,
        )
```

- [ ] **Step 2: Add awareness stage mapping helper**

Add near the top of `main.py` (after `_build_segments`):

```python
_AWARENESS_STAGE_MAP = {
    "Unaware": 1,
    "Problem-Aware": 3,
    "Solution-Aware": 5,
}
```

- [ ] **Step 3: Add video picking and rendering after generation**

In `_run_generation_and_callback`, after the reels are generated and saved to Airtable (after the projects loop, around line 217), add the video picking and rendering logic. Replace the section from building `projects` through sending the callback with:

```python
        # Map reels to content_projects format
        projects = []
        for reel in result.get("reels", []):
            projects.append({
                "title": (reel.get("hook", "") or "")[:100],
                "caption": reel.get("caption", ""),
                "video_text": reel.get("text_on_video", ""),
                "hook": reel.get("hook", ""),
                "hook_type": reel.get("hook_type", ""),
                "verbal_script": reel.get("verbal_script", ""),
                "format": reel.get("format", ""),
                "awareness_stage": reel.get("awareness_stage", ""),
                "content_goal": {"חשיפה": "exposure", "מכירה": "sales", "מעורב": "mixed"}.get(request.batch_type, "mixed"),
                "magnet_name": _resolve_magnet_name(
                    reel.get("magnet_id"), magnets
                ),
                "airtable_record_id": reel.get("record_id", ""),
                "client_airtable_id": request.client_id,
                "client_name": result.get("client_name", ""),
                "batch_id": batch_id,
                "folder_id": reel.get("folder_id"),
                "source_video_url": None,
                "rendered_video_url": None,
                "render_error": None,
                "status": "draft",
            })

        # ── Video picking + rendering ────────────────────────────────
        if request.folders:
            reels_data = result.get("reels", [])
            video_urls = video_picker.pick_videos_for_reels(
                request.user_id, request.folders, reels_data
            )

            # Assign source_video_url to projects
            for i, url in enumerate(video_urls):
                if i < len(projects):
                    projects[i]["source_video_url"] = url

            # Render each reel that has a source video and record_id
            sem = asyncio.Semaphore(5)

            async def _render_one(idx: int, project: dict) -> None:
                source_url = project.get("source_video_url")
                record_id = project.get("airtable_record_id")
                if not source_url or not record_id:
                    return

                async with sem:
                    try:
                        render_req = RenderRequest(
                            source_video_url=source_url,
                            hook_text=project.get("video_text", ""),
                            body_text=project.get("verbal_script", ""),
                            record_id=record_id,
                            client_id=request.client_id,
                            awareness_stage=_AWARENESS_STAGE_MAP.get(
                                project.get("awareness_stage", ""), None
                            ),
                        )

                        renderer = get_renderer()
                        brand_config = at.extract_brand_config(client_record)
                        resolved_brand = resolve_brand_for_render(
                            brand_config, render_req.awareness_stage
                        )
                        segments = _build_segments(render_req)

                        remotion_job_id = await renderer.render(
                            render_req, resolved_brand=resolved_brand, segments=segments
                        )

                        # Poll until done
                        for attempt in range(120):
                            status = await renderer.get_status(remotion_job_id)
                            if status.state == "completed":
                                break
                            elif status.state == "failed":
                                raise RuntimeError(f"Render failed: {status.error}")
                            wait = min(2 + attempt, 5)
                            await asyncio.sleep(wait)
                        else:
                            raise RuntimeError("Render timed out")

                        # Download + upload
                        tmp_path = f"/tmp/{record_id}-{remotion_job_id}.mp4"
                        await renderer.download_file(remotion_job_id, tmp_path)

                        destination = f"{record_id}/{remotion_job_id}.mp4"
                        video_url = await supabase_client.upload_video(tmp_path, destination)

                        await at.update_content_queue_video_attachment(record_id, video_url)

                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass

                        project["rendered_video_url"] = video_url
                        project["status"] = "rendered"
                        logger.info(f"Rendered reel {idx}: {video_url}")

                    except Exception as e:
                        logger.error(f"Render failed for reel {idx}: {e}")
                        project["render_error"] = str(e)
                        project["status"] = "render_failed"

            await asyncio.gather(
                *[_render_one(i, p) for i, p in enumerate(projects)]
            )
```

- [ ] **Step 4: Verify the callback payload still sends correctly**

The existing callback code after this section remains unchanged — it sends `projects` which now includes the new fields.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: end-to-end video picking + parallel rendering in generate-async"
```

---

### Task 7: Smoke test the full flow

- [ ] **Step 1: Run all existing tests to verify no regressions**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/ -v`
Expected: All existing tests pass

- [ ] **Step 2: Run new tests**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_video_picker.py tests/test_supabase_client.py -v`
Expected: All pass

- [ ] **Step 3: Final commit with all files**

```bash
git add -A
git commit -m "feat: complete end-to-end generate + render pipeline"
```
