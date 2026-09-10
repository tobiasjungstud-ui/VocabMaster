"""Von der Datenbank zu zwei überschneidungsfreien Wortauswahlen je Unit.

Beide Niveaus behandeln dieselbe Unit, aber kein Wort steht in beiden Listen.
Möglich wird das durch die getrennten Häufigkeitsfenster aus
:mod:`vocabmaster.niveau`:

* Wörter, die nur im Fenster von Niveau A liegen (selten, anspruchsvoll),
  gehen an A.
* Wörter, die nur im Fenster von Niveau B liegen (häufiger, alltagsnah, für
  die stärkere Gruppe längst bekannt), gehen an B.
* Wörter im Überlappungsbereich sind **strittig**. Sie werden so verteilt,
  dass beide Listen möglichst gleich weit gefüllt sind - wer knapper dran
  ist, bekommt zuerst, und innerhalb dessen entscheidet die Nähe zur Mitte
  des jeweiligen Fensters.

Was danach noch fehlt, bleibt bewusst offen: Die Lücke wird im Chat mit
thematisch passenden Wörtern gefüllt und in
:mod:`vocabmaster.checks` gegen die 40-Prozent-Grenze geprüft. Die
Anwendung dichtet nichts selbst dazu - sie sagt nur, wie viel fehlt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Settings
from .database import Database
from .importer import KIND_LABELS, Row
from .list.dedup import deduplicate, overlap_reason
from .list.leveling import Bounds, is_usable, score_candidate
from .list.models import Candidate, TestItem, TestPair
from .list.selection import balance_summary, select_words, split_balanced
from .niveau import PROFILES, NiveauProfile, profile


def bounds_for(prof: NiveauProfile) -> Bounds:
    return Bounds(too_easy=prof.zipf_max, too_rare=prof.zipf_min, label=prof.cefr)


@dataclass
class PoolReport:
    """Wie aus dem Rohmaterial der Unit die Auswahl wurde - Zeile für Zeile."""

    unit: int = 0
    unit_label: str = ""
    thema: str = ""
    niveau: str = "A"
    cefr: str = ""
    roh: int = 0
    im_fenster: int = 0
    zugeteilt: int = 0
    nach_dedup: int = 0
    gewaehlt: int = 0
    fehlend: int = 0
    nachgerueckt: list[str] = field(default_factory=list)
    doppelungen: list[str] = field(default_factory=list)
    aussortiert: dict[str, list[str]] = field(default_factory=dict)
    abschnitte: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"{self.unit_label}, Niveau {self.niveau} ({self.cefr}): "
            f"{self.roh} Wörter im Hauptteil, {self.im_fenster} im Niveaufenster, "
            f"{self.zugeteilt} diesem Niveau zugeteilt, {self.nach_dedup} nach "
            f"Zusammenfassung von Wortfamilien, {self.gewaehlt} gewählt"
            + (f" - es fehlen {self.fehlend}" if self.fehlend else "")
        )


def _topic(row: Row) -> str:
    """Thematische Nähe innerhalb einer Unit.

    Die Wortlisten der Lehrmittel sind seitenweise nach Lernabschnitt
    geordnet: Wörter derselben Doppelseite gehören zum selben Thema. Die
    Seite ist deshalb ein besseres Streuungsmerkmal als die Sektion, die im
    Hauptteil für jeden Eintrag gleich lautet.
    """
    return f"S. {row.page}" if row.page else (row.section or "ohne Angabe")


def to_candidate(row: Row) -> Candidate:
    """Eine Datenbankzeile als bewertbarer Kandidat."""
    return Candidate(
        english=row.english,
        german=row.german,
        section=_topic(row),
        unit=row.unit,
        oxford3000=row.oxford3000,
        zipf=row.zipf,  # beim Import berechnet, nicht zur Laufzeit
    )


def _bias(prof: NiveauProfile):
    """Der Zuschlag, der die Reihenfolge innerhalb eines Niveaus bestimmt.

    Er wirkt nur auf den Lernwert und verschiebt damit die Reihenfolge - ein
    Wort, das die Prüfung ausgeschlossen hat, kommt dadurch nicht zurück.
    """

    def value(c: Candidate) -> float:
        score = prof.difficulty_weight * (c.difficulty - 0.5) * 2.0
        score -= 0.30 * abs(c.zipf - prof.zipf_centre)
        if len(c.headword.split()) > 1:
            score += 0.25 if prof.name == "A" else -0.35
        return score

    return value


# ---------------------------------------------------------------------------
# Zuteilung
# ---------------------------------------------------------------------------
@dataclass
class Allocation:
    """Welches Wort der Unit gehört zu welchem Niveau?"""

    unit: int
    per_niveau: dict[str, list[Candidate]] = field(default_factory=dict)
    nur_a: int = 0
    nur_b: int = 0
    strittig: int = 0
    ungenutzt: list[Candidate] = field(default_factory=list)


def allocate(db: Database, unit: int, settings: Settings | None = None) -> Allocation:
    """Teilt den Hauptteil einer Unit überschneidungsfrei auf A und B auf."""
    settings = settings or Settings()
    db.require_unit(unit)
    rows = db.unit_pool(unit, core_only=settings.core_sections_only)
    earlier = db.earlier(unit)

    from .list.leveling import LevelContext

    context = LevelContext.from_entries(earlier)

    scored: dict[str, dict[str, Candidate]] = {}
    for name, prof in PROFILES.items():
        scored[name] = {}
        for row in rows:
            c = score_candidate(to_candidate(row), context, bounds_for(prof))
            scored[name][row.english] = c

    allocation = Allocation(unit=unit, per_niveau={"A": [], "B": []})
    contested: list[str] = []
    for row in rows:
        fits = {n: is_usable(scored[n][row.english]) for n in PROFILES}
        if fits["A"] and fits["B"]:
            contested.append(row.english)
            allocation.strittig += 1
        elif fits["A"]:
            allocation.per_niveau["A"].append(scored["A"][row.english])
            allocation.nur_a += 1
        elif fits["B"]:
            allocation.per_niveau["B"].append(scored["B"][row.english])
            allocation.nur_b += 1
        else:
            allocation.ungenutzt.append(scored["A"][row.english])

    # Strittige Wörter dorthin, wo sie am nötigsten gebraucht werden. Bei
    # gleichem Bedarf entscheidet die Nähe zur Mitte des Niveaufensters.
    target = settings.target_total
    order = sorted(
        contested,
        key=lambda e: abs(scored["A"][e].zipf - PROFILES["A"].zipf_centre)
        - abs(scored["B"][e].zipf - PROFILES["B"].zipf_centre),
    )
    for english in order:
        need_a = target - len(allocation.per_niveau["A"])
        need_b = target - len(allocation.per_niveau["B"])
        pick = "A" if need_a >= need_b else "B"
        allocation.per_niveau[pick].append(scored[pick][english])
    return allocation


# ---------------------------------------------------------------------------
# Auswahl je Niveau
# ---------------------------------------------------------------------------
@dataclass
class UnitPlan:
    """Die fertige Wortauswahl einer Unit für ein Niveau."""

    unit: int
    unit_label: str
    thema: str
    niveau: NiveauProfile
    test1: list[Candidate] = field(default_factory=list)
    test2: list[Candidate] = field(default_factory=list)
    report: PoolReport = field(default_factory=PoolReport)
    herkunft: dict[str, Row] = field(default_factory=dict)

    @property
    def all_words(self) -> list[Candidate]:
        return self.test1 + self.test2

    @property
    def balance(self) -> dict:
        return balance_summary(self.test1, self.test2)

    def as_pair(self) -> TestPair:
        pair = TestPair(unit=self.unit, unit_label=self.unit_label)
        pair.test1 = [TestItem.from_candidate(i, c) for i, c in enumerate(self.test1, 1)]
        pair.test2 = [TestItem.from_candidate(i, c) for i, c in enumerate(self.test2, 1)]
        return pair


def plan_unit(
    db: Database,
    unit: int,
    niveau: str | NiveauProfile = "A",
    settings: Settings | None = None,
    allocation: Allocation | None = None,
) -> UnitPlan:
    """Wählt die Wörter eines Niveaus und teilt sie auf Test 1 und Test 2 auf."""
    settings = settings or Settings()
    prof = profile(niveau)
    allocation = allocation or allocate(db, unit, settings)
    mine = allocation.per_niveau[prof.name]
    theme = db.theme(unit)

    rows = db.unit_pool(unit, core_only=settings.core_sections_only)
    report = PoolReport(
        unit=unit,
        unit_label=db.unit_label(unit),
        thema=theme.get("thema", ""),
        niveau=prof.name,
        cefr=prof.cefr,
        roh=len(rows),
        im_fenster=allocation.nur_a + allocation.nur_b + allocation.strittig,
        zugeteilt=len(mine),
    )
    for row in rows:
        label = KIND_LABELS.get(row.kind, row.kind)
        report.abschnitte[label] = report.abschnitte.get(label, 0) + 1
    for c in allocation.ungenutzt:
        reason = c.notes[0] if c.notes else "ohne Begründung aussortiert"
        report.aussortiert.setdefault(reason, []).append(c.headword or c.english)

    kept, dropped = deduplicate(mine)
    report.nach_dedup = len(kept)
    report.doppelungen = [
        f"{loser.headword} (zugunsten von {winner.headword}: {why})"
        for loser, winner, why in dropped
    ]

    # Kein Nachrücken aus dem anderen Niveau: das würde die Listen wieder
    # vermischen. Fehlt etwas, wird es im Chat ergänzt und ausgewiesen.
    selection = select_words(kept, fallback=None, target=settings.target_total,
                             bias=_bias(prof))
    report.gewaehlt = len(selection.chosen)
    report.fehlend = selection.deficit

    plan = UnitPlan(
        unit=unit,
        unit_label=db.unit_label(unit),
        thema=theme.get("thema", ""),
        niveau=prof,
        report=report,
    )
    if selection.deficit:
        plan.test1 = selection.chosen[: settings.words_per_test]
        plan.test2 = selection.chosen[settings.words_per_test :]
    else:
        plan.test1, plan.test2 = split_balanced(
            selection.chosen, settings.words_per_test, settings.seed
        )

    by_headword = {r.headword.lower(): r for r in rows}
    plan.herkunft = {
        c.headword.lower(): by_headword[c.headword.lower()]
        for c in plan.all_words
        if c.headword.lower() in by_headword
    }
    return plan


def plan_both(
    db: Database, unit: int, settings: Settings | None = None
) -> dict[str, UnitPlan]:
    """Beide Niveaus in einem Zug - so ist die Zuteilung garantiert dieselbe."""
    settings = settings or Settings()
    allocation = allocate(db, unit, settings)
    return {
        name: plan_unit(db, unit, name, settings, allocation) for name in PROFILES
    }


def shared_words(plans: dict[str, UnitPlan]) -> list[str]:
    """Wörter, die trotz getrennter Zuteilung in beiden Listen stehen.

    Sollte leer sein. Ist es das nicht, hat jemand von Hand eingegriffen -
    :mod:`vocabmaster.checks` meldet das als Fehler.
    """
    a = {c.headword.lower() for c in plans["A"].all_words}
    return sorted(c.headword for c in plans["B"].all_words if c.headword.lower() in a)


def near_duplicates(plans: dict[str, UnitPlan]) -> list[tuple[str, str, str]]:
    """Wortfamilien, die sich über die beiden Niveaus verteilt haben.

    ``advertise`` in Liste A und ``advertisement`` in Liste B ist nicht
    falsch - beide Gruppen lernen dasselbe Wortfeld -, aber es gehört in den
    Bericht.
    """
    hits = []
    for a in plans["A"].all_words:
        for b in plans["B"].all_words:
            why = overlap_reason(a, b)
            if why:
                hits.append((a.headword, b.headword, why))
    return hits
