"""Mehrere Vokabeldatenbanken nebeneinander.

Auch hier gilt: Der bisherige Weg muss unverändert funktionieren. Wer
nichts angibt, bekommt dieselbe Datenbank wie zuvor; wer einen Pfad
angibt, bekommt diesen Pfad.
"""

from __future__ import annotations

import json

import pytest

from vocabmaster import datenbanken as dbs
from vocabmaster.config import DEFAULT_DATABASE


def test_ohne_angabe_die_bisherige(monkeypatch, tmp_path):
    assert dbs.aufloesen(None) == DEFAULT_DATABASE
    assert dbs.aufloesen("") == DEFAULT_DATABASE


def test_ein_pfad_bleibt_ein_pfad(tmp_path):
    """Jede bisherige Aufrufform muss gültig bleiben."""
    assert dbs.aufloesen(str(tmp_path)) == tmp_path
    assert dbs.aufloesen(tmp_path) == tmp_path


def test_der_grundeintrag_ist_immer_da():
    namen = [d.name for d in dbs.alle()]
    assert dbs.GRUNDEINTRAG["name"] in namen
    grund = dbs.finde(dbs.GRUNDEINTRAG["name"])
    assert grund is not None
    assert grund.verzeichnis == DEFAULT_DATABASE
    assert grund.vorhanden, "die mitgelieferte Datenbank muss auffindbar sein"


def test_name_wird_zu_verzeichnis():
    assert dbs.aufloesen("EnglishPlus4") == DEFAULT_DATABASE
    assert dbs.aufloesen("englishplus4") == DEFAULT_DATABASE, "Schreibweise egal"


def test_kaputte_registratur_legt_nichts_lahm(monkeypatch, tmp_path):
    """Ein fehlerhaftes JSON darf die Anwendung nicht anhalten."""
    kaputt = tmp_path / "datenbanken.json"
    kaputt.write_text("{ das ist kein JSON", encoding="utf-8")
    monkeypatch.setattr(dbs, "REGISTER", kaputt)
    namen = [d.name for d in dbs.alle()]
    assert namen == [dbs.GRUNDEINTRAG["name"]]
    assert dbs.aufloesen(None) == DEFAULT_DATABASE


def test_fehlende_registratur_legt_nichts_lahm(monkeypatch, tmp_path):
    monkeypatch.setattr(dbs, "REGISTER", tmp_path / "gibtsnicht.json")
    assert [d.name for d in dbs.alle()] == [dbs.GRUNDEINTRAG["name"]]


def test_eintragen_und_wiederfinden(monkeypatch, tmp_path):
    register = tmp_path / "datenbanken.json"
    monkeypatch.setattr(dbs, "REGISTER", register)
    ziel = tmp_path / "englishplus3"
    ziel.mkdir()

    eintrag = dbs.eintragen("EnglishPlus3", ziel, "English Plus 3", "Probe")
    assert eintrag.name == "EnglishPlus3"
    assert dbs.aufloesen("EnglishPlus3") == ziel
    # Der Grundeintrag darf dabei nicht verloren gehen.
    assert dbs.finde(dbs.GRUNDEINTRAG["name"]) is not None
    gespeichert = json.loads(register.read_text("utf-8"))["datenbanken"]
    assert any(e["name"] == "EnglishPlus3" for e in gespeichert)


def test_eintragen_ersetzt_statt_zu_doppeln(monkeypatch, tmp_path):
    register = tmp_path / "datenbanken.json"
    monkeypatch.setattr(dbs, "REGISTER", register)
    dbs.eintragen("Zweimal", tmp_path / "a")
    dbs.eintragen("Zweimal", tmp_path / "b")
    treffer = [d for d in dbs.alle() if d.name == "Zweimal"]
    assert len(treffer) == 1
    assert treffer[0].verzeichnis == tmp_path / "b"


@pytest.mark.parametrize("roh,erwartet", [
    ("English Plus 3", "english_plus_3"),
    ("EnglishPlus3", "englishplus3"),
    ("  Access 4!  ", "access_4"),
])
def test_slug(roh, erwartet):
    assert dbs.slug(roh) == erwartet


def test_slug_verweigert_unsinn():
    with pytest.raises(ValueError):
        dbs.slug("!!!")


def test_eine_nicht_importierte_datenbank_meldet_sich_als_leer(monkeypatch, tmp_path):
    register = tmp_path / "datenbanken.json"
    monkeypatch.setattr(dbs, "REGISTER", register)
    dbs.eintragen("Leer", tmp_path / "gibtsnochnicht")
    leer = dbs.finde("Leer")
    assert leer is not None
    assert not leer.vorhanden
    assert leer.units == 0
    assert leer.quelle == {}
