# SDMF Knowledge Injection + Field Mapping Fix Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the content generation → video rendering pipeline by injecting SDMF knowledge into the LLM prompt, correcting inverted field mapping, supporting hook-only reels, and fixing the Airtable double-mapping bug.

**Architecture:** Four targeted fixes across the Python pipeline. SDMF knowledge is loaded from MD file into system prompt at import time. Field mapping in `main.py` is corrected so `hook→hookText` and `text_on_video→bodyText`. `_build_segments` gains a single-segment path for hook-only reels. Airtable save bypasses the broken remapping function.

**Tech Stack:** Python, FastAPI, Pydantic, Ollama, Airtable API

**Spec:** `docs/superpowers/specs/2026-03-14-sdmf-prompt-and-field-mapping-fix-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `prompts.py` | Modify | Load SDMF knowledge, build FULL_SYSTEM_PROMPT, add two-format instructions |
| `agent.py` | Modify | Use FULL_SYSTEM_PROMPT, normalize nulls in `_build_queue_record` |
| `main.py` | Modify | Fix field mapping in project construction + `_render_one`, update `_build_segments` for hook-only |
| `airtable_client.py` | Modify | Remove `_map_reel_to_queue_fields` remapping from `save_reels_to_queue` |
| `tests/test_prompts.py` | Create | Tests for SDMF loading + FULL_SYSTEM_PROMPT |
| `tests/test_segments.py` | Modify | Add hook-only RenderRequest + legacy empty body tests |
| `tests/test_build_segments.py` | Create | Unit tests for `_build_segments` including hook-only path |
| `tests/test_airtable_client.py` | Modify | Test that `save_reels_to_queue` passes records through directly |

---

## Chunk 1: SDMF Knowledge Loading + Prompt Updates

### Task 1: Load SDMF into system prompt (`prompts.py`)

**Files:**
- Modify: `prompts.py:1-14` (add loading function and FULL_SYSTEM_PROMPT)
- Test: `tests/test_prompts.py` (new file)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_prompts.py`:

```python
"""Tests for SDMF knowledge loading and prompt construction."""

import importlib
from pathlib import Path
from unittest.mock import patch

import pytest


class TestSdmfKnowledgeLoading:

    def test_full_system_prompt_contains_sdmf_content(self):
        """FULL_SYSTEM_PROMPT includes SDMF knowledge base content."""
        import prompts
        assert "SDMF" in prompts.FULL_SYSTEM_PROMPT
        assert "Smart DM Funnel" in prompts.FULL_SYSTEM_PROMPT

    def test_full_system_prompt_contains_original_instructions(self):
        """FULL_SYSTEM_PROMPT still contains the original copywriter instructions."""
        import prompts
        assert "קופירייטר ישראלי" in prompts.FULL_SYSTEM_PROMPT

    def test_full_system_prompt_sdmf_comes_before_instructions(self):
        """SDMF knowledge appears before the copywriter instructions in FULL_SYSTEM_PROMPT."""
        import prompts
        sdmf_pos = prompts.FULL_SYSTEM_PROMPT.index("SDMF")
        instructions_pos = prompts.FULL_SYSTEM_PROMPT.index("קופירייטר ישראלי")
        assert sdmf_pos < instructions_pos

    def test_sdmf_file_missing_falls_back_gracefully(self, tmp_path):
        """When SDMF file is missing, FULL_SYSTEM_PROMPT equals SYSTEM_PROMPT."""
        import prompts

        with patch.object(Path, "read_text", side_effect=FileNotFoundError):
            result = prompts._load_sdmf_knowledge()
        assert result == ""

    def test_system_prompt_unchanged(self):
        """Original SYSTEM_PROMPT constant is not modified."""
        import prompts
        assert "קופירייטר ישראלי" in prompts.SYSTEM_PROMPT
        assert "SDMF" not in prompts.SYSTEM_PROMPT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_prompts.py -v`
Expected: FAIL — `FULL_SYSTEM_PROMPT` and `_load_sdmf_knowledge` do not exist yet.

- [ ] **Step 3: Implement SDMF loading in `prompts.py`**

Add at the top of `prompts.py` (before `SYSTEM_PROMPT`):

```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_sdmf_knowledge() -> str:
    """Load SDMF knowledge base from markdown file.

    Returns the file content as a string, or empty string if the file
    is not found (with a warning logged).
    """
    sdmf_path = Path(__file__).parent / "SDMF_agent_knowledge.md"
    try:
        return sdmf_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(f"SDMF knowledge file not found at {sdmf_path}")
        return ""


_SDMF_KNOWLEDGE = _load_sdmf_knowledge()
```

Then after the existing `SYSTEM_PROMPT` constant, add:

```python
FULL_SYSTEM_PROMPT = (
    f"""{_SDMF_KNOWLEDGE}

═══════════════════════════════════════
הנחיות ליצירת תוכן:
═══════════════════════════════════════
{SYSTEM_PROMPT}"""
    if _SDMF_KNOWLEDGE
    else SYSTEM_PROMPT
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_prompts.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add prompts.py tests/test_prompts.py
git commit -m "feat: load SDMF knowledge into system prompt for LLM generation"
```

---

### Task 2: Add two reel format instructions to generation prompt (`prompts.py`)

**Files:**
- Modify: `prompts.py:68-108` (BATCH_GENERATION_PROMPT — add format instructions + update JSON example)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_prompts.py`:

```python
class TestBatchGenerationPrompt:

    def test_prompt_contains_hook_only_format_instructions(self):
        """BATCH_GENERATION_PROMPT explains hook_only reel format."""
        import prompts
        assert "hook_only" in prompts.BATCH_GENERATION_PROMPT

    def test_prompt_contains_hook_with_text_format_instructions(self):
        """BATCH_GENERATION_PROMPT explains hook_with_text reel format."""
        import prompts
        assert "hook_with_text" in prompts.BATCH_GENERATION_PROMPT

    def test_prompt_json_example_shows_text_on_video_can_be_null(self):
        """BATCH_GENERATION_PROMPT JSON example shows text_on_video can be null."""
        import prompts
        assert "null" in prompts.BATCH_GENERATION_PROMPT
        # The JSON example section should mention text_on_video with null
        idx = prompts.BATCH_GENERATION_PROMPT.index('"text_on_video"')
        # Within 50 chars of the field name, "null" should appear
        nearby = prompts.BATCH_GENERATION_PROMPT[idx:idx + 50]
        assert "null" in nearby
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_prompts.py::TestBatchGenerationPrompt -v`
Expected: FAIL — prompt does not contain "hook_only" or null in JSON example.

- [ ] **Step 3: Update BATCH_GENERATION_PROMPT in `prompts.py`**

Before the "הנחיות ליצירת כל רילס" section (line ~68), insert:

```
סוגי תבניות ויזואליות לרילס:
- "hook_only" — רק הוק על הווידאו. מתאים לרילסים קצרים, ויראליים, talking head שבהם האדם מדבר למצלמה ואין צורך בטקסט נוסף מעבר להוק. במקרה הזה: text_on_video = null
- "hook_with_text" — הוק + טקסט מתחלף על הווידאו. מתאים לרילסים ערכיים, הסברתיים, או כשרוצים להדגיש נקודות מרכזיות בטקסט. במקרה הזה: text_on_video = 3-5 שורות קצרות ופאנצ'יות

אתה מחליט איזו תבנית מתאימה לכל רילס לפי התוכן, הפורמט והמטרה.
```

Update the JSON example (line ~98) — change `"text_on_video": "...",` to:

```
"text_on_video": "..." או null,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_prompts.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add prompts.py tests/test_prompts.py
git commit -m "feat: add two reel format instructions (hook_only/hook_with_text) to generation prompt"
```

---

### Task 3: Use FULL_SYSTEM_PROMPT in agent.py

**Files:**
- Modify: `agent.py:164`

- [ ] **Step 1: Update the import in `agent.py`**

Change line 164 from:

```python
result = await ollama.generate_json(prompt, system=prompts.SYSTEM_PROMPT)
```

to:

```python
result = await ollama.generate_json(prompt, system=prompts.FULL_SYSTEM_PROMPT)
```

- [ ] **Step 2: Run existing tests to verify nothing breaks**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/ -v`
Expected: All existing tests PASS.

- [ ] **Step 3: Commit**

```bash
git add agent.py
git commit -m "feat: use FULL_SYSTEM_PROMPT (with SDMF knowledge) for content generation"
```

---

## Chunk 2: Field Mapping Fixes

### Task 4: Fix null normalization + field mapping in `main.py`

**Files:**
- Modify: `main.py:214-236` (project construction) and `main.py:264-267` (_render_one mapping)

- [ ] **Step 1: Fix null normalization in project construction (line ~217-218)**

Change:
```python
"video_text": reel.get("text_on_video", ""),
"hook": reel.get("hook", ""),
```

To:
```python
"video_text": reel.get("text_on_video") or "",
"hook": reel.get("hook") or "",
```

- [ ] **Step 2: Fix field mapping in `_render_one` (line ~264-267)**

Change:
```python
render_req = RenderRequest(
    source_video_url=source_url,
    hook_text=project.get("video_text", ""),
    body_text=project.get("verbal_script", ""),
    record_id=record_id,
```

To:
```python
render_req = RenderRequest(
    source_video_url=source_url,
    hook_text=project.get("hook") or "",
    body_text=project.get("video_text") or "",
    record_id=record_id,
```

- [ ] **Step 3: Run existing tests**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "fix: correct field mapping — hook→hookText, text_on_video→bodyText, normalize nulls"
```

---

### Task 5: Fix null normalization in `agent.py:_build_queue_record`

**Files:**
- Modify: `agent.py:87-99`

- [ ] **Step 1: Update `_build_queue_record` to use `or ""` pattern**

Change lines 89-92 from:
```python
"Hook": reel.get("hook", ""),
"Hook Type": reel.get("hook_type", ""),
"Text On Video": reel.get("text_on_video", ""),
"Verbal Script": reel.get("verbal_script", ""),
"Caption": reel.get("caption", ""),
"Format": reel.get("format", ""),
"Content Type": reel.get("content_type", ""),
"Awareness Stage": reel.get("awareness_stage", ""),
```

To:
```python
"Hook": reel.get("hook") or "",
"Hook Type": reel.get("hook_type") or "",
"Text On Video": reel.get("text_on_video") or "",
"Verbal Script": reel.get("verbal_script") or "",
"Caption": reel.get("caption") or "",
"Format": reel.get("format") or "",
"Content Type": reel.get("content_type") or "",
"Awareness Stage": reel.get("awareness_stage") or "",
```

- [ ] **Step 2: Run existing tests**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add agent.py
git commit -m "fix: normalize null model outputs to empty string in _build_queue_record"
```

---

### Task 6: Fix Airtable double-mapping in `airtable_client.py`

**Files:**
- Modify: `airtable_client.py:241-250`
- Modify: `tests/test_airtable_client.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_airtable_client.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch


class TestSaveReelsToQueue:

    @pytest.mark.asyncio
    async def test_save_reels_passes_records_through_directly(self):
        """save_reels_to_queue passes pre-mapped records to Airtable without remapping."""
        import airtable_client as at

        input_record = {
            "Client": ["recCLIENT"],
            "Hook": "Test hook",
            "Text On Video": "Line 1\nLine 2",
            "Verbal Script": "Full spoken script here",
            "Caption": "Caption with #hashtags",
            "Status": "Draft",
        }

        with patch.object(at, "_create_records_batch", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = [{"id": "recNEW", "fields": input_record}]
            result = await at.save_reels_to_queue([input_record])

        # Verify the record was passed through without modification
        call_args = mock_create.call_args
        saved_records = call_args[0][1]  # second positional arg
        assert len(saved_records) == 1
        assert saved_records[0]["Hook"] == "Test hook"
        assert saved_records[0]["Text On Video"] == "Line 1\nLine 2"
        assert saved_records[0]["Verbal Script"] == "Full spoken script here"
        assert saved_records[0]["Caption"] == "Caption with #hashtags"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_airtable_client.py::TestSaveReelsToQueue -v`
Expected: FAIL — `_map_reel_to_queue_fields` currently discards fields.

- [ ] **Step 3: Fix `save_reels_to_queue` in `airtable_client.py`**

Change lines 241-250 from:
```python
async def save_reels_to_queue(
    reels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Save generated reels to the Content Queue table.

    Accepts reel dicts with internal field names and maps them to the actual
    Airtable Content Queue field names before saving.
    """
    mapped = [_map_reel_to_queue_fields(r) for r in reels]
    return await _create_records_batch(config.TABLE_CONTENT_QUEUE, mapped)
```

To:
```python
async def save_reels_to_queue(
    reels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Save pre-mapped reel records to the Content Queue table.

    Expects records with Airtable field names (e.g. from agent._build_queue_record).
    Records are passed through directly without remapping.
    """
    return await _create_records_batch(config.TABLE_CONTENT_QUEUE, reels)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_airtable_client.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add airtable_client.py tests/test_airtable_client.py
git commit -m "fix: remove broken _map_reel_to_queue_fields remapping from save_reels_to_queue"
```

---

## Chunk 3: Hook-Only Reel Support

### Task 7: Update `_build_segments` for hook-only reels + tests

**Files:**
- Modify: `main.py:54-72`
- Create: `tests/test_build_segments.py`
- Modify: `tests/test_segments.py` (add legacy empty body_text test)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_build_segments.py`:

```python
"""Unit tests for _build_segments in main.py."""

import pytest

from renderer.models import RenderRequest


# Import the function under test
from main import _build_segments


class TestBuildSegmentsHookOnly:

    def test_empty_body_text_returns_single_hook_segment(self):
        """When body_text is empty, _build_segments returns 1 segment spanning full duration."""
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            hook_text="Big hook text",
            body_text="",
            record_id="rec123",
            duration_in_seconds=15,
        )
        segments = _build_segments(req)
        assert len(segments) == 1
        assert segments[0]["text"] == "Big hook text"
        assert segments[0]["startSeconds"] == 0.0
        assert segments[0]["endSeconds"] == 15.0
        assert segments[0]["role"] == "hook"

    def test_hook_only_animation_style_preserved(self):
        """Hook-only segment uses the request's animation_style."""
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            hook_text="Hook",
            body_text="",
            record_id="rec123",
            animation_style="slide",
        )
        segments = _build_segments(req)
        assert segments[0]["animationStyle"] == "slide"


class TestBuildSegmentsHookWithText:

    def test_non_empty_body_text_returns_two_segments(self):
        """When body_text has content, _build_segments returns 2 segments split at midpoint."""
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            hook_text="Hook",
            body_text="Body text here",
            record_id="rec123",
            duration_in_seconds=10,
        )
        segments = _build_segments(req)
        assert len(segments) == 2
        assert segments[0]["role"] == "hook"
        assert segments[0]["endSeconds"] == 5.0
        assert segments[1]["role"] == "body"
        assert segments[1]["startSeconds"] == 5.0
        assert segments[1]["endSeconds"] == 10.0

    def test_two_segment_text_content(self):
        """Two-segment mode passes correct text to each segment."""
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            hook_text="My hook",
            body_text="My body",
            record_id="rec123",
        )
        segments = _build_segments(req)
        assert segments[0]["text"] == "My hook"
        assert segments[1]["text"] == "My body"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/test_build_segments.py -v`
Expected: `test_empty_body_text_returns_single_hook_segment` FAILS — currently always returns 2 segments.

- [ ] **Step 3: Update `_build_segments` in `main.py`**

Change lines 54-72 from:
```python
    # Legacy mode: auto-convert hook_text/body_text to 2 equal-duration segments
    duration = request.duration_in_seconds
    mid = duration / 2
    return [
        {
            "text": request.hook_text or "",
            "startSeconds": 0.0,
            "endSeconds": mid,
            "animationStyle": request.animation_style,
            "role": "hook",
        },
        {
            "text": request.body_text or "",
            "startSeconds": mid,
            "endSeconds": float(duration),
            "animationStyle": request.animation_style,
            "role": "body",
        },
    ]
```

To:
```python
    # Legacy mode: auto-convert hook_text/body_text to segments
    duration = request.duration_in_seconds

    # Hook-only reel: single segment spanning full duration
    if not request.body_text:
        return [
            {
                "text": request.hook_text or "",
                "startSeconds": 0.0,
                "endSeconds": float(duration),
                "animationStyle": request.animation_style,
                "role": "hook",
            },
        ]

    # Hook + text reel: two segments split at midpoint
    mid = duration / 2
    return [
        {
            "text": request.hook_text or "",
            "startSeconds": 0.0,
            "endSeconds": mid,
            "animationStyle": request.animation_style,
            "role": "hook",
        },
        {
            "text": request.body_text or "",
            "startSeconds": mid,
            "endSeconds": float(duration),
            "animationStyle": request.animation_style,
            "role": "body",
        },
    ]
```

- [ ] **Step 4: Add hook-only legacy test to `tests/test_segments.py`**

Add to the `TestRenderRequestLegacyMode` class:

```python
    def test_legacy_hook_text_with_empty_body_text_passes(self):
        """RenderRequest with hook_text and empty body_text passes validation (hook-only reel)."""
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            hook_text="Big hook",
            body_text="",
            record_id="recHOOK",
        )
        assert req.hook_text == "Big hook"
        assert req.body_text == ""
        assert req.segments is None
```

- [ ] **Step 5: Run all tests**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_build_segments.py tests/test_segments.py
git commit -m "feat: support hook-only reels — single segment when body_text is empty"
```

---

## Chunk 4: Final Verification

### Task 8: Run full test suite and verify

- [ ] **Step 1: Run the complete test suite**

Run: `cd /Users/openclaw/wandi-agent && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS.

- [ ] **Step 2: Verify SDMF loading works at runtime**

Run: `cd /Users/openclaw/wandi-agent && python -c "import prompts; print(len(prompts.FULL_SYSTEM_PROMPT)); print('SDMF' in prompts.FULL_SYSTEM_PROMPT)"`
Expected: A large number (>5000) and `True`.

- [ ] **Step 3: Verify field mapping is correct by tracing the code path**

Run: `cd /Users/openclaw/wandi-agent && python -c "
from renderer.models import RenderRequest
req = RenderRequest(
    source_video_url='https://example.com/v.mp4',
    hook_text='My hook line',
    body_text='',
    record_id='rec123',
)
from main import _build_segments
segs = _build_segments(req)
print(f'Segments: {len(segs)}')
print(f'Hook text: {segs[0][\"text\"]}')
print(f'Duration: {segs[0][\"endSeconds\"]}')
"`
Expected: `Segments: 1`, `Hook text: My hook line`, `Duration: 15.0`.

- [ ] **Step 4: Final commit with all changes verified**

If any files were modified during verification, commit them. Otherwise, no action needed.
