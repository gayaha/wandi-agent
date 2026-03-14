# SDMF Knowledge Injection + Field Mapping Fix + Two Reel Formats

## Problem

Four issues in the content generation → video rendering pipeline:

1. **SDMF knowledge not loaded**: `SDMF_agent_knowledge.md` exists in the repo but is never read or sent to the LLM. The model generates content without understanding the SDMF methodology, awareness stages, or content taxonomy.

2. **Field mapping is inverted**: The render pipeline maps `text_on_video` → `hookText` and `verbal_script` → `bodyText`. The correct mapping is `hook` → `hookText` (the one-liner displayed large on video) and `text_on_video` → `bodyText` (the changing text lines). `verbal_script` is a spoken script and should not be sent to the renderer at all.

3. **No hook-only reel support**: The SDMF methodology defines two visual reel formats — hook-only and hook-with-changing-text. The current prompt always asks for `text_on_video` (3-5 lines) on every reel, and `_build_segments()` always creates 2 segments. There is no way to produce a hook-only reel.

4. **Airtable double-mapping overwrites fields**: `agent.py:_build_queue_record()` creates records with separate fields ("Hook", "Text On Video", "Verbal Script", "Caption", etc.), but `airtable_client.py:save_reels_to_queue()` passes them through `_map_reel_to_queue_fields()`, which discards all those fields and replaces them with a single `"text on video"` field containing hook + verbal_script concatenated together. Most fields from the agent are never saved.

## Goal

- Inject the full SDMF knowledge base into the LLM's system prompt so it generates content aligned with the methodology.
- Fix the field mapping so the correct text appears in the correct visual position on the rendered video.
- Enable two reel formats (hook-only / hook+text) where the model decides per reel.
- Fix the Airtable save path so all fields are written correctly.

## Design

### 1. SDMF Knowledge Loading (`prompts.py`)

New function `load_sdmf_knowledge()`:
- Reads `SDMF_agent_knowledge.md` from the project root at import time (module-level cache).
- The file path is resolved relative to the prompts.py file location using `pathlib.Path(__file__).parent`.
- On success: the content is stored in a module-level variable `_SDMF_KNOWLEDGE`.
- On failure (file not found): logs a warning, stores empty string. Generation continues with the existing system prompt only.

A new module-level constant `FULL_SYSTEM_PROMPT` is built at import time:

```python
_SDMF_KNOWLEDGE = _load_sdmf_knowledge()

FULL_SYSTEM_PROMPT = f"""{_SDMF_KNOWLEDGE}

═══════════════════════════════════════
הנחיות ליצירת תוכן:
═══════════════════════════════════════
{SYSTEM_PROMPT}""" if _SDMF_KNOWLEDGE else SYSTEM_PROMPT
```

`agent.py:164` changes from `prompts.SYSTEM_PROMPT` to `prompts.FULL_SYSTEM_PROMPT`. This is the only change in `agent.py` beyond the null-normalization fix.

**Rationale**: SDMF is stable domain knowledge that doesn't change per client — it belongs in the system prompt. Dynamic per-client data (profile, magnets, hooks, etc.) stays in the user prompt as today.

### 2. Render Field Mapping Fix (`main.py`)

#### 2a. Null normalization in project construction (line ~217)

Python's `dict.get("key", "")` returns `None` (not `""`) when the key exists with value `None`. All nullable fields must use `or ""` to normalize:

```python
"video_text": reel.get("text_on_video") or "",   # normalize null → ""
"hook": reel.get("hook") or "",                    # normalize null → ""
```

#### 2b. `_render_one()` — RenderRequest construction (line ~264)

Before:
```python
hook_text=project.get("video_text", ""),      # text_on_video → hookText
body_text=project.get("verbal_script", ""),    # verbal_script → bodyText
```

After:
```python
hook_text=project.get("hook") or "",              # hook → hookText
body_text=project.get("video_text") or "",        # text_on_video → bodyText
```

`verbal_script` is not sent to the renderer. It remains in the Airtable record and callback payload as a spoken script reference only.

#### 2c. Updated mapping table

| AI output field | Project field | RenderRequest field | Displayed on video |
|---|---|---|---|
| `hook` | `hook` | `hook_text` | Large bold hook text |
| `text_on_video` | `video_text` | `body_text` | Changing body text (or `""` for hook-only) |
| `verbal_script` | `verbal_script` | — | Not rendered (spoken script only) |

#### 2d. RenderRequest model validator — hook-only compatibility

The existing validator at `renderer/models.py:116` checks:
```python
has_legacy = self.hook_text is not None and self.body_text is not None
```

For hook-only reels, `body_text` will be `""` (empty string, not `None`) thanks to the `or ""` normalization in 2a/2b. `""` is not `None`, so `has_legacy` evaluates to `True` and validation passes. No change needed to the model validator.

### 3. Two Reel Formats — Hook-Only vs Hook+Text

#### 3a. Prompt update (`prompts.py`)

Add a new section to `BATCH_GENERATION_PROMPT` before the field definitions (around line 70), explaining the two visual formats:

```
סוגי תבניות לרילס:
- "hook_only" — רק הוק על הווידאו. מתאים לרילסים קצרים, ויראליים, talking head
  שבהם האדם מדבר ואין צורך בטקסט נוסף. במקרה הזה: text_on_video = null
- "hook_with_text" — הוק + טקסט מתחלף על הווידאו. מתאים לרילסים ערכיים,
  הסברתיים, או כשרוצים להדגיש נקודות מרכזיות. במקרה הזה: text_on_video = 3-5 שורות קצרות

אתה מחליט איזו תבנית מתאימה לכל רילס לפי התוכן והפורמט.
```

The model decides per reel. No new output field is needed — `text_on_video: null` signals hook-only.

#### 3b. JSON example update in prompt

The JSON example block in `BATCH_GENERATION_PROMPT` (line ~98) must be updated to show that `text_on_video` can be null:

```json
"text_on_video": "..." or null,
```

This is critical — local models like GLM4 are heavily influenced by the example JSON structure. If the example always shows a string value, the model will rarely return null.

#### 3c. `_build_segments()` update (`main.py`)

Current behavior: always creates 2 segments (hook half + body half).

New behavior:
- If `body_text` is falsy (empty string or None): return a single hook segment spanning the full duration.
- Otherwise: return 2 segments as today (hook first half, body second half).

```python
if not request.body_text:
    return [{
        "text": request.hook_text or "",
        "startSeconds": 0.0,
        "endSeconds": float(duration),
        "animationStyle": request.animation_style,
        "role": "hook",
    }]

mid = duration / 2
return [
    {"text": request.hook_text or "", "startSeconds": 0.0, "endSeconds": mid, ...},
    {"text": request.body_text or "", "startSeconds": mid, "endSeconds": float(duration), ...},
]
```

### 4. Airtable Save Fix (`airtable_client.py` + `agent.py`)

#### Problem

`agent.py:_build_queue_record()` creates records with proper Airtable field names:
```python
{"Client": [...], "Hook": "...", "Text On Video": "...", "Verbal Script": "...", "Caption": "...", ...}
```

But `save_reels_to_queue()` calls `_map_reel_to_queue_fields()` which discards all of these and creates a new dict with only:
```python
{"text on video": "hook\nverbal_script", "Status": "Pending", "post status": "processing", ...}
```

All fields from `_build_queue_record` are lost.

#### Fix

`save_reels_to_queue()` should pass records through directly without remapping. The `_map_reel_to_queue_fields()` function is removed (or kept only if another code path needs it, which is not the case currently).

```python
async def save_reels_to_queue(
    reels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Save pre-mapped reel records to the Content Queue table."""
    return await _create_records_batch(config.TABLE_CONTENT_QUEUE, reels)
```

`agent.py:_build_queue_record()` already produces the correct Airtable format, so this works directly.

Additionally, `_build_queue_record` must normalize null values from the model output to avoid writing `None` to Airtable:

```python
"Hook": reel.get("hook") or "",
"Text On Video": reel.get("text_on_video") or "",
"Verbal Script": reel.get("verbal_script") or "",
```

### 5. Spec Correction

The previous spec (`2026-03-11-e2e-generate-render-design.md`) documents the old (incorrect) mapping in its "Reel → RenderRequest Mapping" table. That spec is not modified — this document supersedes the mapping table.

## Files Changed

| File | Change |
|------|--------|
| `prompts.py` | Add `_load_sdmf_knowledge()`, build `FULL_SYSTEM_PROMPT` at module level, add two-format instructions + updated JSON example to generation prompt |
| `main.py:264-267` | Fix field mapping: `hook→hook_text`, `text_on_video→body_text`, with `or ""` null normalization |
| `main.py:217-218` | Normalize `video_text` and `hook` with `or ""` in project construction |
| `main.py:54-72` | `_build_segments()`: single segment when body_text is empty |
| `agent.py:164` | Use `prompts.FULL_SYSTEM_PROMPT` instead of `prompts.SYSTEM_PROMPT` |
| `agent.py:89-91` | Normalize nulls with `or ""` in `_build_queue_record` |
| `airtable_client.py:241-250` | `save_reels_to_queue()`: pass records directly, remove `_map_reel_to_queue_fields()` call |

## Files NOT Changed

- `renderer/models.py` — validator already compatible with empty-string body_text
- `renderer/remotion.py` — HTTP client unchanged
- `renderer/brand.py` — no changes
- `ollama_client.py` — no changes
- `remotion-service/` — already supports 1-segment input via Zod `z.array(SegmentSchema).min(1)`

## Edge Cases

- **SDMF file missing**: warning logged, `FULL_SYSTEM_PROMPT` falls back to `SYSTEM_PROMPT` only (graceful degradation)
- **Model returns `text_on_video: null`**: normalized to `""`, renderer creates hook-only reel (1 segment)
- **Model returns `text_on_video: ""`**: treated same as null (falsy check in `_build_segments`)
- **Model returns `hook: null`** (shouldn't happen but defensive): normalized to `""`, segment renders with no text
- **Existing Airtable records**: no migration needed — field names are unchanged, only the values written and the render mapping change
- **`dict.get()` with null values**: all paths use `or ""` pattern to normalize `None` to empty string, avoiding null propagation through the pipeline

## Test Updates

Existing tests that need updating:
- `tests/test_renderer_remotion.py` — add test for single-segment `_build_segments` path (hook-only reel)
- `tests/test_render_routes.py` — update render payload assertions to use new field mapping
- `tests/test_renderer_protocol.py` — add test for `RenderRequest` with empty body_text
