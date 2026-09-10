"""Von der Datenbank zur geprüften Wortauswahl - **eine Liste je Unit**.

Beide Niveaus lernen dieselben 60 Wörter; unterschieden wird erst bei der
Prüfung (siehe :mod:`vocabmaster.niveau`). Die Auswahl läuft immer gleich:

1. Alle Einträge des **Hauptteils** der Unit aus der Datenbank holen.
2. Jeden Eintrag bewerten (Wortart, Häufigkeit, Niveau, Lernwert) und dabei
   berücksichtigen, was in früheren Units schon vorkam.
3. Doppelungen und Wortfamilien zusammenfassen.
4. 60 Wörter wählen und auf zwei gleich schwere Hälften verteilen.

Woher die Wörter kommen dürfen, ist verbindlich geordnet:

===  ====================================================================
 1.  **Hauptteil** ``Unit N``. Nur dieser Block, nicht Culture, nicht
     Project, nicht Curriculum extra - auch wenn sie dieselbe Nummer tragen.
 2.  Reicht das nicht, bleiben die fehlenden Plätze offen und werden **im
     Chat mit thematisch passenden Wörtern gefüllt**, höchstens 40 Prozent
     der Liste.
 3.  Erst wenn selbst das nicht genügt, zieht die Anwendung so viele Wörter
     aus den **Zusatzteilen derselben Unit** nach, wie nötig sind, um wieder
     unter die 40 Prozent zu kommen - und weist jedes einzelne davon im
     Bericht aus.
===  ====================================================================

Die Anwendung dichtet nichts selbst dazu. Sie sagt nur, wie viele Plätze
offen sind und woher sie im Notfall nachgezogen hat.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Settings
from .database import Database
from .importer import KIND_LABELS, Row
from .list.dedup import deduplicate
from .list.leveling import LevelContext, is_usable, score_candidate
from .list.models import Candidate, TestItem, TestPair
from .list.selection import balance_summary, select_words, split_balanced
from .niveau import LIST_BOUNDS


@dataclass
class PoolReport:
    """Wie aus dem Rohmaterial der Unit die Auswahl wurde - Zeile für Zeile."""

    unit: int = 0
    unit_label: str = ""
    thema: str = ""
    hauptteil: int = 0
    brauchbar: int = 0
    nach_dedup: int = 0
    gewaehlt: int = 0
    aus_hauptteil: int = 0
    aus_zusatzteilen: list[tuple[str, str]] = field(default_factory=list)
    fehlend: int = 0
    doppelungen: list[str] = field(default_factory=list)
    aussortiert: dict[str, list[str]] = field(default_factory=dict)
    ausnahme: str = ""

    @property
    def ergaenzt_anteil(self) -> float:
        return self.fehlend / (self.gewaehlt + self.fehlend) if self.gewaehlt + self.fehlend else 0.0

    def summary(self) -> str:
        text = (
            f"{self.unit_label}: {self.hauptteil} Wörter im Hauptteil, "
            f"{self.brauchbar} davon geeignet, {self.nach_dedup} nach "
            f"Zusammenfassung von Wortfamilien, {self.aus_hauptteil} gewählt"
        )
        if self.aus_zusatzteilen:
            text += f", {len(self.aus_zusatzteilen)} aus Zusatzteilen nachgezogen"
        if self.fehlend:
            text += f", {self.fehlend} im Chat zu ergänzen ({self.ergaenzt_anteil:.0%})"
        return text


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


def _bewerten(rows: list[Row], context: LevelContext) -> list[Candidate]:
    return [score_candidate(to_candidate(r), context, LIST_BOUNDS) for r in rows]


@dataclass
class UnitPlan:
    """Die fertige Wortauswahl einer Unit - für beide Niveaus dieselbe."""

    unit: int
    unit_label: str
    thema: str
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
    db: Database, unit: int, settings: Settings | None = None
) -> UnitPlan:
    """Wählt die 60 Wörter einer Unit und teilt sie auf Test 1 und Test 2 auf."""
    settings = settings or Settings()
    db.require_unit(unit)
    theme = db.theme(unit)
    ziel = settings.target_total

    haupt = db.unit_pool(unit, core_only=True)
    context = LevelContext.from_entries(db.earlier(unit))
    kandidaten = _bewerten(haupt, context)

    report = PoolReport(
        unit=unit,
        unit_label=db.unit_label(unit),
        thema=theme.get("thema", ""),
        hauptteil=len(haupt),
    )
    for c in kandidaten:
        if is_usable(c):
            continue
        grund = c.notes[0] if c.notes else "ohne Begründung aussortiert"
        report.aussortiert.setdefault(grund, []).append(c.headword or c.english)

    brauchbar = [c for c in kandidaten if is_usable(c)]
    report.brauchbar = len(brauchbar)

    kept, dropped = deduplicate(brauchbar)
    report.nach_dedup = len(kept)
    report.doppelungen = [
        f"{loser.headword} (zugunsten von {winner.headword}: {why})"
        for loser, winner, why in dropped
    ]

    auswahl = select_words(kept, fallback=None, target=ziel)
    gewaehlt = list(auswahl.chosen)
    report.aus_hauptteil = len(gewaehlt)

    # Ausnahme: Reichen Hauptteil und die erlaubten 40 Prozent Ergänzung
    # zusammen nicht aus, werden Zusatzteile derselben Unit nachgezogen -
    # nur so viele wie nötig, und jedes wird im Bericht genannt.
    erlaubt_offen = int(ziel * settings.max_invented_share)
    if len(gewaehlt) + erlaubt_offen < ziel:
        gewaehlt = _aus_zusatzteilen_nachziehen(
            db, unit, context, gewaehlt, ziel - erlaubt_offen, report
        )

    report.gewaehlt = len(gewaehlt)
    report.fehlend = max(0, ziel - len(gewaehlt))

    plan = UnitPlan(
        unit=unit,
        unit_label=db.unit_label(unit),
        thema=theme.get("thema", ""),
        report=report,
    )
    if report.fehlend:
        # Ohne 60 Wörter lässt sich nicht ausgewogen aufteilen; die offenen
        # Plätze verteilt das Gerüst gleichmässig auf beide Tests.
        plan.test1 = gewaehlt[: settings.words_per_test]
        plan.test2 = gewaehlt[settings.words_per_test :]
    else:
        plan.test1, plan.test2 = split_balanced(
            gewaehlt, settings.words_per_test, settings.seed
        )

    alle = {r.headword.lower(): r for r in db.unit_pool(unit, core_only=False)}
    plan.herkunft = {
        c.headword.lower(): alle[c.headword.lower()]
        for c in plan.all_words
        if c.headword.lower() in alle
    }
    return plan


def _aus_zusatzteilen_nachziehen(
    db: Database,
    unit: int,
    context: LevelContext,
    gewaehlt: list[Candidate],
    ziel: int,
    report: PoolReport,
) -> list[Candidate]:
    """Letzte Reserve: Culture, Project, Curriculum extra derselben Unit.

    Wird nur betreten, wenn der Hauptteil selbst mit der vollen erlaubten
    Ergänzung keine Liste ergibt. Es werden so wenige Wörter wie möglich
    nachgezogen, und jedes einzelne steht anschliessend im Bericht.
    """
    zusatz = [r for r in db.unit_pool(unit, core_only=False) if not r.is_core]
    if not zusatz:
        report.ausnahme = (
            "Der Hauptteil reicht nicht, und die Unit hat keine Zusatzteile. "
            "Die Liste bleibt unvollständig."
        )
        return gewaehlt

    kandidaten = [c for c in _bewerten(zusatz, context) if is_usable(c)]
    zusammen, _ = deduplicate(gewaehlt + kandidaten)
    nachgezogen = [c for c in zusammen if c not in gewaehlt]
    nachgezogen.sort(key=lambda c: (-c.learning_value, -c.difficulty))

    von_kind = {r.headword.lower(): r.kind for r in zusatz}
    ergebnis = list(gewaehlt)
    for c in nachgezogen:
        if len(ergebnis) >= ziel:
            break
        ergebnis.append(c)
        kind = von_kind.get(c.headword.lower(), "")
        report.aus_zusatzteilen.append((c.headword, KIND_LABELS.get(kind, kind)))

    report.ausnahme = (
        f"Ausnahme: Der Hauptteil von {report.unit_label} gibt nur "
        f"{report.aus_hauptteil} geeignete Wörter her. Das liegt über der "
        f"Grenze von 40 Prozent eigener Ergänzungen, deshalb wurden "
        f"{len(report.aus_zusatzteilen)} Wörter aus den Zusatzteilen derselben "
        "Unit nachgezogen (Culture, Curriculum extra, Project). Sie stehen "
        "einzeln im Bericht."
    )
    return ergebnis
