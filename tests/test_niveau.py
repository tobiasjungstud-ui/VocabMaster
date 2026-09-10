"""Niveau A und B: getrennte Bänder, überschneidungsfreie Listen."""

from __future__ import annotations

import pytest

from vocabmaster.list.leveling import is_usable, score_candidate
from vocabmaster.list.models import Candidate
from vocabmaster.niveau import PROFILES, other, profile
from vocabmaster.pool import (
    allocate,
    bounds_for,
    near_duplicates,
    plan_both,
    shared_words,
)

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


def test_baender_ueberlappen_sich_aber_sind_verschieden():
    a, b = PROFILES["A"], PROFILES["B"]
    assert a.zipf_max < b.zipf_max, "Niveau B darf häufigere Wörter verwenden"
    assert a.zipf_min < b.zipf_min, "Niveau A darf seltenere Wörter verwenden"
    assert a.zipf_min < b.zipf_max, "die Bänder müssen sich überlappen"


@pytest.mark.parametrize("zipf, fuer_a, fuer_b", [(3.0, True, False), (4.2, True, True),
                                                  (5.0, False, True)])
def test_haeufigkeit_entscheidet_ueber_das_niveau(zipf, fuer_a, fuer_b):
    for name, erwartet in (("A", fuer_a), ("B", fuer_b)):
        c = Candidate(english="testword", german="Prüfwort", zipf=zipf)
        score_candidate(c, None, bounds_for(PROFILES[name]))
        assert is_usable(c) is erwartet


@pytest.mark.parametrize("unit", UNITS)
def test_listen_sind_ueberschneidungsfrei(db, unit):
    """Kein Wort darf in beiden Niveaulisten stehen."""
    assert shared_words(plan_both(db, unit)) == []


@pytest.mark.parametrize("unit", UNITS)
def test_niveau_a_ist_schwerer_als_b(db, unit):
    plans = plan_both(db, unit)

    def mittel(plan):
        words = plan.all_words
        return sum(c.difficulty for c in words) / len(words)

    assert mittel(plans["A"]) > mittel(plans["B"]) + 0.05


@pytest.mark.parametrize("unit", UNITS)
def test_beide_niveaus_bleiben_bei_der_unit(db, unit):
    for plan in plan_both(db, unit).values():
        assert plan.unit == unit
        for candidate in plan.all_words:
            assert candidate.unit in (unit, None)


def test_wortfamilien_ueber_die_niveaus_werden_gemeldet(db):
    """Sie sind erlaubt, müssen aber im Bericht auftauchen."""
    familien = near_duplicates(plan_both(db, 1))
    assert all(len(eintrag) == 3 for eintrag in familien)


def test_zuteilung_verteilt_jedes_wort_hoechstens_einmal(db):
    verteilung = allocate(db, 3)
    a = {c.english for c in verteilung.per_niveau["A"]}
    b = {c.english for c in verteilung.per_niveau["B"]}
    assert not (a & b)
    assert len(a) + len(b) == verteilung.nur_a + verteilung.nur_b + verteilung.strittig


def test_grundwortschatz_bleibt_in_beiden_niveaus_draussen(db):
    """Auch Niveau B bekommt kein 'house' oder 'dog'."""
    from vocabmaster.list.leveling import is_core_vocabulary

    for plan in plan_both(db, 1).values():
        for candidate in plan.all_words:
            assert not is_core_vocabulary(candidate.headword), candidate.headword
