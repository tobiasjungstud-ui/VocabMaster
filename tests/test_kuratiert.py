"""Die mitgelieferten Pakete unter ``kuratiert/`` müssen fehlerfrei bleiben.

Sie sind das Referenzbeispiel: Wer die Anwendung ändert und dabei ein
fertiges Paket kaputtmacht, merkt es hier.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vocabmaster.checks import gegenstueck_pfad, pruefe_paket
from vocabmaster.documents import baue_alles
from vocabmaster.pack import Pack

KURATIERT = Path(__file__).resolve().parent.parent / "kuratiert"
PAKETE = sorted(KURATIERT.glob("unit_*.json"))


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", PAKETE, ids=lambda p: p.stem)
def test_paket_ist_fehlerfrei(pfad, db, settings):
    pack = Pack.load(pfad)
    gegen = gegenstueck_pfad(pfad, pack.niveau.name)
    bericht = pruefe_paket(
        pack, db, settings, Pack.load(gegen) if gegen.exists() else None
    )
    assert not bericht.fehler, "\n".join(str(b) for b in bericht.fehler)
    assert not bericht.warnungen, "\n".join(str(b) for b in bericht.warnungen)


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", PAKETE, ids=lambda p: p.stem)
def test_paket_ist_vollstaendig(pfad):
    pack = Pack.load(pfad)
    assert pack.vollstaendig, f"noch offen: {pack.offen()[:5]}"
    assert len(pack.all_entries) == 60
    assert len(pack.exams) == 2


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", PAKETE, ids=lambda p: p.stem)
def test_dokumente_lassen_sich_bauen(pfad, tmp_path, settings):
    ergebnis = baue_alles(Pack.load(pfad), tmp_path, settings)
    assert len(ergebnis.dateien) == 5
    assert ergebnis.ok, "\n".join(str(b) for b in ergebnis.bericht.fehler)


@pytest.mark.skipif(len(PAKETE) < 2, reason="beide Niveaus nötig")
def test_die_beiden_niveaus_einer_unit_sind_ueberschneidungsfrei():
    from vocabmaster.list.normalize import headword

    nach_unit: dict[int, dict[str, set[str]]] = {}
    for pfad in PAKETE:
        pack = Pack.load(pfad)
        nach_unit.setdefault(pack.unit, {})[pack.niveau.name] = {
            headword(e["englisch"]).lower() for e in pack.all_entries
        }
    for unit, niveaus in nach_unit.items():
        if len(niveaus) < 2:
            continue
        gemeinsam = niveaus["A"] & niveaus["B"]
        assert not gemeinsam, f"Unit {unit}: {sorted(gemeinsam)} steht in beiden Listen"
