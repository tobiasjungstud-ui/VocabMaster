"""Kuratierte Inhalte: von Hand geprüfte Wörter und Beispielsätze.

Dieser Weg ist für den Arbeitsablauf gedacht, bei dem die Inhalte im Chat
mit Claude entstehen und nicht von der Anwendung selbst erzeugt werden:

1. ``vocablistmaker wordlist.xlsx "Unit 7" --export-auswahl auswahl.json``
   erzeugt ein Gerüst mit der geprüften Wortauswahl und leeren Satzfeldern.
2. Die Sätze werden eingetragen (im Chat geschrieben und geprüft).
3. ``vocablistmaker --aus-datei auswahl.json -o Unit_7.docx`` baut die
   Word-Datei und lässt alle Qualitätsprüfungen darüber laufen.

Die Datei ist bewusst schlichtes JSON, damit sie sich auch von Hand
bearbeiten lässt.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import Settings
from .leveling import score_candidate
from .models import Candidate, QualityReport, Severity, TestItem, TestPair
from .sentences import find_form_in_sentence
from .validation import validate_all

SCHEMA_VERSION = 1


def _item_to_dict(item: TestItem) -> dict[str, Any]:
    return {
        "nr": item.number,
        "deutsch": item.german,
        "englisch": item.english,
        "satz": item.sentence,
        "form": item.sentence_form,
    }


def export_selection(pair: TestPair, path: str | Path, keep_sentences: bool = False) -> Path:
    """Schreibt die Wortauswahl als bearbeitbares Gerüst."""
    def block(items: list[TestItem]) -> list[dict[str, Any]]:
        rows = []
        for item in items:
            row = _item_to_dict(item)
            if not keep_sentences:
                row["satz"] = ""
                row["form"] = ""
            rows.append(row)
        return rows

    payload = {
        "schema": SCHEMA_VERSION,
        "unit": pair.unit,
        "unit_label": pair.unit_label,
        "hinweis": (
            "Feld 'satz' je Eintrag ausfüllen. 'form' ist die im Satz "
            "verwendete Wortform für die Fettschrift und darf leer bleiben - "
            "sie wird dann automatisch bestimmt."
        ),
        "test1": block(pair.test1),
        "test2": block(pair.test2),
    }
    target = Path(path)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _read_items(rows: list[dict[str, Any]], test_name: str) -> list[TestItem]:
    items: list[TestItem] = []
    for index, row in enumerate(rows, 1):
        english = str(row.get("englisch", "")).strip()
        german = str(row.get("deutsch", "")).strip()
        sentence = str(row.get("satz", "")).strip()
        if not english or not german:
            raise ValueError(
                f"{test_name}, Eintrag {index}: 'deutsch' und 'englisch' sind Pflichtfelder."
            )
        if not sentence:
            raise ValueError(
                f"{test_name}, Eintrag {index} ('{english}'): Es fehlt ein Beispielsatz. "
                "Kuratierte Listen werden nicht mit Mustersätzen aufgefüllt."
            )
        form = str(row.get("form", "")).strip()
        items.append(
            TestItem(
                number=int(row.get("nr", index)),
                german=german,
                english=english,
                sentence=sentence,
                sentence_form=find_form_in_sentence(sentence, english, form) or form or english,
            )
        )
    return items


def load_curated(path: str | Path, settings: Settings | None = None) -> TestPair:
    """Liest eine kuratierte Datei und prüft sie vollständig durch."""
    settings = settings or Settings()
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    test1 = _read_items(list(data.get("test1", [])), "Test 1")
    test2 = _read_items(list(data.get("test2", [])), "Test 2")

    # Nummerierung immer neu vergeben, damit sie lückenlos ist.
    for items in (test1, test2):
        for position, item in enumerate(items, 1):
            item.number = position

    pair = TestPair(
        unit=int(data.get("unit", 0)),
        unit_label=str(data.get("unit_label") or f"Unit {data.get('unit', '')}").strip(),
        test1=test1,
        test2=test2,
    )
    pair.report = review_curated(pair, settings)
    return pair


def _to_candidates(items: list[TestItem]) -> list[Candidate]:
    candidates = []
    for item in items:
        candidate = Candidate(english=item.english, german=item.german)
        score_candidate(candidate)
        candidate.sentence = item.sentence
        candidate.sentence_form = item.sentence_form
        candidates.append(candidate)
    return candidates


def review_curated(pair: TestPair, settings: Settings | None = None) -> QualityReport:
    """Lässt alle Prüfungen über eine kuratierte Liste laufen.

    Damit durchlaufen von Hand geschriebene Inhalte dieselbe Kontrolle wie
    automatisch erzeugte: Doppelungen, Niveau, Balance, Beispielsätze - und
    zusätzlich die Seitenprüfung.
    """
    settings = settings or Settings()
    report = validate_all(
        _to_candidates(pair.test1), _to_candidates(pair.test2), len(pair.test1) or 30
    )
    report.stats["quelle"] = "kuratiert"

    from .docx_writer import check_page_fit

    for name, items in (("Test 1", pair.test1), ("Test 2", pair.test2)):
        fit = check_page_fit(items, settings)
        key = "seitenfuellung_test1" if name == "Test 1" else "seitenfuellung_test2"
        report.stats[key] = round(fit.usage, 3)
        if not fit.fits:
            longest = max(items, key=lambda i: len(i.sentence))
            report.add(
                "seitenueberlauf",
                Severity.ERROR,
                f"{name} passt nicht auf eine A4-Seite ({fit.usage:.0%} Füllung). "
                f"Längster Satz: '{longest.sentence}' ({len(longest.sentence)} Zeichen).",
                stage="layout",
            )
        elif fit.usage > 0.97:
            report.add(
                "seite_knapp",
                Severity.WARNING,
                f"{name} füllt die Seite zu {fit.usage:.0%} - wenig Reserve.",
                stage="layout",
            )
    return report
