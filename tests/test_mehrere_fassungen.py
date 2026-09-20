"""Mehrere Fassungen einer Prüfung in einem Zug — und alle verschieden.

Drei Reihen, drei Blätter, damit niemand beim Nachbarn abschreibt: Das ist
der Grund, aus dem ``fassung --anzahl 3`` entstanden ist. Was dabei nicht
passieren darf, ist dreimal dasselbe Blatt unter drei Nummern.

Eine Fassung unterscheidet sich von ihren Geschwistern an genau zweierlei:
an der **Aufteilung** (welche der zwölf Wörter Lücke werden) und am
**Lückentext**. Beides wird hier geprüft — das eine sofort, das andere,
sobald der Text geschrieben ist.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vocabmaster import cli
from vocabmaster.pack import Pack, aufteilung, pruefungswoerter, text_offen

from .helpers import aufgabe

WURZEL = Path(__file__).resolve().parent.parent


@pytest.fixture
def ordner(tmp_path) -> Path:
    """Ein Probeordner mit einem echten Paket darin."""
    quelle = WURZEL / "kuratiert" / "unit_01.json"
    if not quelle.is_file():
        pytest.skip("kein Paket unter kuratiert/")
    ziel = tmp_path / "unit_01.json"
    ziel.write_text(quelle.read_text("utf-8"), "utf-8")
    return tmp_path


def _fassungen(ordner: Path, teil: int, niveau: str) -> list[Pack]:
    pakete = [Pack.load(p) for p in sorted(ordner.glob("unit_*.json"))]
    return sorted(
        (p for p in pakete if p.exam(teil, niveau)), key=lambda p: p.fassung
    )


def test_drei_auf_einmal_bekommen_fortlaufende_nummern(ordner):
    assert cli.main(["fassung", str(ordner / "unit_01.json"), "--teil", "1",
                     "--niveau", "A", "--anzahl", "3",
                     "--verzeichnis", str(ordner)]) == 0
    assert [p.fassung for p in _fassungen(ordner, 1, "A")] == [1, 2, 3, 4]


def test_jede_teilt_anders_auf(ordner):
    """Sonst wäre es dieselbe Prüfung unter einer anderen Nummer."""
    cli.main(["fassung", str(ordner / "unit_01.json"), "--teil", "1",
              "--niveau", "A", "--anzahl", "3", "--verzeichnis", str(ordner)])
    aufteilungen = [aufteilung(p.exam(1, "A")) for p in _fassungen(ordner, 1, "A")]
    assert len(set(aufteilungen)) == len(aufteilungen), \
        "zwei Fassungen teilen dieselben Wörter in Lücke und Übersetzung auf"


def test_alle_pruefen_dieselbe_liste_und_denselben_anspruch(ordner):
    """Eine Fassung darf nicht leichter sein als ihre Geschwister.

    Der Überschnitt bei den geprüften Wörtern ist ausdrücklich erlaubt —
    die zwölf schwersten bleiben die zwölf schwersten.
    """
    cli.main(["fassung", str(ordner / "unit_01.json"), "--teil", "1",
              "--niveau", "A", "--anzahl", "3", "--verzeichnis", str(ordner)])
    pakete = _fassungen(ordner, 1, "A")
    abdruecke = {p.liste_abdruck for p in pakete}
    assert len(abdruecke) == 1, "die Fassungen hängen an verschiedenen Listen"
    umfaenge = {len(pruefungswoerter(p.exam(1, "A"))) for p in pakete}
    assert len(umfaenge) == 1, "eine Fassung prüft mehr Wörter als die andere"


def test_der_lueckentext_bleibt_offen_und_das_ist_kein_fehler(ordner, capsys):
    """Frisch angelegt tragen alle drei denselben Platzhalter.

    Das ist der normale offene Zustand und darf nicht als "dreimal
    dieselbe Prüfung" gemeldet werden - sonst stünde der Fehler schon da,
    bevor jemand einen Text geschrieben hat.
    """
    cli.main(["fassung", str(ordner / "unit_01.json"), "--teil", "1",
              "--niveau", "A", "--anzahl", "3", "--verzeichnis", str(ordner)])
    capsys.readouterr()
    neue = [p for p in _fassungen(ordner, 1, "A") if p.fassung > 1]
    assert all(text_offen(p.exam(1, "A")) for p in neue)

    assert cli.main(["listen", "--verzeichnis", str(ordner)]) == 0
    assert "denselben Lückentext" not in capsys.readouterr().out


def test_zwei_gleiche_lueckentexte_sind_ein_fehler(ordner, capsys):
    """Der Fehler selbst, eingebaut: zweimal dieselbe Prüfung."""
    cli.main(["fassung", str(ordner / "unit_01.json"), "--teil", "1",
              "--niveau", "A", "--anzahl", "2", "--verzeichnis", str(ordner)])
    for name in ("unit_01_fassung2.json", "unit_01_fassung3.json"):
        pfad = ordner / name
        daten = json.loads(pfad.read_text("utf-8"))
        aufgabe(daten["pruefungen"]["teil1"]["A"])["text"] = (
            "Derselbe {1} Text in {2} beiden {3} Fassungen {4}."
        )
        pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=2), "utf-8")

    capsys.readouterr()
    cli.main(["listen", "--verzeichnis", str(ordner)])
    ausgabe = capsys.readouterr().out
    assert "FEHLER" in ausgabe and "denselben Lückentext" in ausgabe
    assert "zweimal dieselbe Prüfung" in ausgabe


def test_eine_erschoepfte_rotation_wird_gemeldet(ordner, capsys):
    """Irgendwann gibt die Unit nicht mehr her - dann wird es gesagt.

    Das ist keine Nachlässigkeit, sondern eine Eigenschaft der Unit: Es gibt
    nur so viele Wörter je Wortart. Dann muss der Lückentext den Unterschied
    allein tragen, und genau das steht dann da.
    """
    cli.main(["fassung", str(ordner / "unit_01.json"), "--teil", "2",
              "--niveau", "B", "--anzahl", "20", "--verzeichnis", str(ordner)])
    ausgabe = capsys.readouterr().out
    assert "Rotation ist ausgeschöpft" in ausgabe
    assert "Lückentext den Unterschied allein tragen" in ausgabe

    capsys.readouterr()
    cli.main(["listen", "--verzeichnis", str(ordner)])
    assert "WARNUNG" in capsys.readouterr().out


def test_nummer_und_anzahl_schliessen_sich_aus(ordner, capsys):
    """Mehrere Fassungen bekommen fortlaufende Nummern, nicht alle dieselbe."""
    assert cli.main(["fassung", str(ordner / "unit_01.json"), "--teil", "1",
                     "--niveau", "A", "--anzahl", "3", "--nummer", "5",
                     "--verzeichnis", str(ordner)]) == 1
    assert "schliessen sich aus" in capsys.readouterr().out
    assert not list(ordner.glob("*fassung*.json")), "trotzdem etwas geschrieben"


def test_eine_einzelne_fassung_bleibt_wie_sie_war(ordner):
    """Der bisherige Weg darf sich nicht verändern.

    ``--anzahl`` ohne Angabe ist 1, und dann muss dasselbe herauskommen wie
    vor dieser Änderung.
    """
    assert cli.main(["fassung", str(ordner / "unit_01.json"), "--teil", "1",
                     "--niveau", "A", "--verzeichnis", str(ordner)]) == 0
    entstanden = list(ordner.glob("*fassung*.json"))
    assert len(entstanden) == 1
    assert entstanden[0].name == "unit_01_fassung2.json"
