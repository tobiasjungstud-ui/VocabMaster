"""Eine hinaufgereichte Wortliste wieder zusammensetzen.

Die Werkstatt-Seite legt eine im Fenster gewählte Excel-Datei in Stücken in
der Artifact-Datenbank ab: je Stück ein Dokument mit Base64, dazu ein Kopf
mit Name, Grösse, Stückzahl und SHA-256. Der Chat holt diese Dokumente mit
seinem eigenen Werkzeug als JSON-Dateien herunter — hier werden sie wieder
eine Datei.

    python werkstatt/abholen.py <verzeichnis> -o data/

``<verzeichnis>`` ist, wohin die Dokumente ausgeschrieben wurden; darunter
liegen ``uploads/<kennung>.json`` (der Kopf) und
``uploads/<kennung>/teile/<nnnn>.json`` (die Stücke).

Die Prüfsumme ist der Punkt. Eine halb angekommene Wortliste sieht aus wie
eine ganze, bis mitten im Schuljahr Einheiten fehlen, die niemand vermisst
hat. Stimmt sie nicht, entsteht keine Datei — es gibt nichts, was man mit
einer halben Wortliste Sinnvolles täte.

Ein Kopf ohne ``fertig`` wird übersprungen: Er stammt von einem Upload, der
abgebrochen ist, bevor alle Stücke lagen.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path


class Unvollstaendig(Exception):
    """Der Upload taugt nicht — mit dem Grund im Klartext."""


def _inhalt(pfad: Path) -> dict:
    """Das Dokument aus einer ausgeschriebenen JSON-Datei.

    Je nachdem, wie ausgeschrieben wurde, steht das Dokument entweder nackt
    in der Datei oder in einem Umschlag mit ``id``/``version``. Beides wird
    genommen; zu raten gibt es nichts, denn nur eine der beiden Formen hat
    ein ``data``-Feld mit einem Objekt darin.
    """
    roh = json.loads(pfad.read_text("utf-8"))
    if isinstance(roh, dict) and isinstance(roh.get("data"), dict):
        return roh["data"]
    if not isinstance(roh, dict):
        raise Unvollstaendig(f"{pfad.name}: kein Dokument")
    return roh


def _teile_lesen(ordner: Path, erwartet: int) -> list[str]:
    """Die Stücke in ihrer Reihenfolge — lückenlos oder gar nicht."""
    if not ordner.is_dir():
        raise Unvollstaendig(f"kein Verzeichnis {ordner.name}/teile")
    nach_nummer: dict[int, str] = {}
    for pfad in sorted(ordner.glob("*.json")):
        stueck = _inhalt(pfad)
        nummer = stueck.get("nummer")
        text = stueck.get("text")
        if not isinstance(nummer, int) or not isinstance(text, str):
            raise Unvollstaendig(f"{pfad.name}: Stück ohne Nummer oder Text")
        if nummer in nach_nummer:
            raise Unvollstaendig(f"Stück {nummer} liegt doppelt")
        nach_nummer[nummer] = text
    fehlend = [n for n in range(erwartet) if n not in nach_nummer]
    if fehlend:
        raise Unvollstaendig(
            f"{len(fehlend)} von {erwartet} Stücken fehlen "
            f"(erstes: {fehlend[0]})"
        )
    if len(nach_nummer) > erwartet:
        raise Unvollstaendig(
            f"{len(nach_nummer)} Stücke, aber nur {erwartet} angekündigt"
        )
    return [nach_nummer[n] for n in range(erwartet)]


def zusammensetzen(kopf_pfad: Path) -> tuple[str, bytes]:
    """Aus Kopf und Stücken die Datei — Name und Inhalt.

    Geprüft wird beides, was der Kopf verspricht: die Länge des Base64 und
    die Prüfsumme der entpackten Bytes. Die erste findet ein verlorenes
    Stück, die zweite ein verfälschtes.
    """
    kopf = _inhalt(kopf_pfad)
    name = kopf.get("datei")
    if not isinstance(name, str) or not name:
        raise Unvollstaendig("der Kopf nennt keinen Dateinamen")
    if not kopf.get("fertig"):
        raise Unvollstaendig(
            "der Upload ist nie fertig geworden — der Kopf trägt kein "
            "„fertig“, also fehlen Stücke"
        )
    anzahl = kopf.get("teile")
    if not isinstance(anzahl, int) or anzahl < 1:
        raise Unvollstaendig("der Kopf nennt keine Stückzahl")

    ordner = kopf_pfad.with_suffix("") / "teile"
    text = "".join(_teile_lesen(ordner, anzahl))

    zeichen = kopf.get("zeichen")
    if isinstance(zeichen, int) and len(text) != zeichen:
        raise Unvollstaendig(
            f"{len(text)} Zeichen angekommen, {zeichen} angekündigt"
        )

    try:
        roh = base64.b64decode(text, validate=True)
    except Exception as e:  # noqa: BLE001 - der Grund gehört in die Meldung
        raise Unvollstaendig(f"die Stücke ergeben kein Base64: {e}") from e

    groesse = kopf.get("groesse")
    if isinstance(groesse, int) and len(roh) != groesse:
        raise Unvollstaendig(
            f"{len(roh)} Bytes angekommen, {groesse} angekündigt"
        )

    erwartet = kopf.get("pruefsumme")
    if not isinstance(erwartet, str) or not erwartet:
        raise Unvollstaendig("der Kopf nennt keine Prüfsumme")
    gerechnet = hashlib.sha256(roh).hexdigest()
    if gerechnet != erwartet:
        raise Unvollstaendig(
            "die Prüfsumme stimmt nicht — angekündigt "
            f"{erwartet[:16]}…, angekommen {gerechnet[:16]}…"
        )
    return name, roh


def koepfe(verzeichnis: Path) -> list[Path]:
    """Jeden Upload-Kopf unter ``<verzeichnis>``, neueste zuletzt."""
    ordner = verzeichnis / "uploads"
    if not ordner.is_dir():
        ordner = verzeichnis
    return sorted(p for p in ordner.glob("*.json") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    p.add_argument("verzeichnis", type=Path,
                   help="wohin die Dokumente ausgeschrieben wurden")
    p.add_argument("-o", "--ziel", type=Path, default=Path("data"),
                   help="wohin die Datei soll (Vorgabe: data/)")
    args = p.parse_args(argv)

    gefunden = koepfe(args.verzeichnis)
    if not gefunden:
        print(f"Kein Upload unter {args.verzeichnis}.", file=sys.stderr)
        return 1

    args.ziel.mkdir(parents=True, exist_ok=True)
    fehler = 0
    for kopf_pfad in gefunden:
        try:
            name, roh = zusammensetzen(kopf_pfad)
        except Unvollstaendig as e:
            print(f"{kopf_pfad.stem}: {e}", file=sys.stderr)
            fehler += 1
            continue
        ziel = args.ziel / Path(name).name
        ziel.write_bytes(roh)
        print(f"{ziel}: {len(roh)} Bytes, Prüfsumme stimmt")
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
