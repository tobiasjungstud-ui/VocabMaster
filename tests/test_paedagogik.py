"""Das zuschaltbare pädagogische Ranking.

Der wichtigste Test ist der erste: Ausgeschaltet muss **exakt** dasselbe
herauskommen wie zuvor. Ein Zusatz, der den bestehenden Weg verbiegt, ist
kein Zusatz.
"""

from __future__ import annotations

import pytest

from vocabmaster import paedagogik as paed
from vocabmaster.list.leveling import LevelContext, is_usable, score_candidate
from vocabmaster.list.models import Candidate
from vocabmaster.pool import plan_unit


def _kandidaten(db, unit: int) -> list[Candidate]:
    ctx = LevelContext.from_entries(db.earlier(unit))
    heraus = []
    for r in db.unit_pool(unit, core_only=True):
        c = Candidate(english=r.english, german=r.german, section=r.section,
                      unit=unit, oxford3000=bool(r.oxford3000))
        score_candidate(c, ctx)
        heraus.append(c)
    return [c for c in heraus if is_usable(c)]


# ---------------------------------------------------------------- additiv
def test_ausgeschaltet_aendert_es_nichts(db, settings):
    """Der Standardweg muss Wort für Wort derselbe bleiben."""
    ohne = plan_unit(db, 1, settings)
    nochmal = plan_unit(db, 1, settings, ranking="zipf")
    assert [c.headword for c in ohne.all_words] == \
           [c.headword for c in nochmal.all_words]
    assert ohne.report.ranking == "", "ohne Schalter wird nichts vermerkt"
    assert ohne.report.im_band == 0


def test_eingeschaltet_wirkt(db, settings):
    ohne = plan_unit(db, 1, settings)
    mit = plan_unit(db, 1, settings, ranking="paedagogisch", stufe="advanced")
    assert mit.report.ranking == "advanced"
    assert mit.report.im_band > 0
    assert set(c.headword for c in mit.all_words) != \
           set(c.headword for c in ohne.all_words)
    assert len(mit.all_words) == len(ohne.all_words), "die Liste bleibt gleich gross"


# ------------------------------------------------------- harter Vorfilter
def test_grundwortschatz_faellt_aus_jedem_band(db):
    """'good' und 'bad' sollen nicht in jedem Durchlauf wieder auftauchen."""
    for wort, deutsch, zipf in (("good", "gut", 5.6), ("bad", "schlecht", 5.2)):
        c = Candidate(english=wort, german=deutsch, section="Unit 1")
        c.headword, c.zipf = wort, zipf
        for name in paed.STUFEN:
            assert not paed.im_band(c, paed.STUFEN[name]), f"{wort} in {name}"


def test_abschreibbares_faellt_aus_den_oberen_baendern(db):
    """Selten allein genügt nicht - 'Teddybär' schreibt man ab."""
    c = Candidate(english="teddy bear", german="Teddybär", section="Unit 1")
    c.headword, c.zipf = "teddy bear", 3.28
    assert paed.schwer_zu_schreiben(c) < 0.15, "vom Deutschen ablesbar"
    assert not paed.im_band(c, paed.STUFEN["intermediate"])
    assert not paed.im_band(c, paed.STUFEN["advanced"])


def test_beide_dimensionen_zaehlen():
    schwer = Candidate(english="come across", german="auf etw. stoßen")
    schwer.headword, schwer.zipf = "come across", 4.65
    leicht = Candidate(english="lamp", german="Lampe")
    leicht.headword, leicht.zipf = "lamp", 4.2
    assert paed.schwer_zu_verwenden(schwer) > paed.schwer_zu_verwenden(leicht)
    assert paed.fehleranfaelligkeit(schwer) > paed.fehleranfaelligkeit(leicht)


# ------------------------------------------------------------- Rangfolge
def test_gereiht_wird_nach_rangfolge_nicht_nach_summe(db):
    """Das erste Kriterium entscheidet; das zweite nur bei Gleichstand.

    Sortiert wird in zwei Gruppen: erst das Band der Stufe, dann der Rest.
    Innerhalb jeder Gruppe gilt der Rangfolgen-Schlüssel.
    """
    kand = _kandidaten(db, 1)
    stufe = paed.STUFEN[paed.STUFE_VORGABE]
    geordnet, bewertungen = paed.ranken(kand, db.theme(1).get("leitwoerter", []))
    assert len(geordnet) == len(kand), "es wird nichts weggeworfen"

    drin = [i for i, c in enumerate(geordnet) if paed.im_band(c, stufe)]
    draussen = [i for i, c in enumerate(geordnet) if not paed.im_band(c, stufe)]
    assert not drin or not draussen or max(drin) < min(draussen), (
        "das Band steht vorn"
    )
    for gruppe in (drin, draussen):
        schluessel = [bewertungen[i].schluessel() for i in gruppe]
        assert schluessel == sorted(schluessel), "die Reihung folgt dem Schlüssel"


def test_reihung_ist_ueber_durchlaeufe_stabil(db):
    """Zweimal dasselbe muss zweimal dieselbe Reihenfolge ergeben."""
    kand = _kandidaten(db, 3)
    leit = db.theme(3).get("leitwoerter", [])
    a, _ = paed.ranken(kand, leit, "intermediate")
    b, _ = paed.ranken(list(reversed(kand)), leit, "intermediate")
    assert [c.headword for c in a] == [c.headword for c in b], (
        "die Eingabereihenfolge darf das Ergebnis nicht verändern"
    )


@pytest.mark.parametrize("stufe", ["basic", "intermediate", "advanced"])
def test_jede_stufe_hat_ein_eigenes_band(db, stufe):
    kand = _kandidaten(db, 2)
    st = paed.STUFEN[stufe]
    drin = [c for c in kand if paed.im_band(c, st)]
    assert drin, f"Stufe {stufe} lässt in Unit 2 nichts durch"
    for c in drin:
        if c.zipf:
            assert st.zipf_min <= c.zipf <= st.zipf_max
        assert paed.fehleranfaelligkeit(c) >= st.mindest_schwierigkeit


def test_die_stufen_ordnen_verschieden(db):
    kand = _kandidaten(db, 2)
    leit = db.theme(2).get("leitwoerter", [])
    spitzen = {}
    for stufe in ("basic", "intermediate", "advanced"):
        _, bew = paed.ranken(kand, leit, stufe)
        spitzen[stufe] = [b.wort for b in bew[:10]]
    assert spitzen["basic"] != spitzen["intermediate"]
    assert spitzen["intermediate"] != spitzen["advanced"]


def test_unbekannte_stufe_faellt_auf_die_vorgabe_zurueck(db):
    kand = _kandidaten(db, 1)
    a, _ = paed.ranken(kand, [], "gibtsnicht")
    b, _ = paed.ranken(kand, [], paed.STUFE_VORGABE)
    assert [c.headword for c in a] == [c.headword for c in b]
