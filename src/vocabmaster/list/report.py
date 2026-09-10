"""Aufbereitung des Qualitätsberichts für Anzeige und Export."""

from __future__ import annotations

import json
from datetime import datetime

from .models import Severity, TestPair

_LABEL = {
    Severity.ERROR: "Fehler",
    Severity.WARNING: "Hinweis",
    Severity.INFO: "Notiz",
}


def to_markdown(pair: TestPair) -> str:
    """Menschenlesbarer Bericht - eignet sich zum Ausdrucken oder Ablegen."""
    report = pair.report
    lines = [
        f"# Qualitätsbericht - {pair.unit_label or f'Unit {pair.unit}'}",
        "",
        f"Erstellt am {datetime.now():%d.%m.%Y %H:%M}",
        "",
        "## Überblick",
        "",
        f"- Einträge Test 1: **{len(pair.test1)}**",
        f"- Einträge Test 2: **{len(pair.test2)}**",
        f"- Fehler: **{len(report.errors)}**",
        f"- Hinweise: **{len(report.warnings)}**",
        f"- Prüfrunden: **{report.rounds}**",
    ]

    stats = report.stats
    if stats:
        lines += ["", "## Kennzahlen", ""]
        pretty = {
            "unit": "Unit",
            "eintraege_in_unit": "Vokabeln in der Unit",
            "geeignet_nach_pruefung": "nach Prüfung geeignet",
            "aussortiert": "aussortiert",
            "schwierigkeit_test1": "mittlere Schwierigkeit Test 1",
            "schwierigkeit_test2": "mittlere Schwierigkeit Test 2",
            "schwierigkeit_differenz": "Differenz der Schwierigkeit",
            "lernwert_test1": "mittlerer Lernwert Test 1",
            "lernwert_test2": "mittlerer Lernwert Test 2",
            "sprachmodell": "Sprachmodell",
            "modellaufrufe": "Modellaufrufe",
            "gesamturteil": "Gesamturteil",
            "unterrichtsreif": "ohne Nacharbeit einsetzbar",
        }
        for key, label in pretty.items():
            if key in stats:
                lines.append(f"- {label}: {stats[key]}")
        for key in ("wortarten_test1", "wortarten_test2"):
            if key in stats:
                mix = ", ".join(f"{k} {v}" for k, v in stats[key].items() if v)
                lines.append(f"- Wortarten {key[-5:].replace('test', 'Test ')}: {mix}")

    for severity in (Severity.ERROR, Severity.WARNING, Severity.INFO):
        issues = [i for i in report.issues if i.severity is severity]
        if not issues:
            continue
        lines += ["", f"## {_LABEL[severity]} ({len(issues)})", ""]
        for issue in issues:
            words = f" — {', '.join(issue.words[:8])}" if issue.words else ""
            if len(issue.words) > 8:
                words += f" … (+{len(issue.words) - 8})"
            lines.append(f"- **{issue.code}**: {issue.message}{words}")

    if not report.issues:
        lines += ["", "Keine Beanstandungen."]
    return "\n".join(lines) + "\n"


def to_json(pair: TestPair) -> str:
    """Maschinenlesbare Fassung - nützlich für Protokolle und Tests."""
    payload = {
        "unit": pair.unit,
        "unit_label": pair.unit_label,
        "erstellt": datetime.now().isoformat(timespec="seconds"),
        "statistik": pair.report.stats,
        "runden": pair.report.rounds,
        "befunde": [
            {
                "code": i.code,
                "schwere": i.severity.value,
                "meldung": i.message,
                "woerter": i.words,
                "stufe": i.stage,
            }
            for i in pair.report.issues
        ],
        "test1": [
            {"nr": i.number, "deutsch": i.german, "englisch": i.english, "satz": i.sentence}
            for i in pair.test1
        ],
        "test2": [
            {"nr": i.number, "deutsch": i.german, "englisch": i.english, "satz": i.sentence}
            for i in pair.test2
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def summary_line(pair: TestPair) -> str:
    report = pair.report
    if report.errors:
        return (
            f"{len(report.errors)} Fehler und {len(report.warnings)} Hinweise - "
            "bitte den Bericht ansehen."
        )
    if report.warnings:
        return f"Keine Fehler, {len(report.warnings)} Hinweise."
    return "Keine Beanstandungen - die Listen sind einsatzbereit."
