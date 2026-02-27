"""
목적:
- DOCX 레이아웃 추정 유틸을 제공한다.

설명:
- A4 기준 페이지 추정, 줄/자간/문단 간격 계산, 문단/표 블록 높이 산정을 담당한다.

디자인 패턴:
- 함수형 유틸 모듈(Function Utility Module).

참조:
- src_py/vtree_search/ingestion/source_parser.py
"""

from __future__ import annotations

import math
from statistics import median


def iterate_docx_blocks(document: object) -> list[tuple[str, object]]:
    """DOCX 본문을 문서 순서(paragraph/table)대로 순회 가능한 목록으로 변환한다."""

    try:
        from docx.table import Table as DocxTable
        from docx.text.paragraph import Paragraph as DocxParagraph
    except ImportError:
        return []

    body = getattr(getattr(document, "element", None), "body", None)
    if body is None:
        return []

    blocks: list[tuple[str, object]] = []
    for child in body.iterchildren():
        tag = str(getattr(child, "tag", "")).rsplit("}", maxsplit=1)[-1]
        if tag == "p":
            blocks.append(("paragraph", DocxParagraph(child, document)))
            continue
        if tag == "tbl":
            blocks.append(("table", DocxTable(child, document)))
    return blocks


def resolve_docx_layout_metrics(document: object) -> dict[str, float]:
    """DOCX 페이지 추정을 위한 A4 기반 레이아웃 지표를 계산한다."""

    # DOCX는 렌더러가 아니므로 A4(595.28 x 841.89pt) 기준으로 일관되게 추정한다.
    page_width_pt = 595.28
    page_height_pt = 841.89

    section = None
    sections = getattr(document, "sections", None)
    if sections:
        section = sections[0]

    margin_left_pt = _length_to_pt(getattr(section, "left_margin", None), default=72.0)
    margin_right_pt = _length_to_pt(getattr(section, "right_margin", None), default=72.0)
    margin_top_pt = _length_to_pt(getattr(section, "top_margin", None), default=72.0)
    margin_bottom_pt = _length_to_pt(getattr(section, "bottom_margin", None), default=72.0)

    usable_width_pt = max(120.0, page_width_pt - margin_left_pt - margin_right_pt)
    usable_height_pt = max(160.0, page_height_pt - margin_top_pt - margin_bottom_pt)
    return {
        "page_width_pt": page_width_pt,
        "page_height_pt": page_height_pt,
        "usable_width_pt": usable_width_pt,
        "usable_height_pt": usable_height_pt,
        "margin_left_pt": margin_left_pt,
        "margin_right_pt": margin_right_pt,
        "margin_top_pt": margin_top_pt,
        "margin_bottom_pt": margin_bottom_pt,
    }


def estimate_docx_paragraph_layout(
    *,
    paragraph: object,
    text: str,
    font_size: float,
    usable_width_pt: float,
) -> dict[str, float | int]:
    """문단의 A4 레이아웃 추정값(줄수/높이/간격)을 계산한다."""

    line_spacing_pt = _resolve_docx_line_spacing_pt(paragraph=paragraph, font_size=font_size)
    char_spacing_pt = _extract_docx_char_spacing_pt(paragraph)
    space_before_pt = _resolve_docx_space_pt(paragraph=paragraph, field_name="space_before")
    space_after_pt = _resolve_docx_space_pt(paragraph=paragraph, field_name="space_after")
    line_count_estimated = _estimate_wrapped_line_count(
        text=text,
        font_size=font_size,
        char_spacing_pt=char_spacing_pt,
        usable_width_pt=usable_width_pt,
    )
    estimated_height_pt = (
        float(space_before_pt)
        + float(space_after_pt)
        + float(line_spacing_pt) * int(line_count_estimated)
    )
    return {
        "line_spacing_pt": line_spacing_pt,
        "char_spacing_pt": char_spacing_pt,
        "space_before_pt": space_before_pt,
        "space_after_pt": space_after_pt,
        "line_count_estimated": line_count_estimated,
        "estimated_height_pt": max(4.0, estimated_height_pt),
    }


def estimate_docx_table_height(
    *,
    table: object,
    body_font_size: float,
    usable_width_pt: float,
) -> float:
    """표 텍스트량 기준으로 블록 높이를 추정한다."""

    rows = list(getattr(table, "rows", []))
    if not rows:
        return max(14.0, body_font_size * 1.3)

    inferred_col_count = max((len(getattr(row, "cells", [])) for row in rows), default=1)
    cell_width_pt = max(48.0, float(usable_width_pt) / max(1, inferred_col_count))
    line_height_pt = max(10.0, float(body_font_size) * 1.3)

    total_height_pt = 8.0
    for row in rows:
        row_cells = list(getattr(row, "cells", []))
        row_max_lines = 1
        for cell in row_cells:
            cell_text = str(getattr(cell, "text", "") or "").strip()
            if not cell_text:
                continue
            line_count = _estimate_wrapped_line_count(
                text=cell_text,
                font_size=float(body_font_size),
                char_spacing_pt=0.0,
                usable_width_pt=cell_width_pt,
            )
            row_max_lines = max(row_max_lines, line_count)
        total_height_pt += (row_max_lines * line_height_pt) + 4.0
    return max(line_height_pt, total_height_pt)


def advance_docx_page_state(
    *,
    current_page_num: int,
    used_height_pt: float,
    block_height_pt: float,
    usable_height_pt: float,
) -> tuple[int, int, float]:
    """문서 블록 높이를 누적해 시작 페이지 번호와 다음 상태를 계산한다."""

    page_num = max(1, int(current_page_num))
    used_height = max(0.0, float(used_height_pt))
    usable_height = max(160.0, float(usable_height_pt))
    remaining_block = max(1.0, float(block_height_pt))

    if used_height >= usable_height:
        page_num += 1
        used_height = 0.0
    if used_height > 0.0 and (used_height + remaining_block) > usable_height:
        page_num += 1
        used_height = 0.0

    block_start_page = page_num
    while remaining_block > 0.0:
        available_height = usable_height - used_height
        if available_height <= 0.0:
            page_num += 1
            used_height = 0.0
            available_height = usable_height
        consumed = min(available_height, remaining_block)
        used_height += consumed
        remaining_block -= consumed
        if remaining_block > 0.0:
            page_num += 1
            used_height = 0.0

    return block_start_page, page_num, used_height


def is_docx_page_break_before(paragraph: object) -> bool:
    """문단의 page-break-before 설정을 확인한다."""

    paragraph_format = getattr(paragraph, "paragraph_format", None)
    current_value = getattr(paragraph_format, "page_break_before", None)
    if current_value is not None:
        return bool(current_value)

    style = getattr(paragraph, "style", None)
    style_format = getattr(style, "paragraph_format", None)
    style_value = getattr(style_format, "page_break_before", None)
    if style_value is None:
        return False
    return bool(style_value)


def _resolve_docx_line_spacing_pt(*, paragraph: object, font_size: float) -> float:
    """문단 줄간격을 pt 단위로 정규화한다."""

    paragraph_format = getattr(paragraph, "paragraph_format", None)
    line_spacing = getattr(paragraph_format, "line_spacing", None)
    resolved = _coerce_docx_line_spacing_value_pt(line_spacing, font_size=font_size)
    if resolved is not None:
        return resolved

    style = getattr(paragraph, "style", None)
    style_format = getattr(style, "paragraph_format", None)
    style_spacing = getattr(style_format, "line_spacing", None)
    resolved = _coerce_docx_line_spacing_value_pt(style_spacing, font_size=font_size)
    if resolved is not None:
        return resolved

    # 명시값이 없으면 Word 기본(대략 1.5배)으로 간주한다.
    return max(8.0, float(font_size) * 1.5)


def _resolve_docx_space_pt(*, paragraph: object, field_name: str) -> float:
    """문단 전/후 간격(space_before/space_after)을 pt 단위로 추출한다."""

    paragraph_format = getattr(paragraph, "paragraph_format", None)
    raw_value = getattr(paragraph_format, field_name, None)
    resolved = _length_to_pt(raw_value, default=None)
    if resolved is not None:
        return max(0.0, float(resolved))

    style = getattr(paragraph, "style", None)
    style_format = getattr(style, "paragraph_format", None)
    style_value = getattr(style_format, field_name, None)
    resolved = _length_to_pt(style_value, default=None)
    if resolved is not None:
        return max(0.0, float(resolved))
    return 0.0


def _coerce_docx_line_spacing_value_pt(value: object, *, font_size: float) -> float | None:
    """python-docx line_spacing 값을 pt로 변환한다."""

    if value is None:
        return None

    point = getattr(value, "pt", None)
    if point is not None and float(point) > 0:
        return float(point)

    numeric = float(value)
    if numeric <= 0:
        return None
    # 1.0, 1.5, 2.0 형태는 '배수'로 간주한다.
    if numeric <= 4.0:
        return max(8.0, float(font_size) * 1.2 * numeric)
    return numeric


def _extract_docx_char_spacing_pt(paragraph: object) -> float:
    """문단 내 run의 자간(tracking) 값을 pt 단위로 추정한다."""

    spacings: list[float] = []
    for run in getattr(paragraph, "runs", []):
        spacing = _resolve_docx_run_char_spacing_pt(run)
        if spacing is None:
            continue
        spacings.append(float(spacing))
    if not spacings:
        return 0.0
    return float(median(spacings))


def _resolve_docx_run_char_spacing_pt(run: object) -> float | None:
    """run의 자간을 추출한다. (API 우선, XML 경로)"""

    font = getattr(run, "font", None)
    spacing = getattr(font, "spacing", None)
    resolved = _length_to_pt(spacing, default=None)
    if resolved is not None:
        return float(resolved)

    run_element = getattr(run, "_element", None)
    run_properties = getattr(run_element, "rPr", None)
    if run_properties is None:
        return None

    spacing_element = run_properties.find(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}spacing"
    )
    if spacing_element is None:
        return None
    raw = spacing_element.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
    if raw is None:
        return None
    # w:spacing 값은 1/20 pt 단위로 저장된다.
    return float(raw) / 20.0


def _estimate_wrapped_line_count(
    *,
    text: str,
    font_size: float,
    char_spacing_pt: float,
    usable_width_pt: float,
) -> int:
    """텍스트 길이와 폭으로 줄 수를 추정한다."""

    if not text.strip():
        return 1

    normalized_text = " ".join(text.split())
    explicit_lines = max(1, text.count("\n") + 1)
    average_char_width_pt = max(1.0, float(font_size) * 0.6 + max(0.0, float(char_spacing_pt)))
    chars_per_line = max(1, int(float(usable_width_pt) / average_char_width_pt))
    wrapped_lines = max(1, math.ceil(len(normalized_text) / chars_per_line))
    return max(explicit_lines, wrapped_lines)


def _length_to_pt(value: object, default: float | None) -> float | None:
    """Length/EMU/숫자형 값을 pt로 변환한다."""

    if value is None:
        return default

    point = getattr(value, "pt", None)
    if point is not None:
        return float(point)

    numeric = float(value)
    if numeric <= 0:
        return default
    # EMU 값으로 보이면 pt로 환산한다. (1pt = 12700 EMU)
    if numeric > 1000.0:
        return numeric / 12700.0
    if numeric >= 10.0:
        return numeric
    return default


__all__ = [
    "iterate_docx_blocks",
    "resolve_docx_layout_metrics",
    "estimate_docx_paragraph_layout",
    "estimate_docx_table_height",
    "advance_docx_page_state",
    "is_docx_page_break_before",
]
