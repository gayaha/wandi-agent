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

`folders` maps Supabase folder IDs (the actual subfolder names in storage) to Hebrew display names. Videos live at `raw-media/{user_id}/{folder_id}/`.

Validation: `folders` without `user_id` is meaningless — `user_id` is already a required field, so this is enforced by Pydantic.

## Architecture

### Flow

```
POST /generate-async
  1. agent.generate_reels(folders=folders)
     → LLM generates reels, each with a folder_id field
     → Reels saved to Airtable Content Queue (record_id assigned)
  2. video_picker.pick_videos_for_reels(user_id, folders, reels)
     → Lists videos per folder from Supabase (sync, consistent with existing pattern)
     → Assigns source_video_url per reel (diversity-first, reuse when needed)
  3. For each reel: call _run_render() internally (parallel, max 5 concurrent)
     → Requires record_id from step 1 (Airtable save must succeed first)
     → Remotion renders source video + hook text overlay
     → Upload to Supabase rendered-videos bucket
     → Update Airtable attachment
  4. Callback with projects including rendered_video_url
```

### Reel → RenderRequest Mapping

Each generated reel is mapped to a `RenderRequest` as follows:

| Reel field | RenderRequest field | Notes |
|---|---|---|
| (from video_picker) | `source_video_url` | Public URL of selected raw video |
| `text_on_video` | `hook_text` | The visual text overlay |
| `verbal_script` | `body_text` | Used for legacy 2-segment auto-split |
| `record_id` | `record_id` | Airtable Content Queue record ID |
| — | `text_direction` | Always `"rtl"` (Hebrew) |
| — | `animation_style` | Default `"fade"` |
| — | `duration_in_seconds` | Default `15` |
| `awareness_stage` | `awareness_stage` | Mapped: Unaware→1, Problem-Aware→3, Solution-Aware→5 |
| — | `client_id` | Passed through from request |
| — | `callback_url` | `None` (we poll internally, don't use per-render callbacks) |

### Files Changed

#### `main.py`
- Add `folders: dict[str, str] = {}` to `GenerateAsyncRequest`
- In `_run_generation_and_callback()`: after generation, call video picker, build `RenderRequest` per reel using mapping above, submit renders with `asyncio.Semaphore(5)` for concurrency control, poll all to completion, add `source_video_url` and `rendered_video_url` to each project in the callback payload

#### `agent.py`
- `generate_reels()` accepts new `folders: dict[str, str] = {}` parameter
- Passes folders to `prompts.build_generation_prompt()`
- No other logic changes — folder matching is the LLM's job
- Note: `folder_id` from LLM output is passed through in the reel dict but not saved to Airtable (no matching field exists)

#### `prompts.py`
- New `format_folders()` function to format folder list for prompt
- New `{folders_text}` placeholder in `BATCH_GENERATION_PROMPT` template
- New prompt section tells LLM to pick the most relevant `folder_id` per reel
- New field in JSON output schema: `"folder_id": "f1710234567abc"` (or `null` if no folders provided)
- `build_generation_prompt()` accepts `folders: dict[str, str] = {}` kwarg, calls `format_folders()` and passes result to `.format()`

#### `video_picker.py` (new file)
- `pick_videos_for_reels(user_id, folders, reels)` → list of source_video_urls
- Lists videos per referenced folder from Supabase (one call per unique folder)
- Assigns videos with diversity: round-robin through available videos before reusing
- Fallback: if a folder is empty, pick from another folder that has videos
- Handles missing/null/invalid `folder_id` from LLM: falls back to random folder from provided list

#### `supabase_client.py`
- New `list_folder_videos(user_id, folder_id)` — lists videos in a specific folder only
- Sync function (consistent with existing `list_raw_videos` pattern — uses sync supabase-py client)

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

לכל רילס, בחר את ה-folder_id של התיקיה הכי רלוונטית להוק שיצרת.
אם אין תיקיות — החזר null.
```

And the JSON schema adds `folder_id` per reel. The LLM matches semantically — e.g., a hook about "your baby needs a happy mom" maps to "שותה קפה" or "מתאמנת" folders.

When no folders are provided (`folders={}`), the section is omitted from the prompt and `folder_id` is not expected in the output.

## Video Selection Logic (`video_picker.py`)

```python
def pick_videos_for_reels(user_id, folders, reels):
    # 1. Validate folder_ids from reels against provided folders dict
    #    - Missing key, null, or invalid folder_id → pick random folder from list
    # 2. Group reels by (validated) folder_id
    # 3. For each unique folder_id, call list_folder_videos() (one Supabase call per folder)
    # 4. Per folder: shuffle videos, assign round-robin to reels
    #    (ensures diversity before reuse)
    # 5. If folder has 0 videos: pick from another folder that has videos
    # 6. If no folder has videos: return None for all
    # 7. Return list of source_video_urls aligned with reels (or None per reel)
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
      "render_error": null,
      "status": "rendered"
    }
  ]
}
```

Projects where render failed will have `"rendered_video_url": null`, `"render_error": "error message"`, and `"status": "render_failed"`.

## Edge Cases

- **No folders provided**: `folders={}` — skip video picking and rendering, behave like current text-only generation
- **Empty folder**: fallback to another folder with videos
- **No videos in any folder**: skip rendering, return projects with `rendered_video_url: null`
- **LLM returns invalid/missing/null folder_id**: fallback to random folder from the provided list
- **Render fails for one reel**: other reels still complete; failed reel gets `status: "render_failed"` with `render_error`
- **All renders fail**: callback still fires with all projects, each with null video URLs
- **Airtable save fails for a reel**: that reel cannot be rendered (no record_id); skip render, mark as `render_failed`

## Render Parallelism

Render jobs are submitted concurrently using `asyncio.gather()` with `asyncio.Semaphore(5)` to limit concurrent renders to 5 at a time (prevents overwhelming the Remotion service, especially with `quantity=30`). Each render follows the existing `_run_render` flow (submit → poll → download → upload → update Airtable). The callback fires only after all renders complete or fail.
