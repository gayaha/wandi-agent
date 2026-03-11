# End-to-End Generate + Render Pipeline

## Problem

When a user clicks "create content for the week", the system generates text-only content (hooks, scripts, captions) but doesn't produce finished videos. The video rendering requires separate orchestration through n8n, and source video selection is random rather than contextually matched to the content.

## Goal

Make `/generate-async` an end-to-end pipeline: generate content, pick relevant source videos from the user's library based on folder names, render videos with hooks overlaid, and return finished video URLs in the callback.

## Updated Payload

```json
{
  "client_id": "recXXX",
  "batch_type": "חשיפה",
  "quantity": 7,
  "user_id": "user-uuid",
  "connection_id": "conn-uuid",
  "folders": {
    "f1710234567abc": "תינוק ישן",
    "f1710234568def": "מרדימה תינוק",
    "f1710234569ghi": "שותה קפה"
  },
  "callback_url": "...",
  "webhook_secret": "..."
}
```

`folders` maps Supabase folder IDs to Hebrew display names. Videos live at `raw-media/{user_id}/{folder_id}/`.

## Architecture

### Flow

```
POST /generate-async
  1. agent.generate_reels(folders=folders)
     → LLM generates reels, each with a folder_id field
  2. video_picker.pick_videos_for_reels(user_id, folders, reels)
     → Lists videos per folder from Supabase
     → Assigns source_video_url per reel (diversity-first, reuse when needed)
  3. For each reel: POST /render (internal, parallel)
     → Remotion renders source video + hook text overlay
     → Upload to Supabase rendered-videos bucket
     → Update Airtable attachment
  4. Callback with projects including rendered_video_url
```

### Files Changed

#### `main.py`
- Add `folders: dict[str, str] = {}` to `GenerateAsyncRequest`
- Pass `folders` and `user_id` through to `agent.generate_reels()`
- In `_run_generation_and_callback()`: after generation, call video picker, then submit renders in parallel, poll all to completion, add `source_video_url` and `rendered_video_url` to each project in the callback payload

#### `agent.py`
- `generate_reels()` accepts new `folders: dict[str, str] = {}` parameter
- Passes folders to `prompts.build_generation_prompt()`
- No other logic changes — folder matching is the LLM's job

#### `prompts.py`
- New `format_folders()` function to format folder list for prompt
- New prompt section in `BATCH_GENERATION_PROMPT`: tells LLM to pick the most relevant `folder_id` per reel
- New field in JSON output schema: `"folder_id": "f1710234567abc"` (or `null` if no folders provided)
- `build_generation_prompt()` accepts `folders` kwarg

#### `video_picker.py` (new file)
- `pick_videos_for_reels(user_id, folders, reels)` → list of source_video_urls
- Lists videos per referenced folder from Supabase (one call per unique folder)
- Assigns videos with diversity: round-robin through available videos before reusing
- Fallback: if a folder is empty, pick from another folder that has videos

#### `supabase_client.py`
- New `list_folder_videos(user_id, folder_id)` — lists videos in a specific folder only (more efficient than scanning all folders)

### Files NOT Changed
- `renderer/` — no changes to Remotion service or renderer models
- `airtable_client.py` — no schema changes
- `/generate` (sync endpoint) — stays text-only
- `/render` — still available for direct use

## LLM Folder Selection

The prompt includes a new section:

```
═══════════════════════════════════════
תיקיות סרטונים זמינות (בחר תיקיה רלוונטית לכל רילס):
═══════════════════════════════════════
- f1710234567abc: תינוק ישן
- f1710234568def: מרדימה תינוק
- f1710234569ghi: שותה קפה
```

And the JSON schema adds `folder_id` per reel. The LLM matches semantically — e.g., a hook about "your baby needs a happy mom" maps to "שותה קפה" or "מתאמנת" folders.

## Video Selection Logic (`video_picker.py`)

```python
def pick_videos_for_reels(user_id, folders, reels):
    # 1. Group reels by folder_id
    # 2. For each unique folder_id, call list_folder_videos()
    # 3. Per folder: shuffle videos, assign round-robin to reels
    #    (ensures diversity before reuse)
    # 4. If folder has 0 videos: pick from another folder that has videos
    # 5. Return list of source_video_urls aligned with reels
```

## Callback Payload (Updated)

```json
{
  "user_id": "...",
  "connection_id": "...",
  "batch_id": "...",
  "projects": [
    {
      "title": "...",
      "hook": "...",
      "caption": "...",
      "video_text": "...",
      "verbal_script": "...",
      "format": "...",
      "awareness_stage": "...",
      "content_goal": "exposure",
      "magnet_name": "...",
      "airtable_record_id": "recXXX",
      "client_airtable_id": "recXXX",
      "client_name": "...",
      "batch_id": "...",
      "folder_id": "f1710234567abc",
      "source_video_url": "https://...raw-media/.../video.mp4",
      "rendered_video_url": "https://...rendered-videos/recXXX/jobid.mp4",
      "status": "rendered"
    }
  ]
}
```

Projects where render failed will have `"rendered_video_url": null` and `"status": "render_failed"`.

## Edge Cases

- **No folders provided**: `folders={}` — skip video picking and rendering, behave like current text-only generation
- **Empty folder**: fallback to another folder with videos
- **No videos in any folder**: skip rendering, return projects with `rendered_video_url: null`
- **LLM returns invalid folder_id**: fallback to random folder from the provided list
- **Render fails for one reel**: other reels still complete; failed reel gets `status: "render_failed"`
- **All renders fail**: callback still fires with all projects, each with null video URLs

## Render Parallelism

All render jobs are submitted concurrently using `asyncio.gather()`. Each render follows the existing `_run_render` flow (submit → poll → download → upload → update Airtable). The callback fires only after all renders complete or fail.
