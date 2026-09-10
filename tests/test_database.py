"""Die Datenbank ist die einzige Quelle - und muss das auch belegen können."""

from __future__ import annotations

import pytest

from vocabmaster.database import Database


def test_alle_units_vorhanden(db: Database):
    assert db.units() == [0, 1, 2, 3, 4, 5, 6, 7, 8]


def test_herkunft_ist_vollstaendig(db: Database):
    for key in ("datei", "importiert", "pruefsumme_sha256"):
        assert db.quelle.get(key), f"In der Datenbank fehlt die Angabe {key!r}"
    assert db.quelle["datei"].endswith((".xls", ".xlsx"))


def test_jede_unit_hat_ein_thema(db: Database):
    for unit in db.units():
        theme = db.theme(unit)
        assert theme["thema"], f"Unit {unit} hat kein Thema"
        assert theme["leitwoerter"], f"Unit {unit} hat keine Leitwörter"


def test_hauptteil_ist_kleiner_als_gesamt(db: Database):
    """Culture, Project und Curriculum extra zählen nicht zum Hauptteil."""
    for entry in db.overview():
        assert entry["hauptteil"] <= entry["gesamt"]
    unit7 = next(e for e in db.overview() if e["unit"] == 7)
    assert unit7["hauptteil"] < unit7["gesamt"]


def test_unbekannte_unit_meldet_verstaendlich(db: Database):
    with pytest.raises(ValueError, match="Vorhanden sind"):
        db.require_unit(42)


def test_sql_nur_lesend(db: Database):
    assert db.query("SELECT count(*) AS n FROM woerter")[0]["n"] == len(db)
    with pytest.raises(ValueError):
        db.query("DELETE FROM woerter")


def test_keine_reste_einer_alten_wortliste(db: Database):
    """Jede Zeile muss auf die aktuelle Quelle zurückgehen."""
    assert len(db) > 1000
    assert all(row.headword for row in db.rows)
    assert all(row.zipf > 0 for row in db.rows)
