"""Welche Vokabeldatenbanken es gibt und wo sie liegen.

Bis hierher war genau eine Datenbank verdrahtet: das Verzeichnis
``data/wortliste``, gefüllt aus der Wortliste von English Plus 2e Level 4.
Dieses Modul stellt daneben eine **Registratur**, damit weitere Lehrmittel
dazukommen können, ohne dass dafür Code geändert werden muss - ein Eintrag
in ``data/datenbanken.json`` genügt.

Der bisherige Weg bleibt dabei unangetastet: ``DEFAULT_DATABASE`` zeigt
weiter auf dasselbe Verzeichnis, und wer ``--datenbank <pfad>`` angibt,
bekommt genau diesen Pfad. Neu ist nur, dass an derselben Stelle auch ein
**Name** stehen darf.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import DEFAULT_DATABASE, PACKAGE_ROOT

#: Die Registratur. Von Hand zu ergänzen oder von ``db import --name``.
REGISTER = PACKAGE_ROOT / "data" / "datenbanken.json"

#: Der Eintrag, der immer da ist: die Datenbank, mit der alles angefangen
#: hat. Sie steht auch dann zur Verfügung, wenn die Registratur fehlt oder
#: unlesbar ist - sonst bräche ein kaputtes JSON die ganze Anwendung.
GRUNDEINTRAG = {
    "name": "EnglishPlus4",
    "verzeichnis": "wortliste",
    "titel": "English Plus 2nd edition, Level 4",
    "beschreibung": "Die Wortliste, mit der dieses Repository gebaut wurde.",
}


@dataclass(frozen=True)
class Datenbank:
    """Eine registrierte Vokabeldatenbank."""

    name: str
    verzeichnis: Path
    titel: str = ""
    beschreibung: str = ""

    @property
    def vorhanden(self) -> bool:
        """Liegt die Datenbank auch wirklich auf der Platte?"""
        return (self.verzeichnis / "index.json").is_file()

    @property
    def quelle(self) -> dict:
        """Herkunftsangaben aus dem ``index.json`` - Datei, Datum, Prüfsumme."""
        if not self.vorhanden:
            return {}
        try:
            roh = json.loads((self.verzeichnis / "index.json").read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return dict(roh.get("quelle", {}))

    @property
    def units(self) -> int:
        if not self.vorhanden:
            return 0
        return len(list(self.verzeichnis.glob("unit_*.json")))


def slug(name: str) -> str:
    """``English Plus 3`` -> ``english_plus_3`` - taugt als Verzeichnisname."""
    sauber = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    if not sauber:
        raise ValueError(f"{name!r} ergibt keinen brauchbaren Verzeichnisnamen.")
    return sauber


def _roh_lesen() -> list[dict]:
    if not REGISTER.is_file():
        return [dict(GRUNDEINTRAG)]
    try:
        daten = json.loads(REGISTER.read_text("utf-8"))
        eintraege = list(daten.get("datenbanken", []))
    except (OSError, json.JSONDecodeError):
        # Eine kaputte Registratur darf die Anwendung nicht lahmlegen.
        return [dict(GRUNDEINTRAG)]
    if not any(e.get("name") == GRUNDEINTRAG["name"] for e in eintraege):
        eintraege.insert(0, dict(GRUNDEINTRAG))
    return eintraege


def alle() -> list[Datenbank]:
    """Alle registrierten Datenbanken, in der Reihenfolge der Registratur."""
    heraus = []
    for e in _roh_lesen():
        verzeichnis = Path(e.get("verzeichnis", ""))
        if not verzeichnis.is_absolute():
            verzeichnis = PACKAGE_ROOT / "data" / verzeichnis
        heraus.append(Datenbank(
            name=str(e.get("name", "")),
            verzeichnis=verzeichnis,
            titel=str(e.get("titel", "")),
            beschreibung=str(e.get("beschreibung", "")),
        ))
    return heraus


def finde(name: str) -> Datenbank | None:
    """Sucht nach Namen, Gross- und Kleinschreibung egal."""
    gesucht = str(name).strip().lower()
    for d in alle():
        if d.name.lower() == gesucht:
            return d
    return None


def aufloesen(angabe: str | Path | None) -> Path:
    """Aus einer Angabe wird ein Verzeichnis.

    ``--datenbank`` nimmt beides: den **Namen** einer registrierten
    Datenbank (``EnglishPlus4``) oder weiterhin einen **Pfad**. Der Name
    hat Vorrang; was kein Name ist, wird als Pfad genommen. Damit bleibt
    jede bisherige Aufrufform gültig.
    """
    if angabe in (None, ""):
        return Path(DEFAULT_DATABASE)
    treffer = finde(str(angabe))
    return treffer.verzeichnis if treffer else Path(angabe)


def eintragen(name: str, verzeichnis: Path, titel: str = "",
              beschreibung: str = "") -> Datenbank:
    """Nimmt eine Datenbank in die Registratur auf (oder aktualisiert sie)."""
    eintraege = [e for e in _roh_lesen() if e.get("name", "").lower() != name.lower()]
    try:
        relativ = str(verzeichnis.resolve().relative_to(
            (PACKAGE_ROOT / "data").resolve()))
    except ValueError:
        relativ = str(verzeichnis)
    eintraege.append({
        "name": name, "verzeichnis": relativ,
        "titel": titel, "beschreibung": beschreibung,
    })
    REGISTER.parent.mkdir(parents=True, exist_ok=True)
    REGISTER.write_text(
        json.dumps({"datenbanken": eintraege}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    gefunden = finde(name)
    assert gefunden is not None
    return gefunden
