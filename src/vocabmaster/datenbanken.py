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

#: Wie eine Kennung aussehen darf - dieselbe Regel wie auf der Werkstatt-
#: Seite. Sie wird ``--datenbank``-Argument und Verzeichnisname; ein
#: Leerzeichen darin bräche beides.
NAMENSFORM = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,31}$")

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


def zu_verzeichnis(verzeichnis: str | Path | None) -> Datenbank | None:
    """Welche registrierte Datenbank liegt in diesem Verzeichnis?

    Die Gegenrichtung zu :func:`aufloesen`. Gebraucht wird sie dort, wo ein
    geladenes :class:`~vocabmaster.database.Database` seinen Namen nennen
    soll - im Dateinamen eines Pakets etwa, das sonst mit dem gleichnamigen
    Paket eines anderen Lehrmittels zusammenfiele.
    """
    if verzeichnis in (None, ""):
        return None
    try:
        gesucht = Path(verzeichnis).resolve()
    except OSError:
        return None
    for d in alle():
        try:
            if d.verzeichnis.resolve() == gesucht:
                return d
        except OSError:
            continue
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
    """Nimmt eine Datenbank in die Registratur auf (oder aktualisiert sie).

    Ein erneuter Import **behält**, was nicht mitgegeben wird. Wer eine
    Wortliste neu einliest und dabei nur ``--name`` angibt, meint nicht,
    dass die von Hand geschriebene Einordnung weg soll - sie stand vorher
    da und niemand hat ihre Löschung bestellt. Eine leere Zeile ist hier
    „nichts gesagt", nicht „leer machen".

    Die Reihenfolge bleibt ebenfalls: Ein bestehender Eintrag wird an
    seinem Platz aktualisiert, statt ans Ende zu wandern. Sonst mischt
    jeder Import die Liste in der Auswahl neu durch.
    """
    eintraege = _roh_lesen()
    try:
        relativ = str(verzeichnis.resolve().relative_to(
            (PACKAGE_ROOT / "data").resolve()))
    except ValueError:
        relativ = str(verzeichnis)

    stelle = next((i for i, e in enumerate(eintraege)
                   if e.get("name", "").lower() == name.lower()), None)
    bisher = eintraege[stelle] if stelle is not None else {}
    eintrag = {
        "name": name, "verzeichnis": relativ,
        "titel": titel or bisher.get("titel", ""),
        "beschreibung": beschreibung or bisher.get("beschreibung", ""),
    }
    if stelle is None:
        if not NAMENSFORM.match(name):
            raise ValueError(
                f"{name!r} taugt nicht als Kennung: Buchstabe am Anfang, danach "
                "Buchstaben, Ziffern, - oder _, keine Leerzeichen, höchstens 32 "
                "Zeichen. Sie wird zum --datenbank-Argument und zum Verzeichnis."
            )
        eintraege.append(eintrag)
    else:
        eintraege[stelle] = eintrag
    _roh_schreiben(eintraege)
    gefunden = finde(name)
    assert gefunden is not None
    return gefunden


def _roh_schreiben(eintraege: list[dict]) -> None:
    REGISTER.parent.mkdir(parents=True, exist_ok=True)
    REGISTER.write_text(
        json.dumps({"datenbanken": eintraege}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def umbenennen(alt: str, neu: str | None = None, titel: str | None = None,
               beschreibung: str | None = None) -> Datenbank:
    """Kennung, Titel oder Einordnung einer Datenbank ändern - **nur** die
    Registratur. Das Verzeichnis bleibt, wo es ist, und die Wortliste darin
    wird nicht angefasst; die Pakete hängen ohnehin an der Prüfsumme, nicht
    am Namen.

    ``None`` heisst „nicht angegeben", ``""`` heisst „leer machen" - beim
    Umbenennen ist eine leere Einordnung eine Absicht.

    Die Kennung des Grundeintrags lässt sich nicht ändern: Er ist fest im
    Code hinterlegt und käme beim nächsten Lesen unter seinem alten Namen
    zurück - dann zeigten zwei Einträge auf dasselbe Verzeichnis.
    """
    if neu is None and titel is None and beschreibung is None:
        raise ValueError("Nichts angegeben - --name, --titel oder --beschreibung.")
    eintraege = _roh_lesen()
    stelle = next((i for i, e in enumerate(eintraege)
                   if e.get("name", "").lower() == alt.lower()), None)
    if stelle is None:
        raise ValueError(f"'{alt}' ist nicht registriert (siehe 'db liste').")
    eintrag = dict(eintraege[stelle])

    if neu is not None and neu.lower() != alt.lower():
        if not NAMENSFORM.match(neu):
            raise ValueError(
                f"{neu!r} taugt nicht als Kennung: Buchstabe am Anfang, danach "
                "Buchstaben, Ziffern, - oder _, keine Leerzeichen, höchstens 32 "
                "Zeichen."
            )
        if eintrag.get("name") == GRUNDEINTRAG["name"]:
            raise ValueError(
                f"Die Kennung '{GRUNDEINTRAG['name']}' ist fest im Code "
                "hinterlegt und lässt sich nicht ändern - Titel und Einordnung "
                "schon."
            )
        if any(e.get("name", "").lower() == neu.lower() for e in eintraege):
            raise ValueError(f"'{neu}' gibt es schon.")
        eintrag["name"] = neu
    elif neu is not None:
        eintrag["name"] = neu          # nur die Schreibweise
    if titel is not None:
        eintrag["titel"] = titel
    if beschreibung is not None:
        eintrag["beschreibung"] = beschreibung

    eintraege[stelle] = eintrag
    _roh_schreiben(eintraege)
    gefunden = finde(eintrag["name"])
    assert gefunden is not None
    return gefunden
