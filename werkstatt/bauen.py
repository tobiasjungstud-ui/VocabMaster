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
#: Drei Platzhalter, und die Reihenfolge ist nicht beliebig - siehe `baue`.
PLATZHALTER = ("__DATEN__", "__QUELLE__", "__KLINGEL__")


def _json_fuer_script(wert: object) -> str:
    """JSON so, dass es in einem <script type="application/json"> überlebt.

    Ein ``</`` schlösse das Element vorzeitig. In JSON ist ``\\/`` eine
    gültige Schreibweise für ``/``, also kommt der Leser unverändert an sein
    Ergebnis - ``JSON.parse`` löst es von selbst auf.
    """
    return json.dumps(wert, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def baue(vorlage: Path, daten: Path, ziel: Path, klingel: object = None) -> int:
    """Setzt die Seite aus Vorlage, Daten und Klingel zusammen.

    Die Seite trägt ihre eigene Vorlage mit (``__QUELLE__``), damit sie sich
    selbst neu veröffentlichen kann - das ist die Klingel, mit der ein Knopf
    auf der Seite die Chat-Sitzung weckt. Eingebettet wird die **Vorlage**
    mit ihren Platzhaltern, nicht die gebaute Seite; sonst müsste die Datei
    sich selbst enthalten.

    Deshalb steht ``__QUELLE__`` **zuletzt**: Die eingebettete Vorlage muss
    alle drei Platzhalter unversehrt behalten. Wird sie früher eingesetzt,
    trifft die nächste Ersetzung ihr eigenes Vorkommen darin - und die
    übernächste Fassung kann sich nicht mehr selbst bauen. Genau das ist
    beim ersten Versuch passiert. Die Seite hält sich an dieselbe
    Reihenfolge; ein Test baut beide und vergleicht sie Byte für Byte.
    """
    text = vorlage.read_text("utf-8")
    for platzhalter in PLATZHALTER:
        if text.count(platzhalter) != 1:
            raise SystemExit(
                f"{vorlage}: {platzhalter} kommt {text.count(platzhalter)}-mal "
                "vor, erwartet genau einmal."
            )
    # In der Datei stehen die Daten eingerückt, damit git sie lesbar zeigt;
    # in die Seite gehen sie kompakt.
    roh = _json_fuer_script(json.loads(daten.read_text("utf-8")))
    seite = (
        text.replace("__DATEN__", roh)
        .replace("__KLINGEL__", _json_fuer_script(klingel))
        .replace("__QUELLE__", _json_fuer_script(text))
    )
    ziel.write_text(seite, encoding="utf-8")
    return ziel.stat().st_size


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vorlage", default=str(HIER / "vorlage.html"))
    p.add_argument("--daten", default=str(HIER / "daten.json"))
    p.add_argument("-o", "--out", default=str(HIER / "vokabelwerkstatt.html"))
    p.add_argument("--klingel", default=None,
                   help="Kennung des auslösenden Auftrags - normalerweise "
                        "leer; die Seite setzt sie beim Selbstveröffentlichen")
    args = p.parse_args()
    klingel = json.loads(args.klingel) if args.klingel else None
    groesse = baue(Path(args.vorlage), Path(args.daten), Path(args.out), klingel)
    print(f"{args.out}: {groesse // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
