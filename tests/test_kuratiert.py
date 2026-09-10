"""Die mitgelieferten Pakete unter ``kuratiert/`` müssen fehlerfrei bleiben.

Sie sind das Referenzbeispiel: Wer die Anwendung ändert und dabei ein
fertiges Paket kaputtmacht, merkt es hier.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vocabmaster.checks import pruefe_paket
from vocabmaster.documents import baue_alles
from vocabmaster.pack import Pack

KURATIERT = Path(__file__).resolve().parent.parent / "kuratiert"
PAKETE = sorted(KURATIERT.glob("unit_*.json"))


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", PAKETE, ids=lambda p: p.stem)
def test_paket_ist_fehlerfrei(pfad, db, settings):
    pack = Pack.load(pfad)
    bericht = pruefe_paket(pack, db, settings)
    assert not bericht.fehler, "\n".join(str(b) for b in bericht.fehler)
    # Warnungen dürfen nur stehen bleiben, wenn das Paket sie ausdrücklich
    # begründet - siehe Pack.akzeptierte_warnungen.
    unbegruendet = [b for b in bericht.warnungen if not pack.ist_akzeptiert(b.text)]
    assert not unbegruendet, "\n".join(str(b) for b in unbegruendet)


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", PAKETE, ids=lambda p: p.stem)
def test_paket_ist_vollstaendig(pfad):
    pack = Pack.load(pfad)
    assert pack.vollstaendig, f"noch offen: {pack.offen()[:5]}"
    assert len(pack.all_entries) == 60
    assert len(pack.exams) == 4, "je Unit vier Prüfungen: Teil I/II mal Niveau A/B"


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", PAKETE, ids=lambda p: p.stem)
def test_dokumente_lassen_sich_bauen(pfad, tmp_path, settings):
    ergebnis = baue_alles(Pack.load(pfad), tmp_path, settings)
    assert len(ergebnis.dateien) == 9  # 1 Liste + 4 Prüfungen + 4 Lösungen
    assert ergebnis.ok, "\n".join(str(b) for b in ergebnis.bericht.fehler)


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", PAKETE, ids=lambda p: p.stem)
def test_nur_woerter_aus_dem_hauptteil(pfad, db):
    """Culture, Project und Curriculum extra dürfen nicht stillschweigend
    hineinrutschen - und wenn doch, dann ausgewiesen."""
    pack = Pack.load(pfad)
    haupt = {r.headword.lower() for r in db.unit_pool(pack.unit, core_only=True)}
    for entry in pack.all_entries:
        if entry.get("herkunft") != "wortliste":
            continue
        assert entry["englisch"].lower() in haupt, (
            f"{entry['englisch']} ist als 'wortliste' geführt, steht aber nicht "
            f"im Hauptteil von Unit {pack.unit}"
        )
