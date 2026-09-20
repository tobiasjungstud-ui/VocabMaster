"""Zentrale Einstellungen - alles an einem Ort, überschreibbar per Umgebungsvariable.

Die Anwendung läuft vollständig ohne Sprachmodell und ohne API-Schlüssel.
Die Inhalte (Beispielsätze, Lückentexte) entstehen im Chat und werden hier
nur noch geprüft und gesetzt; siehe ``CLAUDE.md``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .aufgaben import ARTEN, KLASSISCH, LUECKEN, sortiert, verteile

#: Wurzel des Repositorys - für die mitgelieferte Wortliste und die Vorlagen.
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent.parent

#: Verzeichnis der Datenbank: eine JSON-Datei je Unit plus index.json.
#: SQLite wird daraus beim Öffnen im Arbeitsspeicher gebaut.
DEFAULT_DATABASE = PACKAGE_ROOT / "data" / "wortliste"
DEFAULT_EXAM_TEMPLATE = PACKAGE_ROOT / "templates" / "exam_template.docx"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "ja", "on"}


def _env_liste(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    """Eine kommagetrennte Liste aus der Umgebung - leer heisst Vorgabe."""
    roh = os.environ.get(name, "")
    teile = tuple(t.strip() for t in roh.split(",") if t.strip())
    return teile or tuple(default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    """Alle Stellschrauben der Anwendung."""

    # --- Datenquelle ------------------------------------------------------
    database: Path = field(default_factory=lambda: Path(
        os.environ.get("VM_DATABASE", str(DEFAULT_DATABASE))
    ))
    exam_template: Path = field(default_factory=lambda: Path(
        os.environ.get("VM_EXAM_TEMPLATE", str(DEFAULT_EXAM_TEMPLATE))
    ))

    # --- Umfang einer Unit ------------------------------------------------
    #: Verbindlich: Es zählt nur der Hauptteil ``Unit N``. Culture, Project,
    #: Curriculum extra, Literature und Extra Listening gehören nicht dazu.
    core_sections_only: bool = field(default_factory=lambda: _env_bool("VM_CORE_ONLY", True))
    words_per_test: int = field(default_factory=lambda: _env_int("VM_WORDS_PER_TEST", 30))
    #: Höchstanteil selbst ergänzter Wörter an einer Liste.
    max_invented_share: float = field(
        default_factory=lambda: float(os.environ.get("VM_MAX_INVENTED", 0.40))
    )

    # --- Prüfungen --------------------------------------------------------
    #: Wie viele Vokabeln eine Prüfung **insgesamt** abfragt. Die Zahl
    #: wird auf die angekreuzten Aufgaben verteilt; siehe ``aufgaben.py``.
    exam_words: int = field(default_factory=lambda: _env_int("VM_EXAM_WORDS", 12))
    #: Welche Aufgabentypen die Prüfung hat, in der Reihenfolge des
    #: Blattes. **Voreingestellt die beiden klassischen**: Wer nichts
    #: umstellt, bekommt die Prüfung, die es immer gab - acht zum
    #: Übersetzen, vier Lücken.
    exam_tasks: tuple[str, ...] = field(
        default_factory=lambda: _env_liste("VM_EXAM_TASKS", KLASSISCH)
    )
    #: Wortzahl je Aufgabe, von Hand gesetzt. Was hier steht, gilt; der
    #: Rest wird verteilt. Leer heisst "alles automatisch".
    exam_task_words: dict[str, int] = field(default_factory=dict)
    #: Verteilt die Gesamtzahl automatisch auf die angekreuzten Aufgaben.
    #: Ausgeschaltet zählt nur noch, was je Aufgabe von Hand dasteht.
    exam_auto_verteilen: bool = field(
        default_factory=lambda: _env_bool("VM_EXAM_AUTO", True)
    )
    #: Lücken von Hand - dieselbe Angabe wie ``exam_task_words['luecken']``,
    #: nur unter dem Namen, unter dem es sie schon immer gab. 0 heisst
    #: "aus der Verteilung nehmen".
    exam_gaps: int = field(default_factory=lambda: _env_int("VM_EXAM_GAPS", 0))

    # --- Layout der Vokabelliste -----------------------------------------
    heading_test1: str = field(default_factory=lambda: os.environ.get("VM_HEADING1", "Test 1"))
    heading_test2: str = field(default_factory=lambda: os.environ.get("VM_HEADING2", "Test 2"))
    column_titles: tuple[str, str, str, str] = ("Nr.", "Deutsch", "English", "Example sentence")
    font_name: str = field(default_factory=lambda: os.environ.get("VM_FONT", "Century Gothic"))
    font_size_pt: float = field(default_factory=lambda: float(os.environ.get("VM_FONT_SIZE", 10)))
    row_height_twips: int = field(default_factory=lambda: _env_int("VM_ROW_HEIGHT", 340))
    bold_target_word: bool = field(default_factory=lambda: _env_bool("VM_BOLD_TARGET", True))
    page_break_between_tests: bool = field(
        default_factory=lambda: _env_bool("VM_PAGE_BREAK", True)
    )

    # --- Reproduzierbarkeit ----------------------------------------------
    seed: int = field(default_factory=lambda: _env_int("VM_SEED", 20240607))

    def aufgabenplan(self) -> dict[str, int]:
        """Wie viele Wörter jede angekreuzte Aufgabe bekommt.

        Von Hand Gesetztes gilt immer; automatisch verteilt wird nur, was
        offen bleibt. So kann man eine Aufgabe festnageln und die anderen
        mitwandern lassen.
        """
        arten = sortiert(self.exam_tasks)
        eigen = {k: max(1, int(v)) for k, v in self.exam_task_words.items()
                 if k in arten}
        if self.exam_gaps and LUECKEN in arten:
            eigen.setdefault(LUECKEN, self.exam_gaps)
        offen = [k for k in arten if k not in eigen]
        if self.exam_auto_verteilen:
            # Was von Hand dasteht, kommt **aus** der Gesamtzahl, nicht
            # obendrauf: Sonst stiege sie bei jedem Festnageln, und der
            # Regler oben zeigte etwas anderes an als die Summe darunter.
            rest = max(0, self.exam_words - sum(eigen.values()))
            plan = verteile(rest, offen)
        else:
            plan = {k: ARTEN[k].mindestens for k in offen}
        plan.update(eigen)
        return {k: plan[k] for k in arten}

    @property
    def target_total(self) -> int:
        return self.words_per_test * 2
