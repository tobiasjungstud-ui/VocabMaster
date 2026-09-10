"""Render an exam spec into a .docx that matches the reference exam exactly.

Design fidelity is achieved by reusing the reference exam as a template: every
part of the package (styles.xml, theme1.xml, settings.xml, fontTable.xml, ...)
is copied through unchanged and only ``word/document.xml`` is rebuilt.  The
XML fragments below mirror the reference document run for run:

  * header table  - full width, 3 columns (2578 / 2126 / 295 pct), first row
    filled black, 15 pt (sz 30) Aptos
  * task headings - Aptos bold, spacing before 240, tabs then the point count
  * translation table - 9067 dxa wide, columns 2405 / 6662, row height 680,
    German prompt vertically centred in the left column
  * word bank     - "Words:" in the 'Fett' character style, the list in italics
  * cloze text    - 'StandardWeb' paragraph style, 1.5 line spacing, gaps
    written as 26 underscores
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

GAP = "_" * 26

APTOS = '<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/>'
APTOS_EA = '<w:rFonts w:ascii="Aptos" w:eastAsiaTheme="majorEastAsia" w:hAnsi="Aptos"/>'
BIG = f"{APTOS}<w:sz w:val=\"30\"/><w:szCs w:val=\"30\"/>"
BOLD = f"{APTOS}<w:b/><w:bCs/>"

DOC_OPEN = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    '<w:document xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    ' xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    ' xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"'
    ' xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
    ' mc:Ignorable="w14"><w:body>'
)

SECT_PR = (
    '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1417" w:right="1417" w:bottom="635" w:left="1417"'
    ' w:header="708" w:footer="708" w:gutter="0"/>'
    '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>'
)

TBL_LOOK = (
    '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1"'
    ' w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
)


def esc(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def run(text: str, rpr: str = "") -> str:
    props = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    space = ' xml:space="preserve"' if text != text.strip() else ""
    return f"<w:r>{props}<w:t{space}>{esc(text)}</w:t></w:r>"


def para(runs: str = "", ppr: str = "", rpr: str = "") -> str:
    props = ""
    if ppr or rpr:
        mark = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
        props = f"<w:pPr>{ppr}{mark}</w:pPr>"
    return f"<w:p>{props}{runs}</w:p>"


def _header_table(title: str, unit: str, name_label: str, grade_label: str) -> str:
    shade = '<w:shd w:val="clear" w:color="auto" w:fill="000000" w:themeFill="text1"/>'

    def cell(width: str, body: str, shaded: bool = False, span: int = 1) -> str:
        gs = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ""
        pr = f'<w:tcPr><w:tcW w:w="{width}" w:type="pct"/>{gs}{shade if shaded else ""}</w:tcPr>'
        return f"<w:tc>{pr}{body}</w:tc>"

    # The reference sets the unit number at 15 pt and the "Part x" suffix at the
    # document default size - keep that two-run split.
    unit_main, _, unit_suffix = unit.partition("|")
    unit_runs = run(unit_main, BIG)
    if unit_suffix:
        unit_runs += run(unit_suffix, "")

    row1 = (
        "<w:tr>"
        + cell("2578", para(run(title, BIG), rpr=BIG), shaded=True)
        + cell("2126", para(unit_runs, rpr=BIG), shaded=True)
        + cell("295", para(rpr=BIG), shaded=True)
        + "</w:tr>"
    )
    row2 = (
        "<w:tr>"
        + cell("2578", para(run(name_label, BIG), rpr=BIG))
        + cell("2422", para(run(grade_label, BIG), rpr=BIG) + para(rpr=BIG), span=2)
        + "</w:tr>"
    )
    return (
        "<w:tbl><w:tblPr><w:tblStyle w:val=\"Tabellenraster\"/>"
        '<w:tblW w:w="5000" w:type="pct"/>' + TBL_LOOK + "</w:tblPr>"
        '<w:tblGrid><w:gridCol w:w="4673"/><w:gridCol w:w="3853"/>'
        '<w:gridCol w:w="536"/></w:tblGrid>' + row1 + row2 + "</w:tbl>"
    )


def _task_heading(text: str, points: str, tabs: int) -> str:
    runs = run(text, BOLD)
    runs += "".join(f"<w:r><w:rPr>{BOLD}</w:rPr><w:tab/></w:r>" for _ in range(tabs))
    runs += run(points, BOLD)
    return para(runs, ppr='<w:spacing w:before="240"/>', rpr=BOLD)


def _translation_table(items: list[dict], show_answers: bool = False) -> str:
    rows = []
    for item in items:
        left = (
            '<w:tc><w:tcPr><w:tcW w:w="2405" w:type="dxa"/>'
            '<w:vAlign w:val="center"/></w:tcPr>'
            + para(run(item["german"]), rpr=BOLD)
            + "</w:tc>"
        )
        answer = run(item.get("english", ""), APTOS) if show_answers else ""
        right = (
            '<w:tc><w:tcPr><w:tcW w:w="6662" w:type="dxa"/></w:tcPr>'
            + para(answer, ppr='<w:spacing w:before="120"/>' if show_answers else "",
                   rpr=BOLD)
            + "</w:tc>"
        )
        rows.append(
            '<w:tr><w:trPr><w:trHeight w:val="680"/></w:trPr>' + left + right + "</w:tr>"
        )
    return (
        '<w:tbl><w:tblPr><w:tblStyle w:val="Tabellenraster"/>'
        '<w:tblW w:w="9067" w:type="dxa"/>' + TBL_LOOK + "</w:tblPr>"
        '<w:tblGrid><w:gridCol w:w="2405"/><w:gridCol w:w="6662"/></w:tblGrid>'
        + "".join(rows)
        + "</w:tbl>"
    )


def _word_bank(label: str, words: list[str]) -> str:
    fett = '<w:rStyle w:val="Fett"/>' + APTOS_EA
    italic_off_bold = fett + '<w:b w:val="0"/><w:bCs w:val="0"/><w:i/><w:iCs/>'
    runs = (
        run(label, fett)
        + run(" ", italic_off_bold)
        + run(" ", italic_off_bold)
        + run(", ".join(words), APTOS_EA + "<w:i/><w:iCs/>")
    )
    return para(
        runs,
        ppr='<w:spacing w:before="240" w:after="0" w:line="240" w:lineRule="auto"/>',
        rpr=BOLD + "<w:i/><w:iCs/>",
    )


def _cloze(text: str) -> str:
    return para(
        run(text, APTOS),
        ppr='<w:pStyle w:val="StandardWeb"/><w:spacing w:line="360" w:lineRule="auto"/>',
        rpr=APTOS,
    )


def render_cloze_text(template: str, gap: str = GAP) -> str:
    """Replace every {} / {1} / ___ placeholder in the cloze template by a gap."""
    text = re.sub(r"\{\d*\}", gap, template)
    text = re.sub(r"_{3,}", gap, text)
    return text


def build_document_xml(spec: dict, show_answers: bool = False) -> str:
    header = spec["header"]
    task1 = spec["task1"]
    task2 = spec["task2"]

    parts = [
        DOC_OPEN,
        _header_table(
            header.get("title", " Vocabulary"),
            header.get("unit", "Unit 8 |Part II"),
            header.get("name_label", "Name:"),
            header.get("grade_label", "Grade :"),
        ),
        _task_heading(task1["instruction"], f"{len(task1['items'])}P", tabs=5),
        _translation_table(task1["items"], show_answers),
        para(rpr=BOLD),
        _task_heading(task2["instruction"], f"{len(task2['gaps'])}P ", tabs=4),
        _word_bank(task2.get("word_bank_label", "Words:"), task2["word_bank"]),
        _cloze(_cloze_text(task2, show_answers)),
        para(rpr=BOLD),
        para(rpr=BOLD),
        SECT_PR,
        "</w:body></w:document>",
    ]
    return "".join(parts)


def build_docx(spec: dict, template_path: str, output_path: str) -> str:
    """Write the exam .docx, copying every non-body part from the template."""
    return _write_package(
        str(template_path),
        str(output_path),
        build_document_xml(spec),
        spec.get("meta", {}).get("title", ""),
    )


def _retitle_core(core_xml: bytes, title: str) -> bytes:
    if not title:
        return core_xml
    text = core_xml.decode("utf-8")
    if "<dc:title>" in text:
        return re.sub(r"<dc:title>.*?</dc:title>", f"<dc:title>{esc(title)}</dc:title>",
                      text, flags=re.S).encode("utf-8")
    return text.replace(
        "<dc:creator>", f"<dc:title>{esc(title)}</dc:title><dc:creator>", 1
    ).encode("utf-8")


def _cloze_text(task2: dict, show_answers: bool) -> str:
    if not show_answers:
        return render_cloze_text(task2["text"])
    text = task2["text"]
    for index, gap in enumerate(task2["gaps"], start=1):
        answer = gap["answer"].upper()
        if f"{{{index}}}" in text:
            text = text.replace(f"{{{index}}}", answer, 1)
        else:
            text = re.sub(r"(\{\}|_{3,})", answer.replace("\\", "\\\\"), text, count=1)
    return text


def _write_package(template_path: str, output_path: str, document_xml: str,
                   title: str = "") -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(template_path) as src:
        infos = src.infolist()
        payload = {info.filename: src.read(info.filename) for info in infos}
    payload["word/document.xml"] = document_xml.encode("utf-8")
    if title and "docProps/core.xml" in payload:
        payload["docProps/core.xml"] = _retitle_core(payload["docProps/core.xml"], title)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in infos:
            dst.writestr(info.filename, payload[info.filename])
    return output_path


def build_answer_key(spec: dict, template_path: str, output_path: str) -> str:
    """Same layout, but with the solutions filled in - for correcting."""
    key = {
        "meta": spec.get("meta", {}),
        "header": dict(spec["header"]),
        "task1": spec["task1"],
        "task2": spec["task2"],
    }
    key["header"]["title"] = key["header"].get("title", " Vocabulary").strip() + " - Solutions"
    xml = build_document_xml(key, show_answers=True)
    title = spec.get("meta", {}).get("title", "")
    return _write_package(template_path, output_path, xml,
                          f"{title} - Solutions" if title else "")
