"""Der eXaminer-Bereich der Werkstatt: daneben, bestellend, nie selbst dort.

eXaminer ist die Prüfungsplattform der Schule. Die Seite erreicht sie nicht -
sie läuft in einem abgeschotteten Rahmen, und eXaminer verlangt eine
Anmeldung. Also sammelt der Bereich die Wahl und legt einen Auftrag ins
Auftragsbuch; der Chat führt ihn aus und schreibt zurück, was er in eXaminer
liest. Die Tests hier halten fest, dass das so bleibt - und dass der Bereich
die Werkstatt nicht berührt.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
WERKSTATT = WURZEL / "werkstatt"

pytestmark = pytest.mark.skipif(
    not (WERKSTATT / "daten.json").exists(), reason="keine Werkstatt-Daten"
)


def _seite() -> str:
    return (WERKSTATT / "vorlage.html").read_text("utf-8")


def _skript() -> str:
    """Der eXaminer-Teil des Skripts - von seinen Konstanten bis zum Start."""
    seite = _seite()
    anfang = seite.index("const EX_ADRESSE")
    ende = seite.index("starteExaminer();\n", anfang)
    return seite[anfang:ende]


def _funktion(name: str) -> str:
    seite = _seite()
    for kopf in (f"async function {name}(", f"function {name}("):
        if kopf in seite:
            körper = seite[seite.index(kopf):]
            return körper[:körper.index("\n}\n")]
    raise AssertionError(f"{name} fehlt")


def _text(körper: str) -> str:
    """Zusammengesetzte Zeichenketten des Quelltexts als ein Satz."""
    return re.sub(r'"\s*\+\s*"', "", körper)


def _bereich() -> str:
    seite = _seite()
    anfang = seite.index('<section class="examiner"')
    return seite[anfang:seite.index("\n  </section>\n", anfang)]


@pytest.fixture(scope="module")
def daten():
    return json.loads((WERKSTATT / "daten.json").read_text("utf-8"))


# ---------------------------------------------------------------------------
# Daneben, nicht darin
# ---------------------------------------------------------------------------
def test_der_bereich_steht_neben_der_werkstatt():
    """Die Werkstatt bleibt, wie sie war: eXaminer steht ausserhalb von
    Leiste und Arbeitsfläche und ist beim Öffnen verborgen."""
    seite = _seite()
    abschnitt = seite.index('<section class="examiner"')
    assert abschnitt > seite.index("</aside>") and abschnitt > seite.index("</main>")
    assert '<section class="examiner" id="examiner" role="tabpanel" ' \
           'aria-labelledby="exTitel" hidden>' in seite
    # Der Reiter der Werkstatt ist voreingestellt.
    assert 'id="reiterWerkstatt"\n            aria-selected="true"' in seite
    assert 'id="reiterExaminer"\n            aria-selected="false"' in seite


def test_die_werkstatt_zeichnet_den_examiner_nicht():
    """Eigener Zustand, eigenes Zeichnen: `alles()` kennt den Bereich nicht,
    und der Bereich zeichnet nur, wenn er offen ist."""
    seite = _seite()
    lauf = seite[seite.index("function alles()"):]
    assert "Ex" not in lauf[:lauf.index("\n")]
    assert 'if(ex.bereich !== "examiner") return;' in _funktion("zeichneExaminer")
    # Kein eXaminer-Feld in der Tabelle der Sichtbarkeit der Werkstatt.
    sicht = _funktion("zeichneSichtbarkeit")
    assert '$("ex' not in sicht


# ---------------------------------------------------------------------------
# Aufgabe erstellen
# ---------------------------------------------------------------------------
TYPEN = ["Lückentext", "Text", "Aufsatz", "Single Choice", "Multiple Choice",
         "K-Prim", "Zuordnung", "Reihenfolge", "Aufgabengruppe"]


def test_neun_aufgabentypen_und_der_lueckentext_ist_ausgebaut():
    skript = _skript()
    katalog = skript[skript.index("const EX_TYPEN = ["):]
    katalog = katalog[:katalog.index("];")]
    assert re.findall(r'name:"([^"]+)"', katalog) == TYPEN
    assert re.findall(r'kennung:"(\w+)"[^\n]*ausgebaut:true', katalog) == ["lueckentext"]
    assert 'typ:"lueckentext"' in skript, "voreingestellt ist der Lückentext"


def test_die_woerter_kommen_aus_der_pruefungsauswahl(daten):
    """Vorbelegt wird mit derselben Auswahl, die die Werkstatt unter
    „Prüfungen" zeigt - je Part und Niveau der gewählten Liste."""
    körper = _funktion("exVorbelegung")
    assert "li.echt" in körper and '"t" + ex.teil + ex.niveau' in körper
    # Und für jede Liste liegt diese Auswahl im selben Part der Liste.
    geprüft = 0
    for db in daten["datenbanken"]:
        for u in db["units"]:
            for li in u["listen"]:
                for teil in (1, 2):
                    part = {w["en"] for w in li["woerter"] if w["test"] == teil}
                    for niveau in ("A", "B"):
                        wahl = li["echt"].get(f"t{teil}{niveau}")
                        assert wahl and wahl["woerter"], (db["name"], u["unit"], li["version"], teil, niveau)
                        assert set(wahl["woerter"]) <= part
                        geprüft += 1
    assert geprüft


def test_getauscht_wird_nur_im_selben_part():
    assert "w.test === ex.teil" in _funktion("exPool")


def test_thema_und_unterthema_werden_vorgeschlagen(daten):
    """„EP3_Unit 8" und „Niveau A" - vor dem Anlegen änderbar."""
    kürzel = _funktion("exKuerzel")
    muster = re.search(r"/(\^EnglishPlus[^/]+)/i", kürzel).group(1)
    for db, erwartet in (("EnglishPlus3", "EP3"), ("EnglishPlus4", "EP4")):
        treffer = re.match(muster, db, re.I)
        assert treffer and "EP" + treffer.group(1) == erwartet
    vorschlag = _funktion("exVorschlag")
    assert 'exKuerzel() + "_" + exUnitname(u)' in vorschlag
    assert '"Niveau " + ex.niveau' in vorschlag
    # Von Hand Geändertes bleibt stehen.
    assert "if(!vonHand" in _funktion("exAblageNachziehen")
    for feld in ("exThema", "exUnterthema", "exTitelFeld"):
        assert f'id="{feld}"' in _bereich()


# ---------------------------------------------------------------------------
# Bestellen, nicht selbst tun
# ---------------------------------------------------------------------------
def test_alle_auftraege_gehen_durch_das_auftragsbuch():
    """Derselbe Weg wie jeder Auftrag: `ausloesen` legt ab und klingelt."""
    skript = _skript()
    assert "db.doc(" not in skript, "der Bereich schreibt am Auslöser vorbei"
    assert "await ausloesen(daten, kennung, knopf, sagen);" in _funktion("exBestellen")
    for art in ("aufgabe", "pruefung", "korrektur", "abgleich"):
        assert f'art:"examiner-{art}"' in skript, art
        assert f'"ex-{art}"' in skript, art


def test_die_seite_greift_nie_selbst_nach_examiner():
    skript = _skript()
    for zugriff in ("fetch(", "XMLHttpRequest", "window.open", "WebSocket"):
        assert zugriff not in skript, zugriff


def test_kein_knopf_wird_abgeschaltet():
    """Ein Einwand antwortet laut und setzt den Cursor ins Feld."""
    skript = _skript()
    assert not re.search(r"\.disabled\s*=\s*true", skript)
    stockt = _funktion("exStockt")
    assert "focus()" in stockt and "ex-merken" in stockt
    bestellen = _funktion("exBestellen")
    assert "if(einwand){ exStockt(einwand, statusId); return; }" in bestellen
    # Ohne Verbindung wird kopiert, statt den Klick verfallen zu lassen.
    assert "if(!verbunden())" in bestellen and "clipboard.writeText" in bestellen


def test_das_auftragsbuch_kennt_die_examiner_auftraege():
    assert "istExaminerAuftrag(e)" in _funktion("auftragsTitel")
    assert "zeichneExAuftraege();" in _funktion("zeichneBuch")


def test_der_waechter_gilt_auch_hier():
    """Wer im eXaminer-Bereich steht, sieht den Verlauf der Werkstatt nicht -
    und muss trotzdem sehen, wenn ein Auftrag hängt."""
    uhr = _funktion("zeichneExUhr")
    assert "wache(e, jetzt)" in uhr
    assert 'data-tun="klingeln"' in uhr and 'data-tun="kopieren"' in uhr
    assert "setInterval(zeichneExUhr, 1000);" in _seite()


# ---------------------------------------------------------------------------
# Was der Chat darf und was nicht
# ---------------------------------------------------------------------------
def test_die_korrektur_bereitet_voreingestellt_nur_vor():
    """Eine Note, die ohne Blick der Lehrperson in eXaminer steht, ist
    schneller geschrieben als zurückgenommen."""
    skript = _skript()
    assert 'modus:"vorbereiten"' in skript
    modi = skript[skript.index("const EX_MODI = ["):]
    assert modi.index('"vorbereiten"') < modi.index('"speichern"')
    assert "In eXaminer nichts speichern" in _text(_funktion("exKorrekturDaten"))


def test_eine_pruefung_wird_angelegt_nicht_freigegeben():
    """Freigeben und einer Klasse zuweisen tut die Lehrperson."""
    assert "nicht freigeben und keine Klasse zuweisen" in _text(_funktion("exPruefungDaten"))


def test_keine_zugangsdaten_und_keine_namen_im_auftragsbuch():
    for name in ("exAufgabeBefehl", "exPruefungDaten"):
        assert "Zugangsdaten gehören nie ins Auftragsbuch" in _text(_funktion(name)), name
    for name in ("exKorrekturDaten", "exAbgleichDaten"):
        assert "Namen von Schülerinnen und Schülern" in _text(_funktion(name)), name
    assert 'type="password"' not in _bereich()


def test_was_aus_examiner_kommt_wird_nur_gezeigt():
    """Die Listen schreibt der Chat nach `examiner/`; die Seite liest sie
    und setzt jeden Wert maskiert ein."""
    start = _funktion("starteExaminerDaten")
    assert 'collection("examiner")' in start
    assert 'doc.id === "aufgaben"' in start and 'doc.id === "pruefungen"' in start
    assert "esc(a.titel" in _funktion("zeichneExPruefung")
    assert "esc(p.name" in _funktion("zeichneExKorrektur")
    # Und das Ergebnis eines Auftrags geht als Text hinein, nie als Markup.
    assert 'querySelector("pre").textContent = text' in _funktion("exErgebnis")
