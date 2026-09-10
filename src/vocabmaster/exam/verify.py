"""Check the .docx that was actually written, not just the spec it came from.

A spec can be perfect and the document still wrong - a placeholder left in, a
solution accidentally rendered, a style lost, a second page. These checks read
the finished file back and compare it with what was asked for.
"""

from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree as ET

from .builder import GAP
from .check import ERROR, INFO, WARN, Finding, stem  # noqa: F401  (stem: Teil der API)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

#: parts that carry the design and must survive untouched
DESIGN_PARTS = (
    "word/styles.xml",
    "word/theme/theme1.xml",
    "word/settings.xml",
    "word/fontTable.xml",
    "word/numbering.xml",
    "word/webSettings.xml",
    "[Content_Types].xml",
)

#: markup the reference exam relies on
REQUIRED_MARKUP = {
    'w:fill="000000"': "the black header bar",
    'w:val="Tabellenraster"': "the table style of the reference exam",
    'w:val="StandardWeb"': "the paragraph style of the cloze text",
    'w:ascii="Aptos"': "the Aptos font",
    'w:val="680"': "the row height of the translation table",
    'w:w="9067"': "the width of the translation table",
}


def document_text(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    out = []
    for para in root.iter(f"{W}p"):
        out.append("".join(t.text or "" for t in para.iter(f"{W}t")))
    return "\n".join(out)


def tables(path: str) -> list[list[list[str]]]:
    """Every table of the document as rows of cell texts, in document order."""
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    out = []
    for table in root.iter(f"{W}tbl"):
        rows = []
        for row in table.findall(f"{W}tr"):
            rows.append([
                " ".join("".join(t.text or "" for t in p.iter(f"{W}t"))
                         for p in cell.iter(f"{W}p")).strip()
                for cell in row.findall(f"{W}tc")
            ])
        out.append(rows)
    return out


def verify_document(path: str, spec: dict, template_path: str,
                    is_answer_key: bool = False) -> list[Finding]:
    findings: list[Finding] = []

    def add(level, check, message):
        findings.append(Finding(level, check, message))

    try:
        with zipfile.ZipFile(path) as out, zipfile.ZipFile(template_path) as tpl:
            names, tpl_names = set(out.namelist()), set(tpl.namelist())
            if names != tpl_names:
                add(ERROR, "package",
                    f"the document has different parts than the template: "
                    f"missing {sorted(tpl_names - names)}, "
                    f"extra {sorted(names - tpl_names)}")
            for part in DESIGN_PARTS:
                if part in tpl_names and part in names and \
                        out.read(part) != tpl.read(part):
                    add(ERROR, "design",
                        f"{part} differs from the template - the design changed")
            for name in names:
                if name.endswith((".xml", ".rels")):
                    try:
                        ET.fromstring(out.read(name))
                    except ET.ParseError as exc:
                        add(ERROR, "package", f"{name} is not valid XML: {exc}")
            document = out.read("word/document.xml").decode("utf-8")
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        add(ERROR, "package", f"the document cannot be read: {exc!r}")
        return findings

    for markup, what in REQUIRED_MARKUP.items():
        if markup not in document:
            add(ERROR, "design", f"{what} is missing from the document")

    text = document_text(path)
    flat = re.sub(r"\s+", " ", text)

    gaps = spec.get("task2", {}).get("gaps", [])
    if not is_answer_key:
        found = text.count(GAP)
        if found != len(gaps):
            add(ERROR, "content",
                f"the document has {found} gaps, the spec declares {len(gaps)}")
        for gap in gaps:
            answer = gap.get("answer", "")
            if answer and re.search(rf"\b{re.escape(answer)}\b", text, re.I):
                add(ERROR, "leak",
                    f"the solution '{answer}' is printed on the exam sheet")
        for item in spec.get("task1", {}).get("items", []):
            english = item.get("english", "")
            if english and re.search(rf"\b{re.escape(english)}\b", text, re.I):
                add(ERROR, "leak",
                    f"the solution '{english}' is printed on the exam sheet")
    else:
        for gap in gaps:
            if gap.get("answer", "").upper() not in text.upper():
                add(ERROR, "content",
                    f"the answer key does not show '{gap.get('answer')}'")

    if re.search(r"\{\d*\}", text):
        add(ERROR, "content", "an unreplaced {n} placeholder is in the document")
    if "TODO" in text.upper():
        add(ERROR, "content", "the document still contains TODO text")

    all_tables = tables(path)
    if len(all_tables) != 2:
        add(ERROR, "content",
            f"the document has {len(all_tables)} tables, expected 2 "
            f"(header and translation)")
    translation_rows = all_tables[1] if len(all_tables) > 1 else []
    expected = len(spec.get("task1", {}).get("items", []))
    if len(translation_rows) != expected:
        add(ERROR, "content",
            f"the translation table has {len(translation_rows)} rows, "
            f"expected {expected}")
    # the prompts must match the spec exactly, in order - a substring match
    # would not notice a truncated or swapped prompt
    for index, item in enumerate(spec.get("task1", {}).get("items", [])):
        wanted = re.sub(r"\s+", " ", item.get("german", "")).strip()
        got = re.sub(r"\s+", " ", translation_rows[index][0]).strip() \
            if index < len(translation_rows) else ""
        if got != wanted:
            add(ERROR, "content",
                f"row {index + 1} of the translation table reads '{got}', "
                f"expected '{wanted}'")
    for row in translation_rows:
        if not is_answer_key and len(row) > 1 and row[1].strip():
            add(ERROR, "content",
                f"the answer column is not empty next to '{row[0]}'")
        if len(row) != 2:
            add(ERROR, "content",
                f"a translation row has {len(row)} cells, expected 2")

    # the word bank must be printed as its own comma-separated list
    bank = spec.get("task2", {}).get("word_bank", [])
    bank_line = next((line for line in text.splitlines()
                      if line.strip().startswith(
                          spec.get("task2", {}).get("word_bank_label", "Words:"))),
                     "")
    printed = [w.strip() for w in
               bank_line.split(":", 1)[-1].split(",") if w.strip()]
    if [re.sub(r"\s+", " ", w) for w in printed] != \
            [re.sub(r"\s+", " ", w).strip() for w in bank]:
        add(ERROR, "content",
            f"the word bank on the sheet is {printed}, expected {bank}")

    # a vocabulary exam that runs onto a second page has been laid out wrongly
    estimate = _page_estimate(spec)
    if estimate > 1:
        add(WARN, "layout",
            f"the sheet is estimated at {estimate} pages - check it in Word")
    add(INFO, "verify",
        f"{len(translation_rows)} prompts, {text.count(GAP)} gaps, "
        f"{len(flat.split())} words on the sheet")
    return findings


def _page_estimate(spec: dict) -> int:
    """Rough height estimate in A4 pages for the reference layout."""
    header = 1400                    # header table, in twips
    per_row = 680 + 60
    rows = len(spec.get("task1", {}).get("items", []))
    instructions = 2 * 500
    text_words = len(re.sub(r"\{\d*\}", "x", spec.get("task2", {}).get("text", "")).split())
    cloze = 360 * max(1, round(text_words / 11))
    total = header + instructions + rows * per_row + cloze + 800
    usable = 16838 - 1417 - 635      # page height minus margins
    return max(1, -(-total // usable))
