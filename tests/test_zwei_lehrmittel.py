"""Zwei Lehrmittel, dieselbe Unit-Nummer - und trotzdem eigene Dateien.

Ein Paket gehört zu der Datenbank, deren **Prüfsumme** es trägt; zwei
Lehrmittel dürfen dieselbe Unit 3 haben. Die **Dateinamen** hingen aber
allein an der Unit-Nummer. Unit 1 von English Plus 3 hätte damit
``kuratiert/unit_01.json`` und ``Unit01_V1_VocabularyList.docx`` von English
Plus 4 überschrieben - Paket, Vokabelliste und vier Prüfungen, und niemand
hätte es gemerkt, bis eine Klasse die Wörter eines anderen Lehrmittels
abgefragt bekommt.

Die Grunddatenbank behält ihre Namen: Sonst hiesse jede bestehende Datei
von heute auf morgen anders, und jedes schon ausgeteilte Blatt zeigte auf
einen Namen, den es nicht mehr gibt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vocabmaster import datenbanken as dbs
from vocabmaster.config import Settings
from vocabmaster.database import Database
from vocabmaster.documents import dateiname
from vocabmaster.pack import (
    Pack,
    kennzeichen,
    lehrmittel_von,
    pack_filename,
    scaffold,
)

from .helpers import fill

ZWEITES = "EnglishPlus3"


@pytest.fixture(scope="module")
def zweites() -> Database:
    """Die zweite mitgelieferte Datenbank - sonst überspringen."""
    eintrag = dbs.finde(ZWEITES)
    if eintrag is None or not eintrag.vorhanden:
        pytest.skip(f"{ZWEITES} ist hier nicht eingelesen")
    return Database.load(eintrag.verzeichnis)


def test_die_grunddatenbank_heisst_wie_bisher():
    """Kein bestehender Name darf sich ändern."""
    assert kennzeichen("") == ""
    assert kennzeichen(dbs.GRUNDEINTRAG["name"]) == ""
    assert pack_filename(1) == "unit_01.json"
    assert pack_filename(1, liste_version=2) == "unit_01_v2.json"
    assert pack_filename(1, fassung=3, liste_version=2) == "unit_01_v2_fassung3.json"
    assert dateiname(3, "VocabularyList") == "Unit03_V1_VocabularyList.docx"
    assert dateiname(3, "Test", 1, "B") == "Unit03_V1_Test_PartI_NiveauB.docx"


def test_ein_zweites_lehrmittel_bekommt_eigene_namen():
    assert pack_filename(1, lehrmittel=ZWEITES) == "unit_01_englishplus3.json"
    assert pack_filename(1, liste_version=2, lehrmittel=ZWEITES) == (
        "unit_01_englishplus3_v2.json")
    assert pack_filename(1, fassung=3, liste_version=2, lehrmittel=ZWEITES) == (
        "unit_01_englishplus3_v2_fassung3.json")
    assert dateiname(1, "VocabularyList", lehrmittel=ZWEITES) == (
        "EnglishPlus3_Unit01_V1_VocabularyList.docx")
    assert dateiname(1, "Test", 1, "A", loesung=True, lehrmittel=ZWEITES) == (
        "EnglishPlus3_Unit01_V1_Test_PartI_NiveauA_Loesung.docx")


def test_die_kennung_steht_hinter_der_unit():
    """Jede Stelle, die den Bestand durchgeht, sucht ``unit_*.json``."""
    name = pack_filename(1, lehrmittel=ZWEITES)
    assert Path(name).match("unit_*.json"), (
        f"{name} würde von 'vocabmaster listen' und von der Werkstatt "
        "schlicht übersehen")


def test_kein_name_faellt_mit_dem_anderen_zusammen():
    """Der Fehler, um den es geht: dieselbe Unit, dieselbe Datei."""
    fuer_jede = [
        lambda lm: pack_filename(1, lehrmittel=lm),
        lambda lm: dateiname(1, "VocabularyList", lehrmittel=lm),
        lambda lm: dateiname(1, "Test", 1, "A", lehrmittel=lm),
        lambda lm: dateiname(1, "Test", 2, "B", loesung=True, lehrmittel=lm),
    ]
    for mach in fuer_jede:
        assert mach("") != mach(ZWEITES)


def test_das_geruest_notiert_sein_lehrmittel(db, zweites, settings):
    """Der Name wird einmal notiert - der Dateiname hängt daran."""
    assert lehrmittel_von(db) == "", "die Grunddatenbank notiert nichts"
    assert lehrmittel_von(zweites) == ZWEITES

    grund = Pack(data=scaffold(db, 1, settings))
    zweit = Pack(data=scaffold(zweites, 1, Settings()))
    assert grund.lehrmittel == ""
    assert zweit.lehrmittel == ZWEITES
    assert grund.unit == zweit.unit == 1, "dieselbe Unit-Nummer - das ist erlaubt"
    assert grund.quelle["pruefsumme_sha256"] != zweit.quelle["pruefsumme_sha256"]


def test_beide_pakete_liegen_nebeneinander(db, zweites, settings, tmp_path):
    """Nebeneinander in einem Ordner, ohne sich zu überschreiben."""
    grund = Pack(data=scaffold(db, 1, settings))
    zweit = Pack(data=scaffold(zweites, 1, Settings()))
    a = grund.save(tmp_path / pack_filename(grund.unit, lehrmittel=grund.lehrmittel))
    b = zweit.save(tmp_path / pack_filename(zweit.unit, lehrmittel=zweit.lehrmittel))
    assert a != b
    assert sorted(p.name for p in tmp_path.glob("unit_*.json")) == [
        "unit_01.json", "unit_01_englishplus3.json"]


def test_ein_paket_ohne_das_feld_heisst_wie_bisher(pack):
    """Die mitgelieferten Pakete kennen das Feld nicht.

    Sie sind vor dieser Unterscheidung entstanden. Ein fehlendes Feld heisst
    deshalb "Grunddatenbank" - und ihre Dateien heissen weiter, wie sie
    heute heissen.
    """
    alt = Pack(data={k: v for k, v in pack.data.items() if k != "lehrmittel"})
    assert alt.lehrmittel == ""
    assert pack_filename(alt.unit, lehrmittel=alt.lehrmittel) == "unit_01.json"
    assert dateiname(alt.unit, "VocabularyList",
                     lehrmittel=alt.lehrmittel) == (
        "Unit01_V1_VocabularyList.docx")


# ---------------------------------------------------------------------------
# Eine Liste, die gegeben ist statt gewählt
# ---------------------------------------------------------------------------
def test_eine_gegebene_liste_haelt_den_bau_nicht_auf(db, settings):
    """Drei Befunde beurteilen die Wahl - bei einer gegebenen gibt es keine.

    Die Liste kommt fertig aus dem Word-Dokument der Lehrperson: eigene
    Aufteilung, eigene Sätze, eigene Paare wie 'adapt' und 'adaptation'.
    Die Anwendung soll das sagen, aber nicht verhindern - sonst liesse sich
    die eigene Liste gar nicht bauen.
    """
    from vocabmaster.checks import Pruefbericht, pruefe_liste

    pack = Pack(data=fill(scaffold(db, 1, settings)))
    # Ein Wort weniger, und zwei, die dasselbe prüfen: dasselbe Wort
    # zweimal, samt seinem Satz - so, wie es in einer von Hand
    # geschriebenen Liste vorkommt.
    pack.data["liste"]["test1"] = pack.data["liste"]["test1"][:-1]
    zwei = pack.data["liste"]["test2"]
    zwei[1] = {**zwei[0], "nr": zwei[1]["nr"]}

    ohne = Pruefbericht()
    pruefe_liste(pack, settings, ohne)
    assert ohne.fehler, "ohne Angabe bleibt es ein Fehler"

    pack.data["liste_gegeben"] = "Word-Dokument der Lehrperson"
    mit = Pruefbericht()
    pruefe_liste(pack, settings, mit)
    assert not mit.fehler, "\n".join(str(b) for b in mit.fehler)
    assert any("gesagt, nicht beanstandet" in b.text for b in mit.warnungen), (
        "verschwiegen werden darf es nicht")


def test_eine_gegebene_liste_entschuldigt_keinen_echten_mangel(db, settings):
    """Was in jeder Liste ein Fehler wäre, bleibt einer."""
    from vocabmaster.checks import Pruefbericht, pruefe_liste

    pack = Pack(data=fill(scaffold(db, 1, settings)))
    pack.data["liste_gegeben"] = "Word-Dokument der Lehrperson"
    pack.data["liste"]["test1"][0] = {
        **pack.data["liste"]["test1"][0], "deutsch": ""}

    bericht = Pruefbericht()
    pruefe_liste(pack, settings, bericht)
    assert any("keine deutsche Übersetzung" in b.text for b in bericht.fehler)
