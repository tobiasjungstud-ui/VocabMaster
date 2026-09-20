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

#: Höhe einer gesetzten Zeile in Twips - für die Seitenschätzung.
LINE = 280

#: Die Schreiblinie eines Mini-Textes.
WRITING_LINE = "_" * 78

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


#: Die Buchstaben, unter denen die Sätze einer Wahlaufgabe stehen.
CHOICE_LETTERS = "abcdefgh"


def choice_letter(index: int) -> str:
    """``0`` -> ``a``. Über das Alphabet hinaus wird durchnummeriert."""
    return CHOICE_LETTERS[index] if index < len(CHOICE_LETTERS) else str(index + 1)


def _choice_block(aufgabe: dict, show_answers: bool = False) -> str:
    """Eine Satzwahl - welcher der Sätze verwendet das Wort richtig?

    Zwei Sätze oder drei, das ändert nur die Zahl der Zeilen. Bewusst
    **ohne Tabelle**: Das Dokument der Referenzprüfung hat genau zwei, den
    Kopf und die Übersetzungstabelle, und eine Kontrolle zählt sie.

    Auf dem Lösungsblatt steht der richtige Satz fett, und darunter noch
    einmal sein Buchstabe im Klartext: Fettdruck ist beim Korrigieren im
    Vorbeigehen zu übersehen, eine Zeile "Solution: b)" nicht.
    """
    out = []
    for nummer, item in enumerate(aufgabe.get("items", []), start=1):
        out.append(_wortzeile(nummer, item.get("english", "")))
        richtig = int(item.get("richtig", 0))
        for i, satz in enumerate(item.get("saetze", [])):
            treffer = show_answers and (i + 1) == richtig
            stil = BOLD if treffer else APTOS
            out.append(_eingerueckt(
                run(f"{choice_letter(i)})  ", stil) + run(satz, stil), stil))
        if show_answers:
            out.append(_eingerueckt(
                run(f"Solution: {choice_letter(richtig - 1)})", BOLD), BOLD))
    return "".join(out)


def _wortzeile(nummer: int, text: str) -> str:
    """Die Kopfzeile einer Teilaufgabe: ihre Nummer und das Wort."""
    return para(
        run(f"{nummer}.  ", BOLD) + run(text, BOLD),
        ppr='<w:spacing w:before="160" w:after="0"/>',
        rpr=BOLD,
    )


def _eingerueckt(runs: str, rpr: str = APTOS) -> str:
    return para(runs, ppr='<w:spacing w:after="0"/><w:ind w:left="284"/>',
                rpr=rpr)


def _definition_block(aufgabe: dict, show_answers: bool = False) -> str:
    """Eine Umschreibung, darunter die Linie für das gesuchte Wort."""
    out = []
    for nummer, item in enumerate(aufgabe.get("items", []), start=1):
        out.append(para(
            run(f"{nummer}.  ", BOLD) + run(item.get("umschreibung", ""), APTOS),
            ppr='<w:spacing w:before="160" w:after="0"/>',
            rpr=APTOS,
        ))
        antwort = item.get("english", "") if show_answers else ""
        out.append(_eingerueckt(
            run(GAP if not show_answers else antwort.upper(),
                APTOS if not show_answers else BOLD),
            APTOS if not show_answers else BOLD))
    return "".join(out)


def _writing_block(aufgabe: dict, show_answers: bool = False) -> str:
    """Micro-Writing: die vorgegebenen Wörter, darunter Platz zum Schreiben.

    Ein Lösungsschlüssel im üblichen Sinn kann es hier nicht geben - was
    die Klasse schreibt, steht vorher nicht fest. Auf dem Lösungsblatt
    steht deshalb, **woran** korrigiert wird: alle Wörter richtig
    verwendet, so viele Sätze, zusammenhängender Text.
    """
    out = []
    for nummer, block in enumerate(aufgabe.get("items", []), start=1):
        woerter = ", ".join(w.get("english", "") for w in block.get("woerter", []))
        out.append(_wortzeile(nummer, woerter))
        anstoss = str(block.get("anstoss", "")).strip()
        if anstoss:
            out.append(_eingerueckt(run(anstoss, APTOS)))
        saetze = int(block.get("mindestsaetze", 0) or 0)
        if show_answers:
            out.append(_eingerueckt(
                run(f"Marking: every word used correctly, at least {saetze} "
                    "sentences, one connected text.", BOLD), BOLD))
        else:
            for _ in range(max(2, saetze)):
                out.append(_eingerueckt(run(WRITING_LINE, APTOS)))
    return "".join(out)


def render_cloze_text(template: str, gap: str = GAP) -> str:
    """Replace every {} / {1} / ___ placeholder in the cloze template by a gap."""
    text = re.sub(r"\{\d*\}", gap, template)
    text = re.sub(r"_{3,}", gap, text)
    return text


#: Wie eine Aufgabe gesetzt wird - je Art ein Setzer und die Zahl der
#: Tabulatoren vor der Punktzahl. Mehr weiss dieses Modul über die Arten
#: nicht; **was** eine Art verlangt, steht in ``vocabmaster.aufgaben``.
def _renderer(art: str):
    return {
        "uebersetzen": _translation_part,
        "luecken": _cloze_part,
        "wortwahl": _choice_block,
        "richtig_falsch": _choice_block,
        "definition": _definition_block,
        "schreiben": _writing_block,
    }.get(art)


TABS = {"uebersetzen": 5, "luecken": 4, "wortwahl": 5,
        "richtig_falsch": 5, "definition": 5, "schreiben": 5}


def _translation_part(aufgabe: dict, show_answers: bool = False) -> str:
    return _translation_table(aufgabe.get("items", []), show_answers)


def _cloze_part(aufgabe: dict, show_answers: bool = False) -> str:
    return (
        _word_bank(aufgabe.get("word_bank_label", "Words:"),
                   aufgabe.get("word_bank", []))
        + _cloze(_cloze_text(aufgabe, show_answers))
    )


def punktzahl(aufgabe: dict) -> int:
    """Die Punkte einer Aufgabe - ein Punkt je geprüftem Wort."""
    art = aufgabe.get("art")
    if art == "uebersetzen":
        return len(aufgabe.get("items", []))
    if art == "luecken":
        return len(aufgabe.get("gaps", []))
    if art == "schreiben":
        return sum(len(b.get("woerter", [])) for b in aufgabe.get("items", []))
    return len(aufgabe.get("items", []))


def nummeriere(instruction: str, nummer: int) -> str:
    """Die führende Nummer einer Aufgabenstellung auf ``nummer`` setzen.

    Der Rest bleibt **unangetastet**, samt der Zahl der Leerzeichen
    dahinter: Die Vorlage hat dort einmal eines und einmal zwei, und ein
    Dokument, das sich in einem Leerzeichen unterscheidet, ist nicht mehr
    dasselbe Dokument.
    """
    ersetzt, wie_oft = re.subn(r"^\s*\d+\)", f"{nummer})", instruction, count=1)
    return ersetzt if wie_oft else f"{nummer})  {instruction}"


def aufgaben_des_specs(spec: dict) -> list[dict]:
    """Die Aufgaben einer Prüfung - auch aus einem Paket von gestern.

    Der Setzer darf ``vocabmaster.pack`` nicht kennen (der kennt ihn), also
    steht die Umsetzung hier noch einmal. Sie ist dieselbe, und ein Test
    vergleicht beide.
    """
    liste = spec.get("aufgaben")
    if isinstance(liste, list):
        return [a for a in liste if isinstance(a, dict)]
    heraus = []
    for schluessel, art in (("task1", "uebersetzen"), ("task2", "luecken"),
                            ("task3", "wortwahl")):
        block = spec.get(schluessel)
        if isinstance(block, dict) and block:
            heraus.append({"art": art, **block})
    return heraus


def build_document_xml(spec: dict, show_answers: bool = False) -> str:
    header = spec["header"]
    parts = [
        DOC_OPEN,
        _header_table(
            header.get("title", " Vocabulary"),
            header.get("unit", "Unit 8 |Part II"),
            header.get("name_label", "Name:"),
            header.get("grade_label", "Grade :"),
        ),
    ]
    aufgaben = aufgaben_des_specs(spec)
    for nummer, aufgabe in enumerate(aufgaben, start=1):
        setzer = _renderer(str(aufgabe.get("art", "")))
        if setzer is None:
            continue
        art = str(aufgabe.get("art"))
        punkte = punktzahl(aufgabe)
        # Der Lückentext trägt hinter seiner Punktzahl ein Leerzeichen -
        # so steht es in der Referenzprüfung, und so bleibt es.
        endung = " " if art == "luecken" else ""
        if nummer > 1:
            parts.append(para(rpr=BOLD))
        parts.append(_task_heading(
            nummeriere(str(aufgabe.get("instruction", "")), nummer),
            f"{punkte}P{endung}", tabs=TABS.get(art, 5),
        ))
        parts.append(setzer(aufgabe, show_answers))
    parts += [
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
    key = {k: v for k, v in spec.items() if k != "header"}
    key["header"] = dict(spec["header"])
    key["header"]["title"] = key["header"].get("title", " Vocabulary").strip() + " - Solutions"
    xml = build_document_xml(key, show_answers=True)
    title = spec.get("meta", {}).get("title", "")
    return _write_package(template_path, output_path, xml,
                          f"{title} - Solutions" if title else "")
