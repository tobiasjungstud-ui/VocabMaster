"""Was sich erst im Nebeneinander zeigt.

`vocabmaster prüfen` sieht immer nur ein Paket. Zwei Pakete, die auf
dieselben Word-Dateien zielen, oder eine Fassung ohne ihre Liste fallen dort
durch - und genau das wäre der Fehler, der beim Austeilen auffliegt.
"""

from __future__ import annotations

import json

import pytest

from vocabmaster.cli import _bestand_pruefen
from vocabmaster.pack import Pack, kennzeichen


def _schluessel(pack: Pack) -> tuple[str, int]:
    """Gruppiert wird nach Lehrmittel **und** Unit - zwei Lehrmittel dürfen
    dieselbe Unit 1 haben, ohne einander in die Quere zu kommen."""
    return (kennzeichen(pack.lehrmittel), pack.unit)


def _paket(tmp_path, name: str, roh: dict) -> Pack:
    pfad = tmp_path / name
    pfad.write_text(json.dumps(roh, ensure_ascii=False), encoding="utf-8")
    return Pack.load(pfad)


@pytest.fixture
def bestand(pack, tmp_path):
    """Ein sauberer Bestand: eine Unit, eine Liste, eine Fassung."""
    roh = json.loads(json.dumps(pack.data))
    return {_schluessel(pack): [_paket(tmp_path, "unit_01.json", roh)]}


def test_sauberer_bestand_meldet_nichts(bestand):
    assert _bestand_pruefen(bestand) == []


def test_zwei_pakete_auf_denselben_dateinamen(bestand, pack, tmp_path):
    """Der teuerste Fall: beide schreiben Unit01_V1_… und überschreiben sich."""
    roh = json.loads(json.dumps(pack.data))
    bestand[_schluessel(pack)].append(_paket(tmp_path, "zwilling.json", roh))
    befunde = _bestand_pruefen(bestand)
    assert any("dieselben Word-Dateien" in b for b in befunde)
    assert any(b.startswith("FEHLER") for b in befunde)


def test_fassung_ohne_ihre_liste(bestand, pack, tmp_path):
    roh = json.loads(json.dumps(pack.data))
    roh["liste_version"] = 7
    roh["fassung"] = 2
    bestand[_schluessel(pack)].append(_paket(tmp_path, "unit_01_v7_fassung2.json", roh))
    befunde = _bestand_pruefen(bestand)
    assert any("diese Liste gibt es nicht" in b for b in befunde)


def test_zwei_listen_mit_demselben_inhalt(bestand, pack, tmp_path):
    """V2, die Wort für Wort V1 ist, ist keine zweite Liste."""
    roh = json.loads(json.dumps(pack.data))
    roh["liste_version"] = 2
    bestand[_schluessel(pack)].append(_paket(tmp_path, "unit_01_v2.json", roh))
    befunde = _bestand_pruefen(bestand)
    assert any("dieselben 60 Wörter" in b for b in befunde)


def test_pruefung_an_fremder_liste(bestand, pack, tmp_path):
    roh = json.loads(json.dumps(pack.data))
    roh["liste_version"] = 2
    roh["pruefungen"]["teil1"]["A"]["meta"]["liste_fingerabdruck"] = "0000dead0000"
    bestand[_schluessel(pack)].append(_paket(tmp_path, "unit_01_v2.json", roh))
    befunde = _bestand_pruefen(bestand)
    assert any("hängt an einer anderen Liste" in b for b in befunde)


def test_luecke_in_der_nummerierung(bestand, pack, tmp_path):
    roh = json.loads(json.dumps(pack.data))
    roh["liste_version"] = 3
    bestand[_schluessel(pack)].append(_paket(tmp_path, "unit_01_v3.json", roh))
    befunde = _bestand_pruefen(bestand)
    assert any("Nummerierung hat eine Lücke" in b for b in befunde)


def test_zwei_lehrmittel_mit_derselben_unit_sind_kein_fehler(
        bestand, pack, tmp_path):
    """Dieselbe Unit 1, dieselbe V1 - aber ein anderes Lehrmittel.

    Die Dateinamen tragen die Kennung des zweiten Lehrmittels und fallen
    deshalb nicht zusammen. Vor dieser Unterscheidung meldete der Bestand
    hier einen Fehler, den es nicht gab - und wer ihn zu beheben versuchte,
    hätte eines der beiden Pakete gelöscht.
    """
    roh = json.loads(json.dumps(pack.data))
    roh["lehrmittel"] = "EnglishPlus3"
    fremd = _paket(tmp_path, "unit_01_englishplus3.json", roh)
    bestand[_schluessel(fremd)] = [fremd]
    assert _schluessel(fremd) != _schluessel(pack)
    assert not [b for b in _bestand_pruefen(bestand)
                if "dieselben Word-Dateien" in b]
