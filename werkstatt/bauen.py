"""Setzt die Oberfläche aus Vorlage und Daten zusammen.

    python werkstatt/export.py     # zuerst die Daten
    python werkstatt/bauen.py      # dann die Seite

Das Ergebnis (``werkstatt/vokabelwerkstatt.html``) ist die Datei, die als
Artifact veröffentlicht wird. Bearbeitet wird immer ``vorlage.html`` - die
gebaute Datei entsteht daraus neu und wird nie von Hand geändert.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HIER = Path(__file__).resolve().parent
PLATZHALTER = "__DATEN__"


def baue(vorlage: Path, daten: Path, ziel: Path) -> int:
    text = vorlage.read_text("utf-8")
    if text.count(PLATZHALTER) != 1:
        raise SystemExit(
            f"{vorlage}: {PLATZHALTER} kommt {text.count(PLATZHALTER)}-mal vor, "
            "erwartet genau einmal."
        )
    # In der Datei stehen die Daten eingerückt, damit git sie lesbar
    # zeigt; in die Seite gehen sie kompakt. Und: die Daten stehen dort in
    # einem <script type="application/json">, wo ein "</" das Element
    # vorzeitig schlösse.
    roh = json.dumps(
        json.loads(daten.read_text("utf-8")), ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    ziel.write_text(text.replace(PLATZHALTER, roh), encoding="utf-8")
    return ziel.stat().st_size


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vorlage", default=str(HIER / "vorlage.html"))
    p.add_argument("--daten", default=str(HIER / "daten.json"))
    p.add_argument("-o", "--out", default=str(HIER / "vokabelwerkstatt.html"))
    args = p.parse_args()
    groesse = baue(Path(args.vorlage), Path(args.daten), Path(args.out))
    print(f"{args.out}: {groesse // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
