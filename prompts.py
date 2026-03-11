"""Prompt templates for Hebrew Instagram Reels content generation."""

SYSTEM_PROMPT = """אתה קופירייטר ישראלי מומחה ליצירת תוכן לאינסטגרם רילס.
אתה כותב בעברית ישראלית טבעית ואותנטית — לא עברית מתורגמת, לא עברית ספרותית.
אתה כותב כמו שישראלי באמת מדבר: ישיר, חד, עם אנרגיה.

כללים קריטיים:
- כתוב בעברית ישראלית יומיומית, לא מתורגמת
- השתמש בביטויים ובסלנג שישראלים באמת משתמשים בהם
- תהיה ישיר וחד — בלי מילים מיותרות
- ההוק חייב לעצור את הסקרול תוך שנייה
- הטקסט על הווידאו חייב להיות קצר ופאנצ'י
- התסריט המילולי צריך להישמע טבעי כשמישהו אומר אותו למצלמה
- הקפשן צריך לגרום לאנשים לשמור, לשתף, ולהגיב"""

BATCH_GENERATION_PROMPT = """אתה צריך ליצור {quantity} רילסים לאינסטגרם עבור הלקוח הזה.

═══════════════════════════════════════
פרופיל הלקוח:
═══════════════════════════════════════
שם העסק: {client_name}
מידע על העסק: {business_info}
טון דיבור: {tone_of_voice}
נישה: {niche}
שם משתמש: @{ig_username}

═══════════════════════════════════════
חלוקת התוכן הנדרשת:
═══════════════════════════════════════
{distribution_text}

═══════════════════════════════════════
מגנטים זמינים (להפניית קהל):
═══════════════════════════════════════
{magnets_text}

═══════════════════════════════════════
דוגמאות סגנון מהלקוח (טופ ביצועים):
═══════════════════════════════════════
{style_examples_text}

═══════════════════════════════════════
הוקים ויראליים לקחת השראה מהם:
═══════════════════════════════════════
{hooks_text}

═══════════════════════════════════════
תוכן ויראלי לקחת קונספטים ממנו:
═══════════════════════════════════════
{viral_content_text}

═══════════════════════════════════════
אירועי RTM (Real Time Marketing) רלוונטיים:
═══════════════════════════════════════
{rtm_text}

═══════════════════════════════════════
תובנות גלובליות לנישה:
═══════════════════════════════════════
{insights_text}

═══════════════════════════════════════
תיקיות סרטונים זמינות (בחר תיקיה רלוונטית לכל רילס):
═══════════════════════════════════════
{folders_text}

═══════════════════════════════════════
הנחיות ליצירת כל רילס:
═══════════════════════════════════════

לכל רילס צור את השדות הבאים:
1. hook — משפט הוק אחד, חד ומושך, שעוצר את הסקרול. השתמש בסוג ההוק המתאים.
2. hook_type — אחד מ: שאלה מאתגרת / מספר + הבטחה / טעות נפוצה / סוד חשיפה / זיהוי קהל / תוצאה מפתיעה / פרובוקציה
3. text_on_video — טקסט קצר ופאנצ'י שמופיע על הווידאו (3-5 שורות קצרות מקסימום)
4. verbal_script — תסריט מילולי מלא שאדם אומר למצלמה (30-60 שניות). צריך להישמע טבעי, כאילו מישהו מדבר לחבר.
5. caption — קפשן לאינסטגרם עם CTA, האשטגים רלוונטיים, ואימוג'ים. אם יש מגנט מתאים — הוסף CTA עם מילת הטריגר.
6. format — אחד מ: talking_head / b_roll / text_animation / mixed
7. content_type — חשיפה או מכירה
8. awareness_stage — Unaware / Problem-Aware / Solution-Aware
9. magnet_id — ה-record ID של המגנט המתאים (אם רלוונטי, אחרת null)
10. folder_id — ה-ID של התיקיה הכי רלוונטית להוק מרשימת התיקיות הזמינות (אם אין תיקיות — null). נסה לגוון בין התיקיות ולא לבחור באותה תיקיה כל הזמן.

חשוב:
- כל רילס צריך להיות שונה ומגוון
- ההוק הוא הדבר הכי חשוב — הוא חייב לעצור את הסקרול
- הטקסט על הווידאו צריך להיות מינימלי וחד
- התסריט המילולי צריך להישמע כמו שיחה טבעית
- לרילס של Solution-Aware — חייב להיות CTA עם מגנט
- אם יש אירוע RTM רלוונטי — שלב אותו באחד הרילסים לפחות
- השתמש בתובנות הגלובליות כדי לבחור סוגי הוק ופורמטים שעובדים בנישה

החזר JSON בפורמט הבא בלבד (בלי טקסט נוסף):
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
}}"""


def format_magnets(magnets: list[dict]) -> str:
    """Format magnets list for prompt insertion."""
    if not magnets:
        return "אין מגנטים זמינים כרגע."

    lines = []
    for m in magnets:
        f = m.get("fields", {})
        lines.append(
            f"- [{m['id']}] {f.get('Magnet Name', 'ללא שם')}: "
            f"{f.get('Description', '')} | "
            f"מילת טריגר: {f.get('Trigger Word', 'אין')} | "
            f"שלב מודעות: {f.get('Awareness Stage', 'לא הוגדר')} | "
            f"הבטחה: {f.get('הבטחה', '')} | "
            f"פנייה: {f.get('פנייה', '')}"
        )
    return "\n".join(lines)


def format_style_examples(examples: list[dict]) -> str:
    """Format style bank examples for prompt insertion."""
    if not examples:
        return "אין דוגמאות סגנון עדיין (לקוח חדש). צור תוכן באיכות גבוהה שמתאים לטון הדיבור של הלקוח."

    lines = []
    for i, ex in enumerate(examples, 1):
        f = ex.get("fields", {})
        lines.append(
            f"דוגמה {i}:\n"
            f"  הוק: {f.get('Hook Type', '')}\n"
            f"  טקסט על וידאו: {f.get('Text On Video', '')}\n"
            f"  תסריט: {f.get('Verbal Script', '')[:200]}...\n"
            f"  קפשן: {f.get('Caption', '')[:200]}...\n"
            f"  פורמט: {f.get('Format', '')} | שלב: {f.get('Awareness Stage', '')}\n"
            f"  ציון ביצועים: {f.get('Performance Score', 'N/A')}"
        )
    return "\n\n".join(lines)


def format_hooks(hooks: list[dict], limit: int = 10) -> str:
    """Format viral hooks for prompt insertion."""
    if not hooks:
        return "אין הוקים ויראליים זמינים. צור הוקים מקוריים."

    lines = []
    for h in hooks[:limit]:
        f = h.get("fields", {})
        lines.append(
            f"- [{f.get('Hook Type', '')}] {f.get('translated hook', '')}"
        )
    return "\n".join(lines)


def format_viral_content(pool: list[dict], limit: int = 5) -> str:
    """Format viral content pool for prompt insertion."""
    if not pool:
        return "אין תוכן ויראלי זמין כרגע."

    lines = []
    for p in pool[:limit]:
        f = p.get("fields", {})
        lines.append(
            f"- [{f.get('Content Type', '')}] {f.get('Concept Summary', '')} | "
            f"הוק: {f.get('Hook Text', '')} | "
            f"פורמט: {f.get('Format', '')} | "
            f"צפיות: {f.get('Views Count', 'N/A')}"
        )
    return "\n".join(lines)


def format_rtm_events(events: list[dict]) -> str:
    """Format RTM events for prompt insertion."""
    if not events:
        return "אין אירועי RTM רלוונטיים כרגע."

    lines = []
    for e in events:
        f = e.get("fields", {})
        lines.append(
            f"- {f.get('Event Name', '')}: {f.get('Event Description', '')} "
            f"(פג תוקף: {f.get('Expires At', 'לא הוגדר')})"
        )
    return "\n".join(lines)


def format_insights(insights: dict | None) -> str:
    """Format global insights for prompt insertion."""
    if not insights:
        return "אין תובנות גלובליות זמינות לנישה זו."

    f = insights.get("fields", {})
    return (
        f"סוג הוק מוביל: {f.get('Top Hook Type', 'N/A')}\n"
        f"פורמט מוביל: {f.get('Top Format', 'N/A')}\n"
        f"דפוס הוק: {f.get('Hook Pattern', 'N/A')}\n"
        f"שעות פרסום מיטביות: {f.get('Best Posting Hours', 'N/A')}\n"
        f"אחוז מעורבות ממוצע: {f.get('Avg Engagement Rate', 'N/A')}"
    )


def format_folders(folders: dict[str, str]) -> str:
    """Format folders map for prompt insertion."""
    if not folders:
        return "אין תיקיות סרטונים זמינות. החזר null בשדה folder_id."

    lines = []
    for folder_id, display_name in folders.items():
        lines.append(f"- {folder_id}: {display_name}")
    lines.append("")
    lines.append("לכל רילס, בחר את ה-folder_id של התיקיה הכי רלוונטית להוק שיצרת.")
    return "\n".join(lines)


def format_distribution(distribution: dict[str, int]) -> str:
    """Format content distribution plan for prompt insertion."""
    lines = []
    for stage, count in distribution.items():
        description = {
            "Unaware": "תוכן ויראלי/חשיפה — לא מוכרים, רק מושכים תשומת לב",
            "Problem-Aware": "תוכן ערכי — מראים שמבינים את הבעיה ונותנים ערך",
            "Solution-Aware": "תוכן עם CTA — מפנים למגנט או להנעה לפעולה",
        }.get(stage, "")
        lines.append(f"- {stage}: {count} רילסים ({description})")
    return "\n".join(lines)


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
