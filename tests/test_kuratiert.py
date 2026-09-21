"""Die mitgelieferten Pakete unter ``kuratiert/`` müssen fehlerfrei bleiben.

Sie sind das Referenzbeispiel: Wer die Anwendung ändert und dabei ein
fertiges Paket kaputtmacht, merkt es hier.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vocabmaster import datenbanken as dbs
from vocabmaster.checks import pruefe_paket
from vocabmaster.database import Database
from vocabmaster.documents import baue_alles
from vocabmaster.pack import Pack, pack_filename

from .helpers import aufgabe

KURATIERT = Path(__file__).resolve().parent.parent / "kuratiert"
ALLE = sorted(KURATIERT.glob("unit_*.json"))


def datenbank_von(pack: Pack) -> Database:
    """Die Datenbank, zu der **dieses** Paket gehört.

    Unter ``kuratiert/`` liegen die Pakete mehrerer Lehrmittel nebeneinander,
    und zwei Lehrmittel dürfen dieselbe Unit 1 haben. Ein Paket gegen die
    Grunddatenbank zu prüfen, weil sie die erste ist, ergäbe lauter
    Scheinfehler: 'instruction' steht im Hauptteil von English Plus 3,
    nicht in dem von English Plus 4. Gefunden wird sie an der **Prüfsumme**
    der Wortliste - nicht am Namen des Pakets.
    """
    eigen = str(pack.quelle.get("pruefsumme_sha256", ""))
    for eintrag in dbs.alle():
        if eintrag.vorhanden and str(
                eintrag.quelle.get("pruefsumme_sha256", "")) == eigen:
            return Database.load(eintrag.verzeichnis)
    raise AssertionError(
        f"Zu {pack.pfad.name if pack.pfad else '?'} gibt es keine Datenbank "
        f"mit der Prüfsumme {eigen[:12]} - das Paket ist Altbestand."
    )


def grundpaket(pfad: Path) -> Pack:
    """Das Paket der Liste, zu der diese Fassung gehört."""
    pack = Pack.load(pfad)
    return Pack.load(pfad.parent / pack_filename(
        pack.unit, liste_version=pack.liste_version,
        lehrmittel=pack.lehrmittel))


def _ist_fassung(pfad: Path) -> bool:
    import json
    return int(json.loads(pfad.read_text("utf-8")).get("fassung", 1)) > 1


#: Vollständige Pakete: eine Liste und alle vier Prüfungen.
PAKETE = [p for p in ALLE if not _ist_fassung(p)]
#: Fassungspakete: dieselbe Liste, aber nur eine neu gesetzte Prüfung.
FASSUNGEN = [p for p in ALLE if _ist_fassung(p)]


@pytest.mark.skipif(not ALLE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", ALLE, ids=lambda p: p.stem)
def test_paket_ist_fehlerfrei(pfad, settings):
    pack = Pack.load(pfad)
    bericht = pruefe_paket(pack, datenbank_von(pack), settings)
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
    if pack.liste_gegeben:
        # Eine Liste, die fertig hereinkommt, hat so viele Wörter, wie ihre
        # Quelle hat. Auf 60 gebracht würde sie nicht vollständiger, nur
        # verändert - und die Aufteilung in Test 1 und Test 2 stammt dann
        # nicht mehr von der Lehrperson. Vollständig heisst hier: kein
        # Eintrag ohne Wort, ohne Übersetzung, ohne Satz.
        assert pack.all_entries, "eine Liste ohne Wörter ist keine"
        for eintrag in pack.all_entries:
            for feld in ("englisch", "deutsch", "satz"):
                assert str(eintrag.get(feld, "")).strip(), (
                    f"Nr. {eintrag.get('nr')}: '{feld}' fehlt")
    else:
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
    grund = grundpaket(pfad)
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
    assert aufgabe(spec)["text"] != aufgabe(alt)["text"], "der Text ist neu"
    neu_l = [g["answer"] for g in aufgabe(spec)["gaps"]]
    alt_l = [g["answer"] for g in aufgabe(alt)["gaps"]]
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
    grund = grundpaket(pfad)
    erste = {p.name for p in baue_alles(grund, tmp_path / "a", settings).dateien}
    ergebnis = baue_alles(pack, tmp_path / "b", settings, teile=("test",))
    assert ergebnis.ok, "\n".join(str(b) for b in ergebnis.bericht.fehler)
    zweite = {p.name for p in ergebnis.dateien}
    assert len(zweite) == 2, "eine Prüfung und ihr Lösungsblatt"
    assert not (erste & zweite), f"würde überschreiben: {sorted(erste & zweite)}"


@pytest.mark.skipif(not PAKETE, reason="keine kuratierten Pakete vorhanden")
@pytest.mark.parametrize("pfad", PAKETE, ids=lambda p: p.stem)
def test_nur_woerter_aus_dem_hauptteil(pfad):
    """Culture, Project und Curriculum extra dürfen nicht stillschweigend
    hineinrutschen - und wenn doch, dann ausgewiesen."""
    pack = Pack.load(pfad)
    haupt = {r.headword.lower()
             for r in datenbank_von(pack).unit_pool(pack.unit, core_only=True)}
    for entry in pack.all_entries:
        if entry.get("herkunft") != "wortliste":
            continue
        assert entry["englisch"].lower() in haupt, (
            f"{entry['englisch']} ist als 'wortliste' geführt, steht aber nicht "
            f"im Hauptteil von Unit {pack.unit}"
        )
