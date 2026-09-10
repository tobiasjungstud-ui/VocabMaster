"""Die Vokabeldatenbank - eine Frage, eine Antwort.

Kanonisch sind die JSON-Dateien aus :mod:`vocabmaster.importer` - eine je
Unit, dazu eine ``index.json``. Sie lassen sich lesen, im Git-Verlauf
vergleichen und von Hand nachpflegen. Für Abfragen wird daraus beim Öffnen
eine SQLite-Datenbank **im Arbeitsspeicher** gebaut: bei rund 1700 Zeilen
dauert das keine messbare Zeit, und im Repository liegt keine Binärdatei,
deren Diff niemand lesen kann.

    db = Database.load()
    db.units()                        -> [0, 1, 2, …, 8]
    db.unit_pool(7)                   -> nur der Hauptteil von Unit 7
    db.unit_pool(7, core_only=False)  -> mit Culture 7, Project 7, …
    db.earlier(7)                     -> alles aus Unit 0-6 (gilt als gelernt)
    db.theme(7)                       -> Titel, Thema, Leitwörter
    db.query("SELECT … FROM woerter WHERE zipf < 3")
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from .config import DEFAULT_DATABASE  # Verzeichnis mit den Unit-Dateien
from .importer import KIND_LABELS, Row

SCHEMA = """
CREATE TABLE woerter (
    id           INTEGER PRIMARY KEY,
    english      TEXT NOT NULL,
    headword     TEXT NOT NULL,
    german       TEXT NOT NULL,
    unit         INTEGER,
    kind         TEXT NOT NULL,
    section      TEXT,
    page         INTEGER,
    pos          TEXT,
    pronunciation TEXT,
    example      TEXT,
    oxford3000   INTEGER NOT NULL DEFAULT 0,
    zipf         REAL NOT NULL DEFAULT 0,
    row          INTEGER
);
CREATE INDEX woerter_unit ON woerter (unit, kind);
CREATE INDEX woerter_headword ON woerter (headword);
"""

_COLUMNS = (
    "english", "headword", "german", "unit", "kind", "section", "page",
    "pos", "pronunciation", "example", "oxford3000", "zipf", "row",
)


@dataclass
class Database:
    """Zugriff auf die Wortliste eines Lehrmittels."""

    rows: list[Row] = field(default_factory=list)
    quelle: dict[str, Any] = field(default_factory=dict)
    themen: dict[int, dict[str, Any]] = field(default_factory=dict)
    hinweise: list[str] = field(default_factory=list)
    pfad: Path | None = None

    # ------------------------------------------------------------------ laden
    @classmethod
    def load(cls, directory: str | Path | None = None) -> Database:
        target = Path(directory or DEFAULT_DATABASE)
        index_path = target / "index.json"
        if not index_path.exists():
            raise FileNotFoundError(
                f"Die Datenbank in {target} fehlt. Sie wird mit\n"
                f"    vocabmaster db import <wortliste.xls>\n"
                "aus der Excel-Wortliste des Lehrmittels erzeugt."
            )
        index = json.loads(index_path.read_text(encoding="utf-8"))
        rows: list[Row] = []
        themen: dict[int, dict[str, Any]] = {}
        for entry in index.get("units", []):
            payload = json.loads((target / entry["datei"]).read_text(encoding="utf-8"))
            rows.extend(Row(**word) for word in payload.get("woerter", []))
            if payload.get("unit") is not None:
                themen[int(payload["unit"])] = {
                    "titel": payload.get("titel", ""),
                    "thema": payload.get("thema", ""),
                    "seiten": payload.get("seiten", ""),
                    "leitwoerter": list(payload.get("leitwoerter", [])),
                }
        return cls(
            rows=rows,
            quelle=index.get("quelle", {}),
            themen=themen,
            hinweise=list(index.get("hinweise", [])),
            pfad=target,
        )

    # ------------------------------------------------------------- Herkunft
    @property
    def herkunft(self) -> str:
        """Eine Zeile, die in jedes erzeugte Dokument gehört."""
        q = self.quelle
        return (
            f"{q.get('datei', 'unbekannte Quelle')} "
            f"(importiert {q.get('importiert', '?')}, "
            f"SHA-256 {str(q.get('pruefsumme_sha256', ''))[:12]})"
        )

    def theme(self, unit: int) -> dict[str, Any]:
        """Titel, Thema und Leitwörter einer Unit."""
        return self.themen.get(unit, {"titel": self.unit_label(unit), "thema": "",
                                      "seiten": "", "leitwoerter": []})

    # ------------------------------------------------------------- SQL-Zugang
    @cached_property
    def connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        conn.executemany(
            f"INSERT INTO woerter ({', '.join(_COLUMNS)}) "
            f"VALUES ({', '.join('?' * len(_COLUMNS))})",
            [
                tuple(
                    int(getattr(r, c)) if c == "oxford3000" else getattr(r, c)
                    for c in _COLUMNS
                )
                for r in self.rows
            ],
        )
        conn.commit()
        return conn

    def query(self, sql: str, parameters: Iterable[Any] = ()) -> list[sqlite3.Row]:
        """Freie SQL-Abfrage - nur lesend."""
        if not sql.lstrip().lower().startswith(("select", "with")):
            raise ValueError("Es sind nur lesende Abfragen (SELECT/WITH) erlaubt.")
        return list(self.connection.execute(sql, tuple(parameters)))

    # ------------------------------------------------------------- Abfragen
    def units(self) -> list[int]:
        """Alle Units, die einen Hauptteil haben (0 = Starter Unit)."""
        return sorted(
            {r.unit for r in self.rows if r.unit is not None and r.is_core}
        )

    def unit_label(self, unit: int) -> str:
        return "Starter Unit" if unit == 0 else f"Unit {unit}"

    def has_unit(self, unit: int) -> bool:
        return unit in set(self.units())

    def require_unit(self, unit: int) -> int:
        """Bricht mit einer verständlichen Meldung ab, wenn es die Unit nicht gibt."""
        if not self.has_unit(unit):
            available = ", ".join(self.unit_label(u) for u in self.units())
            raise ValueError(
                f"{self.unit_label(unit)} steht nicht in der Wortliste "
                f"{self.quelle.get('datei', '')}. Vorhanden sind: {available}."
            )
        return unit

    def unit_pool(self, unit: int, core_only: bool = True) -> list[Row]:
        """Das Vokabular einer Unit.

        ``core_only`` (Voreinstellung) beschränkt auf den Hauptteil ``Unit N``.
        Nach den Arbeitsanweisungen ist das der verbindliche Umfang: Culture,
        Curriculum extra, Project, Literature und Extra Listening zählen nicht
        dazu, auch wenn sie dieselbe Nummer tragen.
        """
        pool = [r for r in self.rows if r.unit == unit]
        if core_only:
            pool = [r for r in pool if r.is_core]
        if not pool:
            available = ", ".join(self.unit_label(u) for u in self.units())
            raise ValueError(
                f"Für {self.unit_label(unit)}"
                f"{' (nur Hauptteil)' if core_only else ''} stehen keine "
                f"Vokabeln in der Datenbank. Verfügbar: {available}"
            )
        return pool

    def earlier(self, unit: int) -> list[Row]:
        """Alles aus früheren Units - gilt als bereits gelernt."""
        return [r for r in self.rows if r.unit is not None and r.unit < unit]

    def find(self, english: str) -> list[Row]:
        """Alle Einträge zu einem englischen Wort, egal aus welcher Unit."""
        needle = str(english).strip().lower()
        return [
            r for r in self.rows
            if r.english.lower() == needle or r.headword.lower() == needle
        ]

    def search(self, text: str, limit: int = 50) -> list[Row]:
        """Freitextsuche über Englisch und Deutsch."""
        needle = f"%{str(text).strip().lower()}%"
        return [
            Row(**{c: row[c] for c in _COLUMNS} | {"oxford3000": bool(row["oxford3000"])})
            for row in self.query(
                "SELECT * FROM woerter WHERE lower(english) LIKE ? "
                "OR lower(german) LIKE ? ORDER BY unit, row LIMIT ?",
                (needle, needle, limit),
            )
        ]

    # ------------------------------------------------------------- Übersicht
    def overview(self) -> list[dict[str, Any]]:
        """Je Unit: wie viele Wörter im Hauptteil, wie viele im Zusatzmaterial."""
        out = []
        for unit in self.units():
            entries = [r for r in self.rows if r.unit == unit]
            kinds: dict[str, int] = {}
            for r in entries:
                kinds[r.kind] = kinds.get(r.kind, 0) + 1
            out.append(
                {
                    "unit": unit,
                    "label": self.unit_label(unit),
                    "thema": self.theme(unit).get("thema", ""),
                    "hauptteil": sum(1 for r in entries if r.is_core),
                    "gesamt": len(entries),
                    "bereiche": {KIND_LABELS.get(k, k): n for k, n in sorted(kinds.items())},
                }
            )
        return out

    def __len__(self) -> int:
        return len(self.rows)
