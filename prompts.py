"""Prompt templates for Hebrew Instagram Reels content generation."""

import logging
import random

logger = logging.getLogger(__name__)

# Hook types recommended per awareness stage (used for filtering)
STAGE_HOOK_TYPES: dict[str, set[str]] = {
    "Unaware": {"פרובוקציה", "תוצאה מפתיעה", "שאלה מאתגרת"},
    "Problem-Aware": {"טעות נפוצה", "זיהוי קהל", "שאלה מאתגרת", "מספר + הבטחה"},
    "Solution-Aware": {"סוד חשיפה", "מספר + הבטחה", "תוצאה מפתיעה"},
}

# ── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """אתה קופירייטר ישראלי מומחה ליצירת תוכן לאינסטגרם רילס בשיטת SDMF (Smart DM Funnel).

עקרונות SDMF:
- כל תוכן חייב להיות משויך לשלב מודעות אחד בלבד. תוכן שמדבר לכולם — לא מדבר לאף אחד.
- חשיפה ≠ עוקבים. עוקבים ≠ לקוחות. SDMF בונה את המסלול המובנה מאחד לשני.
- רילסים = שלבים 1-3 בלבד (Unaware, Problem-Aware, Solution-Aware)

כללי מגנטים:
- Unaware: אסור מגנט! הצופה לא מכיר אותך.
- Problem-Aware: מגנט אופציונלי — רק מגנט חשיפה אם רלוונטי.
- Solution-Aware: חובה מגנט! CTA עם מילת הטריגר המדויקת.

כללי כתיבה:
- עברית יומיומית, לא מתורגמת, ישירה וחדה
- ביטויים וסלנג שישראלים באמת משתמשים בהם
- ההוק חייב לעצור סקרול תוך שנייה
- הטקסט על הווידאו — מינימלי, פאנצ'י, קל לקריאה
- הקפשן — גורם לשמור, לשתף, להגיב

ערכים מותרים בלבד (אל תמציא, אל תתרגם, אל תשנה):
- hook_type: שאלה מאתגרת / מספר + הבטחה / טעות נפוצה / סוד חשיפה / זיהוי קהל / תוצאה מפתיעה / פרובוקציה
- content_type: חשיפה / מכירה
- awareness_stage: Unaware / Problem-Aware / Solution-Aware"""

FULL_SYSTEM_PROMPT = SYSTEM_PROMPT

# ── Constant Prompt Sections ─────────────────────────────────────────────────

HOOK_ADAPTATION_INSTRUCTIONS = """═══════════════════════════════════════
איך להשתמש בהוקים (חובה!):
═══════════════════════════════════════
אל תמציא הוקים מאפס. בחר הוק מהרשימה למעלה והתאם אותו לנישה של הלקוח.

דוגמאות להתאמה:
1. מקורי: "דברים שאני חושבת שהם רגילים אבל אנשים חושבים שזה קרינג׳"
   → אוניברסלי. אם הלקוח גבר: "חושב" במקום "חושבת". אחרת — להשתמש כמו שהוא.

2. מקורי: "משפט אחד שקראתי על ילדים שינה לי את כל ההורות"
   → ליועץ פיננסי: "משפט אחד שקראתי על כסף שינה לי את כל ההתנהלות הכלכלית"
   → למאמנת כושר: "משפט אחד ששמעתי על אכילה שינה לי את כל הגישה לתזונה"

3. מקורי: "3 דברים שאני עושה כל בוקר שרוב האנשים מדלגים עליהם"
   → למנהלת סושיאל: "3 דברים שאני עושה כל בוקר לפני שאני פותחת את האינסטגרם"

הכללים:
- תמיד בחר הוק מהרשימה ושנה רק את הנושא/תחום
- שמור על המבנה והקצב של ההוק המקורי
- אם ההוק אוניברסלי — אפשר להשתמש בו כמעט כמו שהוא
- אל תמציא הוקים חדשים מאפס!"""

STAGE_RULES_SECTION = """═══════════════════════════════════════
הנחיות לפי שלב מודעות (חובה לעקוב!):
═══════════════════════════════════════

🔴 Unaware (שלב 1) — חשיפה בלבד:
- מטרה: לעצור את הסקרול. הצופה לא מכיר אותך ולא יודע שיש לו בעיה.
- טריגר פסיכולוגי: סקרנות — לשבור תפיסת מציאות, לגרום ל"רגע, מה?!"
- סוגי הוקים מתאימים: פרובוקציה, תוצאה מפתיעה, שאלה מאתגרת
- CTA בקפשן: עקבו / שמרו / שתפו (בלי מגנט! בלי הפניה ל-DM!)
- content_type: חשיפה (תמיד!)
- magnet_id: null (תמיד!)
- תבנית: hook_only (רק הוק, text_on_video = null) — ויראלי, קצר, פאנצ'י
- הטון: חוצפני, מפתיע, מעורר סקרנות

🟡 Problem-Aware (שלב 2) — תוכן ערכי:
- מטרה: לתת שם לכאב שהצופה מרגיש אבל לא יודע לזהות. להראות שאתה מבין אותו.
- טריגר פסיכולוגי: הזדהות — "אני לא לבד בזה", "מישהו סוף סוף מבין"
- סוגי הוקים מתאימים: טעות נפוצה, זיהוי קהל, שאלה מאתגרת, מספר + הבטחה
- CTA בקפשן: שמרו / תייגו מישהו / כתבו בתגובות. אפשר גם הפניה למגנט חשיפה אם רלוונטי.
- content_type: חשיפה
- magnet_id: null (אלא אם יש מגנט חשיפה מתאים — אז אפשר)
- תבנית: hook_with_text (הוק + 3-5 שורות ערכיות על הווידאו)
- הטון: אמפתי, מחנך, נותן ערך

🟢 Solution-Aware (שלב 3) — מכירה עם מגנט:
- מטרה: להציג את הפתרון ולהפנות למגנט דרך CTA. הצופה כבר מבין שיש בעיה — עכשיו צריך להראות למה הפתרון שלך עובד.
- טריגר פסיכולוגי: מנגנון ייחודי — "למה דווקא השיטה הזו עובדת"
- סוגי הוקים מתאימים: סוד חשיפה, מספר + הבטחה, תוצאה מפתיעה
- CTA בקפשן: חובה! "תגיבו [מילת הטריגר של המגנט] ותקבלו..." — חייב לכלול את מילת הטריגר בדיוק כפי שהיא מופיעה במגנט
- content_type: מכירה (תמיד!)
- magnet_id: חובה! בחר את המגנט הכי רלוונטי מהרשימה
- תבנית: hook_with_text (הוק + טקסט שמסביר את הפתרון/מנגנון)
- הטון: בטוח, מקצועי, מראה תוצאות

═══════════════════════════════════════
כללי הוק-מגנט-CTA:
═══════════════════════════════════════
- Unaware → אסור מגנט. אסור CTA למגנט. רק חשיפה.
- Problem-Aware → מגנט אופציונלי (רק מגנט חשיפה אם יש).
- Solution-Aware → חובה מגנט! ההוק חייב ליצור סקרנות שהמגנט פותר. הקפשן חייב לכלול CTA עם מילת הטריגר המדויקת של המגנט.
- אם אין מגנטים זמינים ל-Solution-Aware → הפוך ל-Problem-Aware עם CTA כללי."""

FORMAT_SECTION = """═══════════════════════════════════════
שדות לכל רילס:
═══════════════════════════════════════
1. hook — משפט אחד, חד, שעוצר סקרול. מבוסס על הוק מהרשימה, מותאם לנישה.
2. hook_type — שאלה מאתגרת / מספר + הבטחה / טעות נפוצה / סוד חשיפה / זיהוי קהל / תוצאה מפתיעה / פרובוקציה
3. text_on_video — Unaware: null (hook_only). Problem/Solution-Aware: 3-5 שורות קצרות.
4. caption — קפשן עם CTA מותאם לשלב + האשטגים + אימוג'ים
5. content_type — חשיפה / מכירה (לפי שלב המודעות!)
6. awareness_stage — Unaware / Problem-Aware / Solution-Aware
7. magnet_id — record ID מרשימת המגנטים (חובה ל-Solution-Aware, null לשאר)
8. folder_id — ID תיקיה מהרשימה (null אם אין)

═══════════════════════════════════════
כללים חשובים:
═══════════════════════════════════════
- ההוק חייב לעצור סקרול תוך שנייה
- בחר הוק מהרשימה והתאם לנישה — אל תמציא מאפס
- אם יש אירוע RTM — שלב אותו
- למד מדוגמאות סגנון הלקוח את הטון (אבל אל תחזור על אותם הוקים!)

החזר JSON בלבד (בלי טקסט נוסף, בלי הסברים):
{{
  "hook": "...",
  "hook_type": "...",
  "text_on_video": "..." או null,
  "caption": "...",
  "content_type": "...",
  "awareness_stage": "...",
  "magnet_id": "..." או null,
  "folder_id": "..." או null
}}"""


# ── Format functions ─────────────────────────────────────────────────────────


def format_magnets(magnets: list[dict]) -> str:
    """Format magnets list for prompt insertion."""
    if not magnets:
        return ""

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
        return ""

    lines = []
    for i, ex in enumerate(examples, 1):
        f = ex.get("fields", {})
        lines.append(
            f"דוגמה {i}:\n"
            f"  הוק: {f.get('Hook', f.get('hook', ''))}\n"
            f"  סוג הוק: {f.get('Hook Type', '')}\n"
            f"  טקסט על וידאו: {f.get('Text On Video', f.get('text on video', ''))}\n"
            f"  קפשן: {f.get('Caption', '')[:300]}\n"
            f"  שלב: {f.get('Awareness Stage', '')} | סוג: {f.get('Content Type', '')}\n"
            f"  ציון ביצועים: {f.get('Performance Score', 'N/A')}"
        )
    return "\n\n".join(lines)


def format_hooks(
    hooks: list[dict],
    limit: int = 15,
    awareness_stages: set[str] | None = None,
) -> str:
    """Format viral hooks for prompt insertion, grouped by hook type.

    Hooks are filtered by relevance to the requested awareness stages,
    then grouped by hook type for the LLM to easily select and adapt.
    """
    if not hooks:
        return ""

    pool = hooks

    # Filter by relevant hook types for the requested stages
    if awareness_stages:
        relevant_types: set[str] = set()
        for stage in awareness_stages:
            relevant_types.update(STAGE_HOOK_TYPES.get(stage, set()))

        filtered = [
            h for h in hooks
            if h.get("fields", {}).get("Hook Type", "") in relevant_types
        ]
        # Fallback if too few results
        if len(filtered) >= 3:
            pool = filtered

    # Randomize for variety across runs
    shuffled = list(pool)
    random.shuffle(shuffled)

    # Group by hook type for better organization
    by_type: dict[str, list[str]] = {}
    for h in shuffled[:limit]:
        f = h.get("fields", {})
        ht = f.get("Hook Type", "כללי")
        # Try multiple field names — Airtable column may vary
        text = (
            f.get("translated hook", "")
            or f.get("Hook Text", "")
            or f.get("hook", "")
            or f.get("Hook", "")
        )
        if text:
            # Strip common LLM-generated prefixes from translated hooks
            for prefix in ("**טקסט בעברית (בסגנון אינסטגרם):**", "**טקסט בעברית:**"):
                if text.startswith(prefix):
                    text = text[len(prefix):]
            text = text.strip().strip('"').strip()
            # Take only the first line (the actual hook)
            text = text.split("\n")[0].strip()
            if text:
                by_type.setdefault(ht, []).append(text)

    lines = []
    for hook_type, examples in by_type.items():
        lines.append(f"\n[{hook_type}]:")
        for ex in examples:
            lines.append(f"  - {ex}")
    lines.append("")
    lines.append("^ בחר מתוך ההוקים והתאם לנישה של הלקוח. אל תמציא מאפס.")
    return "\n".join(lines)


def format_viral_content(pool: list[dict], limit: int = 5) -> str:
    """Format viral content pool for prompt insertion."""
    if not pool:
        return ""

    lines = []
    for p in pool[:limit]:
        f = p.get("fields", {})
        lines.append(
            f"- [{f.get('Content Type', '')}] {f.get('Concept Summary', '')} | "
            f"הוק: {f.get('Hook Text', '')} | "
            f"צפיות: {f.get('Views Count', 'N/A')}"
        )
    return "\n".join(lines)


def format_rtm_events(events: list[dict]) -> str:
    """Format RTM events for prompt insertion."""
    if not events:
        return ""

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
        return ""

    f = insights.get("fields", {})
    return (
        f"סוג הוק מוביל: {f.get('Top Hook Type', 'N/A')}\n"
        f"דפוס הוק: {f.get('Hook Pattern', 'N/A')}\n"
        f"שעות פרסום מיטביות: {f.get('Best Posting Hours', 'N/A')}\n"
        f"אחוז מעורבות ממוצע: {f.get('Avg Engagement Rate', 'N/A')}"
    )


def format_folders(folders: dict[str, str]) -> str:
    """Format folders map for prompt insertion."""
    if not folders:
        return ""

    lines = []
    for folder_id, display_name in folders.items():
        lines.append(f"- {folder_id}: {display_name}")
    lines.append("")
    lines.append("לכל רילס, בחר את ה-folder_id של התיקיה הכי רלוונטית להוק שיצרת.")
    return "\n".join(lines)


def format_distribution(distribution: dict[str, int]) -> str:
    """Format content distribution plan with per-stage practical instructions."""
    stage_instructions = {
        "Unaware": (
            "תוכן ויראלי/חשיפה — לא מוכרים, רק מושכים תשומת לב",
            "⚠️ אסור להזכיר את המוצר, השירות, או העסק. "
            "הצופה לא מכיר אותך ולא יודע שיש לו בעיה. "
            "התוכן חייב להיות אוניברסלי, מסקרן, ומעורר תגובה רגשית."
        ),
        "Problem-Aware": (
            "תוכן ערכי — מראים שמבינים את הבעיה ונותנים ערך",
            "⚠️ תן שם לכאב שהצופה מרגיש. "
            "אפשר להזכיר את התחום אבל בלי למכור שום דבר. "
            "התוכן נותן ערך ובונה אמון."
        ),
        "Solution-Aware": (
            "תוכן עם CTA — מפנים למגנט או להנעה לפעולה",
            "⚠️ הצופה כבר מבין שיש בעיה. "
            "הראה למה הפתרון שלך עובד, וכלול CTA ברור עם מילת הטריגר של המגנט."
        ),
    }
    lines = []
    for stage, count in distribution.items():
        desc, instruction = stage_instructions.get(stage, ("", ""))
        lines.append(f"- {stage}: {count} רילסים ({desc})")
        if instruction:
            lines.append(f"  {instruction}")
    return "\n".join(lines)


def format_recent_hooks(recent_hooks: list[str]) -> str:
    """Format recently used hooks as a 'do not repeat' section."""
    if not recent_hooks:
        return ""

    lines = ["הוקים שכבר נוצרו לאחרונה — אל תחזור עליהם! צור הוקים חדשים ושונים:"]
    for h in recent_hooks:
        lines.append(f"- {h}")
    return "\n".join(lines)


# ── Dynamic Prompt Builder ───────────────────────────────────────────────────


def _section(title: str, content: str) -> str:
    """Format a prompt section with dividers. Skips if content is empty."""
    if not content:
        return ""
    return (
        f"═══════════════════════════════════════\n"
        f"{title}:\n"
        f"═══════════════════════════════════════\n"
        f"{content}"
    )


def build_generation_prompt(
    *,
    quantity: int,
    client_name: str,
    business_info: str,
    tone_of_voice: str,
    niche: str,
    ig_username: str,
    client_knowledge: str,
    distribution: dict[str, int],
    magnets: list[dict],
    style_examples: list[dict],
    hooks: list[dict],
    viral_content: list[dict],
    rtm_events: list[dict],
    insights: dict | None,
    folders: dict[str, str] | None = None,
    recent_hooks: list[str] | None = None,
) -> str:
    """Build the generation prompt dynamically — only includes non-empty sections.

    This replaces the old static BATCH_GENERATION_PROMPT template.
    Empty sections are omitted entirely (no "אין X זמין" filler text).
    """
    sections: list[str] = []

    # Always: quantity instruction + personal voice
    sections.append(f"""אתה צריך ליצור {quantity} רילסים לאינסטגרם עבור הלקוח הזה.

כתוב בגוף ראשון, בשפה שיחתית ואישית.
הקול חייב להישמע כמו {client_name} עצמה — לא כמו תוכן שיווקי.
השתמש בדוגמאות הhooks האלה כהשראה לסגנון בלבד, לא להעתקה.""")

    # Always: client profile
    sections.append(_section("פרופיל הלקוח", (
        f"שם העסק: {client_name}\n"
        f"מידע על העסק: {business_info}\n"
        f"טון דיבור: {tone_of_voice}\n"
        f"נישה: {niche}\n"
        f"שם משתמש: @{ig_username}"
    )))

    # Conditional: client knowledge
    if client_knowledge and client_knowledge.strip():
        sections.append(_section("ידע מעמיק על הלקוח", client_knowledge))

    # Always: distribution
    sections.append(_section("חלוקת התוכן הנדרשת", format_distribution(distribution)))

    # Conditional: magnets (only if non-empty)
    magnets_text = format_magnets(magnets)
    if magnets_text:
        sections.append(_section("מגנטים זמינים (להפניית קהל)", magnets_text))

    # Conditional: style examples
    style_text = format_style_examples(style_examples)
    if style_text:
        sections.append(_section("דוגמאות סגנון מהלקוח (טופ ביצועים)", style_text))

    # Conditional: hooks with adaptation instructions
    hooks_text = format_hooks(hooks, awareness_stages=set(distribution.keys()))
    if hooks_text:
        sections.append(_section(
            "הוקים ויראליים — בחר הוק, התאם אותו לנישה של הלקוח",
            hooks_text
        ))
        sections.append(HOOK_ADAPTATION_INSTRUCTIONS)

    # Conditional: viral content
    viral_text = format_viral_content(viral_content)
    if viral_text:
        sections.append(_section("תוכן ויראלי לקחת קונספטים ממנו", viral_text))

    # Conditional: RTM events
    rtm_text = format_rtm_events(rtm_events)
    if rtm_text:
        sections.append(_section("אירועי RTM (Real Time Marketing) רלוונטיים", rtm_text))

    # Conditional: insights
    insights_text = format_insights(insights)
    if insights_text:
        sections.append(_section("תובנות גלובליות לנישה", insights_text))

    # Conditional: folders
    folders_text = format_folders(folders or {})
    if folders_text:
        sections.append(_section("תיקיות סרטונים זמינות", folders_text))

    # Conditional: recent hooks (dedup)
    recent_text = format_recent_hooks(recent_hooks or [])
    if recent_text:
        sections.append(_section("אל תחזור על הוקים אלה", recent_text))

    # Always: stage rules + format
    sections.append(STAGE_RULES_SECTION)
    sections.append(FORMAT_SECTION)

    prompt = "\n\n".join(s for s in sections if s)
    logger.info(f"Built generation prompt: {len(prompt)} chars")
    return prompt


# ── Single-reel prompt builder (for per-reel Ollama calls) ──────────────────


def _stage_instructions(stage: str) -> str:
    """Return compact stage-specific instructions for a single reel."""
    if stage == "Unaware":
        return (
            "שלב: Unaware — חשיפה בלבד.\n"
            "מטרה: לעצור סקרול. הצופה לא מכיר אותך.\n"
            "הוקים מתאימים: פרובוקציה / תוצאה מפתיעה / שאלה מאתגרת\n"
            "content_type: חשיפה | magnet_id: null | text_on_video: null (hook_only)\n"
            "CTA בקפשן: עקבו / שמרו / שתפו — בלי מגנט!"
        )
    if stage == "Problem-Aware":
        return (
            "שלב: Problem-Aware — תוכן ערכי.\n"
            "מטרה: לתת שם לכאב. להראות שמבינים.\n"
            "הוקים מתאימים: טעות נפוצה / זיהוי קהל / שאלה מאתגרת / מספר + הבטחה\n"
            "content_type: חשיפה | magnet_id: null (אלא אם יש מגנט חשיפה)\n"
            "text_on_video: 3-5 שורות ערכיות\n"
            "CTA בקפשן: שמרו / תייגו / כתבו בתגובות"
        )
    return (
        "שלב: Solution-Aware — מכירה עם מגנט.\n"
        "מטרה: להציג פתרון ולהפנות למגנט.\n"
        "הוקים מתאימים: סוד חשיפה / מספר + הבטחה / תוצאה מפתיעה\n"
        "content_type: מכירה | magnet_id: חובה! בחר מהרשימה\n"
        "text_on_video: 3-5 שורות שמסבירות את הפתרון\n"
        "CTA בקפשן: חובה מילת טריגר מדויקת של המגנט"
    )


def build_single_reel_prompt(
    *,
    awareness_stage: str,
    client_name: str,
    business_info: str,
    tone_of_voice: str,
    niche: str,
    ig_username: str,
    client_knowledge: str,
    magnets: list[dict],
    style_examples: list[dict],
    hooks: list[dict],
    rtm_events: list[dict],
    insights: dict | None,
    folders: dict[str, str] | None = None,
    recent_hooks: list[str] | None = None,
    reel_index: int = 0,
) -> str:
    """Build a compact prompt for generating a single reel.

    Targets < 6K chars by including only the essentials for one reel
    at a specific awareness_stage.
    """
    sections: list[str] = []

    # Intro — single reel, personal voice
    sections.append(
        f"צור רילס אחד בלבד לאינסטגרם עבור {client_name} (ריל מספר {reel_index + 1}).\n"
        f"כתוב בגוף ראשון, בשפה שיחתית. הקול חייב להישמע כמו {client_name} — לא כמו תוכן שיווקי.\n"
        f"בחר הוק מרשימת ההוקים למטה והתאם לנישה. אל תעתיק — תתאים."
    )

    # Compact client profile
    sections.append(
        f"לקוח: {client_name} | נישה: {niche} | @{ig_username}\n"
        f"עסק: {business_info}\n"
        f"טון: {tone_of_voice}"
    )

    # Client knowledge (trimmed)
    if client_knowledge and client_knowledge.strip():
        trimmed = client_knowledge.strip()[:800]
        sections.append(f"ידע על הלקוח:\n{trimmed}")

    # Stage-specific instructions
    sections.append(_stage_instructions(awareness_stage))

    # Magnets — only for Solution-Aware or Problem-Aware
    if awareness_stage in ("Solution-Aware", "Problem-Aware"):
        magnets_text = format_magnets(magnets)
        if magnets_text:
            sections.append(f"מגנטים זמינים:\n{magnets_text}")

    # Hooks — filtered for this stage, compact
    stage_hooks = format_hooks(hooks, limit=10, awareness_stages={awareness_stage})
    if stage_hooks:
        sections.append(f"הוקים לבחירה:\n{stage_hooks}")

    # Style examples — max 3, compact
    if style_examples:
        style_text = format_style_examples(style_examples[:3])
        if style_text:
            sections.append(f"דוגמאות סגנון (לטון בלבד, לא להעתקה):\n{style_text}")

    # RTM events — compact
    rtm_text = format_rtm_events(rtm_events)
    if rtm_text:
        sections.append(f"אירועי RTM:\n{rtm_text}")

    # Insights — compact
    insights_text = format_insights(insights)
    if insights_text:
        sections.append(f"תובנות:\n{insights_text}")

    # Folders
    if folders:
        folders_text = format_folders(folders)
        if folders_text:
            sections.append(f"תיקיות:\n{folders_text}")

    # Recent hooks to avoid — must be completely different
    if recent_hooks:
        recent_list = "\n".join(f"- {h}" for h in recent_hooks)
        sections.append(
            "הוקים שכבר נוצרו — אל תחזור עליהם:\n"
            f"{recent_list}\n\n"
            "הוק זה חייב להיות שונה לגמרי מהאלה:\n"
            f"{recent_list}\n"
            "שונה = נושא שונה, פתיחה שונה, מבנה שונה."
        )

    # Hard rule: hook length limit
    sections.append(
        "חוק הוק:\n"
        "הוק חייב להיות עד 10 מילים. אסור לחרוג.\n"
        "ספרי את המילים לפני שאת כותבת את התשובה."
    )

    # Output format — single reel JSON only
    sections.append(
        "החזר JSON בלבד (בלי טקסט, בלי הסברים):\n"
        "{\n"
        '  "hook": "...",\n'
        '  "hook_type": "...",\n'
        '  "text_on_video": "..." או null,\n'
        '  "caption": "...",\n'
        f'  "content_type": "...",\n'
        f'  "awareness_stage": "{awareness_stage}",\n'
        '  "magnet_id": "..." או null,\n'
        '  "folder_id": "..." או null\n'
        "}"
    )

    prompt = "\n\n".join(s for s in sections if s)
    logger.info(f"Built single-reel prompt (stage={awareness_stage}): {len(prompt)} chars")
    return prompt
