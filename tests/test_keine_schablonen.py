"""Im Quelltext darf kein fertiges Unterrichtsmaterial stehen.

Die Arbeitsanweisung dieses Repositories ist eindeutig: Beispielsätze,
Lückentexte und ergänzte Wörter entstehen **im Chat**, die Anwendung wählt
aus, prüft und setzt - sie formuliert nicht. Wer einen Massstab samt
Musterwörtern in den Quelltext schreibt, umgeht das: Von da an bekommt jede
Unit dieselbe Antwort zurück, egal worum es in ihr geht.

Dieser Test ist der Wächter davor. Er hat schon einmal angeschlagen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
QUELLEN = sorted((WURZEL / "src").rglob("*.py"))
OBERFLAECHE = [WURZEL / "werkstatt" / "vorlage.html"]

#: Wörter, die einmal als eingebauter "Massstab" im Quelltext standen. Sie
#: stehen hier stellvertretend: Sobald wieder eine Liste fertiger Vokabeln
#: im Code landet, ist der Weg derselbe.
_MUSTERWOERTER = (
    "dreadful", "exhausted", "crucial", "fascinating", "packed",
)


@pytest.mark.parametrize("pfad", QUELLEN, ids=lambda p: p.name)
def test_kein_musterwortschatz_im_quelltext(pfad):
    text = pfad.read_text("utf-8").lower()
    gefunden = [w for w in _MUSTERWOERTER if w in text]
    assert not gefunden, (
        f"{pfad.relative_to(WURZEL)} enthält fertige Beispielvokabeln "
        f"{gefunden}. Was ein aufgewertetes Wort leisten muss, hängt am "
        "Wortfeld der jeweiligen Unit und wird im Chat entschieden."
    )


@pytest.mark.parametrize("pfad", OBERFLAECHE, ids=lambda p: p.name)
def test_die_oberflaeche_schlaegt_keine_vokabeln_vor(pfad):
    if not pfad.exists():
        pytest.skip(f"{pfad.name} fehlt")
    text = pfad.read_text("utf-8").lower()
    gefunden = [w for w in _MUSTERWOERTER if w in text]
    assert not gefunden, (
        f"{pfad.name} schlägt Vokabeln vor ({gefunden}); der Auftrag soll "
        "die Lage beschreiben, nicht die Antwort vorwegnehmen."
    )


def test_kein_musterlueckentext_im_quelltext():
    """Auch Lückentexte gehören nicht in den Code."""
    for pfad in QUELLEN:
        text = pfad.read_text("utf-8")
        assert "{1}" not in text or "task2" in text or "Lücke" in text, (
            f"{pfad.relative_to(WURZEL)} sieht nach einem eingebauten "
            "Lückentext aus."
        )
