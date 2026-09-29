"""Dieselbe Prüfung zweimal auf A4 quer - zum Halbieren.

Das Blatt wird quer gelegt und in zwei gleich breite Spalten geteilt;
**links und rechts steht genau dasselbe**. In der Mitte geschnitten, werden
aus einem A4-Blatt zwei A5-Prüfungsblätter.

Passt eine Prüfung nicht auf eine halbe Seite - sechs Aufgabenarten, oder
die Wiederholung dazu -, dann wird sie auf **mehrere A5-Seiten** verteilt,
und jede davon steht wieder zweimal nebeneinander:

    Blatt 1:  | Seite 1 | Seite 1 |
    Blatt 2:  | Seite 2 | Seite 2 |

Umbrochen wird **zwischen** zwei Aufgaben, nie mitten in einer: Eine
Aufgabenstellung gehört zu ihrer Tabelle. Weil links und rechts gleich sind,
geht auch der beidseitige Druck auf, gleich wie das Blatt gewendet wird -
nach dem Schnitt hat jede Schülerin, jeder Schüler ein A5-Blatt, vorn Seite
1, hinten Seite 2.

Der Inhalt wird **nicht** ein zweites Mal gesetzt. Er entsteht aus genau
dem ``document.xml``, das :func:`builder.build_document_xml` für das A4-Blatt
schreibt, und wird hier nur umgeformt: kleiner gesetzt, auf die
Spaltenbreite gebracht, aufgeteilt und verdoppelt. Eine zweite Umsetzung
des Setzers liefe irgendwann auseinander - und dann stünde auf dem kleinen
Blatt eine andere Prüfung als auf dem grossen.

Was sich ändert, und warum:

* **Schrift 12 pt -> 10 pt**, der Kopf 15 pt -> 12.5 pt. Eine Spalte ist
  12.45 cm breit statt 16 cm und 19 cm hoch statt 26 cm.
* **Tabellen auf die Spaltenbreite**, die Übersetzungstabelle mit einer
  etwas breiteren linken Spalte - dort stehen die deutschen Stichwörter,
  und die brechen sonst in jeder zweiten Zeile um.
* **Zeilenhöhe 680 -> 480** - ein Wort hinzuschreiben braucht keine 12 mm;
  8.5 mm reichen. Die Leerzeile zwischen zwei Aufgaben verliert ihren
  Nachabstand. Der Lückentext behält seinen 1.5-fachen Zeilenabstand:
  In die Lücke wird von Hand geschrieben.
* **Die Punktzahl steht rechtsbündig** statt hinter fünf Tabulatoren: In
  der schmalen Spalte brächen die Tabulatoren um, und die Punkte stünden
  irgendwo.
* **Die Schreiblinie** eines Mini-Textes wird kürzer, sonst bricht sie um.

Die Seitenränder sind so gewählt, dass nach dem Schnitt jede Hälfte links
und rechts denselben Rand hat: Der Abstand zwischen den Spalten ist genau
zweimal der Aussenrand. Eine Schnittlinie wird nicht gedruckt - die Mitte
eines A4-Blatts findet die Schneidemaschine selbst.
"""

from __future__ import annotations

import copy

from lxml import etree

from .builder import WRITING_LINE, _write_package, build_document_xml

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


#: A4 quer, in Twips.
SEITE_BREIT, SEITE_HOCH = 16838, 11906
#: Aussenrand links und rechts; zwischen den Spalten steht das Doppelte -
#: so hat nach dem Schnitt jede Hälfte links und rechts denselben Rand.
RAND = 680
ABSTAND = 2 * RAND
OBEN, UNTEN = 567, 567
#: Die Breite einer Spalte - einer halben Prüfung.
SPALTE = (SEITE_BREIT - 2 * RAND - ABSTAND) // 2
#: Die nutzbare Höhe einer Spalte.
SPALTE_HOCH = SEITE_HOCH - OBEN - UNTEN

#: Schriftgrösse im Verhältnis zum A4-Blatt: 12 pt werden 10 pt.
SCHRIFT = 20 / 24
#: Die Grundschrift der Vorlage (docDefaults), in halben Punkt.
GRUNDSCHRIFT = 24
#: Zeilenhöhe der Übersetzungstabelle.
ZEILE = 480
#: Die linke Spalte der Übersetzungstabelle - die deutschen Stichwörter.
STICHWORT = 2150
#: Die Schreiblinie eines Mini-Textes, auf die Spalte gekürzt.
SCHREIBLINIE = "_" * 60

#: Das A4-Blatt setzt die Übersetzungstabelle 9067 Twips breit.
_A4_TABELLE = "9067"
#: und den Kopf über diese Spalten.
_A4_KOPF = 9062

SECT_PR = (
    f'<w:sectPr xmlns:w="{W_NS}">'
    f'<w:pgSz w:w="{SEITE_BREIT}" w:h="{SEITE_HOCH}" w:orient="landscape"/>'
    f'<w:pgMar w:top="{OBEN}" w:right="{RAND}" w:bottom="{UNTEN}" w:left="{RAND}"'
    ' w:header="340" w:footer="340" w:gutter="0"/>'
    f'<w:cols w:num="2" w:space="{ABSTAND}"/>'
    '<w:docGrid w:linePitch="360"/></w:sectPr>'
)

#: Der Umbruch in die nächste Spalte - aus der rechten auf das nächste
#: Blatt. Er steht in einem Absatz von 1 pt Höhe: Der Absatz nach einem
#: Spaltenumbruch beginnt oben in der neuen Spalte, und in normaler Grösse
#: stünde die rechte Hälfte dort eine Zeile tiefer als die linke.
UMBRUCH = (
    f'<w:p xmlns:w="{W_NS}"><w:pPr>'
    '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
    '<w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr>'
    '<w:r><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr>'
    '<w:br w:type="column"/></w:r></w:p>'
)

#: Die Reihenfolge der Kinder von ``w:rPr`` nach dem Schema, soweit dieser
#: Setzer sie verwendet. Word liest ein Dokument mit falscher Reihenfolge
#: als beschädigt.
_VOR_SZ = {w(t) for t in ("rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps",
                          "smallCaps", "strike", "dstrike", "outline",
                          "shadow", "emboss", "imprint", "noProof",
                          "snapToGrid", "vanish", "webHidden", "color",
                          "spacing", "w", "kern", "position")}
#: und von ``w:pPr`` - ``w:tabs`` steht nach dem Absatzstil, vor allem
#: anderen, was dieser Setzer schreibt.
_VOR_TABS = {w(t) for t in ("pStyle", "keepNext", "keepLines",
                            "pageBreakBefore", "framePr", "widowControl",
                            "numPr", "suppressLineNumbers", "pBdr", "shd")}


def _schrift(rpr: etree._Element) -> None:
    """Die Grösse eines Laufs auf das kleine Blatt bringen.

    Ein Lauf ohne eigene Grösse erbt die 12 pt der Vorlage - er bekommt
    deshalb eine. Die Vorlage selbst (``styles.xml``) bleibt unangetastet.
    """
    for tag in ("sz", "szCs"):
        el = rpr.find(w(tag))
        if el is not None:
            alt = int(el.get(w("val")))
            el.set(w("val"), str(max(2, round(alt * SCHRIFT))))
            continue
        el = etree.Element(w(tag))
        el.set(w("val"), str(round(GRUNDSCHRIFT * SCHRIFT)))
        # Hinter das letzte Kind, das nach dem Schema davor steht.
        stelle = 0
        for i, kind in enumerate(rpr):
            if kind.tag in _VOR_SZ or kind.tag == w("sz"):
                stelle = i + 1
        rpr.insert(stelle, el)


def _rpr(eltern: etree._Element, erstes: bool = True) -> etree._Element:
    rpr = eltern.find(w("rPr"))
    if rpr is None:
        rpr = etree.Element(w("rPr"))
        if erstes:
            eltern.insert(0, rpr)
        else:
            eltern.append(rpr)
    return rpr


def _absatz(p: etree._Element) -> None:
    """Abstände, Schrift und Tabulatoren eines Absatzes."""
    ppr = p.find(w("pPr"))
    for r in p.findall(w("r")):
        _schrift(_rpr(r))
        for t in r.findall(w("t")):
            if t.text == WRITING_LINE:
                t.text = SCHREIBLINIE
    if ppr is not None:
        marke = ppr.find(w("rPr"))
        if marke is not None:
            _schrift(marke)
        abstand = ppr.find(w("spacing"))
        if abstand is not None:
            for attr in ("before", "after"):
                wert = abstand.get(w(attr))
                if wert is not None:
                    abstand.set(w(attr), str(round(int(wert) * SCHRIFT)))
    # Eine Aufgabenstellung: der Text, Tabulatoren, die Punktzahl. Aus den
    # Tabulatoren wird einer, der an den rechten Rand springt.
    tab_laeufe = [r for r in p.findall(w("r")) if r.find(w("tab")) is not None]
    if tab_laeufe:
        for r in tab_laeufe[1:]:
            p.remove(r)
        if ppr is None:
            ppr = etree.Element(w("pPr"))
            p.insert(0, ppr)
        tabs = etree.Element(w("tabs"))
        tab = etree.SubElement(tabs, w("tab"))
        tab.set(w("val"), "right")
        tab.set(w("pos"), str(SPALTE))
        stelle = 0
        for i, kind in enumerate(ppr):
            if kind.tag in _VOR_TABS:
                stelle = i + 1
        ppr.insert(stelle, tabs)


def _tabelle(tbl: etree._Element) -> None:
    """Eine Tabelle auf die Spaltenbreite bringen."""
    tblw = tbl.find(f"{w('tblPr')}/{w('tblW')}")
    uebersetzung = tblw is not None and tblw.get(w("w")) == _A4_TABELLE
    if uebersetzung:
        tblw.set(w("w"), str(SPALTE))
        breiten = [STICHWORT, SPALTE - STICHWORT]
        for spalte, breite in zip(tbl.find(w("tblGrid")).findall(w("gridCol")),
                                  breiten, strict=True):
            spalte.set(w("w"), str(breite))
        for tr in tbl.findall(w("tr")):
            for tc, breite in zip(tr.findall(w("tc")), breiten, strict=True):
                tcw = tc.find(f"{w('tcPr')}/{w('tcW')}")
                if tcw is not None:
                    tcw.set(w("w"), str(breite))
            hoehe = tr.find(f"{w('trPr')}/{w('trHeight')}")
            if hoehe is not None:
                hoehe.set(w("val"), str(ZEILE))
    else:
        # Der Kopf ist in Prozent gesetzt und passt sich selbst an; nur das
        # Raster darunter trägt Twips.
        for spalte in tbl.find(w("tblGrid")).findall(w("gridCol")):
            alt = int(spalte.get(w("w")))
            spalte.set(w("w"), str(round(alt * SPALTE / _A4_KOPF)))
    for p in tbl.iter(w("p")):
        _absatz(p)


def _leer(el: etree._Element) -> bool:
    return el.tag == w("p") and not "".join(el.itertext()).strip() \
        and el.find(f".//{w('br')}") is None


def _ohne_nachabstand(p: etree._Element) -> None:
    """Eine Leerzeile zwischen zwei Aufgaben: ihre Höhe, kein Abstand dazu."""
    ppr = p.find(w("pPr"))
    if ppr is None:
        ppr = etree.Element(w("pPr"))
        p.insert(0, ppr)
    abstand = ppr.find(w("spacing"))
    if abstand is None:
        abstand = etree.Element(w("spacing"))
        # w:spacing steht im Schema vor w:rPr.
        marke = ppr.find(w("rPr"))
        if marke is not None:
            marke.addprevious(abstand)
        else:
            ppr.append(abstand)
    abstand.set(w("after"), "0")


def _ist_aufgabenstellung(el: etree._Element) -> bool:
    """Eine Aufgabenstellung ist der einzige Absatz mit Tabulator."""
    return el.tag == w("p") and el.find(f"{w('r')}/{w('tab')}") is not None


def bloecke(inhalt: list) -> list[list]:
    """Den Inhalt in Blöcke teilen: der Kopf, dann je Aufgabe einer.

    Ein Block beginnt mit der Leerzeile vor einer Aufgabenstellung, oder mit
    der Aufgabenstellung selbst. Nur zwischen Blöcken wird umbrochen.
    """
    heraus: list[list] = [[]]
    for i, el in enumerate(inhalt):
        folgt = i + 1 < len(inhalt) and _ist_aufgabenstellung(inhalt[i + 1])
        vorher_leer = i > 0 and _leer(inhalt[i - 1])
        if (_leer(el) and folgt) or (_ist_aufgabenstellung(el) and not vorher_leer):
            heraus.append([])
        heraus[-1].append(el)
    return heraus


def seiten(hoehen: list[int]) -> list[list[int]]:
    """Die Blöcke auf A5-Seiten verteilen - der Reihe nach, so viele wie passen.

    Ein Block, der eine neue Seite beginnt, lässt seine Leerzeile davor weg;
    oben auf der Seite trennt sie von nichts. (Die erste Aufgabe hat keine.)
    """
    verteilt: list[list[int]] = [[]]
    belegt = 0
    for i, h in enumerate(hoehen):
        if verteilt[-1] and belegt + h > SPALTE_HOCH:
            verteilt.append([])
            h -= _EINZEILIG if i >= 2 else 0
            belegt = 0
        verteilt[-1].append(i)
        belegt += h
    return verteilt


def als_doppelblatt(document_xml: str, hoehen: list[int] | None = None) -> str:
    """Aus dem ``document.xml`` des A4-Blatts das Doppelblatt machen.

    ``hoehen`` sind die geschätzten Höhen der Blöcke (:func:`hoehen`); ohne
    sie steht alles auf einer Seite.
    """
    root = etree.fromstring(document_xml.encode("utf-8"))
    body = root.find(w("body"))
    kinder = list(body)
    inhalt = [k for k in kinder if k.tag != w("sectPr")]
    # Die Leerabsätze am Ende des A4-Blatts halten die Seite nach unten
    # offen. In der Spalte kosten sie nur Platz.
    while inhalt and _leer(inhalt[-1]):
        inhalt.pop()
    for kind in kinder:
        body.remove(kind)
    for el in inhalt:
        if el.tag == w("tbl"):
            _tabelle(el)
        elif el.tag == w("p"):
            _absatz(el)
            if _leer(el):
                _ohne_nachabstand(el)
    teile = bloecke(inhalt)
    if hoehen is None:
        verteilung = [list(range(len(teile)))]
    elif len(hoehen) != len(teile):
        raise ValueError(
            f"die Schätzung kennt {len(hoehen)} Blöcke, das Blatt hat "
            f"{len(teile)} - Setzer und Schätzung sind auseinandergelaufen")
    else:
        verteilung = seiten(hoehen)
    erste = True
    for seite in verteilung:
        elemente = [el for i in seite for el in teile[i]]
        # Oben auf einer neuen Seite trennt die Leerzeile von nichts.
        if seite[0] and elemente and _leer(elemente[0]):
            elemente = elemente[1:]
        for haelfte in (elemente, [copy.deepcopy(el) for el in elemente]):
            if not erste:
                body.append(etree.fromstring(UMBRUCH))
            erste = False
            for el in haelfte:
                body.append(el)
    body.append(etree.fromstring(SECT_PR))
    # Dieselbe Deklaration wie das A4-Blatt - Word liest beide gleich.
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            + etree.tostring(root, encoding="unicode"))


def build_doppelblatt(spec: dict, template_path: str, output_path: str) -> str:
    """Dieselbe Prüfung zweimal auf A4 quer - Vorlage und Stile unverändert."""
    return _write_package(
        str(template_path),
        str(output_path),
        als_doppelblatt(build_document_xml(spec), hoehen(spec)),
        spec.get("meta", {}).get("title", ""),
    )


# ---------------------------------------------------------------------------
# Wie hoch ist ein Block?
# ---------------------------------------------------------------------------
#
# Läuft eine Seite über ihre Spalte hinaus, fliesst sie in die rechte, und
# links und rechts stehen nicht mehr dieselben Seiten. Deshalb wird vorher
# geschätzt, und umbrochen wird, bevor es so weit kommt.
#
# Die Masse sind nicht geraten, sondern an allen mitgelieferten Prüfungen
# gemessen (LibreOffice, mit einer Ersatzschrift, die breiter läuft als
# Aptos - die Schätzung liegt damit eher zu hoch als zu tief). Zeilen werden
# nicht gezählt, sondern umbrochen: Eine Lücke ist 26 Zeichen breit, und
# wo sie nicht mehr auf die Zeile passt, beginnt eine neue - das kostet im
# Lückentext mehr Platz als die Wörter selbst.

#: Punkt je Zeichen bei 10 pt: ein Buchstabe im Mittel, ein Leerzeichen,
#: ein Unterstrich; fett etwas breiter.
_ZEICHEN, _LEER, _STRICH, _FETT = 5.6, 3.2, 5.0, 6.1
#: Eine Textzeile bei 10 pt, in Twips.
_EINZEILIG = 240
#: Der Lückentext steht 1.5-zeilig.
_LUECKENZEILE = 360


def _zeilen(text: str, breite_twips: int, zeichen: float = _ZEICHEN) -> int:
    """Wie viele Zeilen ``text`` in dieser Breite braucht - umbrochen."""
    breite = breite_twips / 20
    zeilen, x = 1, 0.0
    for wort in str(text).split():
        striche = wort.count("_")
        w_ = striche * _STRICH + (len(wort) - striche) * zeichen
        if x and x + _LEER + w_ > breite:
            zeilen += 1
            x = w_
        else:
            x += (_LEER if x else 0) + w_
    return zeilen


def hoehen(spec: dict) -> list[int]:
    """Die geschätzte Höhe jedes Blocks, in Twips: Kopf, Aufgaben, Wiederholung.

    Jede Aufgabe ab der zweiten trägt die Leerzeile davor mit.
    """
    from .builder import (
        GAP,
        _renderer,
        aufgaben_des_specs,
        render_cloze_text,
        wiederholung_des_specs,
    )

    zelle = STICHWORT - 216            # abzüglich der Zellränder
    satz = SPALTE - 284                # eingerückte Sätze

    def ueberschrift(text: str) -> int:
        # Abstand davor, die Zeile (bricht sie um, rückt die Punktzahl mit
        # nach), Abstand danach.
        return 200 + _EINZEILIG * _zeilen(text + " 12P", SPALTE, _FETT) + 160

    def tabelle(items: list[dict]) -> int:
        return sum(max(ZEILE, _EINZEILIG * _zeilen(i.get("german", ""), zelle) + 40)
                   for i in items) + 60

    heraus = [900]                     # der Kopf mit Name und Note
    aufgaben = [a for a in aufgaben_des_specs(spec)
                if _renderer(str(a.get("art", ""))) is not None]
    block = wiederholung_des_specs(spec)
    for nummer, a in enumerate(aufgaben, start=1):
        art = str(a.get("art", ""))
        total = _EINZEILIG if nummer > 1 else 0   # die Leerzeile davor
        total += ueberschrift(str(a.get("instruction", "")))
        if art == "uebersetzen":
            total += tabelle(a.get("items", []))
        elif art == "luecken":
            bank = "Words: " + ", ".join(a.get("word_bank", []))
            total += 200 + _EINZEILIG * _zeilen(bank, SPALTE)
            text = render_cloze_text(str(a.get("text", "")), GAP)
            # Der Abstand danach (280) steht im Block der nächsten Aufgabe
            # gut: Oben auf einer neuen Seite fällt er weg wie die Leerzeile.
            total += 280 + _LUECKENZEILE * _zeilen(text, SPALTE)
        elif art in ("wortwahl", "richtig_falsch"):
            for item in a.get("items", []):
                total += 133 + _EINZEILIG
                for s in item.get("saetze", []):
                    total += _EINZEILIG * _zeilen("a)  " + str(s), satz)
        elif art == "definition":
            for item in a.get("items", []):
                total += 133 + _EINZEILIG * _zeilen(
                    str(item.get("umschreibung", "")), SPALTE - 400)
                total += _EINZEILIG
        elif art == "schreiben":
            for b in a.get("items", []):
                total += 133 + _EINZEILIG
                if str(b.get("anstoss", "")).strip():
                    total += _EINZEILIG * _zeilen(str(b["anstoss"]), satz)
                total += _EINZEILIG * max(2, int(b.get("mindestsaetze", 0) or 0))
        if nummer > 1 and str(aufgaben[nummer - 2].get("art")) == "luecken":
            total += 280                # der Abstand nach dem Lückentext davor
        heraus.append(total)
    if block:
        total = _EINZEILIG + ueberschrift(str(block.get("instruction", "")))
        total += tabelle(block["items"])
        if aufgaben and str(aufgaben[-1].get("art")) == "luecken":
            total += 280
        heraus.append(total)
    return heraus


def hoehe(spec: dict) -> int:
    """Die geschätzte Höhe der ganzen Prüfung, als stünde sie auf einer Seite."""
    return sum(hoehen(spec))


def aufteilung(spec: dict) -> list[int]:
    """Wie voll jede A5-Seite geschätzt wird, in Prozent - je Seite eine Zahl."""
    h = hoehen(spec)
    heraus = []
    for seite in seiten(h):
        belegt = sum(h[i] for i in seite) - (_EINZEILIG if seite[0] >= 2 else 0)
        heraus.append(round(100 * belegt / SPALTE_HOCH))
    return heraus


def passt(spec: dict) -> tuple[bool, list[int]]:
    """Ob jede Seite in ihre Spalte passt - und wie voll jede ist.

    Nicht passen kann nur noch eine **einzelne** Aufgabe, die für sich
    schon höher ist als eine halbe Seite: Innerhalb einer Aufgabe wird
    nicht umbrochen.
    """
    prozente = aufteilung(spec)
    return all(p <= 100 for p in prozente), prozente
