"""Schreibt die Daten, aus denen die Vokabelwerkstatt-Oberfläche besteht.

Die Oberfläche rechnet nichts nach: Wortauswahl, Schwierigkeit und Lücken
kommen aus den fertigen Paketen unter ``kuratiert/`` und aus der Datenbank,
damit die Vorschau im Browser dasselbe zeigt wie der spätere Bau.

    python werkstatt/export.py            # schreibt werkstatt/daten.json
    python werkstatt/export.py -o x.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "src"))

from vocabmaster.config import Settings  # noqa: E402
from vocabmaster.database import Database  # noqa: E402
from vocabmaster.exam.difficulty import score  # noqa: E402
from vocabmaster.niveau import PROFILES  # noqa: E402
from vocabmaster.pack import wortart_von  # noqa: E402
from vocabmaster.pool import plan_unit  # noqa: E402


def _zipf_tabelle(db: Database, unit: int) -> dict[str, float]:
    """Häufigkeit je Wort der Unit.

    Mehrwortausdrücke stehen in der Wortliste oft ausführlicher als in der
    Vokabelliste ("remind sb of sth" gegen "remind of"), deshalb zählt auch
    das Stichwort als Schlüssel. Ergänzte Wörter stehen nirgends und
    behalten 0.
    """
    tabelle: dict[str, float] = {}
    for row in db.unit_pool(unit, core_only=False):
        for schluessel in (row.english, row.headword):
            if schluessel:
                tabelle.setdefault(schluessel.lower(), round(row.zipf, 2))
    return tabelle


def _stamm(englisch: str) -> str:
    """Das erste Wort eines Mehrwortausdrucks - als zweiter Versuch."""
    return englisch.lower().split()[0] if englisch.split() else ""


def _woerter(pack: dict, zipf: dict[str, float]) -> list[dict]:
    heraus = []
    for test, schluessel in ((1, "test1"), (2, "test2")):
        for eintrag in pack["liste"][schluessel]:
            en = eintrag["englisch"]
            de = eintrag["deutsch"]
            pos = wortart_von(eintrag)
            heraus.append({
                "nr": eintrag["nr"],
                "test": test,
                "en": en,
                "de": de,
                "pos": pos,
                "satz": eintrag.get("satz", ""),
                "score": round(score(en, de, pos).score, 2),
                "zipf": zipf.get(en.lower(), zipf.get(_stamm(en), 0.0)),
                "quelle": eintrag.get("herkunft", "wortliste"),
                "abschnitt": eintrag.get("abschnitt", ""),
            })
    return heraus


def _rang(nach_en: dict[str, dict], englisch: str) -> float:
    return float(nach_en.get(englisch.lower(), {}).get("score", 0.0))


def _echte_auswahl(pack: dict, woerter: list[dict]) -> dict[str, dict]:
    """Die Wörter, die in den vier Prüfungen wirklich stehen."""
    nach_en = {w["en"].lower(): w for w in woerter}
    heraus: dict[str, dict] = {}
    for teil, tnr in (("teil1", 1), ("teil2", 2)):
        for niveau in ("A", "B"):
            # Niveau A führt mit den schwersten Wörtern, Niveau B mit den
            # zugänglichsten - so, wie die Oberfläche beide Spalten zeigt.
            zuerst = PROFILES[niveau].zuerst
            pruef = pack["pruefungen"][teil][niveau]
            uebersetzen = [i["english"] for i in pruef["task1"]["items"]]
            # `word_bank` steht auf Deutsch im Blatt; die englische Lösung
            # jeder Lücke liefert `gaps`.
            luecken = [g["answer"] for g in pruef["task2"].get("gaps") or []]
            alle = uebersetzen + [w for w in luecken if w not in uebersetzen]
            rang = {w: _rang(nach_en, w) for w in alle}
            alle.sort(key=lambda w: (-rang[w] if zuerst else rang[w], w))
            werte = [rang[w] for w in alle if w.lower() in nach_en]
            heraus[f"t{tnr}{niveau}"] = {
                "woerter": alle,
                "luecken": luecken,
                "schnitt": round(sum(werte) / len(werte), 2) if werte else 0.0,
            }
    return heraus


def _herkunft(db: Database, unit: int, settings: Settings) -> dict[str, int]:
    """Wie die Auswahl zustande kam - dieselbe Rechnung wie beim Gerüst."""
    r = plan_unit(db, unit, settings).report
    return {
        "hauptteil": r.hauptteil,
        "gefiltert": r.hauptteil - r.brauchbar,
        "gewaehlt": r.aus_hauptteil,
        "ergaenzt": r.fehlend,
        "zusatzteile": len(r.aus_zusatzteilen),
    }


def baue(pakete: Path, db: Database, settings: Settings) -> dict:
    themen = json.loads(
        (WURZEL / "src" / "vocabmaster" / "data" / "themen.json").read_text("utf-8")
    )["themen"]

    units = []
    quelle = None
    for datei in sorted(pakete.glob("unit_*.json")):
        pack = json.loads(datei.read_text("utf-8"))
        # Fassungspakete (unit_01_fassung2.json) enthalten nur eine einzelne
        # Prüfung und keine zweite Niveaustufe. Die Oberfläche zeigt die
        # Grundfassung; eine weitere Fassung entsteht erst auf Auftrag.
        if int(pack.get("fassung", 1)) > 1:
            continue
        unit = pack["unit"]
        quelle = quelle or pack["quelle"]
        thema = themen.get(str(unit), {})
        zipf = _zipf_tabelle(db, unit)
        woerter = _woerter(pack, zipf)
        units.append({
            "unit": unit,
            "titel": pack.get("unit_label") or pack.get("titel", f"Unit {unit}"),
            "thema": pack.get("thema") or thema.get("thema", ""),
            "seiten": thema.get("seiten", ""),
            "herkunft": _herkunft(db, unit, settings),
            "woerter": woerter,
            "echt": _echte_auswahl(pack, woerter),
        })

    return {
        "quelle": quelle or {},
        "niveaus": {
            n: {
                "label": p.label,
                "cefr": p.cefr,
                "beschreibung": p.beschreibung,
            }
            for n, p in PROFILES.items()
        },
        "units": units,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-o", "--out", default=str(Path(__file__).parent / "daten.json"))
    p.add_argument("--pakete", default=str(WURZEL / "kuratiert"))
    args = p.parse_args()

    daten = baue(Path(args.pakete), Database.load(), Settings())
    Path(args.out).write_text(
        json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"{args.out}: {len(daten['units'])} Units, "
          f"{sum(len(u['woerter']) for u in daten['units'])} Wörter")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
