"""Mehrstufige Qualitätskontrolle vor der Ausgabe.

Die Prüfungen laufen in Stufen und wiederholen sich nach jeder Reparatur:

1. **Struktur** - je 30 Einträge, keine leeren Felder, fortlaufende Nummern
2. **Überschneidung** - kein Wort doppelt, keine Wortfamilien, keine Synonyme
3. **Niveau** - nichts deutlich unter B1 oder unnötig exotisch
4. **Balance** - vergleichbare Schwierigkeit und Wortartenmischung
5. **Beispielsätze** - Zielwort enthalten, korrekt, verrät die Lösung nicht
"""

from __future__ import annotations

from collections import Counter

from .dedup import find_cross_overlaps, find_internal_overlaps
from .leveling import DEFAULT_BOUNDS, Bounds
from .models import POS, Candidate, QualityReport, Severity
from .normalize import normalize_key
from .selection import balance_summary
from .sentences import check_sentence

# Ab dieser Differenz im mittleren Schwierigkeitsgrad gelten die Tests
# als unterschiedlich schwer.
DIFFICULTY_TOLERANCE = 0.055
DIFFICULTY_TOLERANCE_HARD = 0.10


def validate_structure(
    test1: list[Candidate], test2: list[Candidate], expected: int, report: QualityReport
) -> None:
    for name, items in (("Test 1", test1), ("Test 2", test2)):
        if len(items) != expected:
            report.add(
                "falsche_anzahl",
                Severity.ERROR,
                f"{name} enthält {len(items)} statt {expected} Einträge.",
                stage="struktur",
            )
        for c in items:
            if not (c.headword or c.english).strip():
                report.add("leeres_wort", Severity.ERROR, f"{name}: Eintrag ohne englisches Wort.", stage="struktur")
            if not c.german.strip():
                report.add(
                    "leere_uebersetzung",
                    Severity.ERROR,
                    f"{name}: '{c.headword}' hat keine deutsche Übersetzung.",
                    words=[c.headword],
                    stage="struktur",
                )


def validate_overlaps(
    test1: list[Candidate], test2: list[Candidate], report: QualityReport
) -> None:
    for a, b, why in find_cross_overlaps(test1, test2):
        report.add(
            "ueberschneidung",
            Severity.ERROR,
            f"'{a.headword}' (Test 1) und '{b.headword}' (Test 2) überschneiden sich: {why}.",
            words=[a.headword, b.headword],
            stage="ueberschneidung",
        )
    for name, items in (("Test 1", test1), ("Test 2", test2)):
        for a, b, why in find_internal_overlaps(items):
            report.add(
                "doppelung",
                Severity.ERROR,
                f"{name}: '{a.headword}' und '{b.headword}' prüfen dasselbe ({why}).",
                words=[a.headword, b.headword],
                stage="ueberschneidung",
            )

    seen: dict[str, str] = {}
    for _name, items in (("Test 1", test1), ("Test 2", test2)):
        for c in items:
            key = normalize_key(c.german)
            if key and key in seen:
                report.add(
                    "gleiche_uebersetzung",
                    Severity.WARNING,
                    f"'{c.headword}' hat dieselbe deutsche Übersetzung wie '{seen[key]}'.",
                    words=[c.headword, seen[key]],
                    stage="ueberschneidung",
                )
            elif key:
                seen[key] = c.headword


def validate_level(
    items: list[Candidate], report: QualityReport, bounds: Bounds | None = None
) -> None:
    """Niveau der Wörter prüfen.

    ``bounds`` ist das Häufigkeitsfenster des Niveaus. Ohne Angabe gilt das
    Band für Niveau A - sonst würde jedes Wort der Niveau-B-Liste als
    "zu einfach" gemeldet, obwohl es genau dort hingehört.
    """
    bounds = bounds or DEFAULT_BOUNDS
    for c in items:
        if "aufgefuellt" in c.flags:
            report.add(
                "nachgerueckt",
                Severity.WARNING,
                f"'{c.headword}' musste nachrücken, weil die Unit zu wenig "
                f"geeignetes Material bietet ({'; '.join(c.notes) or 'kein Grund vermerkt'}).",
                words=[c.headword],
                stage="niveau",
            )
            continue
        if c.zipf >= bounds.too_easy:
            report.add(
                "zu_einfach",
                Severity.WARNING,
                f"'{c.headword}' dürfte für {bounds.label} zu einfach sein "
                f"(Zipf {c.zipf:.2f}).",
                words=[c.headword],
                stage="niveau",
            )
        if c.zipf < bounds.too_rare:
            report.add(
                "zu_selten",
                Severity.WARNING,
                f"'{c.headword}' ist für {bounds.label} zu selten "
                f"(Zipf {c.zipf:.2f}).",
                words=[c.headword],
                stage="niveau",
            )


def validate_balance(
    test1: list[Candidate], test2: list[Candidate], report: QualityReport
) -> dict:
    summary = balance_summary(test1, test2)
    diff = summary["schwierigkeit_differenz"]
    if diff > DIFFICULTY_TOLERANCE_HARD:
        report.add(
            "unausgewogen",
            Severity.ERROR,
            f"Die Tests sind unterschiedlich schwer (Differenz {diff:.3f}). "
            "Ein Test enthält deutlich mehr schwierige Wörter als der andere.",
            stage="balance",
        )
    elif diff > DIFFICULTY_TOLERANCE:
        report.add(
            "leicht_unausgewogen",
            Severity.WARNING,
            f"Kleiner Schwierigkeitsunterschied zwischen den Tests ({diff:.3f}).",
            stage="balance",
        )

    for pos in POS:
        c1 = sum(1 for c in test1 if c.pos is pos)
        c2 = sum(1 for c in test2 if c.pos is pos)
        if abs(c1 - c2) > max(3, round(0.25 * max(c1, c2))):
            report.add(
                "wortarten_ungleich",
                Severity.WARNING,
                f"Wortart '{pos.value}' ist ungleich verteilt ({c1} zu {c2}).",
                stage="balance",
            )

    for name, items in (("Test 1", test1), ("Test 2", test2)):
        counts = Counter(c.pos for c in items)
        dominant, n = counts.most_common(1)[0]
        if len(items) and n / len(items) > 0.8:
            report.add(
                "einseitige_wortarten",
                Severity.WARNING,
                f"{name} besteht zu {n / len(items):.0%} aus '{dominant.value}'. "
                "Das Ausgangsmaterial gibt keine bessere Mischung her.",
                stage="balance",
            )
    return summary


def validate_sentences(items: list[Candidate], report: QualityReport, test_name: str) -> None:
    for c in items:
        for issue in check_sentence(c):
            severity = (
                Severity.ERROR
                if issue.code in {"satz_fehlt", "zielwort_fehlt", "loesung_verraten", "deutsch_im_satz"}
                else Severity.WARNING
            )
            report.add(
                issue.code,
                severity,
                f"{test_name}, '{c.headword}': {issue.message}",
                words=[c.headword],
                stage="saetze",
            )


def validate_all(
    test1: list[Candidate],
    test2: list[Candidate],
    expected: int,
    report: QualityReport | None = None,
    bounds: Bounds | None = None,
) -> QualityReport:
    """Führt alle regelbasierten Prüfungen aus."""
    report = report or QualityReport()
    validate_structure(test1, test2, expected, report)
    validate_overlaps(test1, test2, report)
    validate_level(test1 + test2, report, bounds)
    summary = validate_balance(test1, test2, report)
    validate_sentences(test1, report, "Test 1")
    validate_sentences(test2, report, "Test 2")
    report.stats.update(summary)
    report.stats["anzahl_test1"] = len(test1)
    report.stats["anzahl_test2"] = len(test2)
    report.stats["fehler"] = len(report.errors)
    report.stats["warnungen"] = len(report.warnings)
    return report


def problem_words(report: QualityReport, codes: set[str] | None = None) -> set[str]:
    """Alle Wörter, zu denen es Befunde gibt - Grundlage für die Reparatur."""
    codes = codes or {
        "satz_fehlt", "zielwort_fehlt", "loesung_verraten", "deutsch_im_satz",
        "satz_zu_kurz", "satz_zu_lang", "satz_ohne_punkt", "satz_klein",
        "satz_formatierung",
    }
    words: set[str] = set()
    for issue in report.issues:
        if issue.code in codes:
            words.update(issue.words)
    return words
