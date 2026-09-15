"""Ein Import darf eine gute Datenbank nie beschädigen.

Drei Wege, auf denen das passieren könnte, je einer eingebaut:

* eine Datei, die keine Wortliste ist, muss **laut** scheitern — mit
  Dateinamen, nicht mit einem Traceback aus einer Bibliothek;
* ein Absturz mitten im Schreiben darf keine halbe Datenbank hinterlassen;
* eine **andere** Wortliste unter einem Namen, an dem Pakete hängen, wird
  abgewiesen — ihre Lösungsschlüssel zeigten sonst auf Wörter, die es nicht
  mehr gibt.
"""

from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pytest

from vocabmaster import cli, datenbanken, importer
from vocabmaster.database import Database
from vocabmaster.importer import (
    ImportResult,
    Row,
    import_wordlist,
    themen_pfad,
    write_database,
)


# ---------------------------------------------------------------- Vorrat
def _excel(pfad: Path, zeilen: list[list[str]]) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    for z in zeilen:
        ws.append(z)
    wb.save(pfad)
    return pfad


def _wortliste(pfad: Path, units: tuple[int, ...] = (1, 2), praefix: str = "w") -> Path:
    zeilen = [["English", "German", "Section"]]
    for u in units:
        zeilen.append([f"{praefix}{u}a", f"Wort {u}a", f"Unit {u}"])
        zeilen.append([f"{praefix}{u}b", f"Wort {u}b", f"Unit {u}"])
    return _excel(pfad, zeilen)


def _ergebnis(*units: int) -> ImportResult:
    zeilen = [
        Row(english=f"word{u}", german=f"Wort {u}", unit=u, kind="hauptteil",
            section=f"Unit {u}", page=10 * u, pos="", pronunciation="",
            example="", oxford3000=False, zipf=3.5, headword=f"word{u}", row=u)
        for u in units
    ]
    return ImportResult(rows=zeilen, source="probe.xlsx", checksum="abc" * 8,
                        imported="2026-01-01", warnings=[])


def _schnappschuss(ordner: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(ordner.iterdir()) if p.is_file()}


# ---------------------------------------------------- kaputte Eingaben
@pytest.mark.parametrize("name, inhalt, erwartet", [
    ("leer.xlsx", b"", "leer"),
    ("text.xlsx", b"English;German\nhello;hallo\n", "keine lesbare Excel"),
    ("liste.csv", b"English,German\n", "Excel-Datei"),
])
def test_keine_excel_datei_scheitert_laut_und_mit_namen(tmp_path, name, inhalt, erwartet):
    pfad = tmp_path / name
    pfad.write_bytes(inhalt)
    with pytest.raises(ValueError) as e:
        import_wordlist(pfad)
    assert name in str(e.value)
    assert erwartet in str(e.value)


def test_eine_fehlende_datei_wird_benannt(tmp_path):
    with pytest.raises(FileNotFoundError) as e:
        import_wordlist(tmp_path / "gibtsnicht.xlsx")
    assert "gibtsnicht.xlsx" in str(e.value)


def test_falsche_spalten_scheitern(tmp_path):
    _excel(tmp_path / "spalten.xlsx", [["Foo", "Bar"], ["a", "b"]])
    with pytest.raises(ValueError, match="Kopfzeile"):
        import_wordlist(tmp_path / "spalten.xlsx")


def test_zeilen_ohne_eine_einzige_unit_sind_keine_wortliste(tmp_path):
    """Sonst entstünde aus dem falschen Tabellenblatt eine leere Datenbank."""
    _excel(tmp_path / "ohne.xlsx",
           [["English", "German", "Section"], ["hello", "hallo", ""]])
    with pytest.raises(ValueError, match="keine einzige"):
        import_wordlist(tmp_path / "ohne.xlsx")


# ------------------------------------------------ nichts Halbes hinterlassen
def test_ein_absturz_beim_schreiben_laesst_die_alte_datenbank_stehen(tmp_path, monkeypatch):
    ziel = tmp_path / "db"
    write_database(_ergebnis(1, 2, 3), ziel)
    vorher = _schnappschuss(ziel)
    assert Database.load(ziel).themen.keys() == {1, 2, 3}

    # Der Absturz: beim zweiten Unit-Dateinamen geht die Platte "voll".
    echt = importer.unit_filename
    zaehler = {"n": 0}

    def kaputt(unit):
        zaehler["n"] += 1
        if zaehler["n"] == 2:
            raise OSError("No space left on device")
        return echt(unit)

    monkeypatch.setattr(importer, "unit_filename", kaputt)
    with pytest.raises(OSError):
        write_database(_ergebnis(7, 8), ziel)

    assert _schnappschuss(ziel) == vorher, "die alte Datenbank wurde angefasst"
    assert not ziel.with_name("db.neu").exists(), "ein halbes .neu blieb liegen"
    assert not ziel.with_name("db.alt").exists()


def test_die_themen_ueberleben_den_tausch(tmp_path):
    ziel = tmp_path / "db"
    write_database(_ergebnis(1), ziel)
    themen_pfad(ziel).write_text(json.dumps({"themen": {
        "1": {"titel": "Unit 1", "thema": "Von Hand", "seiten": "", "leitwoerter": []}
    }}), "utf-8")
    write_database(_ergebnis(1), ziel)
    assert themen_pfad(ziel).exists()
    assert Database.load(ziel).theme(1)["thema"] == "Von Hand"


def test_reste_einer_frueheren_wortliste_verschwinden_und_werden_gemeldet(tmp_path):
    ziel = tmp_path / "db"
    write_database(_ergebnis(1, 2, 3), ziel)
    ergebnis = _ergebnis(1)
    write_database(ergebnis, ziel)
    assert not (ziel / "unit_02.json").exists()
    assert not (ziel / "unit_03.json").exists()
    gemeldet = [w for w in ergebnis.warnings if "gelöscht" in w]
    assert len(gemeldet) == 2


# --------------------------------------- eine andere Wortliste unter dem Namen
@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    """Eine Datenbank, ein Paket daran, eine Registratur - alles im Sandkasten."""
    monkeypatch.setattr(datenbanken, "REGISTER", tmp_path / "datenbanken.json")
    monkeypatch.setattr(datenbanken, "PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(cli, "PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(cli, "KURATIERT", tmp_path / "kuratiert")
    (tmp_path / "kuratiert").mkdir()

    erste = _wortliste(tmp_path / "erste.xlsx", praefix="e")
    assert cli.main(["db", "import", str(erste), "--name", "Probe"]) == 0
    db = datenbanken.finde("Probe")
    assert db is not None and db.vorhanden
    pruefsumme = db.quelle["pruefsumme_sha256"]

    # Ein Paket, das an dieser Wortliste hängt - nur die Herkunft zählt hier.
    (tmp_path / "kuratiert" / "unit_01.json").write_text(json.dumps({
        "unit": 1, "quelle": {"datei": "erste.xlsx",
                              "pruefsumme_sha256": pruefsumme},
    }), "utf-8")
    return tmp_path, db, pruefsumme


def test_dieselbe_wortliste_noch_einmal_geht_ohne_rueckfrage(umgebung):
    tmp_path, db, pruefsumme = umgebung
    assert cli.main(["db", "import", str(tmp_path / "erste.xlsx"),
                     "--name", "Probe"]) == 0
    assert datenbanken.finde("Probe").quelle["pruefsumme_sha256"] == pruefsumme


def test_eine_andere_wortliste_wird_abgewiesen_wenn_pakete_daran_haengen(umgebung, capsys):
    tmp_path, db, pruefsumme = umgebung
    zweite = _wortliste(tmp_path / "zweite.xlsx", units=(1, 2, 3), praefix="z")
    vorher = _schnappschuss(db.verzeichnis)

    assert cli.main(["db", "import", str(zweite), "--name", "Probe"]) == 2
    meldung = capsys.readouterr().err
    assert "unit_01.json" in meldung and "--ersetzen" in meldung
    assert _schnappschuss(db.verzeichnis) == vorher, "die Datenbank wurde angefasst"


def test_mit_ersetzen_geht_es_und_wird_angesagt(umgebung, capsys):
    tmp_path, db, pruefsumme = umgebung
    zweite = _wortliste(tmp_path / "zweite.xlsx", units=(1, 2, 3), praefix="z")
    assert cli.main(["db", "import", str(zweite), "--name", "Probe",
                     "--ersetzen"]) == 0
    assert "altbestand" in capsys.readouterr().out
    neu = datenbanken.finde("Probe")
    assert neu.quelle["pruefsumme_sha256"] != pruefsumme
    assert (neu.verzeichnis / "unit_03.json").exists()


def test_ohne_abhaengige_pakete_reicht_ein_hinweis(umgebung, capsys):
    tmp_path, db, pruefsumme = umgebung
    (tmp_path / "kuratiert" / "unit_01.json").unlink()
    zweite = _wortliste(tmp_path / "zweite.xlsx", praefix="z")
    assert cli.main(["db", "import", str(zweite), "--name", "Probe"]) == 0
    assert "andere Wortliste als bisher" in capsys.readouterr().out


def test_dieselbe_datei_unter_zweitem_namen_wird_gesagt(umgebung, capsys):
    tmp_path, db, pruefsumme = umgebung
    assert cli.main(["db", "import", str(tmp_path / "erste.xlsx"),
                     "--name", "Zwilling"]) == 0
    assert "schon als 'Probe' registriert" in capsys.readouterr().out


def test_eine_unlesbare_index_json_wird_nicht_still_ueberschrieben(umgebung, capsys):
    """Dort liegt etwas, und man weiss nicht, was."""
    tmp_path, db, pruefsumme = umgebung
    (db.verzeichnis / "index.json").write_text("{ kaputt", "utf-8")
    assert cli.main(["db", "import", str(tmp_path / "erste.xlsx"),
                     "--name", "Probe"]) == 2
    assert "nicht lesbar" in capsys.readouterr().err
    assert (db.verzeichnis / "index.json").read_text("utf-8") == "{ kaputt"
    # Mit --ersetzen geht es - bewusst.
    assert cli.main(["db", "import", str(tmp_path / "erste.xlsx"),
                     "--name", "Probe", "--ersetzen"]) == 0
    assert datenbanken.finde("Probe").vorhanden
