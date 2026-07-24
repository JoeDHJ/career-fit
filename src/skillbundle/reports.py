"""Human-readable Career Fit action-plan exports."""

from __future__ import annotations

from html import escape
from importlib.resources import as_file, files
from io import BytesIO
from typing import Any


def _text(value: object, limit: int = 800) -> str:
    return " ".join(str(value or "").replace("\x00", "").split())[:limit]


def _items(analysis: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = analysis.get(key, [])
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def build_markdown_plan(analysis: dict[str, Any]) -> str:
    """Create a compact report that keeps evidence, gates, and actions distinct."""

    summary = (
        analysis.get("summary", {}) if isinstance(analysis.get("summary"), dict) else {}
    )
    lines = [
        "# Career Fit application plan",
        "",
        "This plan supports job-search preparation. It is not a hiring prediction.",
        "",
        "## Current decision",
        "",
        _text(summary.get("decision_label"), 600)
        or "Review the current evidence before relying on a result.",
        "",
        f"- Review status: {_text(summary.get('review_status')) or 'not confirmed'}",
        f"- Eligibility status: {_text(summary.get('eligibility_status')) or 'not available'}",
        f"- Requirements identified: {_text(summary.get('requirements_identified')) or _text(summary.get('requirement_count')) or 'not available'}",
        "",
        "## Next actions",
        "",
    ]
    actions = _items(analysis, "next_actions")
    if actions:
        for index, action in enumerate(actions[:6], start=1):
            lines.extend(
                [
                    f"{index}. {_text(action.get('action'), 600) or 'Review this item.'}",
                    f"   - Why: {_text(action.get('basis'), 500) or 'Based on the supplied role and evidence.'}",
                    f"   - Useful artifact: {_text(action.get('expected_artifact'), 400) or 'A clear, reviewable example.'}",
                ]
            )
    else:
        lines.append(
            "- No next action was generated. Recheck the reviewed requirements and evidence."
        )
    lines.extend(["", "## Evidence and eligibility to verify", ""])
    requirements = _items(analysis, "requirements")
    if requirements:
        for item in requirements[:20]:
            label = _text(item.get("canonical_skill") or item.get("original_text"), 180)
            status = _text(item.get("status_label") or item.get("status"), 100)
            importance = _text(item.get("importance_level"), 100).replace("_", " ")
            lines.append(
                f"- {label or 'Requirement'}: {status or 'needs review'} ({importance or 'importance not set'})"
            )
    else:
        lines.append("- No reviewed requirements are available yet.")
    gates = _items(analysis, "hard_constraints")
    if gates:
        lines.extend(["", "## Eligibility gates", ""])
        for gate in gates[:12]:
            lines.append(
                f"- {_text(gate.get('canonical_skill') or gate.get('original_text'), 180)}: "
                f"{_text(gate.get('status_label') or gate.get('status'), 100) or 'verify'}"
            )
    lines.extend(
        [
            "",
            "## How to use this plan",
            "",
            "Confirm that the posting was extracted correctly, keep proof separate from self-reported claims, and verify any eligibility requirement with the employer or your own records.",
        ]
    )
    return "\n".join(lines) + "\n"


_ARABIC_FORMS = {
    "ء": ("ﺀ", None, None, None),
    "آ": ("ﺁ", "ﺂ", None, None),
    "أ": ("ﺃ", "ﺄ", None, None),
    "ؤ": ("ﺅ", "ﺆ", None, None),
    "إ": ("ﺇ", "ﺈ", None, None),
    "ئ": ("ﺉ", "ﺊ", "ﺋ", "ﺌ"),
    "ا": ("ﺍ", "ﺎ", None, None),
    "ب": ("ﺏ", "ﺐ", "ﺑ", "ﺒ"),
    "ة": ("ﺓ", "ﺔ", None, None),
    "ت": ("ﺕ", "ﺖ", "ﺗ", "ﺘ"),
    "ث": ("ﺙ", "ﺚ", "ﺛ", "ﺜ"),
    "ج": ("ﺝ", "ﺞ", "ﺟ", "ﺠ"),
    "ح": ("ﺡ", "ﺢ", "ﺣ", "ﺤ"),
    "خ": ("ﺥ", "ﺦ", "ﺧ", "ﺨ"),
    "د": ("ﺩ", "ﺪ", None, None),
    "ذ": ("ﺫ", "ﺬ", None, None),
    "ر": ("ﺭ", "ﺮ", None, None),
    "ز": ("ﺯ", "ﺰ", None, None),
    "س": ("ﺱ", "ﺲ", "ﺳ", "ﺴ"),
    "ش": ("ﺵ", "ﺶ", "ﺷ", "ﺸ"),
    "ص": ("ﺹ", "ﺺ", "ﺻ", "ﺼ"),
    "ض": ("ﺽ", "ﺾ", "ﺿ", "ﻀ"),
    "ط": ("ﻁ", "ﻂ", "ﻃ", "ﻄ"),
    "ظ": ("ﻅ", "ﻆ", "ﻇ", "ﻈ"),
    "ع": ("ﻉ", "ﻊ", "ﻋ", "ﻌ"),
    "غ": ("ﻍ", "ﻎ", "ﻏ", "ﻐ"),
    "ف": ("ﻑ", "ﻒ", "ﻓ", "ﻔ"),
    "ق": ("ﻕ", "ﻖ", "ﻗ", "ﻘ"),
    "ك": ("ﻙ", "ﻚ", "ﻛ", "ﻜ"),
    "ل": ("ﻝ", "ﻞ", "ﻟ", "ﻠ"),
    "م": ("ﻡ", "ﻢ", "ﻣ", "ﻤ"),
    "ن": ("ﻥ", "ﻦ", "ﻧ", "ﻨ"),
    "ه": ("ﻩ", "ﻪ", "ﻫ", "ﻬ"),
    "و": ("ﻭ", "ﻮ", None, None),
    "ى": ("ﻯ", "ﻰ", None, None),
    "ي": ("ﻱ", "ﻲ", "ﻳ", "ﻴ"),
    "پ": ("ﭖ", "ﭗ", "ﭘ", "ﭙ"),
    "چ": ("ﭺ", "ﭻ", "ﭼ", "ﭽ"),
    "ژ": ("ﮊ", "ﮋ", None, None),
    "گ": ("ﮒ", "ﮓ", "ﮔ", "ﮕ"),
}


def _unicode_font() -> str:
    """Register the bundled open font used for Cyrillic and Arabic PDF text."""

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "CareerFitUnicode"
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    font_resource = files("skillbundle.resources").joinpath("DejaVuSans.ttf")
    with as_file(font_resource) as path:
        pdfmetrics.registerFont(TTFont(font_name, str(path)))
    return font_name


def _cjk_font() -> str:
    """Register ReportLab's CID font for Chinese text without host font lookup."""

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    font_name = "STSong-Light"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    return font_name


def _shape_arabic_run(value: str) -> str:
    """Use Arabic presentation forms for ReportLab's non-shaping text engine."""

    characters = list(value)
    shaped: list[str] = []
    for index, character in enumerate(characters):
        forms = _ARABIC_FORMS.get(character)
        if forms is None:
            shaped.append(character)
            continue
        previous = _ARABIC_FORMS.get(characters[index - 1]) if index else None
        following = (
            _ARABIC_FORMS.get(characters[index + 1])
            if index + 1 < len(characters)
            else None
        )
        joins_previous = bool(previous and previous[2] and forms[1])
        joins_following = bool(following and forms[2] and following[1])
        shaped.append(
            forms[3]
            if joins_previous and joins_following
            else forms[1]
            if joins_previous
            else forms[2]
            if joins_following
            else forms[0]
        )
    return "".join(reversed(shaped))


def _prepare_pdf_text(value: str, unicode_font_available: bool) -> str:
    """Keep multilingual PDF text readable and make unsupported symbols explicit."""

    result: list[str] = []
    arabic_run: list[str] = []

    def flush_arabic() -> None:
        if arabic_run:
            result.append(_shape_arabic_run("".join(arabic_run)))
            arabic_run.clear()

    for character in value:
        if character in _ARABIC_FORMS:
            arabic_run.append(character)
            continue
        flush_arabic()
        if ord(character) > 0xFFFF:
            result.append(f"[symbol U+{ord(character):04X}]")
        elif unicode_font_available or ord(character) < 128:
            result.append(character)
        else:
            result.append(f"[U+{ord(character):04X}]")
    flush_arabic()
    return "".join(result)


def _is_cjk(character: str) -> bool:
    point = ord(character)
    return (
        0x3400 <= point <= 0x4DBF
        or 0x4E00 <= point <= 0x9FFF
        or 0xF900 <= point <= 0xFAFF
        or 0x3000 <= point <= 0x303F
        or 0xFF00 <= point <= 0xFFEF
    )


def _pdf_markup(value: str, cjk_font_available: bool) -> str:
    """Escape text and apply the bundled/CID fallback font per script run."""

    prepared = _prepare_pdf_text(value, True)
    if not cjk_font_available:
        return escape(prepared)
    output: list[str] = []
    run: list[str] = []
    cjk_run = False

    def flush() -> None:
        if run:
            escaped = escape("".join(run))
            output.append(
                f'<font name="STSong-Light">{escaped}</font>' if cjk_run else escaped
            )
            run.clear()

    for character in prepared:
        is_cjk = _is_cjk(character)
        if run and is_cjk != cjk_run:
            flush()
        cjk_run = is_cjk
        run.append(character)
    flush()
    return "".join(output)


def _pdf_font(markdown: str) -> tuple[str, bool]:
    if not any(ord(character) > 127 for character in markdown):
        return "Helvetica", False
    font = _unicode_font()
    cjk_font_available = any(_is_cjk(character) for character in markdown)
    if cjk_font_available:
        _cjk_font()
    return font, cjk_font_available


def build_pdf_plan(analysis: dict[str, Any]) -> bytes:
    """Render the Markdown plan as a compact, portable PDF."""

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    markdown = build_markdown_plan(analysis)
    font, unicode_font_available = _pdf_font(markdown)
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "CareerFitTitle",
        parent=styles["Title"],
        fontName=font,
        fontSize=20,
        leading=25,
        textColor=colors.HexColor("#153b62"),
        spaceAfter=12,
    )
    heading = ParagraphStyle(
        "CareerFitHeading",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#153b62"),
        spaceBefore=11,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "CareerFitBody",
        parent=styles["BodyText"],
        fontName=font,
        fontSize=9.5,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Career Fit application plan",
        author="Career Fit",
    )
    story = []
    for line in markdown.splitlines():
        clean = _pdf_markup(line, unicode_font_available)
        if line.startswith("# "):
            story.append(Paragraph(clean[2:], title))
        elif line.startswith("## "):
            story.append(Paragraph(clean[3:], heading))
        elif not line:
            story.append(Spacer(1, 3))
        else:
            story.append(Paragraph(clean.replace("  ", "&nbsp; "), body))
    document.build(story)
    return output.getvalue()
