"""Niveau A und B: eine Liste, zwei überschneidungsfreie Prüfungen."""

from __future__ import annotations

import pytest

from vocabmaster.niveau import LIST_BOUNDS, PROFILES, other, profile
from vocabmaster.pack import _schwierigkeit, scaffold, waehle_pruefungswoerter
from vocabmaster.pool import plan_unit

UNITS = [1, 2, 3, 4, 5, 6, 7, 8]


def test_profile_werden_erkannt():
    assert profile("A").name == "A"
    assert profile("niveau b").name == "B"
    assert profile("Niv. B").name == "B"
    assert other("A").name == "B"
    with pytest.raises(ValueError, match="Unbekanntes Niveau"):
        profile("C")


def test_cefr_baender_sind_die_zugesagten():
    assert PROFILES["A"].cefr == "B1.2-B2.1"
    assert PROFILES["B"].cefr == "A2.2-B1.1"


def test_die_liste_spannt_beide_niveaus():
    """Eine gemeinsame Liste braucht ein Fenster, das beide Gruppen abdeckt."""
    assert LIST_BOUNDS.too_rare <= 2.45
    assert LIST_BOUNDS.too_easy >= 5.3


def test_niveau_b_hat_ein_engeres_band_als_a():
    a, b = PROFILES["A"].level_targets, PROFILES["B"].level_targets
    assert b["max_sentence_length"] < a["max_sentence_length"]
    assert b["min_flesch_ease"] > a["min_flesch_ease"]
    assert b["max_flesch_grade"] < a["max_flesch_grade"]
    assert b["max_words"] < a["max_words"]
    assert b["max_subordinators_per_sentence"] < a["max_subordinators_per_sentence"]


@pytest.mark.parametrize("unit", UNITS)
def test_jede_unit_ergibt_genau_eine_liste_mit_60_woertern(db, unit):
    plan = plan_unit(db, unit)
    assert len(plan.test1) == 30
    assert len(plan.test2) == 30


@pytest.mark.parametrize("unit", UNITS)
def test_liste_kommt_ohne_zusatzteile_aus(db, unit):
    """Culture, Project und Curriculum extra sind die letzte Reserve.

    Mit der aktuellen Wortliste wird sie in keiner Unit gebraucht - der
    Hauptteil trägt überall 60 Wörter.
    """
    report = plan_unit(db, unit).report
    assert report.aus_zusatzteilen == [], report.ausnahme
    assert report.fehlend == 0


@pytest.mark.parametrize("unit", UNITS)
def test_kein_wort_stammt_aus_culture_oder_project(db, unit, settings):
    haupt = {r.headword.lower() for r in db.unit_pool(unit, core_only=True)}
    for c in plan_unit(db, unit, settings).all_words:
        assert c.headword.lower() in haupt, (
            f"{c.headword} stammt nicht aus dem Hauptteil von Unit {unit}"
        )


@pytest.mark.parametrize("unit", UNITS)
def test_die_beiden_pruefungen_unterscheiden_sich_deutlich(db, unit, settings):
    """Ein Überschnitt ist erlaubt - aber die Fassungen müssen zwei bleiben.

    Niveau A prüft von oben, Niveau B von unten. Bei 30 Wörtern je Test darf
    sich das berühren; deckungsgleich werden dürfen die beiden Auswahlen nicht.
    """
    data = scaffold(db, unit, settings)
    for teil in ("teil1", "teil2"):
        a = {i["english"] for i in data["pruefungen"][teil]["A"]["task1"]["items"]}
        a |= {g["english"] for g in data["pruefungen"][teil]["A"]["task2"]["gaps"]}
        b = {i["english"] for i in data["pruefungen"][teil]["B"]["task1"]["items"]}
        b |= {g["english"] for g in data["pruefungen"][teil]["B"]["task2"]["gaps"]}
        assert len(a & b) <= len(a) // 2, (
            f"Unit {unit} {teil}: {len(a & b)} von {len(a)} Wörtern gleich"
        )


@pytest.mark.parametrize("unit", UNITS)
def test_pruefung_a_ist_schwerer_als_pruefung_b(db, unit, settings):
    plan = plan_unit(db, unit, settings)
    for words in (plan.test1, plan.test2):
        eintraege = [
            {"englisch": c.headword, "deutsch": c.german, "wortart": "", "nr": i}
            for i, c in enumerate(words, 1)
        ]

        def mittel(niveau, eintraege=eintraege):
            gewaehlt = waehle_pruefungswoerter(eintraege, PROFILES[niveau], settings)
            return sum(_schwierigkeit(e) for e in gewaehlt) / len(gewaehlt)

        assert mittel("A") > mittel("B") + 0.3


@pytest.mark.parametrize("unit", UNITS)
def test_beide_pruefungen_schoepfen_aus_derselben_liste(db, unit, settings):
    data = scaffold(db, unit, settings)
    for teil, block in ((1, "test1"), (2, "test2")):
        erlaubt = {e["englisch"] for e in data["liste"][block]}
        for niveau in ("A", "B"):
            spec = data["pruefungen"][f"teil{teil}"][niveau]
            geprueft = [i["english"] for i in spec["task1"]["items"]]
            geprueft += [g["english"] for g in spec["task2"]["gaps"]]
            assert set(geprueft) <= erlaubt


def test_grundwortschatz_bleibt_draussen(db):
    from vocabmaster.list.leveling import is_core_vocabulary

    for candidate in plan_unit(db, 1).all_words:
        assert not is_core_vocabulary(candidate.headword), candidate.headword


def test_zusatzteile_nur_als_letzte_reserve(db, settings):
    """Wird der Hauptteil künstlich zu klein, greift die Ausnahme - und nur dann."""
    from dataclasses import replace as _replace

    eng = _replace(settings) if False else settings
    eng.words_per_test = 200  # 400 Wörter verlangt: unmöglich aus dem Hauptteil
    report = plan_unit(db, 6, eng).report
    assert report.aus_zusatzteilen, "die Ausnahme hätte greifen müssen"
    assert report.ausnahme
    assert "Zusatzteilen" in report.ausnahme
