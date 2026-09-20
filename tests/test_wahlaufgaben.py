"""Aufgabe 3 - welcher der drei Sätze verwendet das Wort richtig?

Zwei Sätze verwenden die Vokabel falsch, einer richtig, und die Klasse
kreuzt an. Geprüft wird damit etwas, das Übersetzen und Einsetzen beide
nicht prüfen: nicht was das Wort heisst, sondern **wie** man es gebraucht.

Die Aufgabe ist abwählbar und voreingestellt aus. Der erste Test hier ist
deshalb der wichtigste: Ohne Bestellung darf sich an einem Paket und an
seinem Dokument **nichts** ändern.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from vocabmaster import cli
from vocabmaster.checks import Pruefbericht, pruefe_wahlaufgaben
from vocabmaster.config import Settings
from vocabmaster.database import Database
from vocabmaster.exam.builder import build_answer_key, build_document_xml, build_docx
from vocabmaster.exam.verify import (
    _page_estimate,
    document_text,
    tables,
    verify_document,
)
from vocabmaster.pack import Pack, scaffold

WURZEL = Path(__file__).resolve().parent.parent
WERKSTATT = WURZEL / "werkstatt"


@pytest.fixture(scope="module")
def db() -> Database:
    return Database.load(Settings().database)


@pytest.fixture(scope="module")
def ohne(db) -> dict:
    """Das Gerüst, wie es ohne Bestellung entsteht."""
    return scaffold(db, 1, Settings())


@pytest.fixture(scope="module")
def mit(db) -> dict:
    """Dasselbe Gerüst mit zwei Wahlaufgaben je Prüfung."""
    return scaffold(db, 1, replace(Settings(), exam_choice_items=2))


def _pruefungen(paket: dict):
    for teil in ("teil1", "teil2"):
        for niveau in ("A", "B"):
            yield teil, niveau, paket["pruefungen"][teil][niveau]


# ---------------------------------------------------------------------------
# Ohne Bestellung ändert sich nichts
# ---------------------------------------------------------------------------
def test_ohne_bestellung_gibt_es_die_aufgabe_nicht(ohne):
    """Voreingestellt aus - sonst stünde sie in jedem Paket von gestern."""
    assert "task3" not in json.dumps(ohne)
    for _, _, spec in _pruefungen(ohne):
        xml = build_document_xml(spec)
        assert "3)" not in xml, "das Dokument zeigt eine Aufgabe 3"


def test_die_zwoelf_geprueften_woerter_bleiben_dieselben(ohne, mit):
    """Der teuerste denkbare Nebeneffekt, hier ausgeschlossen.

    Die Wortwahl der Wahlaufgabe läuft in einem **zweiten** Durchlauf über
    das, was der erste übrig gelassen hat. Würde stattdessen der erste
    Durchlauf grösser gemacht, verschöbe die Obergrenze je Wortart, welche
    zwölf Wörter die Prüfung abfragt - und die Prüfung wäre eine andere,
    ohne dass es jemand bestellt hätte.
    """
    for teil, niveau, spec in _pruefungen(mit):
        vorher = ohne["pruefungen"][teil][niveau]
        assert spec["task1"] == vorher["task1"], f"{teil} {niveau}: Aufgabe 1"
        assert spec["task2"] == vorher["task2"], f"{teil} {niveau}: Aufgabe 2"


# ---------------------------------------------------------------------------
# Mit Bestellung: die Form stimmt
# ---------------------------------------------------------------------------
def test_zwei_aufgaben_mit_je_drei_saetzen(mit):
    for teil, niveau, spec in _pruefungen(mit):
        items = spec["task3"]["items"]
        assert len(items) == 2, f"{teil} {niveau}"
        for item in items:
            assert len(item["saetze"]) == 3
            assert 1 <= item["richtig"] <= 3
            assert item["english"] and item["german"]


def test_das_wort_steht_in_keiner_anderen_aufgabe(mit):
    """Alle drei Sätze schreiben das Wort aus.

    Wäre es zugleich Lücke oder Übersetzung, stünde deren Lösung damit auf
    demselben Blatt - und die Prüfung prüfte dort nichts mehr.
    """
    for teil, niveau, spec in _pruefungen(mit):
        andere = {i["english"].lower() for i in spec["task1"]["items"]}
        andere |= {g["answer"].lower() for g in spec["task2"]["gaps"]}
        for item in spec["task3"]["items"]:
            assert item["english"].lower() not in andere, f"{teil} {niveau}"


def test_die_loesung_steht_nicht_immer_an_derselben_stelle(mit):
    """Sonst wäre die Aufgabe nach dem zweiten Blatt keine mehr."""
    stellen = {
        item["richtig"]
        for _, _, spec in _pruefungen(mit)
        for item in spec["task3"]["items"]
    }
    assert len(stellen) > 1, f"alle Lösungen stehen an Stelle {stellen}"


def test_offen_nennt_jeden_fehlenden_satz(mit, tmp_path):
    pfad = tmp_path / "unit_01.json"
    Pack(data=copy.deepcopy(mit)).save(pfad)
    offen = Pack.load(pfad).offen()
    wahl = [z for z in offen if "Wahlaufgabe" in z]
    assert len(wahl) == 8, "vier Prüfungen mal zwei Aufgaben"
    assert "Satz 1, 2, 3 fehlt" in wahl[0]


# ---------------------------------------------------------------------------
# Die Kontrolle - je ein eingebauter Fehler
# ---------------------------------------------------------------------------
@pytest.fixture
def geprueft() -> dict:
    """Ein Paket aus ``kuratiert/`` mit einer ausgefüllten Wahlaufgabe."""
    quelle = WURZEL / "kuratiert" / "unit_01.json"
    if not quelle.is_file():
        pytest.skip("kein Paket unter kuratiert/")
    daten = json.loads(quelle.read_text("utf-8"))
    daten["pruefungen"]["teil1"]["A"]["task3"] = {
        "instruction": "3)  Tick the sentence that uses the word correctly. ",
        "items": [{
            # Ein Wort, das in Test 1 wirklich steht und das diese Prüfung
            # nicht ohnehin abfragt - sonst prüfte der Test eine Lage, die
            # es so gar nicht gibt.
            "english": "adopt", "german": "adoptieren", "pos": "verb",
            "richtig": 2,
            "saetze": ["The adopt arrived late on Tuesday morning.",
                       "They decided to adopt a cat from the shelter.",
                       "He adopted the wall with a new colour."],
        }],
    }
    return daten


def _befunde(daten: dict) -> list[str]:
    bericht = Pruefbericht()
    pruefe_wahlaufgaben(Pack(data=daten), bericht)
    return [f"{b.stufe} {b.text}" for b in bericht.befunde]


def test_eine_saubere_wahlaufgabe_meldet_nichts(geprueft):
    assert _befunde(geprueft) == []


def test_zwei_saetze_sind_zu_wenige(geprueft):
    item = geprueft["pruefungen"]["teil1"]["A"]["task3"]["items"][0]
    item["saetze"] = item["saetze"][:2]
    assert any("FEHLER" in b and "Raten die halbe Miete" in b
               for b in _befunde(geprueft))


def test_eine_loesung_ausserhalb_der_saetze(geprueft):
    geprueft["pruefungen"]["teil1"]["A"]["task3"]["items"][0]["richtig"] = 5
    assert any("FEHLER" in b and "Lösung ist '5'" in b
               for b in _befunde(geprueft))


def test_ein_wort_das_auch_uebersetzt_wird(geprueft):
    spec = geprueft["pruefungen"]["teil1"]["A"]
    spec["task3"]["items"][0]["english"] = spec["task1"]["items"][0]["english"]
    assert any("FEHLER" in b and "auch übersetzt oder eingesetzt" in b
               for b in _befunde(geprueft))


def test_saetze_ohne_das_wort_pruefen_nichts(geprueft):
    geprueft["pruefungen"]["teil1"]["A"]["task3"]["items"][0]["saetze"] = [
        "One two three four.", "Five six seven eight.", "Nine ten eleven.",
    ]
    assert any("FEHLER" in b and "In keinem der Sätze" in b
               for b in _befunde(geprueft))


def test_eine_gebeugte_form_ist_nur_eine_warnung(geprueft):
    """Die Anwendung konjugiert nicht - ein Fehlalarm wäre schlimmer."""
    geprueft["pruefungen"]["teil1"]["A"]["task3"]["items"][0]["saetze"][2] = \
        "He painted the wall with a new colour."
    befunde = _befunde(geprueft)
    assert any("WARNUNG" in b and "nicht zu erkennen" in b for b in befunde)
    assert not any("FEHLER" in b for b in befunde)


def test_zweimal_derselbe_satz(geprueft):
    saetze = geprueft["pruefungen"]["teil1"]["A"]["task3"]["items"][0]["saetze"]
    saetze[2] = saetze[0]
    assert any("FEHLER" in b and "derselbe" in b for b in _befunde(geprueft))


def test_der_richtige_satz_darf_nicht_der_laengste_sein(geprueft):
    """Wer den langen ankreuzt, ohne zu lesen, hat ihn trotzdem."""
    geprueft["pruefungen"]["teil1"]["A"]["task3"]["items"][0]["saetze"][1] = (
        "They swap stickers during the lunch break every single day of "
        "the school week."
    )
    assert any("HINWEIS" in b and "durch seine Länge auf" in b
               for b in _befunde(geprueft))


# ---------------------------------------------------------------------------
# Das Dokument
# ---------------------------------------------------------------------------
def test_das_blatt_zeigt_die_aufgabe_und_nicht_die_loesung(geprueft, tmp_path):
    spec = geprueft["pruefungen"]["teil1"]["A"]
    vorlage = Settings().exam_template
    blatt = tmp_path / "blatt.docx"
    loesung = tmp_path / "loesung.docx"
    build_docx(spec, vorlage, blatt)
    build_answer_key(spec, vorlage, loesung)

    text = document_text(str(blatt))
    assert "3)  Tick the sentence that uses the word correctly." in text
    assert "1P" in text, "die Punktzahl der Aufgabe fehlt"
    for satz in spec["task3"]["items"][0]["saetze"]:
        assert satz in text
    assert "Solution:" not in text, "die Lösung steht auf dem Blatt"
    # Der Kopf und die Übersetzungstabelle - mehr Tabellen hat das
    # Referenzlayout nicht, und die Wahlaufgabe braucht keine.
    assert len(tables(str(blatt))) == 2

    assert "Solution: b)" in document_text(str(loesung))


def test_die_nachkontrolle_liest_die_aufgabe_zurueck(geprueft, tmp_path):
    spec = geprueft["pruefungen"]["teil1"]["A"]
    vorlage = Settings().exam_template
    blatt = tmp_path / "blatt.docx"
    build_docx(spec, vorlage, blatt)
    befunde = verify_document(str(blatt), spec, str(vorlage))
    schwer = [f for f in befunde if f.level == "ERROR"]
    assert not schwer, [f.message for f in schwer]


def test_zwei_aufgaben_passen_auf_die_seite_drei_nicht(geprueft):
    """Das Blatt muss auf eine A4-Seite - sonst sagt es das."""
    spec = geprueft["pruefungen"]["teil1"]["A"]
    eine = spec["task3"]["items"][0]
    for anzahl, seiten in ((1, 1), (2, 1), (3, 2)):
        probe = copy.deepcopy(spec)
        probe["task3"]["items"] = [copy.deepcopy(eine) for _ in range(anzahl)]
        assert _page_estimate(probe) == seiten, f"{anzahl} Wahlaufgaben"


# ---------------------------------------------------------------------------
# Befehl und Oberfläche
# ---------------------------------------------------------------------------
def test_die_flagge_steht_bei_geruest_liste_neu_und_fassung(tmp_path, capsys):
    assert cli.main(["gerüst", "1", "-o", str(tmp_path),
                     "--wahlaufgaben", "2"]) == 0
    capsys.readouterr()
    paket = Pack.load(tmp_path / "unit_01.json")
    assert len(paket.exam(1, "A")["task3"]["items"]) == 2

    assert cli.main(["fassung", str(tmp_path / "unit_01.json"), "--teil", "1",
                     "--niveau", "A", "--wahlaufgaben", "1",
                     "--verzeichnis", str(tmp_path)]) == 0
    neu = Pack.load(tmp_path / "unit_01_fassung2.json")
    assert len(neu.exam(1, "A")["task3"]["items"]) == 1

    capsys.readouterr()
    assert cli.main(["liste-neu", str(tmp_path / "unit_01.json"),
                     "--wahlaufgaben", "2",
                     "--verzeichnis", str(tmp_path)]) == 0
    v2 = Pack.load(tmp_path / "unit_01_v2.json")
    assert len(v2.exam(1, "A")["task3"]["items"]) == 2


def test_ohne_flagge_bleibt_der_befehl_wie_er_war(tmp_path, capsys):
    assert cli.main(["gerüst", "1", "-o", str(tmp_path)]) == 0
    capsys.readouterr()
    assert "task3" not in (tmp_path / "unit_01.json").read_text("utf-8")


def test_die_seite_bietet_die_aufgabe_an():
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    assert 'id="wahl"' in seite and 'id="wahlAnzahl"' in seite
    # Der Auftragssatz muss beides nennen: die Zahl und wozu die drei Sätze
    # da sind. "Wahlaufgabe: 2" allein sagt niemandem, was zu schreiben ist.
    körper = seite[seite.index("function befehlstext("):]
    körper = körper[:körper.index("\n}")]
    assert "--wahlaufgaben" in körper
    assert "falsch" in körper and "drei Sätze" in körper


def test_die_seite_zeigt_die_aufgabe_in_der_pruefungskarte():
    """Was auf dem Blatt steht, muss man ansehen können, bevor man baut."""
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    assert "function wahlblock(" in seite
    assert "wahlblock(pr.wahl)" in seite
    quelle = (WERKSTATT / "export.py").read_text("utf-8")
    assert '"wahl": [' in quelle, "daten.json trägt die Aufgabe nicht"
