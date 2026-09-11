"""Aus einem geprüften Paket werden die Word-Dateien.

Je Unit entstehen neun Dokumente: **eine** Vokabelliste für beide Gruppen
und vier Prüfungen mit ihren Lösungsblättern.

============================================  ==========================================
``Unit03_V1_VocabularyList.docx``             Vokabelliste V1, Test 1 und Test 2
``Unit03_V1_Test_PartI_NiveauA.docx``         Prüfung zu Test 1, stärkere Gruppe
``Unit03_V1_Test_PartI_NiveauB.docx``         Prüfung zu Test 1, schwächere Gruppe
``Unit03_V1_Test_PartII_NiveauA.docx``        Prüfung zu Test 2, stärkere Gruppe
``Unit03_V1_Test_PartII_NiveauB.docx``        Prüfung zu Test 2, schwächere Gruppe
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
from .niveau import NIVEAUS, PROFILES
from .pack import Pack

TEIL_NAMEN = {1: "PartI", 2: "PartII"}


def dateiname(unit: int, art: str, teil: int | None = None,
              niveau: str | None = None, loesung: bool = False,
              fassung: int = 1, liste_version: int = 1) -> str:
    """Einheitliche Benennung: ``Unit03_V1_Test_PartI_NiveauB_Loesung.docx``.

    Der Code **V1, V2, V3** benennt die Vokabelliste. Er steht auf der Liste
    und auf jeder Prüfung, die zu ihr gehört - denn genau das ist die Frage,
    die sich zwei Tage später stellt: Zu welcher Liste gehört dieser Test?
    Am Dateinamen ist das ablesbar, ohne eine Datei zu öffnen.

    Die Vokabelliste trägt kein Niveau im Namen - es gibt je Liste nur eine.

    Eine zweite oder dritte **Fassung** derselben Prüfung - für eine
    Nachprüfung, oder weil die erste bekannt geworden ist - trägt ihre
    Nummer dahinter. Die erste nicht.
    """
    parts = [f"Unit{unit:02d}", f"V{max(1, int(liste_version))}", art]
    if teil:
        parts.append(TEIL_NAMEN[teil])
    if niveau:
        parts.append(f"Niveau{niveau}")
    if fassung and fassung > 1:
        parts.append(f"Fassung{fassung}")
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


def _herkunftszeile(pack: Pack, niveau: str | None = None) -> str:
    q = pack.quelle
    return (
        f"Quelle: {q.get('datei', 'unbekannt')} "
        f"(Import {q.get('importiert', '?')}, "
        f"SHA-256 {str(q.get('pruefsumme_sha256', ''))[:12]}) · "
        f"erzeugt {date.today().isoformat()} · {pack.unit_label}"
        + (f" · Niveau {niveau} ({PROFILES[niveau].cefr})" if niveau else "")
    )


def _stempeln_python_docx(document, pack: Pack, titel: str) -> None:
    """Herkunft in die Dokumenteigenschaften schreiben."""
    props = document.core_properties
    props.title = titel
    props.subject = f"{pack.unit_label} - {pack.thema}"
    props.comments = _herkunftszeile(pack)
    props.category = "Vokabelliste für Niveau A und Niveau B"


def schreibe_liste(pack: Pack, ziel: Path, settings: Settings | None = None) -> Path:
    """Die Vokabelliste als Word-Datei, im Layout der Vorlage."""
    settings = settings or Settings()
    pair = _pair_from_pack(pack)
    document = build_document(pair, settings)
    _stempeln_python_docx(document, pack, f"Vocabulary {pack.unit_label}")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(ziel))
    return ziel


def _spec_mit_herkunft(pack: Pack, teil: int, niveau: str) -> dict:
    spec = pack.exam(teil, niveau)
    meta = dict(spec.get("meta", {}))
    meta["title"] = meta.get(
        "titel", f"{pack.unit_label} Teil {teil} - Niveau {niveau}"
    )
    meta["herkunft"] = _herkunftszeile(pack, niveau)
    return {**spec, "meta": meta}


def schreibe_pruefung(
    pack: Pack, teil: int, niveau: str, ziel: Path,
    settings: Settings | None = None, mit_loesung: bool = True,
) -> list[Path]:
    """Prüfung und Lösungsblatt, byteweise im Layout der Referenzprüfung."""
    settings = settings or Settings()
    spec = _spec_mit_herkunft(pack, teil, niveau)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    geschrieben = [Path(build_docx(spec, str(settings.exam_template), str(ziel)))]
    if mit_loesung:
        loesung = ziel.with_name(
            dateiname(pack.unit, "Test", teil, niveau, loesung=True,
                      fassung=pack.fassung, liste_version=pack.liste_version)
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
    niveaus: tuple[str, ...] = NIVEAUS,
) -> Ergebnis:
    """Schreibt die gewünschten Dokumente und kontrolliert sie danach.

    ``teile`` und ``niveaus`` erlauben Teilanfragen: ``teile=("test",)`` mit
    ``niveaus=("B",)`` erzeugt nur die beiden Prüfungen für Niveau B und
    lässt Vokabelliste und Niveau A unberührt.
    """
    settings = settings or Settings()
    ziel = Path(verzeichnis)
    ergebnis = Ergebnis()
    ergebnis.bericht.gelaufen.append("dokument")

    if "liste" in teile:
        pfad = ziel / dateiname(pack.unit, "VocabularyList",
                                liste_version=pack.liste_version)
        ergebnis.dateien.append(schreibe_liste(pack, pfad, settings))

    if "test" in teile:
        for teil, niveau in sorted(pack.exams):
            if niveau not in niveaus:
                continue
            pfad = ziel / dateiname(pack.unit, "Test", teil, niveau,
                                    fassung=pack.fassung,
                                    liste_version=pack.liste_version)
            geschrieben = schreibe_pruefung(
                pack, teil, niveau, pfad, settings, mit_loesung
            )
            ergebnis.dateien.extend(geschrieben)
            # Nachkontrolle des geschriebenen Dokuments gegen die Vorlage.
            spec = _spec_mit_herkunft(pack, teil, niveau)
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
