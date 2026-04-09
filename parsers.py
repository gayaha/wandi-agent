"""Parsers for structured model output.

Contains parse_dicta_response() which converts Dicta's structured-text
output into a dict, and related helpers.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Labels Dicta is instructed to use (UPPERCASE English, easy to parse)
_FIELD_LABELS = {
    "HOOK": "hook",
    "CAPTION": "caption",
    "TEXT_ON_VIDEO": "text_on_video",
    "HOOK_TYPE": "hook_type",
    "CONTENT_TYPE": "content_type",
    "AWARENESS_STAGE": "awareness_stage",
    "MAGNET_ID": "magnet_id",
}


def parse_dicta_response(text: str) -> dict | None:
    """Parse Dicta's structured-text response into a dict.

    Expected input format (one field per line):
        HOOK: בעלי עסקים קטנים, זה ככה...
        CAPTION: בעלי עסקים קטנים, הייתם מעדיפים...
        TEXT_ON_VIDEO: חופש זה לעבוד 140 שעות
        HOOK_TYPE: פרובוקציה
        CONTENT_TYPE: חשיפה
        AWARENESS_STAGE: Unaware

    Returns:
        A dict with snake_case keys, or None if the required field
        'hook' is missing (so the retry mechanism can kick in).

    The parser is lenient:
    - Ignores blank lines and lines without a recognized label
    - Strips whitespace around values
    - Handles optional fields gracefully (missing = None)
    """
    if not text or not text.strip():
        return None

    result: dict[str, str | None] = {
        "hook": None,
        "caption": None,
        "text_on_video": None,
        "hook_type": None,
        "content_type": None,
        "awareness_stage": None,
        "magnet_id": None,
    }

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Try to match LABEL: value
        for label, field in _FIELD_LABELS.items():
            # Match "HOOK:" or "HOOK :" at the start of the line (case-insensitive)
            pattern = rf"^{re.escape(label)}\s*:\s*(.+)$"
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Treat "null", "none", "-", empty as None
                if value.lower() in ("null", "none", "-", ""):
                    result[field] = None
                else:
                    result[field] = value
                break

    # 'hook' is the only required field
    if not result.get("hook"):
        logger.warning(
            f"parse_dicta_response: no HOOK field found in response "
            f"(first 200 chars: {text[:200]})"
        )
        return None

    logger.info(
        f"parse_dicta_response: successfully parsed "
        f"({sum(1 for v in result.values() if v)} fields)"
    )
    return result
