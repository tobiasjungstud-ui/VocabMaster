"""Das Unit-Paket: eine Datei je Unit, von der Auswahl bis zum Druck.

Ein Paket hält alles zusammen, was für **eine** Unit gebraucht wird:

* die 60 Wörter der Vokabelliste (Test 1 und Test 2) mit ihren
  Beispielsätzen - für beide Gruppen dieselben,
* vier Prüfungen: Teil I und Teil II, jeweils für Niveau A und Niveau B.

Eine Datei je Unit ist Absicht: Wer nur die Prüfung für Niveau B neu bauen
lässt, ändert an der Vokabelliste nichts - gebaut wird nur, was verlangt ist.

Ablauf:

1. ``vocabmaster gerüst 3`` schreibt ``kuratiert/unit_03.json`` mit der
   geprüften Wortauswahl und leeren Feldern für die Sätze.
2. Die Felder ``satz`` und die vier Lückentexte werden **im Chat**
   geschrieben - vom Sprachmodell selbst, ohne Musterbausteine.
3. ``vocabmaster bauen kuratiert/unit_03.json`` prüft alles und schreibt die
   Word-Dateien.

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
from .exam.select import _clashes as _exam_clashes
from .exam.vocab import VocabItem, VocabTest, guess_pos
from .niveau import NIVEAUS, PROFILES, NiveauProfile, profile
from .pool import UnitPlan, plan_unit

SCHEMA_VERSION = 2

ANLEITUNG = [
    "Feld 'satz' je Eintrag ausfüllen: ein natürlicher, idiomatischer",
    "Beispielsatz, der das Zielwort erschliessbar macht, ohne die deutsche",
    "Lösung zu verraten. Keine Definitionen ('A villain is a bad person').",
    "Die Liste lernen beide Gruppen, deshalb höchstens 13 Wörter je Satz.",
    "Feld 'form' ist die im Satz verwendete Wortform für die Fettschrift und",
    "darf leer bleiben - sie wird dann selbst bestimmt.",
    "Einträge mit 'herkunft': 'ergänzt' stehen nicht in der Wortliste des",
    "Lehrmittels und müssen thematisch zur Unit passen; ihr Anteil ist auf",
    "40 Prozent begrenzt und wird im Prüfbericht ausgewiesen.",
    "In jeder der vier Prüfungen 'task2.text' schreiben: {1} bis {4}",
    "markieren die Lücken, die Reihenfolge in 'gaps' ist die im Text.",
]

TEIL_NAMEN = {1: ("Part I", "Test 1"), 2: ("Part II", "Test 2")}


# ---------------------------------------------------------------------------
# Gerüst
# ---------------------------------------------------------------------------
def _list_entry(number: int, english: str, german: str, herkunft: str,
                abschnitt: str = "", wortart: str = "") -> dict[str, Any]:
    return {
        "nr": number,
        "deutsch": german,
        "englisch": english,
        "satz": "",
        "form": "",
        "wortart": wortart,
        "herkunft": herkunft,
        "abschnitt": abschnitt,
    }


def wortart_von(entry: dict[str, Any]) -> str:
    """Die Wortart eines Listeneintrags.

    Vorrang hat die Angabe der Wortliste des Lehrmittels - sie steht dort in
    einer eigenen Spalte und ist verlässlicher als jede Ableitung aus dem
    deutschen Stichwort. Ohne Angabe (bei ergänzten Wörtern) wird sie aus dem
    Deutschen geraten; das trifft bei "inzwischen" oder "hölzern" daneben.
    """
    return entry.get("wortart") or guess_pos(entry.get("deutsch", ""))


def _placeholder(number: int) -> dict[str, Any]:
    entry = _list_entry(number, "", "", "ergänzt")
    entry["hinweis"] = (
        "Zu ergänzen: ein thematisch passendes, im Englischen gebräuchliches "
        "Wort, das noch nicht in dieser Liste steht."
    )
    return entry


def _as_vocab_item(entry: dict[str, Any]) -> VocabItem:
    return VocabItem(
        number=int(entry.get("nr", 0)),
        german=entry.get("deutsch", ""),
        english=entry.get("englisch", ""),
        example=entry.get("satz", ""),
    )


#: Ab dieser Ähnlichkeit zum deutschen Stichwort schreibt man das englische
#: Wort einfach ab - geprüft wird damit nichts, auf keinem Niveau.
ABSCHREIBBAR = 0.80


def _bewertung(entry: dict[str, Any]):
    return score_item(
        {"english": entry.get("englisch", ""), "german": entry.get("deutsch", ""),
         "pos": wortart_von(entry)}
    )


def _schwierigkeit(entry: dict[str, Any]) -> float:
    return _bewertung(entry).score


def _abschreibbar(entry: dict[str, Any]) -> bool:
    return _bewertung(entry).similarity >= ABSCHREIBBAR


def waehle_pruefungswoerter(
    entries: list[dict[str, Any]],
    prof: NiveauProfile,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Welche Wörter eines Tests dieses Niveau prüft.

    Die 30 Wörter des Tests werden nach Schwierigkeit sortiert. Niveau A
    prüft von oben - die zwölf schwersten -, Niveau B von unten - die zwölf
    zugänglichsten. Beide schöpfen aus derselben Liste; dass sich die beiden
    Auswahlen dabei berühren, ist erlaubt und bei 30 Wörtern selten.

    Übersprungen wird, was der Checker anschliessend beanstanden würde: zwei
    Wörter einer Wortfamilie, Beinah-Synonyme, bekannte Verwechslungspaare.
    """
    settings = settings or Settings()
    take = settings.exam_words
    brauchbar = [e for e in entries if e.get("englisch") and e.get("deutsch")]
    # "Anekdote" -> "anecdote" schreibt man ab; das prüft nichts. Solche
    # Wörter bleiben in der Liste (gelernt werden sie trotzdem), rutschen in
    # der Prüfung aber ans Ende - auch für Niveau B. In einer Unit wie
    # "Wissenschaft", die zu einem grossen Teil aus Internationalismen
    # besteht, kommen sie dennoch dran; der Checker meldet das dann.
    reihenfolge = sorted(
        brauchbar,
        key=lambda e: (
            _abschreibbar(e),
            -_schwierigkeit(e) if prof.zuerst else _schwierigkeit(e),
        ),
    )

    # Zwei Obergrenzen, die der Checker anschliessend ohnehin einfordert:
    # zu viele Mehrwortausdrücke kosten in der Prüfung nur Schreibzeit, und
    # zwölf Nomen hintereinander prüfen immer dieselbe Struktur.
    max_mehrwort = prof.selection_targets["max_multiword_items"]
    max_anteil = prof.selection_targets["max_share_one_word_class"]
    grenze_wortart = int(take * max_anteil)

    def passt(entry: dict[str, Any], gewaehlt: list[dict[str, Any]]) -> bool:
        if _exam_clashes(_as_vocab_item(entry),
                         [_as_vocab_item(c) for c in gewaehlt]):
            return False
        if len(entry["englisch"].split()) > 1:
            mehrwort = sum(1 for c in gewaehlt if len(c["englisch"].split()) > 1)
            if mehrwort >= max_mehrwort:
                return False
        pos = wortart_von(entry)
        if sum(1 for c in gewaehlt if wortart_von(c) == pos) >= grenze_wortart:
            return False
        return True

    gewaehlt: list[dict[str, Any]] = []
    for entry in reihenfolge:
        if len(gewaehlt) >= take:
            break
        if passt(entry, gewaehlt):
            gewaehlt.append(entry)
    if len(gewaehlt) < take:  # notfalls auffüllen, der Checker meldet es dann
        gewaehlt += [e for e in reihenfolge if e not in gewaehlt][
            : take - len(gewaehlt)
        ]
    return gewaehlt


def _exam_scaffold(
    entries: list[dict[str, Any]],
    unit_label: str,
    teil: int,
    prof: NiveauProfile,
    settings: Settings,
    seed: int,
) -> dict[str, Any]:
    part_label, source = TEIL_NAMEN[teil]
    chosen = waehle_pruefungswoerter(entries, prof, settings)
    by_score = sorted(chosen, key=lambda e: -_schwierigkeit(e))

    # Für die Wortbank taugt kein Stichwort mit Komma: Die Bank wird als eine
    # Zeile gedruckt, ein Komma im Stichwort macht daraus zwei Wörter - vier
    # Lücken, aber fünf Wörter zur Auswahl.
    bankfaehig = [e for e in by_score if "," not in e.get("deutsch", "")]

    # Je Lücke eine andere Wortart, damit sich zwei Lücken nicht schon von der
    # Grammatik her vertauschen lassen. Adverbien zählen als eigene Wortart.
    gaps: list[dict[str, Any]] = []
    for pos in ("verb", "noun", "adj", "adv"):
        for entry in bankfaehig:
            if len(gaps) >= settings.exam_gaps:
                break
            if wortart_von(entry) == pos and entry not in gaps:
                gaps.append(entry)
                break
    for entry in bankfaehig:
        if len(gaps) >= settings.exam_gaps:
            break
        if entry not in gaps:
            gaps.append(entry)

    translation = [e for e in chosen if e not in gaps]
    rng = random.Random(seed + teil + (0 if prof.name == "A" else 97))
    reihenfolge = [g["deutsch"] for g in gaps]
    bank = list(reihenfolge)
    # Weder die Lückenreihenfolge noch ihre Umkehrung: beides liesse die
    # Aufgabe lösen, ohne den Text zu lesen.
    for _ in range(50):
        if bank != reihenfolge and bank != list(reversed(reihenfolge)):
            break
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
                 "pos": wortart_von(e)}
                for e in translation
            ],
        },
        "task2": {
            "instruction": f"2)  Fill in the gaps using the vocabulary from {sentence_unit}. ",
            "word_bank_label": "Words:",
            "word_bank": bank,
            "gaps": [
                {"german": g["deutsch"], "english": g["englisch"],
                 "answer": g["englisch"], "pos": wortart_von(g)}
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
    settings: Settings | None = None,
    plan: UnitPlan | None = None,
) -> dict[str, Any]:
    """Das leere Paket einer Unit: eine Liste, vier Prüfungen."""
    settings = settings or Settings()
    plan = plan or plan_unit(db, unit, settings)
    theme = db.theme(unit)

    zusatz = {w.lower() for w, _ in plan.report.aus_zusatzteilen}
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
                    "zusatzteil" if c.headword.lower() in zusatz
                    else ("wortliste" if source else "ergänzt"),
                    f"{source.section}, S. {source.page}" if source and source.page
                    else (source.section if source else ""),
                    source.pos if source else "",
                )
            )
        blocks[name] = rows

    # Fehlbestand gleichmässig auf beide Tests verteilen, damit die Lücke
    # nicht ganz am Ende von Test 2 klebt.
    for _ in range(settings.target_total - len(plan.all_words)):
        target = "test1" if len(blocks["test1"]) <= len(blocks["test2"]) else "test2"
        blocks[target].append(_placeholder(len(blocks[target]) + 1))
    for rows in blocks.values():
        for number, row in enumerate(rows, 1):
            row["nr"] = number

    unit_label = db.unit_label(unit)
    pruefungen = {
        f"teil{teil}": {
            name: _exam_scaffold(
                blocks[f"test{teil}"], unit_label, teil, PROFILES[name],
                settings, settings.seed,
            )
            for name in NIVEAUS
        }
        for teil in (1, 2)
    }

    return {
        "schema": SCHEMA_VERSION,
        "unit": unit,
        "unit_label": unit_label,
        "titel": theme.get("titel", unit_label),
        "thema": theme.get("thema", ""),
        "leitwoerter": theme.get("leitwoerter", []),
        "quelle": dict(db.quelle),
        "erzeugt": date.today().isoformat(),
        "fehlbestand": plan.report.fehlend,
        "herkunft_uebersicht": {
            "hauptteil": plan.report.aus_hauptteil,
            "zusatzteile": [
                {"englisch": w, "bereich": b} for w, b in plan.report.aus_zusatzteilen
            ],
            "zu_ergaenzen": plan.report.fehlend,
            "ausnahme": plan.report.ausnahme,
        },
        "anleitung": ANLEITUNG,
        "liste": blocks,
        "pruefungen": pruefungen,
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
        if int(data.get("schema", 0)) < SCHEMA_VERSION:
            raise ValueError(
                f"{target.name} stammt aus einer älteren Fassung "
                f"(Schema {data.get('schema')}, erwartet {SCHEMA_VERSION}). "
                "Damals gab es zwei Wortlisten je Unit; heute ist es eine. "
                "Bitte das Gerüst neu erzeugen: vocabmaster gerüst "
                f"{data.get('unit', '<n>')}"
            )
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

    @property
    def akzeptierte_warnungen(self) -> list[dict[str, Any]]:
        """Warnungen, die bewusst stehen bleiben - mit Begründung.

        Manche Warnungen beschreiben keine Nachlässigkeit, sondern eine
        Eigenschaft der Unit: In einer Wissenschafts-Unit besteht die
        zugängliche Worthälfte nun einmal überwiegend aus Internationalismen.
        Solche Fälle werden hier benannt, statt die Schwelle stillschweigend
        zu senken. Der Prüfbericht zeigt sie weiterhin an.
        """
        return list(self.data.get("akzeptierte_warnungen", []))

    def ist_akzeptiert(self, befund_text: str) -> str:
        """Die Begründung, falls diese Warnung bewusst hingenommen wird."""
        for eintrag in self.akzeptierte_warnungen:
            if str(eintrag.get("enthaelt", "")) in befund_text:
                return str(eintrag.get("grund", ""))
        return ""

    def wortart(self, english: str) -> str:
        """Die Wortart eines Wortes, wie sie in der Liste dieses Pakets steht."""
        needle = str(english).strip().lower()
        for entry in self.all_entries:
            if entry.get("englisch", "").strip().lower() == needle:
                return wortart_von(entry)
        return ""

    # ------------------------------------------------------------- Prüfungen
    def exam(self, teil: int, niveau: str | NiveauProfile) -> dict[str, Any]:
        prof = profile(niveau)
        return dict(self.data.get("pruefungen", {}).get(f"teil{teil}", {})
                    .get(prof.name, {}))

    @property
    def exams(self) -> dict[tuple[int, str], dict[str, Any]]:
        """Alle vier Prüfungen, angesprochen über ``(teil, niveau)``."""
        out = {}
        for teil in (1, 2):
            for name in NIVEAUS:
                spec = self.exam(teil, name)
                if spec:
                    out[(teil, name)] = spec
        return out

    def vocab_test(self, teil: int) -> VocabTest:
        """Die Vokabelliste als Prüfgrundlage für die Prüfungen dieses Teils.

        Das ist die Naht zwischen den beiden ursprünglichen Anwendungen: Der
        Prüfungs-Checker vergleicht nicht mehr gegen ein separat gelesenes
        Word-Dokument, sondern gegen genau die Liste, die in derselben Datei
        steht. Ein Auseinanderdriften von Liste und Prüfung ist damit
        ausgeschlossen.
        """
        block = "test1" if teil == 1 else "test2"
        name = TEIL_NAMEN[teil][1]
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
        """Wörter, die nicht aus der Wortliste des Lehrmittels stammen."""
        return [e for e in self.all_entries if e.get("herkunft") == "ergänzt"]

    @property
    def aus_zusatzteilen(self) -> list[dict[str, Any]]:
        """Wörter aus Culture, Project oder Curriculum extra derselben Unit."""
        return [e for e in self.all_entries if e.get("herkunft") == "zusatzteil"]

    @property
    def ergaenzt_anteil(self) -> float:
        entries = self.all_entries
        return len(self.ergaenzt) / len(entries) if entries else 0.0

    @property
    def vollstaendig(self) -> bool:
        """Sind alle Wörter, alle Sätze und alle vier Lückentexte da?"""
        if any(not e.get("englisch") or not e.get("deutsch") or not e.get("satz")
               for e in self.all_entries):
            return False
        return all(
            not re.search(r"TODO", spec.get("task2", {}).get("text", ""))
            for spec in self.exams.values()
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
        for (teil, name), spec in sorted(self.exams.items()):
            text = spec.get("task2", {}).get("text", "")
            if not text or "TODO" in text:
                out.append(f"Prüfung Teil {teil}, Niveau {name}: Lückentext fehlt")
        return out


def pack_filename(unit: int) -> str:
    return f"unit_{unit:02d}.json"


def ausgleichen(pack: Pack, settings: Settings | None = None) -> Pack:
    """Verteilt die 60 Wörter neu auf Test 1 und Test 2.

    Nötig, sobald im Chat Wörter ergänzt wurden: Das Gerüst konnte sie beim
    Aufteilen noch nicht kennen und hat die offenen Plätze nur hinten
    angehängt. Danach sind die beiden Tests unterschiedlich schwer und die
    Wortarten ungleich verteilt.

    Sätze, Herkunft und Wortart bleiben an ihrem Eintrag; neu ist nur, in
    welchem Test er steht. Die vier Prüfungen werden anschliessend neu
    aufgesetzt - sie schöpfen ja aus genau diesen Tests. Bereits
    geschriebene Lückentexte bleiben erhalten, soweit ihre Wörter im selben
    Teil bleiben; sonst meldet der Selbstcheck es.
    """
    from .list.leveling import score_candidate
    from .list.models import Candidate
    from .list.selection import split_balanced
    from .niveau import LIST_BOUNDS

    settings = settings or Settings()
    eintraege = [e for e in pack.all_entries if e.get("englisch")]
    if len(eintraege) != settings.target_total:
        raise ValueError(
            f"Zum Ausgleichen werden {settings.target_total} vollständige "
            f"Einträge gebraucht, vorhanden sind {len(eintraege)}."
        )

    nach_wort: dict[str, dict[str, Any]] = {}
    kandidaten: list[Candidate] = []
    for eintrag in eintraege:
        c = Candidate(
            english=eintrag["englisch"],
            german=eintrag.get("deutsch", ""),
            section=eintrag.get("abschnitt", ""),
        )
        score_candidate(c, None, LIST_BOUNDS)
        kandidaten.append(c)
        nach_wort[c.headword.lower()] = eintrag

    a, b = split_balanced(kandidaten, settings.words_per_test, settings.seed)
    for name, haelfte in (("test1", a), ("test2", b)):
        rows = []
        for nummer, c in enumerate(haelfte, 1):
            eintrag = dict(nach_wort[c.headword.lower()])
            eintrag["nr"] = nummer
            rows.append(eintrag)
        pack.data["liste"][name] = rows

    unit_label = pack.unit_label
    alte_texte = {
        (teil, niveau): spec.get("task2", {}).get("text", "")
        for (teil, niveau), spec in pack.exams.items()
    }
    pack.data["pruefungen"] = {
        f"teil{teil}": {
            niveau: _exam_scaffold(
                pack.entries(f"test{teil}"), unit_label, teil,
                PROFILES[niveau], settings, settings.seed,
            )
            for niveau in NIVEAUS
        }
        for teil in (1, 2)
    }
    for (teil, niveau), text in alte_texte.items():
        if text and "TODO" not in text:
            pack.data["pruefungen"][f"teil{teil}"][niveau]["task2"]["text"] = text
    return pack
