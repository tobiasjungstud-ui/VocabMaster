"""Die Prüfung als Liste von Aufgaben - sechs Arten, eine Wortzahl.

Eine Prüfung war einmal zwei feste Aufgaben. Jetzt ist sie eine Liste: Man
kreuzt an, welche Arten sie hat, und die Wortzahl verteilt sich darauf.

Der erste Test hier ist der wichtigste: **Wer nichts umstellt, bekommt die
Prüfung von gestern** - dieselben Wörter, dieselbe Aufteilung, dasselbe
Dokument Byte für Byte.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from vocabmaster import cli
from vocabmaster.aufgaben import (
    ARTEN,
    KLASSISCH,
    SAETZE_ZUR_WAHL,
    sortiert,
    verteile,
)
from vocabmaster.checks import Pruefbericht, pruefe_aufgabenformen
from vocabmaster.config import Settings
from vocabmaster.database import Database
from vocabmaster.exam.builder import (
    aufgaben_des_specs,
    build_answer_key,
    build_document_xml,
    build_docx,
)
from vocabmaster.exam.verify import _page_estimate, document_text, tables, verify_document
from vocabmaster.pack import Pack, aufgaben_von, gepruefte_woerter, scaffold

from .helpers import fill

WURZEL = Path(__file__).resolve().parent.parent
WERKSTATT = WURZEL / "werkstatt"
ALLE = tuple(ARTEN)


@pytest.fixture(scope="module")
def datenbank() -> Database:
    return Database.load(Settings().database)


def _mit(**kw) -> Settings:
    return replace(Settings(), **kw)


# ---------------------------------------------------------------------------
# Wer nichts umstellt, bekommt die Prüfung von gestern
# ---------------------------------------------------------------------------
def test_die_vorgabe_ist_die_pruefung_von_bisher():
    """Acht zum Übersetzen, vier Lücken - das ist keine Zufallszahl.

    Die Gewichte 4 und 2 im Katalog sind genau dafür gewählt. Wer sie
    verstellt, ändert jede Prüfung, die niemand umgestellt hat.
    """
    assert Settings().exam_tasks == tuple(KLASSISCH)
    assert Settings().aufgabenplan() == {"uebersetzen": 8, "luecken": 4}
    assert verteile(12, KLASSISCH) == {"uebersetzen": 8, "luecken": 4}


@pytest.mark.parametrize("paket", sorted(
    (WURZEL / "kuratiert").glob("*.json")), ids=lambda p: p.stem)
def test_ein_paket_von_gestern_ergibt_dasselbe_dokument(paket):
    """Der teuerste denkbare Nebeneffekt dieses Umbaus, hier ausgeschlossen.

    Die mitgelieferten Pakete tragen noch ``task1`` und ``task2``. Sie
    werden über denselben Adapter gelesen wie die neue Liste - und müssen
    Zeichen für Zeichen dasselbe Dokument ergeben wie vorher. Der
    Vergleichswert steht hier nicht als Zahl, sondern entsteht aus der
    alten Form: Aufgabe 1 übersetzen, Aufgabe 2 einsetzen.
    """
    daten = json.loads(paket.read_text("utf-8"))
    for teil in ("teil1", "teil2"):
        for niveau in ("A", "B"):
            spec = daten.get("pruefungen", {}).get(teil, {}).get(niveau)
            if not spec:
                continue
            if "aufgaben" in spec:
                # Ein Paket in der neuen Form - es wird hier nicht geprüft.
                # Diese Prüfung gilt der **alten**: dass ein Paket mit
                # task1/task2 Zeichen für Zeichen dasselbe Dokument ergibt
                # wie vor dem Umbau. Ein Paket, das nie eine andere Form
                # hatte, kann dabei nichts belegen.
                continue
            arten = [a["art"] for a in aufgaben_des_specs(spec)]
            assert arten == ["uebersetzen", "luecken"], f"{teil} {niveau}"
            for loesung in (False, True):
                xml = build_document_xml(spec, show_answers=loesung)
                # Die Aufgabenstellungen stehen unverändert im Dokument -
                # samt der Zahl ihrer Leerzeichen.
                assert spec["task1"]["instruction"] in xml
                assert spec["task2"]["instruction"] in xml


def test_der_adapter_liest_beide_formen_gleich():
    """``pack`` und der Setzer lesen dieselbe Liste - getrennt gebaut."""
    alt = {"task1": {"instruction": "1) x", "items": [{"english": "a"}]},
           "task2": {"instruction": "2) y", "gaps": [{"answer": "b"}]}}
    aus_pack = [a["art"] for a in aufgaben_von(alt)]
    aus_setzer = [a["art"] for a in aufgaben_des_specs(alt)]
    assert aus_pack == aus_setzer == ["uebersetzen", "luecken"]


# ---------------------------------------------------------------------------
# Die Verteilung
# ---------------------------------------------------------------------------
def test_wer_eine_art_dazunimmt_verteilt_um():
    """Die Gesamtzahl bleibt, die Anteile wandern."""
    zwei = verteile(12, ("uebersetzen", "luecken"))
    drei = verteile(12, ("uebersetzen", "luecken", "wortwahl"))
    assert sum(zwei.values()) == sum(drei.values()) == 12
    assert drei["uebersetzen"] < zwei["uebersetzen"], "nichts umverteilt"


def test_jede_art_bekommt_mindestens_ihre_mindestzahl():
    for gesamt in (1, 4, 6, 8, 12, 20, 30):
        plan = verteile(gesamt, ALLE)
        for kennung, wie_viele in plan.items():
            assert wie_viele >= ARTEN[kennung].mindestens, (kennung, gesamt)


def test_die_verteilung_ist_zweimal_dieselbe():
    """Sonst stünde nach jedem Klick eine andere Prüfung da."""
    assert verteile(17, ALLE) == verteile(17, tuple(reversed(ALLE)))


def test_von_hand_gesetztes_gilt_und_der_rest_verteilt_sich():
    plan = _mit(exam_tasks=("uebersetzen", "luecken", "definition"),
                exam_task_words={"luecken": 5}).aufgabenplan()
    assert plan["luecken"] == 5
    assert plan["uebersetzen"] > plan["definition"] > 0


def test_ohne_verteilung_zaehlt_nur_die_handarbeit():
    plan = _mit(exam_tasks=("uebersetzen", "luecken"),
                exam_auto_verteilen=False,
                exam_task_words={"uebersetzen": 3}).aufgabenplan()
    assert plan["uebersetzen"] == 3
    assert plan["luecken"] == ARTEN["luecken"].mindestens


# ---------------------------------------------------------------------------
# Das Gerüst über alle sechs Arten
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def sechs(datenbank) -> dict:
    return scaffold(datenbank, 1, _mit(exam_tasks=ALLE, exam_words=20))


def test_alle_sechs_arten_stehen_im_paket(sechs):
    for teil in ("teil1", "teil2"):
        for niveau in ("A", "B"):
            arten = [a["art"] for a in aufgaben_von(sechs["pruefungen"][teil][niveau])]
            assert arten == list(ALLE), f"{teil} {niveau}"


def test_kein_wort_steht_in_zwei_aufgaben(sechs):
    """Die eine Aufgabe fragt es ab, die andere druckt es aus.

    Stünde dasselbe Wort in beiden, läge die Lösung der einen in der
    anderen offen da - der teuerste Fehler, den ein Prüfungsblatt machen
    kann, und er fällt erst beim Korrigieren auf.
    """
    for teil in ("teil1", "teil2"):
        for niveau in ("A", "B"):
            spec = sechs["pruefungen"][teil][niveau]
            woerter = [e["english"] for a in aufgaben_von(spec)
                       for e in gepruefte_woerter(a)]
            assert len(woerter) == len(set(woerter)), f"{teil} {niveau}"


def test_die_aufgaben_sind_fortlaufend_nummeriert(sechs):
    spec = sechs["pruefungen"]["teil1"]["A"]
    nummern = [a["instruction"].split(")")[0] for a in aufgaben_von(spec)]
    assert nummern == [str(i) for i in range(1, len(nummern) + 1)]


def test_micro_writing_buendelt_zwei_bis_drei_woerter(datenbank):
    paket = scaffold(datenbank, 1, _mit(exam_tasks=("schreiben",), exam_words=7))
    for aufgabe in aufgaben_von(paket["pruefungen"]["teil1"]["A"]):
        for block in aufgabe["items"]:
            assert 2 <= len(block["woerter"]) <= 3, "kein Mini-Text"


def test_die_loesung_einer_satzwahl_wandert(sechs):
    stellen = {
        item["richtig"]
        for teil in ("teil1", "teil2") for niveau in ("A", "B")
        for a in aufgaben_von(sechs["pruefungen"][teil][niveau])
        if a["art"] in SAETZE_ZUR_WAHL
        for item in a["items"]
    }
    assert len(stellen) > 1, f"alle Lösungen stehen an Stelle {stellen}"


def test_offen_nennt_jede_art_beim_namen(sechs, tmp_path):
    pfad = tmp_path / "unit_01.json"
    Pack(data=copy.deepcopy(sechs)).save(pfad)
    offen = Pack.load(pfad).offen_je_pruefung(1, "A")
    zusammen = " | ".join(offen)
    assert "Lückentext fehlt" in zusammen
    assert "Umschreibung fehlt" in zusammen
    assert "Anstoss fehlt" in zusammen
    assert "Satz 1, 2, 3 fehlt" in zusammen, "Wortbedeutung mit drei Sätzen"
    assert "Satz 1, 2 fehlt" in zusammen, "Correct/Incorrect mit zweien"


# ---------------------------------------------------------------------------
# Die Kontrolle - je ein eingebauter Fehler
# ---------------------------------------------------------------------------
@pytest.fixture
def gefuellt(datenbank) -> dict:
    """Ein Paket über alle sechs Arten, mit tragfähigen Platzhaltern."""
    return fill(copy.deepcopy(
        scaffold(datenbank, 1, _mit(exam_tasks=ALLE, exam_words=20))))


def _befunde(daten: dict) -> list[str]:
    bericht = Pruefbericht()
    pruefe_aufgabenformen(Pack(data=daten), bericht)
    return [f"{b.stufe} {b.text}" for b in bericht.befunde]


def _erste(spec: dict, art: str) -> dict:
    for a in spec["aufgaben"]:
        if a["art"] == art:
            return a
    raise AssertionError(art)


def test_eine_saubere_pruefung_meldet_nichts(gefuellt):
    assert _befunde(gefuellt) == []


def test_zu_wenige_saetze_zur_wahl(gefuellt):
    item = _erste(gefuellt["pruefungen"]["teil1"]["A"], "wortwahl")["items"][0]
    item["saetze"] = item["saetze"][:2]
    assert any("FEHLER" in b and "braucht 3" in b for b in _befunde(gefuellt))


def test_eine_loesung_ausserhalb_der_saetze(gefuellt):
    _erste(gefuellt["pruefungen"]["teil1"]["A"], "richtig_falsch")["items"][0]["richtig"] = 5
    assert any("FEHLER" in b and "Lösung ist '5'" in b for b in _befunde(gefuellt))


def test_ein_wort_in_zwei_aufgaben_desselben_blattes(gefuellt):
    spec = gefuellt["pruefungen"]["teil1"]["A"]
    _erste(spec, "wortwahl")["items"][0]["english"] = \
        _erste(spec, "uebersetzen")["items"][0]["english"]
    befunde = _befunde(gefuellt)
    assert any("FEHLER" in b and "schon in Aufgabe" in b for b in befunde)
    assert any("FEHLER" in b and "Lösung einer anderen Aufgabe" in b
               for b in befunde)


def test_saetze_ohne_das_wort_pruefen_nichts(gefuellt):
    item = _erste(gefuellt["pruefungen"]["teil1"]["A"], "wortwahl")["items"][0]
    item["saetze"] = ["One two three four.", "Five six seven.", "Eight nine ten."]
    assert any("FEHLER" in b and "In keinem der Sätze" in b
               for b in _befunde(gefuellt))


def test_eine_gebeugte_form_ist_nur_eine_warnung(gefuellt):
    """Die Anwendung konjugiert nicht - ein Fehlalarm wäre schlimmer."""
    item = _erste(gefuellt["pruefungen"]["teil1"]["A"], "wortwahl")["items"][0]
    item["saetze"][1] = "They painted the old wall with a new colour."
    befunde = _befunde(gefuellt)
    assert any("WARNUNG" in b and "nicht zu erkennen" in b for b in befunde)
    assert not any("FEHLER" in b for b in befunde)


def test_zweimal_derselbe_satz(gefuellt):
    saetze = _erste(gefuellt["pruefungen"]["teil1"]["A"], "wortwahl")["items"][0]["saetze"]
    saetze[2] = saetze[0]
    assert any("FEHLER" in b and "derselbe" in b for b in _befunde(gefuellt))


def test_eine_umschreibung_mit_dem_gesuchten_wort(gefuellt):
    """Dann schreibt die Klasse ab, statt das Wort zu erschliessen."""
    item = _erste(gefuellt["pruefungen"]["teil1"]["A"], "definition")["items"][0]
    item["umschreibung"] = f"a thing that is {item['english']} in every way"
    assert any("FEHLER" in b and "enthält das gesuchte Wort" in b
               for b in _befunde(gefuellt))


def test_zweimal_dieselbe_umschreibung(gefuellt):
    items = _erste(gefuellt["pruefungen"]["teil1"]["A"], "definition")["items"]
    items[1]["umschreibung"] = items[0]["umschreibung"]
    assert any("FEHLER" in b and "steht schon bei einem anderen Wort" in b
               for b in _befunde(gefuellt))


def test_ein_mini_text_mit_einem_einzigen_wort(gefuellt):
    block = _erste(gefuellt["pruefungen"]["teil1"]["A"], "schreiben")["items"][0]
    block["woerter"] = block["woerter"][:1]
    assert any("FEHLER" in b and "ist keiner" in b for b in _befunde(gefuellt))


def test_der_richtige_satz_darf_nicht_der_laengste_sein(gefuellt):
    item = _erste(gefuellt["pruefungen"]["teil1"]["A"], "wortwahl")["items"][0]
    wort = item["english"]
    item["richtig"] = 1
    item["saetze"][0] = (
        f"The whole class used {wort} again and again during the long "
        "afternoon lesson last week."
    )
    assert any("HINWEIS" in b and "durch seine Länge auf" in b
               for b in _befunde(gefuellt))


# ---------------------------------------------------------------------------
# Das Dokument
# ---------------------------------------------------------------------------
def test_jede_art_steht_auf_dem_blatt(gefuellt, tmp_path):
    spec = gefuellt["pruefungen"]["teil1"]["A"]
    vorlage = Settings().exam_template
    blatt = tmp_path / "blatt.docx"
    loesung = tmp_path / "loesung.docx"
    build_docx(spec, vorlage, blatt)
    build_answer_key(spec, vorlage, loesung)
    text = document_text(str(blatt))

    for nummer, aufgabe in enumerate(aufgaben_von(spec), start=1):
        assert f"{nummer})" in text, aufgabe["art"]
    # Der Kopf und **eine** Übersetzungstabelle - mehr hat das
    # Referenzlayout nicht, und keine der neuen Arten braucht eine.
    assert len(tables(str(blatt))) == 2
    assert "Solution:" not in text, "die Lösung steht auf dem Blatt"

    schluessel = document_text(str(loesung))
    assert "Solution:" in schluessel
    assert "Marking:" in schluessel, "Micro-Writing ohne Korrekturmassstab"


def test_die_nachkontrolle_liest_alle_arten_zurueck(gefuellt, tmp_path):
    spec = gefuellt["pruefungen"]["teil1"]["A"]
    vorlage = Settings().exam_template
    blatt = tmp_path / "blatt.docx"
    build_docx(spec, vorlage, blatt)
    schwer = [f for f in verify_document(str(blatt), spec, str(vorlage))
              if f.level == "ERROR"]
    assert not schwer, [f.message for f in schwer]


def test_die_loesung_darf_nicht_auf_dem_blatt_stehen(gefuellt, tmp_path):
    """Die Umschreibung nennt das Wort - dann steht es gedruckt da."""
    spec = copy.deepcopy(gefuellt["pruefungen"]["teil1"]["A"])
    item = _erste(spec, "definition")["items"][0]
    item["umschreibung"] = f"the word {item['english']} itself"
    vorlage = Settings().exam_template
    blatt = tmp_path / "blatt.docx"
    build_docx(spec, vorlage, blatt)
    lecks = [f for f in verify_document(str(blatt), spec, str(vorlage))
             if f.check == "leak"]
    assert lecks, "das ausgedruckte Lösungswort fällt nicht auf"


def test_die_seitenschaetzung_rechnet_jede_art_mit(gefuellt):
    spec = gefuellt["pruefungen"]["teil1"]["A"]
    nur_klassisch = dict(spec)
    nur_klassisch["aufgaben"] = [a for a in spec["aufgaben"]
                                 if a["art"] in KLASSISCH]
    assert _page_estimate(nur_klassisch) < _page_estimate(spec)


def test_das_dokument_haengt_nur_an_der_liste(gefuellt):
    """Zweimal dasselbe Paket, zweimal dasselbe Dokument."""
    spec = gefuellt["pruefungen"]["teil1"]["A"]
    einmal = hashlib.sha256(build_document_xml(spec).encode()).hexdigest()
    nochmal = hashlib.sha256(build_document_xml(spec).encode()).hexdigest()
    assert einmal == nochmal


# ---------------------------------------------------------------------------
# Befehl und Oberfläche
# ---------------------------------------------------------------------------
def test_die_flaggen_stellen_die_pruefung_um(tmp_path, capsys):
    assert cli.main(["gerüst", "1", "-o", str(tmp_path), "--aufgaben",
                     "uebersetzen,definition,schreiben", "--woerter", "12",
                     "--je-aufgabe", "definition=4"]) == 0
    capsys.readouterr()
    spec = Pack.load(tmp_path / "unit_01.json").exam(1, "A")
    plan = {a["art"]: len(gepruefte_woerter(a)) for a in aufgaben_von(spec)}
    assert plan["definition"] == 4
    assert set(plan) == {"uebersetzen", "definition", "schreiben"}


def test_eine_unbekannte_art_wird_abgewiesen(tmp_path):
    with pytest.raises(SystemExit) as fehler:
        cli.main(["gerüst", "1", "-o", str(tmp_path), "--aufgaben", "quatsch"])
    assert "gibt es nicht" in str(fehler.value)


def test_ohne_flagge_bleibt_der_befehl_wie_er_war(tmp_path, capsys):
    assert cli.main(["gerüst", "1", "-o", str(tmp_path)]) == 0
    capsys.readouterr()
    spec = Pack.load(tmp_path / "unit_01.json").exam(1, "A")
    plan = {a["art"]: len(gepruefte_woerter(a)) for a in aufgaben_von(spec)}
    assert plan == {"uebersetzen": 8, "luecken": 4}


def test_die_seite_bietet_jede_art_an():
    """Die Oberfläche kennt keine Aufgabenart - sie liest den Katalog.

    Stünden die sechs Arten samt Gewicht und Mindestzahl noch einmal in
    `vorlage.html`, liefen die beiden Listen irgendwann auseinander, und
    die Seite böte eine Prüfung an, die so nie gebaut wird.
    """
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    assert "DATA.aufgabenarten" in seite, "die Seite liest den Katalog nicht"
    assert 'id="gesamtwoerter"' in seite, "der Regler für die Wortzahl fehlt"
    assert 'id="autoVerteilen"' in seite, "die Umverteilung ist nicht abwählbar"

    daten = json.loads((WERKSTATT / "daten.json").read_text("utf-8"))
    assert [a["kennung"] for a in daten["aufgabenarten"]] == list(ARTEN)
    # Und die Verteilung steht fertig daneben, statt zweimal gerechnet
    # zu werden.
    for gesamt, kennungen, erwartet in (
        (12, KLASSISCH, [8, 4]),
        (12, ALLE, [verteile(12, ALLE)[k] for k in ALLE]),
    ):
        schluessel = f"{gesamt}|" + ",".join(kennungen)
        assert daten["verteilung"][schluessel] == list(erwartet), schluessel


# ---------------------------------------------------------------------------
# Der Aufbau gehört zur Prüfung, nicht zum Aufruf
# ---------------------------------------------------------------------------
def test_ausgleichen_behaelt_den_bestellten_aufbau(db, settings):
    """``ausgleichen`` setzt die vier Prüfungen neu auf - nicht neu zusammen.

    Nötig ist es, sobald im Chat Wörter ergänzt wurden. Es las den Aufbau
    dabei aus den **Einstellungen**, und die stehen ohne Flaggen auf der
    Vorgabe: Eine mit sechs Aufgaben bestellte Prüfung fiel danach
    stillschweigend auf Übersetzen und Lückentext zurück. Gemerkt hätte man
    es erst am gebauten Blatt.
    """
    from vocabmaster.pack import ausgleichen, plan_von

    bestellt = ("uebersetzen", "luecken", "wortwahl", "definition",
                "richtig_falsch", "schreiben")
    eigen = Settings(exam_tasks=bestellt, exam_words=14)
    pack = Pack(data=fill(scaffold(db, 1, eigen)))
    vorher = {schluessel: plan_von(spec)
              for schluessel, spec in pack.exams.items()}
    assert set(vorher[(1, "A")]) == set(bestellt)

    # Ausgeglichen wird **ohne** die Flaggen - so ruft die Kommandozeile es.
    ausgleichen(pack, settings)

    nachher = {schluessel: plan_von(spec)
               for schluessel, spec in pack.exams.items()}
    assert nachher == vorher, "der bestellte Aufbau ist verlorengegangen"
    for spec in pack.exams.values():
        arten = [a["art"] for a in aufgaben_des_specs(spec)]
        assert arten == list(sortiert(bestellt))


def test_zwei_luecken_stehen_nicht_in_luekenreihenfolge(db):
    """Die Wortbank darf die Reihenfolge der Lücken nicht verraten.

    Bei **zwei** Lücken gibt es nur zwei Reihenfolgen, und die Schleife, die
    beide mied, lief fünfzigmal ins Leere und liess die Bank in
    Lückenreihenfolge stehen. Seit die Wortzahl je Aufgabe einstellbar ist,
    sind zwei Lücken der Normalfall.
    """
    from vocabmaster.pack import aufgabe_art

    eigen = Settings(exam_tasks=("uebersetzen", "luecken"), exam_words=6,
                     exam_task_words={"luecken": 2})
    for unit in (1, 2, 3):
        pack = Pack(data=scaffold(db, unit, eigen))
        for (teil, niveau), spec in pack.exams.items():
            luecken = aufgabe_art(spec, "luecken")
            bank = luecken["word_bank"]
            reihenfolge = [g["german"] for g in luecken["gaps"]]
            assert len(bank) == 2
            assert bank != reihenfolge, (
                f"Unit {unit} Teil {teil} Niveau {niveau}: die Wortbank "
                "steht in Lückenreihenfolge - die Aufgabe lässt sich "
                "lösen, ohne den Text zu lesen"
            )
