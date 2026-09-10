"""Herkunftsnachweis: Was kam aus der Excel-Datei, was nicht?

Beantwortet für eine fertige Liste drei Fragen, die vor dem Einsatz im
Unterricht zählen:

* Welche Wörter der Unit wurden **weggelassen** - und warum?
* Welche Wörter stehen in der Liste, aber **nicht in der Excel-Datei**?
  Das sind Ergänzungen, die jemand (oder etwas) hinzugedichtet hat und die
  deshalb besonders kritisch zu lesen sind.
* Bei welchen Einträgen wurde die **deutsche Übersetzung geändert**?
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .excel_reader import Workbook, is_core_section, strip_page_reference
from .leveling import LevelContext, is_usable, score_candidate
from .models import Candidate, TestPair
from .normalize import headword, normalize_key

#: Lesbare Begründungen für die internen Merkmale.
REASONS = {
    "grundwortschatz": "gehört zum A1/A2-Grundwortschatz",
    "zu_einfach": "zu einfach für B1.2-B2.1",
    "zu_selten": "im Englischen kaum gebräuchlich",
    "kognat": "fast identisch mit dem deutschen Wort",
    "frueher_gelernt": "kam schon in einer früheren Unit vor",
    "eigenname": "wirkt wie ein Eigenname",
    "unbrauchbar": "kein verwertbares Stichwort",
    "modell_abgelehnt": "inhaltlich abgelehnt",
}


@dataclass
class Provenance:
    """Ergebnis des Abgleichs zwischen Excel-Datei und fertiger Liste."""

    unit_label: str = ""
    pool_size: int = 0
    used: list[str] = field(default_factory=list)
    sections: dict[str, list[str]] = field(default_factory=dict)
    invented: list[tuple[str, str]] = field(default_factory=list)
    invented_share: float = 0.0
    readmitted: list[tuple[str, str]] = field(default_factory=list)
    gloss_changed: list[tuple[str, str, str]] = field(default_factory=list)
    left_out: dict[str, list[str]] = field(default_factory=dict)

    @property
    def left_out_count(self) -> int:
        return sum(len(v) for v in self.left_out.values())

    def to_markdown(self) -> str:
        lines = [f"## Herkunft der Wörter - {self.unit_label}", ""]
        lines.append(
            f"Die Unit enthält **{self.pool_size}** Vokabeln. Verwendet wurden "
            f"**{len(self.used)}**, weggelassen **{self.left_out_count}**."
        )
        lines.append("")

        if self.sections:
            lines += ["### Aus welchen Abschnitten die Wörter stammen", ""]
            for section, words in sorted(
                self.sections.items(), key=lambda kv: (-len(kv[1]), kv[0])
            ):
                lines.append(f"- **{section}** ({len(words)}): {', '.join(words)}")
            lines.append("")

        if self.invented:
            share = f"{self.invented_share:.0%}"
            lines += [
                f"### Selbst ergänzt, nicht aus der Excel-Datei ({len(self.invented)} von "
                f"{len(self.used)} = {share})",
                "",
                "| Englisch | Deutsch |",
                "|---|---|",
            ]
            for english, german in self.invented:
                lines.append(f"| {english} | {german} |")
        else:
            lines += [
                "### Nicht aus der Excel-Datei (eigene Ergänzungen)",
                "",
                "Keine. Jedes Wort der Liste steht so in der Excel-Datei.",
            ]
        lines.append("")

        if self.readmitted:
            lines += [
                "### Bewusst behalten, obwohl die Prüfung sie aussortiert hätte",
                "",
            ]
            for english, reason in self.readmitted:
                lines.append(f"- **{english}** — {reason}")
            lines.append("")

        if self.gloss_changed:
            lines += ["### Geänderte deutsche Übersetzung", ""]
            for english, before, after in self.gloss_changed:
                lines.append(f"- **{english}**: „{before}“ → „{after}“")
            lines.append("")

        lines += ["### Weggelassen", ""]
        for reason, words in sorted(self.left_out.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"**{reason}** ({len(words)}): {', '.join(sorted(words))}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def _reason_for(candidate: Candidate) -> str:
    for flag in (
        "grundwortschatz", "unbrauchbar", "eigenname", "zu_selten",
        "kognat", "frueher_gelernt", "zu_einfach", "modell_abgelehnt",
    ):
        if flag in candidate.flags:
            return REASONS[flag]
    return "nicht ausgewählt (Platz für höherwertige Wörter)"


def analyse(
    pair: TestPair, workbook: Workbook, unit: int, core_only: bool = False
) -> Provenance:
    """Gleicht eine fertige Liste gegen das Vokabular der Unit ab.

    ``core_only`` vergleicht nur gegen den Hauptteil ``Unit N``. Wurde die
    Liste so erstellt, ist das der richtige Massstab: Ein Wort aus
    ``Culture N`` wäre dann ebenfalls eine Ergänzung von aussen.
    """
    pool = workbook.unit_entries(unit)
    if core_only:
        pool = [e for e in pool if is_core_section(e.section, unit)]
    context = LevelContext.from_entries(workbook.entries_before(unit))

    scored: dict[str, Candidate] = {}
    original_gloss: dict[str, str] = {}
    section_of: dict[str, str] = {}
    for entry in pool:
        candidate = score_candidate(
            Candidate(
                english=entry.english, german=entry.german, section=entry.section,
                unit=entry.unit, oxford3000=entry.oxford3000,
            ),
            context,
        )
        key = headword(entry.english).lower()
        scored.setdefault(key, candidate)
        original_gloss.setdefault(key, entry.german)
        section_of.setdefault(key, strip_page_reference(entry.section))

    result = Provenance(
        unit_label=(workbook.unit_label(unit) if unit is not None else "")
        + (" (nur Hauptteil)" if core_only else ""),
        pool_size=len(pool),
    )

    from collections import defaultdict as _dd

    sections: dict[str, list[str]] = _dd(list)
    used_keys: set[str] = set()
    for item in pair.all_items:
        key = headword(item.english).lower()
        used_keys.add(key)
        result.used.append(item.english)

        source = scored.get(key)
        if source is None:
            result.invented.append((item.english, item.german))
            sections["nicht in der Excel-Datei"].append(item.english)
            continue
        section = section_of.get(key) or "ohne Angabe"
        if unit is not None and is_core_section(section, unit):
            section += " (Hauptteil)"
        sections[section].append(item.english)
        if not is_usable(source):
            result.readmitted.append((item.english, _reason_for(source)))
        before = original_gloss.get(key, "")
        if before and normalize_key(before) != normalize_key(item.german):
            result.gloss_changed.append((item.english, before, item.german))

    grouped: dict[str, list[str]] = defaultdict(list)
    for key, candidate in scored.items():
        if key in used_keys:
            continue
        grouped[_reason_for(candidate)].append(candidate.headword or candidate.english)
    result.left_out = dict(grouped)
    result.sections = dict(sections)
    result.invented_share = (
        len(result.invented) / len(result.used) if result.used else 0.0
    )
    return result
