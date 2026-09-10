"""Das Unit-Paket: eine Datei je Unit und Niveau, von der Auswahl bis zum Druck.

Ein Paket hält alles zusammen, was für **eine** Unit auf **einem** Niveau
gebraucht wird: die 60 Wörter der Vokabelliste (Test 1 und Test 2), die
Beispielsätze und die beiden Prüfungen (Teil I und Teil II). Getrennte
Dateien je Unit und Niveau sind Absicht: ``Test B für Unit 3 neu erzeugen``
rührt ``unit_03_A.json`` nicht an.

Ablauf:

1. ``vocabmaster gerüst 3 --niveau A`` schreibt ``kuratiert/unit_03_A.json``
   mit der geprüften Wortauswahl und leeren Feldern für die Sätze.
2. Die Felder ``satz`` und die beiden Lückentexte werden **im Chat**
   geschrieben - vom Sprachmodell selbst, ohne Musterbausteine.
3. ``vocabmaster bauen kuratiert/unit_03_A.json`` prüft alles und schreibt
   die Word-Dateien.

Die Datei ist bewusst schlichtes JSON: sie lässt sich von Hand bearbeiten und
ihr Diff im Git-Verlauf lesen.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from .config import Settings
from .database import Database
from .exam.difficulty import score_item
from .exam.vocab import VocabItem, VocabTest, guess_pos
from .niveau import NiveauProfile, profile
from .pool import UnitPlan, plan_both

SCHEMA_VERSION = 1

ANLEITUNG = [
    "Feld 'satz' je Eintrag ausfüllen: ein natürlicher, idiomatischer",
    "Beispielsatz, der das Zielwort erschliessbar macht, ohne die deutsche",
    "Lösung zu verraten. Keine Definitionen ('A villain is a bad person').",
    "Feld 'form' ist die im Satz verwendete Wortform für die Fettschrift und",
    "darf leer bleiben - sie wird dann selbst bestimmt.",
    "Einträge mit 'herkunft': 'ergänzt' stehen nicht in der Wortliste des",
    "Lehrmittels und müssen thematisch zur Unit passen; ihr Anteil ist auf",
    "40 Prozent begrenzt und wird im Prüfbericht ausgewiesen.",
    "In jeder Prüfung 'task2.text' schreiben: {1} bis {4} markieren die",
    "Lücken, die Reihenfolge in 'gaps' ist die Reihenfolge im Text.",
]

_TEIL = {1: ("Part I", "Test 1"), 2: ("Part II", "Test 2")}


# ---------------------------------------------------------------------------
# Gerüst
# ---------------------------------------------------------------------------
def _list_entry(number: int, english: str, german: str, herkunft: str,
                abschnitt: str = "") -> dict[str, Any]:
    return {
        "nr": number,
        "deutsch": german,
        "englisch": english,
        "satz": "",
        "form": "",
        "herkunft": herkunft,
        "abschnitt": abschnitt,
    }


def _placeholder(number: int) -> dict[str, Any]:
    entry = _list_entry(number, "", "", "ergänzt")
    entry["hinweis"] = (
        "Zu ergänzen: ein thematisch passendes, im Englischen gebräuchliches "
        "Wort, das noch in keiner der beiden Listen dieser Unit steht."
    )
    return entry


def _exam_scaffold(
    items: list[dict[str, Any]],
    unit_label: str,
    teil: int,
    prof: NiveauProfile,
    settings: Settings,
    seed: int,
) -> dict[str, Any]:
    """Wortauswahl für eine Prüfung: die schwersten Wörter, die sich nicht
    in die Quere kommen - für Niveau B die zugänglicheren derselben Liste."""
    part_label, source = _TEIL[teil]
    usable = [i for i in items if i["englisch"] and i["deutsch"]]
    scored = sorted(
        usable,
        key=lambda i: -score_item(
            {"english": i["englisch"], "german": i["deutsch"],
             "pos": guess_pos(i["deutsch"])}
        ).score,
    )
    take = settings.exam_words
    # Niveau A prüft von oben, Niveau B aus der Mitte: die schwersten Wörter
    # der eigenen Liste sind für die schwächere Gruppe der Frust, die
    # leichtesten prüfen nichts.
    chosen = scored[:take] if prof.name == "A" else scored[len(scored) // 4 :][:take]
    if len(chosen) < take:
        chosen = scored[:take]

    by_score = sorted(
        chosen,
        key=lambda i: -score_item(
            {"english": i["englisch"], "german": i["deutsch"],
             "pos": guess_pos(i["deutsch"])}
        ).score,
    )
    gaps: list[dict[str, Any]] = []
    for pos in ("verb", "noun", "adj"):
        for entry in by_score:
            if len(gaps) >= settings.exam_gaps:
                break
            if guess_pos(entry["deutsch"]) == pos and entry not in gaps:
                gaps.append(entry)
                break
    for entry in by_score:
        if len(gaps) >= settings.exam_gaps:
            break
        if entry not in gaps:
            gaps.append(entry)

    translation = [e for e in chosen if e not in gaps]
    rng = random.Random(seed + teil)
    bank = [g["deutsch"] for g in gaps]
    while len(bank) > 1 and bank == [g["deutsch"] for g in gaps]:
        rng.shuffle(bank)

    sentence_unit = f"{unit_label.lower()} {part_label.lower()}"
    number = unit_label.split()[-1] if unit_label.split() else ""
    return {
        "meta": {
            "titel": f"{unit_label} {part_label} - Vokabelprüfung, Niveau {prof.name}",
            "niveau": prof.name,
            "cefr": prof.cefr,
            "quelle_liste": source,
        },
        "total_words": settings.exam_words,
        "header": {
            "title": " Vocabulary",
            "unit": f"Unit {number} |{part_label}",
            "name_label": "Name:",
            "grade_label": "Grade :",
        },
        "task1": {
            "instruction": f"1) Translate using the vocabulary from {sentence_unit}.",
            "items": [
                {"german": e["deutsch"], "english": e["englisch"],
                 "pos": guess_pos(e["deutsch"])}
                for e in translation
            ],
        },
        "task2": {
            "instruction": f"2)  Fill in the gaps using the vocabulary from {sentence_unit}. ",
            "word_bank_label": "Words:",
            "word_bank": bank,
            "gaps": [
                {"german": g["deutsch"], "english": g["englisch"],
                 "answer": g["englisch"], "pos": guess_pos(g["deutsch"])}
                for g in gaps
            ],
            "text": (
                "TODO: Lückentext schreiben - "
                + " ".join(f"{{{i + 1}}}" for i in range(settings.exam_gaps))
            ),
        },
    }


def scaffold(
    db: Database,
    unit: int,
    niveau: str | NiveauProfile,
    settings: Settings | None = None,
    plan: UnitPlan | None = None,
) -> dict[str, Any]:
    """Das leere Paket einer Unit für ein Niveau."""
    settings = settings or Settings()
    prof = profile(niveau)
    if plan is None:
        plan = plan_both(db, unit, settings)[prof.name]

    theme = db.theme(unit)
    blocks: dict[str, list[dict[str, Any]]] = {}
    for name, words in (("test1", plan.test1), ("test2", plan.test2)):
        rows = []
        for number, c in enumerate(words, 1):
            source = plan.herkunft.get(c.headword.lower())
            rows.append(
                _list_entry(
                    number,
                    c.headword or c.english,
                    c.german,
                    "wortliste" if source else "ergänzt",
                    f"{source.section}, S. {source.page}" if source and source.page
                    else (source.section if source else ""),
                )
            )
        blocks[name] = rows

    # Fehlbestand gleichmässig auf beide Tests verteilen, damit die Lücke
    # nicht ganz am Ende von Test 2 klebt.
    missing = settings.target_total - len(plan.all_words)
    for _ in range(missing):
        target = "test1" if len(blocks["test1"]) <= len(blocks["test2"]) else "test2"
        blocks[target].append(_placeholder(len(blocks[target]) + 1))
    for rows in blocks.values():
        for number, row in enumerate(rows, 1):
            row["nr"] = number

    unit_label = db.unit_label(unit)
    return {
        "schema": SCHEMA_VERSION,
        "unit": unit,
        "unit_label": unit_label,
        "titel": theme.get("titel", unit_label),
        "thema": theme.get("thema", ""),
        "leitwoerter": theme.get("leitwoerter", []),
        "niveau": prof.name,
        "cefr": prof.cefr,
        "zielgruppe": prof.beschreibung,
        "quelle": dict(db.quelle),
        "erzeugt": date.today().isoformat(),
        "fehlbestand": missing,
        "anleitung": ANLEITUNG,
        "liste": blocks,
        "pruefungen": {
            "teil1": _exam_scaffold(blocks["test1"], unit_label, 1, prof, settings,
                                    settings.seed),
            "teil2": _exam_scaffold(blocks["test2"], unit_label, 2, prof, settings,
                                    settings.seed),
        },
    }


# ---------------------------------------------------------------------------
# Lesen
# ---------------------------------------------------------------------------
def _no_duplicate_keys(pairs):
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"Doppelter Schlüssel {key!r} in der Paketdatei.")
        seen[key] = value
    return seen


@dataclass
class Pack:
    """Ein geladenes Unit-Paket."""

    data: dict[str, Any] = field(default_factory=dict)
    pfad: Path | None = None

    @classmethod
    def load(cls, path: str | Path) -> Pack:
        target = Path(path)
        data = json.loads(target.read_text(encoding="utf-8"),
                          object_pairs_hook=_no_duplicate_keys)
        return cls(data=data, pfad=target)

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path or self.pfad)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return target

    # ------------------------------------------------------------- Zugriffe
    @property
    def unit(self) -> int:
        return int(self.data.get("unit", 0))

    @property
    def unit_label(self) -> str:
        return str(self.data.get("unit_label") or f"Unit {self.unit}")

    @property
    def niveau(self) -> NiveauProfile:
        return profile(self.data.get("niveau", "A"))

    @property
    def thema(self) -> str:
        return str(self.data.get("thema", ""))

    @property
    def quelle(self) -> dict[str, Any]:
        return dict(self.data.get("quelle", {}))

    def entries(self, block: str) -> list[dict[str, Any]]:
        return list(self.data.get("liste", {}).get(block, []))

    @property
    def all_entries(self) -> list[dict[str, Any]]:
        return self.entries("test1") + self.entries("test2")

    def exam(self, teil: int) -> dict[str, Any]:
        return dict(self.data.get("pruefungen", {}).get(f"teil{teil}", {}))

    @property
    def exams(self) -> dict[int, dict[str, Any]]:
        return {t: self.exam(t) for t in (1, 2) if self.exam(t)}

    def vocab_test(self, teil: int) -> VocabTest:
        """Die Vokabelliste als Prüfgrundlage für die Prüfung dieses Teils.

        Das ist die Naht zwischen den beiden ursprünglichen Anwendungen: Der
        Prüfungs-Checker vergleicht nicht mehr gegen ein separat gelesenes
        Word-Dokument, sondern gegen genau die Liste, die in derselben Datei
        steht. Ein Auseinanderdriften von Liste und Prüfung ist damit
        ausgeschlossen.
        """
        block = "test1" if teil == 1 else "test2"
        name = _TEIL[teil][1]
        return VocabTest(
            name=name,
            items=[
                VocabItem(
                    number=int(e.get("nr", i)),
                    german=e.get("deutsch", ""),
                    english=e.get("englisch", ""),
                    example=e.get("satz", ""),
                    test=name,
                )
                for i, e in enumerate(self.entries(block), 1)
                if e.get("englisch")
            ],
        )

    @property
    def all_vocab_tests(self) -> list[VocabTest]:
        return [self.vocab_test(1), self.vocab_test(2)]

    # ------------------------------------------------------------- Kennzahlen
    @property
    def ergaenzt(self) -> list[dict[str, Any]]:
        """Alle Wörter, die nicht aus der Wortliste des Lehrmittels stammen."""
        return [e for e in self.all_entries if e.get("herkunft") != "wortliste"]

    @property
    def ergaenzt_anteil(self) -> float:
        entries = self.all_entries
        return len(self.ergaenzt) / len(entries) if entries else 0.0

    @property
    def vollstaendig(self) -> bool:
        """Sind alle Wörter und alle Sätze eingetragen?"""
        if any(not e.get("englisch") or not e.get("deutsch") or not e.get("satz")
               for e in self.all_entries):
            return False
        return all(
            not re.search(r"TODO", exam.get("task2", {}).get("text", ""))
            for exam in self.exams.values()
        )

    def offen(self) -> list[str]:
        """Was noch fehlt - als Liste für den Chat."""
        out = []
        for block in ("test1", "test2"):
            for e in self.entries(block):
                where = f"{block}, Nr. {e.get('nr')}"
                if not e.get("englisch") or not e.get("deutsch"):
                    out.append(f"{where}: Wort fehlt ({e.get('hinweis', 'zu ergänzen')})")
                elif not e.get("satz"):
                    out.append(f"{where}: Beispielsatz für '{e['englisch']}' fehlt")
        for teil, exam in self.exams.items():
            text = exam.get("task2", {}).get("text", "")
            if not text or "TODO" in text:
                out.append(f"Prüfung Teil {teil}: Lückentext fehlt")
        return out


def pack_filename(unit: int, niveau: str | NiveauProfile) -> str:
    return f"unit_{unit:02d}_{profile(niveau).name}.json"
