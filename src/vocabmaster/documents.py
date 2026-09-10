"""Aus einem geprüften Paket werden die Word-Dateien.

Je Unit und Niveau entstehen vier Dokumente:

============================================  ==========================================
``Unit03_VocabularyList_NiveauA.docx``        Vokabelliste, Test 1 und Test 2
``Unit03_Test_PartI_NiveauA.docx``            Prüfung zu Test 1
``Unit03_Test_PartII_NiveauA.docx``           Prüfung zu Test 2
``…_Loesung.docx``                            je Prüfung ein Lösungsblatt
============================================  ==========================================

Beide Layouts stammen unverändert aus den Ursprungsanwendungen: Die
Vokabelliste wird mit den Massen der Vorlage gesetzt
(:mod:`vocabmaster.list.docx_writer`), die Prüfung übernimmt **jeden** Teil
des Word-Pakets der Referenzprüfung und schreibt nur ``word/document.xml``
neu (:mod:`vocabmaster.exam.builder`). Nach dem Schreiben wird jedes
Dokument gegen die Vorlage kontrolliert.

Die Herkunft (Quelldatei, Importdatum, Prüfsumme, Erstellungsdatum) steht in
den Dokumenteigenschaften jeder Datei und im Dateinamen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .checks import FEHLER, HINWEIS, WARNUNG, Pruefbericht, _pair_from_pack
from .config import Settings
from .exam.builder import build_answer_key, build_docx
from .exam.verify import verify_document
from .list.docx_writer import build_document
from .pack import Pack

TEIL_NAMEN = {1: "PartI", 2: "PartII"}


def dateiname(unit: int, niveau: str, art: str, teil: int | None = None,
              loesung: bool = False) -> str:
    """Einheitliche Benennung: ``Unit03_Test_PartI_NiveauB_Loesung.docx``."""
    parts = [f"Unit{unit:02d}", art]
    if teil:
        parts.append(TEIL_NAMEN[teil])
    parts.append(f"Niveau{niveau}")
    if loesung:
        parts.append("Loesung")
    return "_".join(parts) + ".docx"


@dataclass
class Ergebnis:
    """Was geschrieben wurde und was die Nachkontrolle ergab."""

    dateien: list[Path] = field(default_factory=list)
    bericht: Pruefbericht = field(default_factory=Pruefbericht)

    @property
    def ok(self) -> bool:
        return self.bericht.ok


def _herkunftszeile(pack: Pack) -> str:
    q = pack.quelle
    return (
        f"Quelle: {q.get('datei', 'unbekannt')} "
        f"(Import {q.get('importiert', '?')}, "
        f"SHA-256 {str(q.get('pruefsumme_sha256', ''))[:12]}) · "
        f"erzeugt {date.today().isoformat()} · "
        f"{pack.unit_label}, Niveau {pack.niveau.name} ({pack.niveau.cefr})"
    )


def _stempeln_python_docx(document, pack: Pack, titel: str) -> None:
    """Herkunft in die Dokumenteigenschaften schreiben."""
    props = document.core_properties
    props.title = titel
    props.subject = f"{pack.unit_label} - {pack.thema}"
    props.comments = _herkunftszeile(pack)
    props.category = f"Niveau {pack.niveau.name} ({pack.niveau.cefr})"


def schreibe_liste(pack: Pack, ziel: Path, settings: Settings | None = None) -> Path:
    """Die Vokabelliste als Word-Datei, im Layout der Vorlage."""
    settings = settings or Settings()
    pair = _pair_from_pack(pack)
    document = build_document(pair, settings)
    _stempeln_python_docx(
        document,
        pack,
        f"Vocabulary {pack.unit_label} - Niveau {pack.niveau.name}",
    )
    ziel.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(ziel))
    return ziel


def _spec_mit_herkunft(pack: Pack, teil: int) -> dict:
    spec = pack.exam(teil)
    meta = dict(spec.get("meta", {}))
    meta["title"] = meta.get(
        "titel", f"{pack.unit_label} Teil {teil} - Niveau {pack.niveau.name}"
    )
    meta["herkunft"] = _herkunftszeile(pack)
    return {**spec, "meta": meta}


def schreibe_pruefung(
    pack: Pack, teil: int, ziel: Path, settings: Settings | None = None,
    mit_loesung: bool = True,
) -> list[Path]:
    """Prüfung und Lösungsblatt, byteweise im Layout der Referenzprüfung."""
    settings = settings or Settings()
    spec = _spec_mit_herkunft(pack, teil)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    geschrieben = [Path(build_docx(spec, str(settings.exam_template), str(ziel)))]
    if mit_loesung:
        loesung = ziel.with_name(
            dateiname(pack.unit, pack.niveau.name, "Test", teil, loesung=True)
        )
        geschrieben.append(
            Path(build_answer_key(spec, str(settings.exam_template), str(loesung)))
        )
    return geschrieben


def baue_alles(
    pack: Pack,
    verzeichnis: str | Path,
    settings: Settings | None = None,
    teile: tuple[str, ...] = ("liste", "test"),
    mit_loesung: bool = True,
) -> Ergebnis:
    """Schreibt die gewünschten Dokumente und kontrolliert sie danach.

    ``teile`` erlaubt Teilanfragen: ``("test",)`` erzeugt nur die beiden
    Prüfungen und lässt die Vokabelliste unberührt.
    """
    settings = settings or Settings()
    ziel = Path(verzeichnis)
    ergebnis = Ergebnis()
    ergebnis.bericht.gelaufen.append("dokument")

    if "liste" in teile:
        pfad = ziel / dateiname(pack.unit, pack.niveau.name, "VocabularyList")
        ergebnis.dateien.append(schreibe_liste(pack, pfad, settings))

    if "test" in teile:
        for teil in sorted(pack.exams):
            pfad = ziel / dateiname(pack.unit, pack.niveau.name, "Test", teil)
            geschrieben = schreibe_pruefung(pack, teil, pfad, settings, mit_loesung)
            ergebnis.dateien.extend(geschrieben)
            # Nachkontrolle des geschriebenen Dokuments gegen die Vorlage.
            spec = _spec_mit_herkunft(pack, teil)
            for pfad_geschrieben in geschrieben:
                ist_loesung = pfad_geschrieben.name.endswith("_Loesung.docx")
                for finding in verify_document(
                    str(pfad_geschrieben), spec, str(settings.exam_template), ist_loesung
                ):
                    stufe = {"ERROR": FEHLER, "WARN": WARNUNG, "INFO": HINWEIS}[
                        finding.level
                    ]
                    ergebnis.bericht.add(
                        stufe, "dokument",
                        f"{pfad_geschrieben.name} - {finding.check}: {finding.message}",
                    )

    ergebnis.bericht.kennzahlen["dokument"] = (
        f"{len(ergebnis.dateien)} Dateien geschrieben und nachkontrolliert"
    )
    return ergebnis
