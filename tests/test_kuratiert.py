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
ALLE = sorted(KURATIERT.glob("unit_*.json"))


def _ist_fassung(pfad: Path) -> bool:
    import json
    return int(json.loads(pfad.read_text("utf-8")).get("fassung", 1)) > 1


#: Vollständige Pakete: eine Liste und alle vier Prüfungen.
PAKETE = [p for p in ALLE if not _ist_fassung(p)]
#: Fassungspakete: dieselbe Liste, aber nur eine neu gesetzte Prüfung.
FASSUNGEN = [p for p in ALLE if _ist_fassung(p)]


@pytest.mark.skipif(not ALLE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", ALLE, ids=lambda p: p.stem)
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


@pytest.mark.skipif(not FASSUNGEN, reason="keine Fassungspakete vorhanden")
@pytest.mark.parametrize("pfad", FASSUNGEN, ids=lambda p: p.stem)
def test_fassung_ersetzt_genau_eine_pruefung(pfad):
    """Ein Fassungspaket trägt dieselbe Liste, aber nur die eine Prüfung.

    Der klassische Fehler wäre, dass es die drei anderen mitschleppt und beim
    Bauen die bestehenden Dateien überschreibt.
    """
    pack = Pack.load(pfad)
    grund = Pack.load(pfad.parent / f"unit_{pack.unit:02d}.json")
    assert pack.fassung > 1
    assert len(pack.exams) == 1, "eine Fassung setzt genau eine Prüfung neu"
    assert len(pack.all_entries) == 60
    assert [e["englisch"] for e in pack.all_entries] == [
        e["englisch"] for e in grund.all_entries
    ], "die Vokabelliste bleibt Wort für Wort dieselbe"

    (teil, niveau), spec = next(iter(pack.exams.items()))
    alt = grund.exam(teil, niveau)

    # Ein Überschnitt der geprüften Wörter ist ausdrücklich erlaubt: Alle
    # Fassungen prüfen dieselbe Liste, und die zwölf schwersten Wörter
    # bleiben die zwölf schwersten. Was eine Fassung unterscheidet, ist ihr
    # Lückentext und die Aufteilung in Übersetzung und Lücke.
    assert spec["task2"]["text"] != alt["task2"]["text"], "der Text ist neu"
    neu_l = [g["answer"] for g in spec["task2"]["gaps"]]
    alt_l = [g["answer"] for g in alt["task2"]["gaps"]]
    assert neu_l != alt_l, "dieselben Lücken wären dasselbe Blatt"
    assert spec["meta"]["fassung"] == pack.fassung, "die Fassung ist hinterlegt"
    assert spec["meta"]["erzeugt"], "mit Datum"


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", PAKETE, ids=lambda p: p.stem)
def test_dokumente_lassen_sich_bauen(pfad, tmp_path, settings):
    ergebnis = baue_alles(Pack.load(pfad), tmp_path, settings)
    assert len(ergebnis.dateien) == 9  # 1 Liste + 4 Prüfungen + 4 Lösungen
    assert ergebnis.ok, "\n".join(str(b) for b in ergebnis.bericht.fehler)


@pytest.mark.skipif(not FASSUNGEN, reason="keine Fassungspakete vorhanden")
@pytest.mark.parametrize("pfad", FASSUNGEN, ids=lambda p: p.stem)
def test_fassung_ueberschreibt_die_erste_nicht(pfad, tmp_path, settings):
    """Die Dateinamen einer Fassung dürfen sich nicht mit denen der ersten
    decken - sonst überschreibt ein Bau die bestehende Prüfung."""
    pack = Pack.load(pfad)
    grund = Pack.load(pfad.parent / f"unit_{pack.unit:02d}.json")
    erste = {p.name for p in baue_alles(grund, tmp_path / "a", settings).dateien}
    ergebnis = baue_alles(pack, tmp_path / "b", settings, teile=("test",))
    assert ergebnis.ok, "\n".join(str(b) for b in ergebnis.bericht.fehler)
    zweite = {p.name for p in ergebnis.dateien}
    assert len(zweite) == 2, "eine Prüfung und ihr Lösungsblatt"
    assert not (erste & zweite), f"würde überschreiben: {sorted(erste & zweite)}"


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
