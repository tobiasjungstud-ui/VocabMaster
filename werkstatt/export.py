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
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "src"))

from vocabmaster import datenbanken as _dbs  # noqa: E402
from vocabmaster import paedagogik as _paed  # noqa: E402
from vocabmaster.config import Settings  # noqa: E402
from vocabmaster.database import Database  # noqa: E402
from vocabmaster.exam.difficulty import score  # noqa: E402
from vocabmaster.exam.english import readability  # noqa: E402
from vocabmaster.list.dedup import deduplicate  # noqa: E402
from vocabmaster.list.leveling import LevelContext, is_usable  # noqa: E402
from vocabmaster.niveau import (  # noqa: E402
    _GRAD_SPANNE,
    _TEXT_ANKER,
    NORMAL_TEXTSTUFE,
    PROFILES,
    textstufe,
)
from vocabmaster.pack import wortart_von  # noqa: E402
from vocabmaster.pool import _bewerten, plan_unit  # noqa: E402

#: Die Begründungen der Auswahl in Gruppen. Die Anwendung schreibt sie als
#: ganze Sätze und trägt den Zipf-Wert mitten hinein - fünfzehn Sätze für
#: denselben Grund. Für eine Spalte, in der man nach Gründen sortiert,
#: braucht es ein kurzes Wort; der ganze Satz bleibt je Wort daneben stehen.
GRUENDE = (
    ("Grundwortschatz", "A1/A2-Grundwortschatz"),
    ("zu häufig", "zu häufig, damit bekannt"),
    ("Deckungsgleich", "Kognat — aus dem Deutschen abzuschreiben"),
    ("früheren Unit", "früher schon gelernt"),
)


def _grund(satz: str) -> str:
    for merkmal, kurz in GRUENDE:
        if merkmal in satz:
            return kurz
    return "aussortiert"


def _hauptteil(db: Database, unit: int) -> list[dict]:
    """Jedes Wort des Hauptteils - mit dem Urteil der Auswahl darüber.

    Damit lässt sich in der Oberfläche nebeneinanderlegen, was in der Liste
    steht und was nicht, und einzelne Wörter von Hand herüberholen. Die
    Auswahl selbst rührt das nicht an: Sie trifft weiterhin `plan_unit`,
    hier wird nur nachgezeichnet, was sie verworfen hat und warum.

    Das Urteil gehört zur **Unit, nicht zur Liste**: Ob ein Wort zum
    Grundwortschatz zählt, hängt nicht davon ab, welche Liste man gerade
    ansieht. Ein leeres ``grund`` heisst „brauchbar" - ob ein brauchbares
    Wort in *dieser* Liste steht, rechnet die Oberfläche aus, denn es kann
    je Liste anders ausfallen.
    """
    rows = db.unit_pool(unit, core_only=True)
    kandidaten = _bewerten(rows, LevelContext.from_entries(db.earlier(unit)))
    brauchbar = [c for c in kandidaten if is_usable(c)]
    _, verloren = deduplicate(brauchbar)
    zugunsten = {
        (loser.headword or loser.english).lower(): (winner.headword or winner.english)
        for loser, winner, _ in verloren
    }

    heraus = []
    for c in kandidaten:
        en = c.english or c.headword or ""
        if not en:
            continue
        if not is_usable(c):
            satz = c.notes[0] if c.notes else "ohne Begründung aussortiert"
            grund, text = _grund(satz), satz
        elif en.lower() in zugunsten:
            grund = "Doppelung"
            text = f"Deckt sich mit {zugunsten[en.lower()]}."
        else:
            # Brauchbar und nicht doppelt. Ob es in die Liste kam, entscheidet
            # sich erst je Liste - die Oberfläche weiss das besser als wir.
            grund = ""
            text = ""
        de = c.german or ""
        pos = wortart_von({"englisch": en, "deutsch": de})
        heraus.append({
            "en": en,
            "de": de,
            "pos": pos,
            "grund": grund,
            "warum": text,
            "score": round(score(en, de, pos).score, 2),
            "zipf": round(float(c.zipf or 0.0), 2),
            "abschnitt": getattr(c, "section", "") or "",
        })
    heraus.sort(key=lambda w: (bool(w["grund"]), -w["score"], w["en"]))
    return heraus


def datei_name(unit: int, version: int) -> str:
    """Wie das Paket dieser Liste heisst - für die Anzeige."""
    name = f"unit_{unit:02d}"
    if version > 1:
        name += f"_v{version}"
    return name + ".json"


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
            text = re.sub(r"\{\d+\}", "word", pruef["task2"].get("text", ""))
            mass = readability(text) if text else {}
            heraus[f"t{tnr}{niveau}"] = {
                "woerter": alle,
                "luecken": luecken,
                "schnitt": round(sum(werte) / len(werte), 2) if werte else 0.0,
                "textstufe": textstufe(mass) if mass else 0.0,
                "textmass": {
                    "woerter": mass.get("words", 0),
                    "satzlaenge": mass.get("words_per_sentence", 0),
                    "lesbarkeit": mass.get("flesch_reading_ease", 0),
                    "grad": mass.get("flesch_kincaid_grade", 0),
                    "nebensaetze": round(
                        mass.get("subordinators", 0)
                        / max(1, mass.get("sentences", 1)), 2
                    ),
                } if mass else {},
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

    # Je Unit kann es mehrere Vokabellisten geben (V1, V2, ...). Jede ist ein
    # eigener Eintrag mit ihren eigenen 60 Wörtern; die Oberfläche lässt
    # zwischen ihnen wählen, statt eine davon zu erraten.
    roh: dict[int, list[dict]] = {}
    # Eine Fassung ist eine weitere Ausgabe **einer** Prüfung, nicht der
    # ganzen Liste: `vocabmaster fassung ... --teil 1 --niveau A` legt genau
    # eine an. Welche, muss die Oberfläche sagen können - sonst liest sich
    # "Fassung 2, 3" wie eine zweite und dritte Vokabelliste.
    fassungen: dict[tuple[int, int], list[dict]] = {}
    quelle = None
    for datei in sorted(pakete.glob("unit_*.json")):
        pack = json.loads(datei.read_text("utf-8"))
        unit = int(pack["unit"])
        version = int(pack.get("liste_version", 1))
        if int(pack.get("fassung", 1)) > 1:
            # Ein Fassungspaket ist eine weitere Prüfung zu einer bestehenden
            # Liste, keine eigene Liste.
            for teil, tnr in (("teil1", 1), ("teil2", 2)):
                for niveau in ("A", "B"):
                    if niveau in pack.get("pruefungen", {}).get(teil, {}):
                        fassungen.setdefault((unit, version), []).append({
                            "nummer": int(pack.get("fassung", 1)),
                            "teil": tnr,
                            "niveau": niveau,
                        })
            continue
        quelle = quelle or pack["quelle"]
        roh.setdefault(unit, []).append(pack)

    units = []
    for unit in sorted(roh):
        thema = themen.get(str(unit), {})
        zipf = _zipf_tabelle(db, unit)
        listen = []
        for pack in sorted(roh[unit], key=lambda p: int(p.get("liste_version", 1))):
            version = int(pack.get("liste_version", 1))
            woerter = _woerter(pack, zipf)
            aufgewertet = [
                {"en": e["englisch"], "de": e["deutsch"],
                 "ersetzt": e.get("ersetzt", ""),
                 "begruendung": e.get("begruendung", "")}
                for e in pack["liste"]["test1"] + pack["liste"]["test2"]
                if e.get("herkunft") == "fancy"
            ]
            offen = sum(1 for e in pack["liste"]["test1"] + pack["liste"]["test2"]
                        if not e.get("englisch") or not e.get("satz"))
            listen.append({
                "version": version,
                "datei": datei_name(unit, version),
                "abdruck": pack.get("pruefungen", {}).get("teil1", {})
                               .get("A", {}).get("meta", {})
                               .get("liste_fingerabdruck", ""),
                "erzeugt": pack.get("erzeugt", ""),
                "aufgewertet": aufgewertet,
                "offen": offen,
                "fassungen": sorted(
                    fassungen.get((unit, version), []),
                    key=lambda f: (f["nummer"], f["teil"], f["niveau"]),
                ),
                "woerter": woerter,
                "echt": _echte_auswahl(pack, woerter),
            })
        units.append({
            "unit": unit,
            "titel": roh[unit][0].get("unit_label") or f"Unit {unit}",
            "thema": roh[unit][0].get("thema") or thema.get("thema", ""),
            "seiten": thema.get("seiten", ""),
            "leitwoerter": thema.get("leitwoerter", []),
            "herkunft": _herkunft(db, unit, settings),
            "listen": listen,
            # Was die Unit hergibt - alles, mit dem Urteil der Auswahl. Die
            # Oberfläche legt es neben die gewählte Liste, damit man sieht,
            # was fehlt, und einzelne Wörter von Hand herüberholen kann.
            "hauptteil": _hauptteil(db, unit),
        })

    return {
        "quelle": quelle or {},
        # Welche Vokabeldatenbanken registriert sind. Die Seite zeigt sie
        # zur Auswahl; gebaut wird im Chat mit --datenbank <Name>.
        "datenbanken": [
            {"name": d.name, "titel": d.titel, "beschreibung": d.beschreibung,
             "units": d.units, "vorhanden": d.vorhanden,
             "quelle": d.quelle.get("datei", ""),
             "importiert": d.quelle.get("importiert", "")}
            for d in _dbs.alle()
        ],
        "aktive_datenbank": _dbs.GRUNDEINTRAG["name"],
        # Die Stufen des pädagogischen Rankings, mit ihren Bändern.
        "ranking_stufen": [
            {"name": st.name, "titel": st.titel,
             "zipf_min": st.zipf_min, "zipf_max": st.zipf_max,
             "mindest_schwierigkeit": st.mindest_schwierigkeit,
             "beschreibung": st.beschreibung}
            for st in _paed.STUFEN.values()
        ],
        "ranking_vorgabe": _paed.STUFE_VORGABE,
        "ranking_kriterien": [name for _, name in _paed._RANGFOLGE],
        "textstufe_normal": dict(NORMAL_TEXTSTUFE),
        # Damit die Oberfläche die Zielbänder mit denselben Zahlen ausrechnet
        # wie die Anwendung und nicht mit einer Kopie davon.
        "textanker": {k: list(v) for k, v in _TEXT_ANKER.items()},
        "textgrad_spanne": _GRAD_SPANNE,
        "niveaus": {
            n: {
                "label": p.label,
                "cefr": p.cefr,
                "beschreibung": p.beschreibung,
                "textziele": dict(p.level_targets),
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
    listen = sum(len(u["listen"]) for u in daten["units"])
    woerter = sum(len(li["woerter"]) for u in daten["units"] for li in u["listen"])
    print(f"{args.out}: {len(daten['units'])} Units, {listen} Vokabellisten, "
          f"{woerter} Wörter")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
