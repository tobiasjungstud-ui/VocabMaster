"""Dieselbe Prüfung zweimal auf A4 quer - zum Halbieren.

Das Doppelblatt entsteht aus dem ``document.xml`` des A4-Blatts, nicht aus
einem zweiten Setzer. Diese Tests halten fest, was daraus folgen muss:

* auf **jedem** Blatt steht links und rechts dasselbe, und hintereinander
  gelesen ist es die Prüfung des A4-Blatts,
* was länger ist als eine halbe Seite, geht auf ein zweites Blatt - nicht
  in die rechte Hälfte,
* die Mitte ist die Mitte: beide Hälften haben dieselben Ränder,
* das A4-Blatt bleibt, was es war.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from vocabmaster.documents import (
    _spec_mit_herkunft,
    baue_alles,
    dateiname,
    schreibe_pruefung,
)
from vocabmaster.exam import doppelblatt as db
from vocabmaster.exam.builder import aufgaben_des_specs, build_document_xml, build_docx
from vocabmaster.exam.verify import verify_document
from vocabmaster.pack import Pack

WURZEL = Path(__file__).resolve().parent.parent
KURATIERT = WURZEL / "kuratiert"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

#: Die echte Höhe **einer** Prüfung in der Spalte, in Twips - gemessen mit
#: LibreOffice (eine Kopie, eine Spalte, eine sehr hohe Seite; unterster
#: Text oder unterste Tabellenlinie). Die Ersatzschrift dort läuft breiter
#: als Aptos, die Werte liegen also eher zu hoch.
#:
#: Wer das Layout des Doppelblatts ändert, misst neu - sonst prüft dieser
#: Test eine Schätzung gegen ein Blatt, das es nicht mehr gibt.
GEMESSEN = {
    "unit_01.json:1A": 9503, "unit_01.json:1B": 8456,
    "unit_01.json:2A": 9503, "unit_01.json:2B": 9154,
    "unit_01_englishplus3.json:1A": 18061, "unit_01_englishplus3.json:1B": 17630,
    "unit_01_englishplus3.json:2A": 18061, "unit_01_englishplus3.json:2B": 17014,
    "unit_01_fassung2.json:1A": 9474, "unit_01_fassung3.json:1A": 9503,
    "unit_01_v2.json:1A": 9387, "unit_01_v2.json:1B": 8805,
    "unit_01_v2.json:2A": 9154, "unit_01_v2.json:2B": 9154,
    "unit_02.json:1A": 10085, "unit_02.json:1B": 8805,
    "unit_02.json:2A": 9503, "unit_02.json:2B": 8805,
    "unit_03.json:1A": 9503, "unit_03.json:1B": 8805,
    "unit_03.json:2A": 9503, "unit_03.json:2B": 8805,
    "unit_04.json:1A": 9503, "unit_04.json:1B": 8805,
    "unit_04.json:2A": 9503, "unit_04.json:2B": 8805,
    "unit_05.json:1A": 9503, "unit_05.json:1B": 8805,
    "unit_05.json:2A": 9503, "unit_05.json:2B": 8805,
    "unit_06.json:1A": 9736, "unit_06.json:1B": 9154,
    "unit_06.json:2A": 9387, "unit_06.json:2B": 8805,
    "unit_07.json:1A": 10085, "unit_07.json:1B": 8805,
    "unit_07.json:2A": 9503, "unit_07.json:2B": 8805,
    "unit_08.json:1A": 9852, "unit_08.json:1B": 8805,
    "unit_08.json:2A": 9503, "unit_08.json:2B": 8805,
    "unit_08_englishplus3.json:1A": 9154, "unit_08_englishplus3.json:1B": 9267,
    "unit_08_englishplus3.json:2A": 9736, "unit_08_englishplus3.json:2B": 8805,
}


def _pruefungen():
    for datei in sorted(KURATIERT.glob("unit_*.json")):
        pack = Pack.load(datei)
        for teil, niveau in sorted(pack.exams):
            yield f"{datei.name}:{teil}{niveau}", pack, teil, niveau


ALLE = list(_pruefungen())


def _spec(name: str) -> dict:
    datei, wer = name.split(":")
    return _spec_mit_herkunft(Pack.load(KURATIERT / datei), int(wer[0]), wer[1])


def _spalten(xml: str):
    """Die Spalten eines Doppelblatts: Blatt 1 links, rechts, Blatt 2 ..."""
    root = etree.fromstring(xml.encode("utf-8"))
    teile = [[]]
    for k in root.find(f"{W}body"):
        if k.tag == f"{W}sectPr":
            continue
        if k.find(f".//{W}br[@{W}type='column']") is not None:
            teile.append([])
        else:
            teile[-1].append(k)
    return teile, root


def _doppel_xml(spec: dict) -> str:
    return db.als_doppelblatt(build_document_xml(spec), db.hoehen(spec))


def _text(elemente) -> list[str]:
    zeilen = []
    for el in elemente:
        for p in el.iter(f"{W}p"):
            zeile = "".join(t.text or "" for t in p.iter(f"{W}t"))
            if zeile.strip():
                zeilen.append(zeile)
    return zeilen


# ---------------------------------------------------------------------------
# Zweimal dieselbe Prüfung - und es ist die des A4-Blatts
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", [n for n, *_ in ALLE])
def test_links_und_rechts_steht_dasselbe_und_es_ist_die_pruefung(name):
    spec = _spec(name)
    teile, _ = _spalten(_doppel_xml(spec))
    assert len(teile) % 2 == 0 and len(teile) // 2 == len(db.aufteilung(spec))
    links = []
    for blatt in range(len(teile) // 2):
        li, re_ = teile[2 * blatt], teile[2 * blatt + 1]
        assert [etree.tostring(e) for e in li] == [etree.tostring(e) for e in re_], \
            f"Blatt {blatt + 1}: links und rechts verschieden"
        links += li
    a4 = build_document_xml(spec)
    a4_text = _text(etree.fromstring(a4.encode("utf-8")).find(f"{W}body"))
    a4_text = [z.replace("_" * 78, db.SCHREIBLINIE) for z in a4_text]
    assert _text(links) == a4_text


def test_eine_lange_pruefung_geht_auf_ein_zweites_blatt_nicht_nach_rechts():
    """Sechs Aufgabenarten passen nicht auf eine halbe Seite.

    Einmal floss die erste Prüfung dann in die rechte Hälfte, und links und
    rechts stand nicht mehr dasselbe. Jetzt kommt ein zweites Blatt, und
    umbrochen wird zwischen zwei Aufgaben.
    """
    spec = _spec("unit_01_englishplus3.json:1A")
    assert len(db.aufteilung(spec)) == 2
    teile, _ = _spalten(_doppel_xml(spec))
    assert len(teile) == 4
    # Jede Seite beginnt mit dem Kopf oder mit einer Aufgabenstellung - nie
    # mitten in einer Aufgabe, und nie mit einer Leerzeile.
    for spalte in teile:
        erstes = spalte[0]
        kopf = erstes.tag == f"{W}tbl"
        stellung = erstes.find(f"{W}pPr/{W}tabs") is not None
        assert kopf or stellung, _text([erstes])


def test_die_wiederholung_kommt_aufs_zweite_blatt_wenn_sie_nicht_mehr_passt(tmp_path):
    from vocabmaster import wiederholung as wh
    for datei in ("unit_01.json", "unit_02.json"):
        (tmp_path / datei).write_bytes((KURATIERT / datei).read_bytes())
    pack = Pack.load(tmp_path / "unit_02.json")
    wh.setze(pack, 1, Pack.load(tmp_path / "unit_01.json"), 2, folge=True)
    spec = _spec_mit_herkunft(pack, 1, "A")
    assert len(db.aufteilung(spec)) == 2
    teile, _ = _spalten(_doppel_xml(spec))
    zweites = _text(teile[2])
    assert zweites[0].startswith("3) Revision"), zweites


def test_die_mitte_ist_die_mitte():
    """Nach dem Schnitt hat jede Hälfte links und rechts denselben Rand.

    Eine Schnittlinie wird nicht gedruckt - die Mitte findet die
    Schneidemaschine selbst.
    """
    _, root = _spalten(_doppel_xml(_spec("unit_02.json:1A")))
    sect = root.find(f"{W}body/{W}sectPr")
    seite, rand, spalten = (sect.find(f"{W}{t}") for t in ("pgSz", "pgMar", "cols"))
    breite, hoehe = int(seite.get(f"{W}w")), int(seite.get(f"{W}h"))
    assert breite > hoehe and seite.get(f"{W}orient") == "landscape"
    assert spalten.get(f"{W}num") == "2" and spalten.get(f"{W}sep") is None
    links, rechts = int(rand.get(f"{W}left")), int(rand.get(f"{W}right"))
    abstand = int(spalten.get(f"{W}space"))
    assert links == rechts and abstand == 2 * links
    spalte = (breite - links - rechts - abstand) / 2
    # Der Schnitt: Rand + Spalte + halber Abstand = halbe Seite.
    assert links + spalte + abstand / 2 == breite / 2


def test_jeder_lauf_ist_klein_gesetzt_und_in_schemareihenfolge():
    """Kein Lauf fällt auf die 12 pt der Vorlage zurück - und Word liest es.

    Ein Lauf ohne eigene Grösse erbte die Grundschrift, und eine halbe
    Prüfung stünde in A4-Schrift da. Die Reihenfolge der Kinder von
    ``w:rPr`` ist im Schema festgelegt; Word meldet sonst ein beschädigtes
    Dokument.
    """
    reihe = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "kern", "sz", "szCs", "lang"]
    for name in ("unit_02.json:1A", "unit_01_englishplus3.json:1A"):
        root = etree.fromstring(_doppel_xml(_spec(name)).encode("utf-8"))
        for r in root.iter(f"{W}r"):
            rpr = r.find(f"{W}rPr")
            assert rpr is not None and rpr.find(f"{W}sz") is not None, name
            assert int(rpr.find(f"{W}sz").get(f"{W}val")) <= 25
            tags = [etree.QName(k).localname for k in rpr]
            bekannt = [t for t in tags if t in reihe]
            assert bekannt == sorted(bekannt, key=reihe.index), tags
        for ppr in root.iter(f"{W}pPr"):
            tags = [etree.QName(k).localname for k in ppr]
            if "tabs" in tags and "spacing" in tags:
                assert tags.index("tabs") < tags.index("spacing")
            if "spacing" in tags and "rPr" in tags:
                assert tags.index("spacing") < tags.index("rPr")


def test_die_punktzahl_steht_rechtsbuendig_statt_hinter_fuenf_tabulatoren():
    root = etree.fromstring(_doppel_xml(_spec("unit_02.json:1A")).encode("utf-8"))
    for p in root.iter(f"{W}p"):
        tabs = p.findall(f"{W}r/{W}tab")
        if tabs:
            assert len(tabs) == 1
            stop = p.find(f"{W}pPr/{W}tabs/{W}tab")
            assert stop.get(f"{W}val") == "right"
            assert stop.get(f"{W}pos") == str(db.SPALTE)


# ---------------------------------------------------------------------------
# Passt es in die Hälfte?
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(GEMESSEN))
def test_die_schaetzung_liegt_nie_unter_der_messung(name):
    """Die gefährliche Richtung ist die zu tiefe Schätzung.

    Schätzt sie zu hoch, bekommt eine Prüfung ein zweites Blatt, das sie
    nicht gebraucht hätte - ärgerlich. Schätzt sie zu tief, läuft eine Seite
    in die rechte Hälfte, und links und rechts steht nicht mehr dasselbe.
    Wo die Messung eine Seite zeigt, muss die Schätzung eine Seite planen -
    und darf dabei nie unter der Messung liegen.
    """
    spec = _spec(name)
    gemessen, geschaetzt = GEMESSEN[name], db.hoehe(spec)
    eine_seite = gemessen <= db.SPALTE_HOCH
    assert (len(db.aufteilung(spec)) == 1) == eine_seite, (name, geschaetzt, gemessen)
    if eine_seite:
        assert gemessen <= geschaetzt <= gemessen * 1.15, (name, geschaetzt, gemessen)


def test_die_gewohnte_pruefung_bleibt_auf_einem_blatt():
    """Übersetzen und Lückentext, zwölf Wörter - jede mitgelieferte: ein Blatt."""
    for name, pack, teil, niveau in ALLE:
        arten = {a.get("art") for a in pack.exam(teil, niveau).get("aufgaben", [])} \
            or {"uebersetzen", "luecken"}
        if arten <= {"uebersetzen", "luecken"}:
            assert len(db.aufteilung(_spec(name))) == 1, name


def _riesig(spec: dict) -> dict:
    """Eine Übersetzung mit 30 Wörtern - höher als eine halbe Seite."""
    aufgaben = [dict(a) for a in aufgaben_des_specs(spec)]
    ueb = next(a for a in aufgaben if a["art"] == "uebersetzen")
    ueb["items"] = (ueb["items"] * 4)[:30]
    rest = {k: v for k, v in spec.items() if k not in ("task1", "task2", "task3")}
    return {**rest, "aufgaben": aufgaben}


def test_eine_einzelne_aufgabe_hoeher_als_die_halbe_seite_passt_nicht():
    passt, prozente = db.passt(_riesig(_spec("unit_02.json:1A")))
    assert not passt and max(prozente) > 100


def test_was_nicht_passt_wird_nicht_als_doppelblatt_gebaut(tmp_path, settings, monkeypatch):
    import vocabmaster.documents as documents
    echt = documents._spec_mit_herkunft
    monkeypatch.setattr(documents, "_spec_mit_herkunft",
                        lambda *a, **k: _riesig(echt(*a, **k)))
    pack = Pack.load(KURATIERT / "unit_02.json")
    ergebnis = baue_alles(pack, tmp_path, settings, ("test",), niveaus=("A",),
                          pruefungsteile=(1,), blatt="a5")
    assert not ergebnis.ok
    assert not list(tmp_path.glob("*.docx")), "a5 bestellt - weder Doppel- noch A4-Blatt"
    text = " ".join(str(b) for b in ergebnis.bericht.befunde)
    assert "nicht gebaut" in text and "--blatt a4" in text
    # Bei "beide" bleibt das A4-Blatt samt Lösung.
    baue_alles(pack, tmp_path, settings, ("test",), niveaus=("A",),
               pruefungsteile=(1,), blatt="beide")
    assert sorted(p.name for p in tmp_path.glob("*.docx")) == [
        "Unit02_V1_Test_PartI_NiveauA.docx", "Unit02_V1_Test_PartI_NiveauA_Loesung.docx"]


def test_der_bericht_sagt_wie_viele_blaetter_und_wie_man_druckt(tmp_path, settings):
    ergebnis = baue_alles(Pack.load(KURATIERT / "unit_01_englishplus3.json"), tmp_path,
                          settings, ("test",), niveaus=("B",), pruefungsteile=(1,),
                          blatt="a5", mit_loesung=False)
    text = " ".join(str(b) for b in ergebnis.bericht.befunde)
    assert "2 Blätter A4 quer" in text and "Beidseitig drucken" in text


# ---------------------------------------------------------------------------
# Bauen, benennen, nachkontrollieren
# ---------------------------------------------------------------------------
def test_dateiname():
    assert dateiname(2, "Test", 1, "A", doppelblatt=True) == \
        "Unit02_V1_Test_PartI_NiveauA_2xA5.docx"
    assert dateiname(1, "Test", 1, "A", fassung=3, doppelblatt=True,
                     lehrmittel="EnglishPlus3") == \
        "EnglishPlus3_Unit01_V1_Test_PartI_NiveauA_Fassung3_2xA5.docx"
    # Das Lösungsblatt ist immer A4 - es trägt die Endung nie.
    assert dateiname(2, "Test", 1, "A", loesung=True, doppelblatt=True) == \
        "Unit02_V1_Test_PartI_NiveauA_Loesung.docx"


def test_a5_baut_doppelblatt_und_loesung_aber_kein_a4_blatt(tmp_path, settings):
    pack = Pack.load(KURATIERT / "unit_02.json")
    ergebnis = baue_alles(pack, tmp_path, settings, ("test",), niveaus=("B",),
                          pruefungsteile=(2,), blatt="a5")
    assert ergebnis.ok, ergebnis.bericht.befunde
    assert sorted(p.name for p in tmp_path.glob("*.docx")) == [
        "Unit02_V1_Test_PartII_NiveauB_2xA5.docx",
        "Unit02_V1_Test_PartII_NiveauB_Loesung.docx",
    ]


def test_das_a4_blatt_bleibt_byte_fuer_byte(tmp_path, settings):
    """Wer nichts umstellt, bekommt das Blatt von gestern."""
    pack = Pack.load(KURATIERT / "unit_02.json")
    spec = _spec_mit_herkunft(pack, 1, "A")
    vorher = build_docx(spec, str(settings.exam_template), str(tmp_path / "vorher.docx"))
    ziel = tmp_path / "neu" / "Unit02_V1_Test_PartI_NiveauA.docx"
    for blatt in ("a4", "beide"):
        schreibe_pruefung(pack, 1, "A", ziel, settings, mit_loesung=False, blatt=blatt)
        assert ziel.read_bytes() == Path(vorher).read_bytes(), blatt


def test_die_nachkontrolle_besteht_das_gebaute_doppelblatt(tmp_path, settings):
    ergebnis = baue_alles(Pack.load(KURATIERT / "unit_07.json"), tmp_path, settings,
                          ("test",), blatt="a5")
    assert ergebnis.ok, [str(b) for b in ergebnis.bericht.befunde]
    assert len(list(tmp_path.glob("*_2xA5.docx"))) == 4


def _doppel(tmp_path, settings, name="unit_02.json:1A") -> tuple[Path, dict]:
    """Ein gebautes Doppelblatt - zum Verderben in den Tests darunter."""
    spec = _spec(name)
    pfad = tmp_path / "Test_2xA5.docx"
    db.build_doppelblatt(spec, str(settings.exam_template), str(pfad))
    return pfad, spec


def _umschreiben(pfad: Path, aendern) -> None:
    with zipfile.ZipFile(pfad) as zf:
        teile = {i.filename: zf.read(i.filename) for i in zf.infolist()}
    teile["word/document.xml"] = aendern(teile["word/document.xml"].decode()).encode()
    with zipfile.ZipFile(pfad, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, daten in teile.items():
            zf.writestr(name, daten)


def _fehler(pfad, spec, settings, check=None):
    return [f for f in verify_document(str(pfad), spec, str(settings.exam_template),
                                       doppelblatt=True)
            if f.level == "ERROR" and (check is None or f.check == check)]


def test_nachkontrolle_findet_zwei_verschiedene_haelften(tmp_path, settings):
    pfad, spec = _doppel(tmp_path, settings)
    assert not _fehler(pfad, spec, settings)
    # Die rechte Hälfte fragt ein anderes Stichwort ab.
    _umschreiben(pfad, lambda x: _letztes_ersetzen(x, "Fazit", "Ergebnis"))
    befunde = _fehler(pfad, spec, settings, "doppelblatt")
    assert any("sheet 1: left and right differ" in f.message for f in befunde)


def test_nachkontrolle_findet_verschiedene_haelften_auf_dem_zweiten_blatt(tmp_path, settings):
    pfad, spec = _doppel(tmp_path, settings, "unit_01_englishplus3.json:1B")
    assert not _fehler(pfad, spec, settings)
    _umschreiben(pfad, lambda x: _letztes_ersetzen(x, "comic", "cartoon"))
    befunde = _fehler(pfad, spec, settings, "doppelblatt")
    assert any("sheet 2: left and right differ" in f.message for f in befunde)


def _letztes_ersetzen(text: str, alt: str, neu: str) -> str:
    i = text.rfind(alt)
    return text[:i] + neu + text[i + len(alt):]


def test_nachkontrolle_findet_einen_schiefen_schnitt(tmp_path, settings):
    pfad, spec = _doppel(tmp_path, settings)
    _umschreiben(pfad, lambda x: x.replace(f'w:space="{db.ABSTAND}"', 'w:space="700"'))
    assert any("margins" in f.message for f in _fehler(pfad, spec, settings, "doppelblatt"))


def test_nachkontrolle_findet_ein_blatt_ohne_spaltenumbruch(tmp_path, settings):
    pfad, spec = _doppel(tmp_path, settings)
    _umschreiben(pfad, lambda x: x.replace('<w:br w:type="column"/>', ""))
    assert any("not the same page twice" in f.message
               for f in _fehler(pfad, spec, settings, "doppelblatt"))


def test_nachkontrolle_findet_eine_verratene_loesung_auf_dem_doppelblatt(tmp_path, settings):
    pfad, spec = _doppel(tmp_path, settings)
    wort = next(a for a in aufgaben_des_specs(spec)
                if a["art"] == "uebersetzen")["items"][0]["english"]
    # In beiden Hälften - sonst meldete schon der Hälftenvergleich.
    _umschreiben(pfad, lambda x: x.replace("Nobody in the room", f"Nobody ({wort}) in the room"))
    assert any(f.check == "leak" for f in _fehler(pfad, spec, settings))


def test_nachkontrolle_findet_eine_haelfte_die_nicht_dem_a4_blatt_entspricht(tmp_path, settings):
    pfad, spec = _doppel(tmp_path, settings)
    _umschreiben(pfad, lambda x: re.sub(r"Last year", "Two years ago", x))
    assert any("A4 sheet" in f.message for f in _fehler(pfad, spec, settings, "doppelblatt"))


def test_das_blatt_zaehlt_seine_blaetter_selbst(tmp_path, settings):
    """Ein Doppelblatt mit einem Blatt zu wenig ist eine halbe Prüfung."""
    pfad, spec = _doppel(tmp_path, settings, "unit_01_englishplus3.json:1A")
    with zipfile.ZipFile(pfad) as zf:
        x = zf.read("word/document.xml").decode()
    # Das zweite Blatt entfernen: alles ab dem zweiten Spaltenumbruch.
    marke = '<w:br w:type="column"/>'
    zweiter = x.index(marke, x.index(marke) + 1)
    absatz = x.rindex("<w:p>", 0, zweiter)
    rest = x[x.index("<w:sectPr>"):]
    _umschreiben(pfad, lambda _: x[:absatz] + rest)
    befunde = _fehler(pfad, spec, settings, "doppelblatt")
    assert any("A4 sheet" in f.message or "page plan" in f.message for f in befunde)
