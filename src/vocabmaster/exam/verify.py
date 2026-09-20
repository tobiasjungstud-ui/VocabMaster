"""Check the .docx that was actually written, not just the spec it came from.

A spec can be perfect and the document still wrong - a placeholder left in, a
solution accidentally rendered, a style lost, a second page. These checks read
the finished file back and compare it with what was asked for.
"""

from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree as ET

from .builder import GAP, LINE, aufgaben_des_specs, choice_letter
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
    aufgaben = aufgaben_des_specs(spec)
    nach_art = {}
    for a in aufgaben:
        nach_art.setdefault(str(a.get("art", "")), []).append(a)

    # --- die Lösungen, die nicht auf dem Blatt stehen dürfen -------------
    # Eine Aufgabe fragt ein Wort ab (übersetzen, einsetzen, umschreiben)
    # oder sie druckt es aus (Satzwahl, Micro-Writing). Nur die erste Sorte
    # darf nirgends auftauchen - bei der zweiten ist das Wort die Angabe.
    geheim = []
    for a in nach_art.get("uebersetzen", []):
        geheim += [i.get("english", "") for i in a.get("items", [])]
    for a in nach_art.get("luecken", []):
        geheim += [g.get("answer", "") for g in a.get("gaps", [])]
    for a in nach_art.get("definition", []):
        geheim += [i.get("english", "") for i in a.get("items", [])]

    alle_gaps = [g for a in nach_art.get("luecken", []) for g in a.get("gaps", [])]
    if not is_answer_key:
        gefunden = _luecken_zaehlen(text)
        erwartet = len(alle_gaps) + sum(
            len(a.get("items", [])) for a in nach_art.get("definition", []))
        if gefunden != erwartet:
            add(ERROR, "content",
                f"the document has {gefunden} blanks, the spec declares "
                f"{erwartet}")
        for wort in geheim:
            if wort and re.search(rf"\b{re.escape(wort)}\b", text, re.I):
                add(ERROR, "leak",
                    f"the solution '{wort}' is printed on the exam sheet")
    else:
        for gap in alle_gaps:
            if gap.get("answer", "").upper() not in text.upper():
                add(ERROR, "content",
                    f"the answer key does not show '{gap.get('answer')}'")
        for a in nach_art.get("definition", []):
            for item in a.get("items", []):
                wort = item.get("english", "")
                if wort and wort.upper() not in text.upper():
                    add(ERROR, "content",
                        f"the answer key does not show '{wort}'")

    if re.search(r"\{\d*\}", text):
        add(ERROR, "content", "an unreplaced {n} placeholder is in the document")
    if "TODO" in text.upper():
        add(ERROR, "content", "the document still contains TODO text")

    # --- die Übersetzungstabelle ----------------------------------------
    all_tables = tables(path)
    erwartete_tabellen = 1 + len(nach_art.get("uebersetzen", []))
    if len(all_tables) != erwartete_tabellen:
        add(ERROR, "content",
            f"the document has {len(all_tables)} tables, expected "
            f"{erwartete_tabellen} (header and one per translation task)")
    for nr, aufgabe in enumerate(nach_art.get("uebersetzen", []), start=1):
        rows = all_tables[nr] if nr < len(all_tables) else []
        items = aufgabe.get("items", [])
        if len(rows) != len(items):
            add(ERROR, "content",
                f"the translation table has {len(rows)} rows, "
                f"expected {len(items)}")
        # the prompts must match the spec exactly, in order - a substring
        # match would not notice a truncated or swapped prompt
        for index, item in enumerate(items):
            wanted = re.sub(r"\s+", " ", item.get("german", "")).strip()
            got = re.sub(r"\s+", " ", rows[index][0]).strip() \
                if index < len(rows) else ""
            if got != wanted:
                add(ERROR, "content",
                    f"row {index + 1} of the translation table reads '{got}', "
                    f"expected '{wanted}'")
        for row in rows:
            if not is_answer_key and len(row) > 1 and row[1].strip():
                add(ERROR, "content",
                    f"the answer column is not empty next to '{row[0]}'")
            if len(row) != 2:
                add(ERROR, "content",
                    f"a translation row has {len(row)} cells, expected 2")

    # --- die Wortbank ---------------------------------------------------
    for aufgabe in nach_art.get("luecken", []):
        bank = aufgabe.get("word_bank", [])
        label = aufgabe.get("word_bank_label", "Words:")
        bank_line = next((line for line in text.splitlines()
                          if line.strip().startswith(label)), "")
        printed = [w.strip() for w in
                   bank_line.split(":", 1)[-1].split(",") if w.strip()]
        if [re.sub(r"\s+", " ", w) for w in printed] != \
                [re.sub(r"\s+", " ", w).strip() for w in bank]:
            add(ERROR, "content",
                f"the word bank on the sheet is {printed}, expected {bank}")

    # --- Satzwahl, Umschreibung, Micro-Writing --------------------------
    for art in ("wortwahl", "richtig_falsch"):
        for aufgabe in nach_art.get(art, []):
            for nummer, item in enumerate(aufgabe.get("items", []), start=1):
                for i, satz in enumerate(item.get("saetze", [])):
                    satz = re.sub(r"\s+", " ", str(satz)).strip()
                    if satz and satz not in flat:
                        add(ERROR, "content",
                            f"sentence {choice_letter(i)}) of {art} item "
                            f"{nummer} is not on the sheet")
                marke = f"Solution: {choice_letter(int(item.get('richtig', 1)) - 1)})"
                if is_answer_key and marke not in flat:
                    add(ERROR, "content",
                        f"the answer key does not name the solution of "
                        f"{art} item {nummer} ('{marke}')")
    if not is_answer_key and "Solution:" in text:
        add(ERROR, "leak", "the exam sheet names a solution")

    for aufgabe in nach_art.get("definition", []):
        for nummer, item in enumerate(aufgabe.get("items", []), start=1):
            umschreibung = re.sub(r"\s+", " ", str(item.get("umschreibung", ""))).strip()
            if umschreibung and umschreibung not in flat:
                add(ERROR, "content",
                    f"the description of definition item {nummer} is not "
                    "on the sheet")

    for aufgabe in nach_art.get("schreiben", []):
        for nummer, block in enumerate(aufgabe.get("items", []), start=1):
            for wort in block.get("woerter", []):
                en = wort.get("english", "")
                if en and en not in flat:
                    add(ERROR, "content",
                        f"'{en}' of writing task {nummer} is not on the sheet")

    # a vocabulary exam that runs onto a second page has been laid out wrongly
    estimate = _page_estimate(spec)
    if estimate > 1:
        zusatz = [a for a in aufgaben
                  if str(a.get("art")) not in ("uebersetzen", "luecken")]
        grund = (f" - {len(zusatz)} extra task(s) take space"
                 if zusatz else "")
        add(WARN, "layout",
            f"the sheet is estimated at {estimate} pages{grund} - "
            "check it in Word")
    add(INFO, "verify",
        f"{sum(len(a.get('items', [])) for a in nach_art.get('uebersetzen', []))}"
        f" prompts, {_luecken_zaehlen(text)} blanks, "
        f"{len(flat.split())} words "
        f"on the sheet")
    return findings


def _luecken_zaehlen(text: str) -> int:
    """Wie viele Lücken auf dem Blatt stehen - genau die, keine anderen.

    Eine Lücke ist ein Strich aus genau 26 Unterstrichen. Die Schreiblinie
    eines Mini-Textes ist länger, und `count` fand in ihr gleich drei
    Lücken - das Blatt meldete zwölf, wo sechs standen.
    """
    return len(re.findall(rf"(?<!_){re.escape(GAP)}(?!_)", text))


def _page_estimate(spec: dict) -> int:
    """Rough height estimate in A4 pages for the reference layout."""
    total = 1400                     # header table, in twips
    per_row = 680 + 60
    for aufgabe in aufgaben_des_specs(spec):
        art = str(aufgabe.get("art", ""))
        total += 500                 # die Aufgabenstellung
        if art == "uebersetzen":
            total += len(aufgabe.get("items", [])) * per_row
        elif art == "luecken":
            woerter = len(re.sub(r"\{\d*\}", "x",
                                 aufgabe.get("text", "")).split())
            total += 360 * max(1, round(woerter / 11))
        elif art in ("wortwahl", "richtig_falsch"):
            for item in aufgabe.get("items", []):
                total += LINE
                for satz in item.get("saetze", []):
                    total += LINE * max(1, round(len(str(satz).split()) / 13))
        elif art == "definition":
            for item in aufgabe.get("items", []):
                woerter = len(str(item.get("umschreibung", "")).split())
                total += LINE * max(1, round(woerter / 13)) + LINE
        elif art == "schreiben":
            for block in aufgabe.get("items", []):
                total += LINE * 2
                total += LINE * max(2, int(block.get("mindestsaetze", 2) or 2))
    total += 800
    usable = 16838 - 1417 - 635      # page height minus margins
    return max(1, -(-total // usable))
