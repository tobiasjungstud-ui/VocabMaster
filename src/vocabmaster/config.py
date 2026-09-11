"""Zentrale Einstellungen - alles an einem Ort, überschreibbar per Umgebungsvariable.

Die Anwendung läuft vollständig ohne Sprachmodell und ohne API-Schlüssel.
Die Inhalte (Beispielsätze, Lückentexte) entstehen im Chat und werden hier
nur noch geprüft und gesetzt; siehe ``CLAUDE.md``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

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
    exam_words: int = field(default_factory=lambda: _env_int("VM_EXAM_WORDS", 12))
    exam_gaps: int = field(default_factory=lambda: _env_int("VM_EXAM_GAPS", 4))

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

    @property
    def target_total(self) -> int:
        return self.words_per_test * 2
