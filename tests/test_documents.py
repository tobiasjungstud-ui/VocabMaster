"""Die geschriebenen Dokumente: Layout der Vorlage, Herkunft, keine Reste."""

from __future__ import annotations

import zipfile

from vocabmaster.documents import baue_alles, dateiname
from vocabmaster.exam.verify import verify_document
from vocabmaster.pack import Pack, scaffold

from .helpers import fill


def test_dateinamen_folgen_der_konvention():
    # Die Vokabelliste trägt kein Niveau - es gibt je Liste nur eine.
    assert dateiname(3, "VocabularyList") == "Unit03_V1_VocabularyList.docx"
    assert dateiname(3, "Test", 1, "B") == "Unit03_V1_Test_PartI_NiveauB.docx"
    assert dateiname(12, "Test", 2, "A", loesung=True) == (
        "Unit12_V1_Test_PartII_NiveauA_Loesung.docx"
    )


def test_dateiname_nennt_liste_und_fassung():
    """Am Namen muss ablesbar sein, zu welcher Liste eine Prüfung gehört."""
    assert dateiname(3, "VocabularyList", liste_version=2) == (
        "Unit03_V2_VocabularyList.docx"
    )
    assert dateiname(3, "Test", 1, "A", liste_version=2) == (
        "Unit03_V2_Test_PartI_NiveauA.docx"
    )
    # Liste und Fassung sind zwei verschiedene Dinge und stehen beide drin.
    assert dateiname(3, "Test", 1, "A", fassung=2, liste_version=3) == (
        "Unit03_V3_Test_PartI_NiveauA_Fassung2.docx"
    )
    # Zwei Listen derselben Unit dürfen sich nie auf denselben Namen abbilden.
    namen = {dateiname(3, "Test", 1, "A", liste_version=v) for v in (1, 2, 3)}
    assert len(namen) == 3


def test_alle_dokumente_entstehen(tmp_path, pack, settings):
    """Eine Liste, vier Prüfungen, vier Lösungsblätter."""
    ergebnis = baue_alles(pack, tmp_path, settings)
    namen = sorted(p.name for p in ergebnis.dateien)
    assert namen == [
        "Unit01_V1_Test_PartII_NiveauA.docx",
        "Unit01_V1_Test_PartII_NiveauA_Loesung.docx",
        "Unit01_V1_Test_PartII_NiveauB.docx",
        "Unit01_V1_Test_PartII_NiveauB_Loesung.docx",
        "Unit01_V1_Test_PartI_NiveauA.docx",
        "Unit01_V1_Test_PartI_NiveauA_Loesung.docx",
        "Unit01_V1_Test_PartI_NiveauB.docx",
        "Unit01_V1_Test_PartI_NiveauB_Loesung.docx",
        "Unit01_V1_VocabularyList.docx",
    ]
    for pfad in ergebnis.dateien:
        assert pfad.exists() and pfad.stat().st_size > 0
        assert zipfile.is_zipfile(pfad), f"{pfad.name} ist kein gültiges Word-Paket"


def test_pruefung_uebernimmt_die_vorlage_byteweise(tmp_path, pack, settings):
    """Nur word/document.xml darf sich von der Vorlage unterscheiden."""
    baue_alles(pack, tmp_path, settings, teile=("test",))
    erzeugt = tmp_path / dateiname(pack.unit, "Test", 1, "A")
    with zipfile.ZipFile(settings.exam_template) as vorlage, \
            zipfile.ZipFile(erzeugt) as neu:
        assert set(vorlage.namelist()) == set(neu.namelist())
        for name in vorlage.namelist():
            if name in ("word/document.xml", "docProps/core.xml"):
                continue
            assert vorlage.read(name) == neu.read(name), f"{name} wurde verändert"


def test_nachkontrolle_der_dokumente_laeuft(tmp_path, pack, settings):
    ergebnis = baue_alles(pack, tmp_path, settings)
    assert "dokument" in ergebnis.bericht.gelaufen
    assert ergebnis.ok, [str(b) for b in ergebnis.bericht.fehler]


def test_keine_platzhalter_im_dokument(tmp_path, pack, settings):
    ergebnis = baue_alles(pack, tmp_path, settings)
    for pfad in ergebnis.dateien:
        with zipfile.ZipFile(pfad) as z:
            text = z.read("word/document.xml").decode("utf-8")
        assert "TODO" not in text, f"{pfad.name} enthält einen Platzhalter"
        assert "{1}" not in text and "{}" not in text


def test_herkunft_steht_in_den_dokumenteigenschaften(tmp_path, pack, settings):
    baue_alles(pack, tmp_path, settings, teile=("liste",))
    pfad = tmp_path / dateiname(pack.unit, "VocabularyList")
    with zipfile.ZipFile(pfad) as z:
        core = z.read("docProps/core.xml").decode("utf-8")
    assert "english_plus" in core
    assert "Niveau A und Niveau B" in core


def test_loesungsblatt_enthaelt_die_loesungen(tmp_path, pack, settings):
    baue_alles(pack, tmp_path, settings, teile=("test",))
    pruefung = tmp_path / dateiname(pack.unit, "Test", 1, "A")
    loesung = tmp_path / dateiname(pack.unit, "Test", 1, "A", loesung=True)
    antworten = [g["answer"] for g in pack.exam(1, "A")["task2"]["gaps"]]

    def text_of(path):
        with zipfile.ZipFile(path) as z:
            return z.read("word/document.xml").decode("utf-8")

    for antwort in antworten:
        assert antwort.upper() in text_of(loesung)
    # Auf dem Prüfungsblatt darf keine Lösung stehen.
    findings = verify_document(
        str(pruefung), pack.exam(1, "A"), str(settings.exam_template)
    )
    assert not [f for f in findings if f.check == "leak"]


def test_nur_test_laesst_die_liste_unberuehrt(tmp_path, pack, settings):
    baue_alles(pack, tmp_path, settings, teile=("liste",))
    liste = tmp_path / dateiname(pack.unit, "VocabularyList")
    vorher = liste.read_bytes()
    baue_alles(pack, tmp_path, settings, teile=("test",))
    assert liste.read_bytes() == vorher


def test_vokabelliste_passt_auf_eine_seite(db, settings):
    from vocabmaster.checks import _pair_from_pack
    from vocabmaster.list.docx_writer import check_page_fit

    data = fill(
        scaffold(db, 1, settings),
        satz="The whole class talked about {} during the lesson yesterday.",
    )
    pair = _pair_from_pack(Pack(data=data))
    for items in (pair.test1, pair.test2):
        assert check_page_fit(items, settings).fits
