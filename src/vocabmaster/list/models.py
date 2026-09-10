"""Datenmodelle für die gesamte Pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class POS(str, Enum):
    """Grobe Wortart, abgeleitet aus der deutschen Übersetzung."""

    NOUN = "Nomen"
    VERB = "Verb"
    ADJECTIVE = "Adjektiv"
    ADVERB = "Adverb"
    PHRASE = "Wendung"
    OTHER = "Sonstiges"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class VocabEntry:
    """Eine Rohzeile aus der Excel-Datei."""

    english: str
    german: str
    section: str
    unit: int | None
    block: str | None = None
    oxford3000: bool = False
    row: int = 0
    sheet: str = ""

    @property
    def is_starter(self) -> bool:
        return self.unit == 0


@dataclass
class Candidate:
    """Ein bewerteter Kandidat für die Testliste."""

    english: str
    german: str
    section: str = ""
    unit: int | None = None
    origin: str = "excel"  # "excel" oder "llm" (Ersatzwort)
    oxford3000: bool = False

    # von normalize/leveling gefüllt
    headword: str = ""
    stem: str = ""
    pos: POS = POS.OTHER
    zipf: float = 0.0
    difficulty: float = 0.0  # 0.0 = sehr leicht, 1.0 = sehr schwer
    cefr: str = ""  # "A1".."C1"
    learning_value: float = 0.0
    topic: str = ""
    flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    replaces: str | None = None  # englisches Wort, das ersetzt wurde

    sentence: str = ""
    sentence_form: str = ""  # die im Satz tatsächlich verwendete Wortform

    def flag(self, name: str, note: str = "") -> None:
        if name not in self.flags:
            self.flags.append(name)
        if note and note not in self.notes:
            self.notes.append(note)

    @property
    def key(self) -> str:
        return self.headword.lower()


@dataclass
class Issue:
    """Ein Befund der Qualitätsprüfung."""

    code: str
    severity: Severity
    message: str
    words: list[str] = field(default_factory=list)
    stage: str = ""

    def __str__(self) -> str:  # pragma: no cover - reine Darstellung
        who = f" [{', '.join(self.words)}]" if self.words else ""
        return f"{self.severity.value.upper()} {self.code}: {self.message}{who}"


@dataclass
class QualityReport:
    """Sammelbericht aller Validierungsläufe."""

    issues: list[Issue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    rounds: int = 0

    def add(
        self,
        code: str,
        severity: Severity,
        message: str,
        words: list[str] | None = None,
        stage: str = "",
    ) -> None:
        self.issues.append(
            Issue(code=code, severity=severity, message=message, words=words or [], stage=stage)
        )

    def extend(self, other: QualityReport) -> None:
        self.issues.extend(other.issues)
        self.stats.update(other.stats)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def by_code(self, code: str) -> list[Issue]:
        return [i for i in self.issues if i.code == code]


@dataclass
class TestItem:
    """Eine nummerierte Zeile im fertigen Word-Dokument."""

    __test__ = False  # kein pytest-Testfall, trotz des Namens

    number: int
    german: str
    english: str
    sentence: str
    sentence_form: str = ""

    @classmethod
    def from_candidate(cls, number: int, c: Candidate) -> TestItem:
        return cls(
            number=number,
            german=c.german,
            english=c.headword or c.english,
            sentence=c.sentence,
            sentence_form=c.sentence_form or (c.headword or c.english),
        )


@dataclass
class TestPair:
    """Das Endergebnis: zwei Tests plus Qualitätsbericht."""

    __test__ = False  # kein pytest-Testfall, trotz des Namens

    unit: int
    test1: list[TestItem] = field(default_factory=list)
    test2: list[TestItem] = field(default_factory=list)
    report: QualityReport = field(default_factory=QualityReport)
    unit_label: str = ""

    @property
    def all_items(self) -> list[TestItem]:
        return self.test1 + self.test2
