"""Packt die gebauten Word-Dateien so, dass die Seite sie ausliefern kann.

    python werkstatt/beilagen.py      # schreibt werkstatt/beilagen/

Neben einer veröffentlichten Seite lassen sich nur übliche Web-Medientypen
ausliefern - eine ``.docx`` gehört nicht dazu. Jede Datei wird deshalb in
ein JSON gepackt (Base64), das die Seite bei einem Klick holt, entpackt und
über die Fähigkeit ``downloads`` weiterreicht. Der Betrachter bekommt sie
unter ihrem richtigen Namen; ``docx`` steht dort auf der Liste der erlaubten
Endungen.

Gepackt wird erst beim Veröffentlichen, nicht bei jedem Bau: Die Beilagen
sind abgeleitet und stehen deshalb nicht unter Versionskontrolle.
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent


def packe(gebaut: Path, ziel: Path) -> list[Path]:
    """Schreibt je Word-Datei ein ``<name>.docx.json``."""
    if ziel.exists():
        # Was nicht mehr gebaut ist, darf nicht als Beilage liegenbleiben:
        # Sonst bietet die Seite eine Prüfung an, die es nicht mehr gibt.
        shutil.rmtree(ziel)
    if not gebaut.is_dir():
        return []
    ziel.mkdir(parents=True)
    geschrieben = []
    for datei in sorted(gebaut.glob("*.docx")):
        roh = datei.read_bytes()
        paket = ziel / (datei.name + ".json")
        paket.write_text(json.dumps({
            "datei": datei.name,
            "groesse": len(roh),
            "base64": base64.b64encode(roh).decode("ascii"),
        }), encoding="utf-8")
        geschrieben.append(paket)
    return geschrieben


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gebaut", default=str(WURZEL / "out"))
    p.add_argument("-o", "--out", default=str(HIER / "beilagen"))
    args = p.parse_args()
    dateien = packe(Path(args.gebaut), Path(args.out))
    gesamt = sum(d.stat().st_size for d in dateien)
    print(f"{args.out}: {len(dateien)} Beilagen, {gesamt // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
