"""PDF export of collections and libraries using ReportLab.

Built-in PDF fonts (Helvetica) are used so no font files need to be shipped.
They cover Latin-1/Windows-1252 characters; scripts outside that range (e.g.
Chinese, Arabic) are not rendered correctly - a documented limitation.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import APP_NAME, TAGLINE
from app.core.constants import MEDIA_TYPES
from app.models import Item

PLUM = colors.HexColor("#3d2c6e")
AMBER = colors.HexColor("#d98d1c")
INK = colors.HexColor("#1d1a2b")
MUTED = colors.HexColor("#6b6780")
BORDER = colors.HexColor("#e7e3ee")
ROW_ALT = colors.HexColor("#f8f6f2")

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 18 * mm


def _text(value: str | None) -> str:
    """Escape user text for ReportLab's mini-HTML and keep line breaks."""
    return escape(value or "").replace("\n", "<br/>")


def safe_filename(name: str, default: str = "collection") -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_name).strip("-").lower()
    return f"curio-{slug or default}.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("CurioTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22,
                                leading=26, textColor=PLUM, alignment=TA_LEFT, spaceAfter=4),
        "subtitle": ParagraphStyle("CurioSubtitle", parent=base["Normal"], fontName="Helvetica", fontSize=11,
                                   leading=15, textColor=INK, spaceAfter=4),
        "meta": ParagraphStyle("CurioMeta", parent=base["Normal"], fontName="Helvetica", fontSize=9,
                               leading=12, textColor=MUTED),
        "cell": ParagraphStyle("CurioCell", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
                               leading=11, textColor=INK),
        "cell_small": ParagraphStyle("CurioCellSmall", parent=base["Normal"], fontName="Helvetica", fontSize=7.5,
                                     leading=10, textColor=MUTED),
        "heading": ParagraphStyle("CurioHeading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13,
                                  leading=16, textColor=PLUM, spaceBefore=14, spaceAfter=6),
        "note": ParagraphStyle("CurioNote", parent=base["Normal"], fontName="Helvetica", fontSize=9,
                               leading=12.5, textColor=INK, spaceAfter=6),
    }


def _decorate_page(canvas, doc) -> None:  # pragma: no cover - drawing callback
    canvas.saveState()
    # Header
    canvas.setFillColor(PLUM)
    canvas.rect(0, PAGE_HEIGHT - 12 * mm, PAGE_WIDTH, 12 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 8 * mm, APP_NAME)
    canvas.setFont("Helvetica-Oblique", 8.5)
    canvas.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 7.6 * mm, TAGLINE)
    # Footer
    canvas.setStrokeColor(BORDER)
    canvas.line(MARGIN, 14 * mm, PAGE_WIDTH - MARGIN, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, 9 * mm, f"Exported from {APP_NAME}")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _rating_text(rating: int | None) -> str:
    return f"{rating}/5" if rating else "-"


def build_items_pdf(
    *,
    title: str,
    owner_name: str,
    items: Sequence[Item],
    description: str | None = None,
    include_private: bool = True,
) -> bytes:
    """Render a list of items as a styled A4 PDF and return the bytes.

    ``include_private=False`` (used for public share links) omits personal
    notes and tags.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=f"{title} - {APP_NAME}",
        author=owner_name,
        subject=TAGLINE,
        creator=APP_NAME,
    )
    styles = _styles()
    story: list = [Paragraph(_text(title), styles["title"])]
    if description:
        story.append(Paragraph(_text(description), styles["subtitle"]))

    counts = Counter(item.media_type for item in items)
    breakdown = ", ".join(
        f"{count} {MEDIA_TYPES.get(t, MEDIA_TYPES['other'])['plural'].lower() if count != 1 else MEDIA_TYPES.get(t, MEDIA_TYPES['other'])['label'].lower()}"
        for t, count in counts.most_common()
    )
    meta = f"Curated by {_text(owner_name)} · {len(items)} item{'s' if len(items) != 1 else ''}"
    if breakdown:
        meta += f" ({_text(breakdown)})"
    meta += f" · Exported {datetime.now().strftime('%d %B %Y')}"
    story += [Paragraph(meta, styles["meta"]), Spacer(1, 8 * mm)]

    if not items:
        story.append(Paragraph("This collection doesn't contain any items yet.", styles["subtitle"]))
        doc.build(story, onFirstPage=_decorate_page, onLaterPages=_decorate_page)
        return buffer.getvalue()

    header = ["#", "Title", "Type", "Year", "Rating", "Tags" if include_private else "Genres"]
    rows: list[list] = [header]
    for index, item in enumerate(items, start=1):
        title_markup = f"<b>{_text(item.title)}</b>"
        if item.creator:
            title_markup += f"<br/><font size='7.5' color='#6b6780'>{_text(item.creator)}</font>"
        if item.is_favourite:
            title_markup += "<br/><font size='7' color='#d98d1c'><b>FAVOURITE</b></font>"
        labels = item.tag_names if include_private else item.genre_list
        rows.append(
            [
                str(index),
                Paragraph(title_markup, styles["cell"]),
                Paragraph(_text(item.media_label), styles["cell"]),
                str(item.release_year or "-"),
                _rating_text(item.rating),
                Paragraph(_text(", ".join(labels[:6])) or "-", styles["cell_small"]),
            ]
        )

    usable_width = PAGE_WIDTH - 2 * MARGIN
    widths = [0.06, 0.40, 0.13, 0.09, 0.10, 0.22]
    table = Table(rows, colWidths=[w * usable_width for w in widths], repeatRows=1)
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), PLUM),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 1), (-1, -1), INK),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (3, 0), (4, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, BORDER),
        ]
    )
    for row_index in range(1, len(rows)):
        if row_index % 2 == 0:
            style.add("BACKGROUND", (0, row_index), (-1, row_index), ROW_ALT)
    table.setStyle(style)
    story.append(table)

    if include_private:
        noted = [item for item in items if item.notes]
        if noted:
            story.append(Paragraph("Personal notes", styles["heading"]))
            for item in noted:
                story.append(
                    KeepTogether([Paragraph(f"<b>{_text(item.title)}</b> - {_text(item.notes)}", styles["note"])])
                )

    doc.build(story, onFirstPage=_decorate_page, onLaterPages=_decorate_page)
    return buffer.getvalue()
