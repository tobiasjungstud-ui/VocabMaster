"""Der Regler für die Schwierigkeit des Lückentexts.

Der klassische Fehler ist hier, dass der Regler zwar wackelt, aber nichts
bewirkt - oder dass er in der Mittelstellung schon etwas verändert und
damit die bestehenden Pakete umwertet.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from vocabmaster.exam.english import readability
from vocabmaster.niveau import (
    NORMAL_TEXTSTUFE,
    PROFILES,
    textstufe,
    ziele_fuer_textstufe,
)
from vocabmaster.pack import Pack

KURATIERT = Path(__file__).resolve().parent.parent / "kuratiert"
PAKETE = [
    p for p in sorted(KURATIERT.glob("unit_*.json"))
    if int(json.loads(p.read_text("utf-8")).get("fassung", 1)) == 1
]


def _stufe(text: str) -> float:
    return textstufe(readability(re.sub(r"\{\d+\}", "word", text)))


@pytest.mark.parametrize("niveau", ["A", "B"])
def test_normallage_aendert_nichts(niveau):
    """In der Normalstellung muss genau das Profil herauskommen."""
    prof = PROFILES[niveau]
    assert ziele_fuer_textstufe(prof, NORMAL_TEXTSTUFE[niveau]) == prof.level_targets
    assert ziele_fuer_textstufe(prof, None) == prof.level_targets


@pytest.mark.parametrize("niveau", ["A", "B"])
def test_regler_wirkt_in_beide_richtungen(niveau):
    prof = PROFILES[niveau]
    normal = NORMAL_TEXTSTUFE[niveau]
    hoch = ziele_fuer_textstufe(prof, normal + 3)
    tief = ziele_fuer_textstufe(prof, normal - 1)
    mitte = prof.level_targets
    # Höher: längerer Text, längere Sätze, schwerer zu lesen, mehr Nebensätze.
    assert hoch["max_words"] > mitte["max_words"] > tief["max_words"]
    assert hoch["max_avg_sentence"] > mitte["max_avg_sentence"] > tief["max_avg_sentence"]
    assert hoch["min_flesch_ease"] < mitte["min_flesch_ease"] < tief["min_flesch_ease"]
    assert (hoch["max_subordinators_per_sentence"]
            > mitte["max_subordinators_per_sentence"]
            > tief["max_subordinators_per_sentence"])


def test_baender_bleiben_brauchbar():
    """Auch an den Anschlägen darf kein unsinniges Band entstehen."""
    for niveau in ("A", "B"):
        for stufe in (0.0, 2.5, 5.0, 7.5, 10.0):
            z = ziele_fuer_textstufe(PROFILES[niveau], stufe)
            assert z["min_words"] >= 25
            assert z["max_words"] > z["min_words"]
            assert z["max_avg_sentence"] >= z["min_avg_sentence"]
            assert z["max_sentence_length"] > z["max_avg_sentence"]
            assert 20.0 <= z["min_flesch_ease"] <= 100.0
            assert z["max_flesch_grade"] >= 1.0
            assert z["max_subordinators_per_sentence"] >= 0.0


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
def test_gelieferte_texte_liegen_auf_ihrer_normallage():
    """Die Normallage ist gemessen, nicht gesetzt - das muss so bleiben.

    Wer die Anker verstellt, ohne NORMAL_TEXTSTUFE nachzuziehen, merkt es
    hier: Die 32 Lückentexte im Paket sind die Eichung dieser Skala.
    """
    nach_niveau: dict[str, list[float]] = {"A": [], "B": []}
    for pfad in PAKETE:
        pack = Pack.load(pfad)
        for (_teil, niveau), spec in pack.exams.items():
            text = spec.get("task2", {}).get("text", "")
            if text:
                nach_niveau[niveau].append(_stufe(text))

    for niveau, werte in nach_niveau.items():
        assert werte, f"keine Lückentexte für Niveau {niveau}"
        schnitt = sum(werte) / len(werte)
        assert abs(schnitt - NORMAL_TEXTSTUFE[niveau]) < 0.25, (
            f"Niveau {niveau}: gemessener Schnitt {schnitt:.2f}, "
            f"NORMAL_TEXTSTUFE sagt {NORMAL_TEXTSTUFE[niveau]}"
        )

    # Und die beiden Niveaus müssen sich trennen, sonst misst die Skala nichts.
    assert min(nach_niveau["A"]) > max(nach_niveau["B"]), (
        "Niveau A muss durchgehend über Niveau B liegen"
    )
