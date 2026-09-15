"""Jede Datenbank hat ihre eigenen Themen.

Eine einzige gemeinsame ``themen.json`` ging genau so schief, wie sie
musste: Die zweite importierte Datenbank erbte Themen, Seitenbereiche und
Leitwörter der ersten. Unit 3 hiess dann „Werbung, Marketing und Konsum",
obwohl in ihr ``kayaking`` und ``skydiving`` stehen — und die
Themenkongruenz-Prüfung mass ein ergänztes Wort am Wortfeld eines anderen
Lehrmittels.

Der Fehler war nicht laut. Er sah aus wie eine Angabe.
"""

from __future__ import annotations

import json
from pathlib import Path

from vocabmaster import datenbanken
from vocabmaster.database import Database
from vocabmaster.importer import (
    ImportResult,
    Row,
    load_themes,
    themen_geruest,
    themen_pfad,
    write_database,
)

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "src" / "vocabmaster" / "data"


def _ergebnis(*units: int) -> ImportResult:
    """Eine winzige Wortliste — je Unit ein Wort im Hauptteil."""
    zeilen = [
        Row(english=f"word{u}", german=f"Wort {u}", unit=u, kind="hauptteil",
            section=f"Unit {u}", page=10 * u, pos="", pronunciation="",
            example="", oxford3000=False, zipf=3.5, headword=f"word{u}", row=u)
        for u in units
    ]
    return ImportResult(rows=zeilen, source="probe.xls", checksum="abc",
                        imported="2026-01-01", warnings=[])


def test_eine_datenbank_erbt_die_themen_der_anderen_nicht(tmp_path):
    """Der Fehler selbst, nachgebaut."""
    erste, zweite = tmp_path / "erste", tmp_path / "zweite"
    erste.mkdir()
    themen_pfad(erste).write_text(json.dumps({"themen": {
        "3": {"titel": "Unit 3", "thema": "Werbung, Marketing und Konsum",
              "seiten": "28-37", "leitwoerter": ["advert", "brand"]},
    }}), "utf-8")

    write_database(_ergebnis(3), erste)
    write_database(_ergebnis(3), zweite)

    assert Database.load(erste).theme(3)["thema"] == "Werbung, Marketing und Konsum"
    zwei = Database.load(zweite).theme(3)
    assert zwei["thema"] == "", "die zweite Datenbank hat das Thema der ersten geerbt"
    assert zwei["leitwoerter"] == [], "und ihre Leitwörter dazu"


def test_ohne_angabe_wird_keine_gemeinsame_datei_geraten():
    """``load_themes()`` ohne Pfad darf nichts finden.

    Sonst schleicht sich die gemeinsame Datei über die Vorgabe wieder ein.
    """
    assert load_themes() == {}
    assert not (DATEN / "themen.json").exists(), \
        "die gemeinsame themen.json ist wieder da"


def test_jede_vorhandene_datenbank_hat_ihre_eigene():
    """Und zwar in ihrem eigenen Verzeichnis."""
    vorhanden = [d for d in datenbanken.alle() if d.vorhanden]
    assert len(vorhanden) >= 2, "der Test braucht zwei importierte Datenbanken"
    for d in vorhanden:
        assert themen_pfad(d.verzeichnis).exists(), \
            f"{d.name} hat keine eigene themen.json"


def test_ein_erneuter_import_loescht_die_einordnung_nicht(tmp_path, monkeypatch):
    """Sie stand vorher da, und niemand hat ihre Löschung bestellt."""
    register = tmp_path / "datenbanken.json"
    monkeypatch.setattr(datenbanken, "REGISTER", register)
    monkeypatch.setattr(datenbanken, "PACKAGE_ROOT", tmp_path)

    datenbanken.eintragen("Probe", tmp_path / "data" / "probe",
                          "Ein Lehrmittel", "Von Hand geschrieben")
    # Noch einmal einlesen, diesmal ohne Einordnung - wie `db import --name`.
    datenbanken.eintragen("Probe", tmp_path / "data" / "probe")

    # Der Grundeintrag EnglishPlus4 steht immer dabei - er ist fest im Code.
    roh = [e for e in json.loads(register.read_text("utf-8"))["datenbanken"]
           if e["name"] == "Probe"]
    assert len(roh) == 1
    assert roh[0]["beschreibung"] == "Von Hand geschrieben"
    assert roh[0]["titel"] == "Ein Lehrmittel"


def test_ein_erneuter_import_mischt_die_reihenfolge_nicht(tmp_path, monkeypatch):
    """Sonst steht die Auswahl nach jedem Import anders da."""
    register = tmp_path / "datenbanken.json"
    monkeypatch.setattr(datenbanken, "REGISTER", register)
    monkeypatch.setattr(datenbanken, "PACKAGE_ROOT", tmp_path)

    for name in ("Eins", "Zwei", "Drei"):
        datenbanken.eintragen(name, tmp_path / "data" / name.lower(), name)
    datenbanken.eintragen("Eins", tmp_path / "data" / "eins", "Eins")

    namen = [e["name"] for e in json.loads(register.read_text("utf-8"))["datenbanken"]
             if e["name"] != "EnglishPlus4"]
    assert namen == ["Eins", "Zwei", "Drei"], "der Import hat die Liste umsortiert"


def test_das_geruest_raet_kein_thema(tmp_path):
    """Ein geratenes Thema wäre schlimmer als ein leeres."""
    geschrieben = themen_geruest(_ergebnis(1, 2, 3), tmp_path, "Irgendein Lehrmittel")
    assert geschrieben == themen_pfad(tmp_path)
    themen = json.loads(geschrieben.read_text("utf-8"))["themen"]
    assert set(themen) == {"1", "2", "3"}
    for unit, eintrag in themen.items():
        assert eintrag["thema"] == "", f"Unit {unit} hat ein erfundenes Thema"
        assert eintrag["leitwoerter"] == []
        # Der Seitenbereich steht in der Wortliste - der darf mit.
        assert eintrag["seiten"] == f"{10 * int(unit)}-{10 * int(unit)}"


def test_eine_bestehende_datei_wird_nie_ueberschrieben(tmp_path):
    """Von Hand eingetragene Themen sind das Wertvollste an der Datei."""
    themen_pfad(tmp_path).write_text(json.dumps({"themen": {
        "1": {"titel": "Unit 1", "thema": "Von Hand gesetzt",
              "seiten": "1-9", "leitwoerter": ["eins"]},
    }}), "utf-8")
    assert themen_geruest(_ergebnis(1, 2), tmp_path) is None
    write_database(_ergebnis(1, 2), tmp_path)
    assert Database.load(tmp_path).theme(1)["thema"] == "Von Hand gesetzt"
