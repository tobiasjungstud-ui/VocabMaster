"""Der eXaminer-Bereich der Werkstatt: daneben, bestellend, nie selbst dort.

eXaminer ist die Prüfungsplattform der Schule. Die Seite erreicht sie nicht -
sie läuft in einem abgeschotteten Rahmen, und eXaminer verlangt eine
Anmeldung. Also sammelt der Bereich die Wahl und legt **einen** Auftrag ins
Auftragsbuch: Aufgaben schreiben, anlegen, daraus zwei Prüfungen machen
(Niveau A und B) und die beiden Links für den Safe Exam Browser zurückgeben.
Die Tests hier halten fest, dass das so bleibt - und dass der Bereich die
Werkstatt nicht berührt.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
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
            return körper[:körper.index("\n}\n") + 2]
    raise AssertionError(f"{name} fehlt")


def _konstante(name: str) -> str:
    skript = _skript()
    körper = skript[skript.index(f"const {name} = "):]
    ende = "\n};" if körper[len(f"const {name} = ")] == "{" else "\n];"
    return körper[:körper.index(ende) + 3]


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
    assert 'id="reiterWerkstatt"\n            aria-selected="true"' in seite
    assert 'id="reiterExaminer"\n            aria-selected="false"' in seite


def test_die_werkstatt_zeichnet_den_examiner_nicht():
    """Eigener Zustand, eigenes Zeichnen: `alles()` kennt den Bereich nicht,
    und der Bereich zeichnet nur, wenn er offen ist."""
    seite = _seite()
    lauf = seite[seite.index("function alles()"):]
    assert "Ex" not in lauf[:lauf.index("\n")]
    assert 'if(ex.bereich !== "examiner") return;' in _funktion("zeichneExaminer")
    assert '$("ex' not in _funktion("zeichneSichtbarkeit")


# ---------------------------------------------------------------------------
# Ein Knopf für Aufgaben und Prüfungen
# ---------------------------------------------------------------------------
def test_aufgaben_und_pruefung_sind_ein_auftrag():
    """Kein getrenntes „Prüfung erstellen" aus vorhandenen Aufgaben mehr:
    Ein Knopf bestellt alles, der Chat hält die Reihenfolge ein."""
    skript = _skript()
    aktionen = _konstante("EX_AKTIONEN")
    assert re.findall(r"^\s*(\w+):\[", aktionen, re.M) == ["erstellen", "korrektur"]
    assert 'art:"examiner-pruefungen"' in skript
    for alt in ('art:"examiner-aufgabe"', 'art:"examiner-pruefung"', 'id="exAufPruefung"'):
        assert alt not in _seite(), f"{alt} ist zurück"
    befehl = _text(_funktion("exErstellenBefehl"))
    # Die Reihenfolge: schreiben, Aufgaben anlegen, Prüfungen anlegen, Links.
    schritte = [befehl.index(s) for s in ("1. Je Niveau", "2. In eXaminer", "3. Zwei Prüfungen",
                                          "4. Je Prüfung den Link")]
    assert schritte == sorted(schritte)


def test_immer_zwei_pruefungen():
    daten = _funktion("exErstellenDaten")
    assert 'pruefungen:{A:exPruefungDaten("A"), B:exPruefungDaten("B")}' in daten
    assert "Erwartet: 2 Prüfungen" in _text(_funktion("exErstellenBefehl"))


TYPEN = ["Lückentext", "Text", "Aufsatz", "Single Choice", "Multiple Choice",
         "K-Prim", "Zuordnung", "Reihenfolge", "Aufgabengruppe"]


def test_neun_aufgabentypen_und_der_lueckentext_ist_ausgebaut():
    katalog = _konstante("EX_TYPEN")
    assert re.findall(r'name:"([^"]+)"', katalog) == TYPEN
    assert re.findall(r'kennung:"(\w+)"[^\n]*ausgebaut:true', katalog) == ["lueckentext"]


def test_aufgabe_eins_steht_offen_und_plus_bringt_weitere():
    """Aufgabe 1 ist aufgeklappt; mit ＋ kommt die nächste dazu."""
    assert "offen:new Set([0])" in _skript()
    assert 'ex.offen.has(i) ? " open" : ""' in _funktion("zeichneExAufgaben")
    assert 'id="exPlus"' in _bereich()
    plus = _skript()[_skript().index('$("exPlus").addEventListener'):]
    assert "ex.aufgaben.push(" in plus[:plus.index("});")]


def test_die_woerter_werden_auf_die_aufgaben_verteilt():
    """Kein Wort in zwei Aufgaben; die Zahl je Aufgabe folgt dem Typ."""
    assert "kein Wort in zwei Aufgaben" in _text(_funktion("exErstellenBefehl"))
    katalog = _konstante("EX_TYPEN")
    assert len(re.findall(r"gewicht:\d+, mindestens:\d+", katalog)) == len(TYPEN)
    # Stimmt die Summe nicht, sagt die Seite es laut.
    einwand = _funktion("exErstellenEinwand")
    assert "summe !== gesamt" in einwand and "v[i] < min" in einwand


def test_die_zahl_der_geprueften_woerter_steht_auf_der_seite():
    assert 'id="exAnzahl"' in _bereich()
    assert "ex.anzahl, Math.min(ex.vorlage.schwer, ex.anzahl)" in _funktion("exVorbelegung")


def _verteilen_in_node(faelle: list[dict]) -> list[list[int]]:
    knoten = shutil.which("node")
    if not knoten:
        pytest.skip("node fehlt - die Rechnung der Seite lässt sich nicht ausführen")
    skript = _funktion("exVerteilen") + (
        "\nconst f = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n"
        "process.stdout.write(JSON.stringify(f.map(x => exVerteilen(x.gesamt, x.aufgaben))));\n")
    lauf = subprocess.run([knoten, "-e", skript], input=json.dumps(faelle),
                          capture_output=True, text=True, check=True)
    return json.loads(lauf.stdout)


def test_die_verteilung_folgt_gewicht_mindestzahl_und_festem():
    """Die Rechnung der Seite, ausgeführt: proportional zum Gewicht, jede
    Mindestzahl erfüllt, Festes kommt aus der Gesamtzahl, nie obendrauf."""
    def a(gewicht, mindestens=1, fest=None):
        return {"gewicht": gewicht, "mindestens": mindestens, "fest": fest}
    faelle = [
        {"gesamt": 12, "aufgaben": [a(2, 2)]},                    # nur Lückentext
        {"gesamt": 12, "aufgaben": [a(2, 2), a(3)]},              # Lückentext + Text
        {"gesamt": 12, "aufgaben": [a(2, 2), a(1, 3)]},           # + Reihenfolge
        {"gesamt": 12, "aufgaben": [a(2, 2), a(1, 2), a(1, 3)]},  # Aufsatz, Reihenfolge
        {"gesamt": 12, "aufgaben": [a(2, 2), a(3, 1, 7)]},        # Text festgelegt
        {"gesamt": 10, "aufgaben": [a(2, 2), a(2, 3), a(3)]},
    ]
    z = _verteilen_in_node(faelle)
    assert z[0] == [12]
    assert z[1] == [5, 7]                  # 12 * 2/5 und 12 * 3/5
    assert z[2] == [8, 4]
    assert z[3][1] >= 2 and z[3][2] >= 3 and sum(z[3]) == 12
    assert z[4] == [5, 7]
    for fall, zahlen in zip(faelle, z, strict=True):
        assert sum(zahlen) == fall["gesamt"]
        assert all(n >= x["mindestens"] for n, x in zip(zahlen, fall["aufgaben"], strict=True))
    assert _verteilen_in_node(faelle) == z, "zweimal dieselbe Eingabe, zweimal dasselbe"


# ---------------------------------------------------------------------------
# Die Vorlage
# ---------------------------------------------------------------------------
ANKUENDIGUNG = (
    "English Vocabulary Test (Datum: {datum}). Unit {unit} Part {part}.\n"
    "If you are Niveau A, copy this link into your browser:\n{link_A}\n"
    "If you are Niveau B, copy this link into your browser:\n{link_B}"
)


def test_die_vorlage_steht_auf_zwoelf_woertern_und_drei_mittelschweren():
    vorlage = _konstante("EX_VORLAGE_STANDARD")
    assert "woerter:12, schwer:3," in vorlage
    assert 'aufgaben:[{typ:"lueckentext", fest:null' in vorlage


def test_der_text_zum_austeilen_hat_die_verlangte_form():
    vorlage = _konstante("EX_VORLAGE_STANDARD")
    text = re.search(r'text:((?:"[^"]*"\s*\+?\s*)+),', vorlage).group(1)
    teile = re.findall(r'"([^"]*)"', text)
    assert "".join(teile).replace("\\n", "\n") == ANKUENDIGUNG


def test_die_vorlage_liegt_im_auftragsbuch_und_wird_geprueft():
    """Sie gilt auf jedem Gerät und der Chat kann sie lesen - aber sie kommt
    von aussen, also wird jeder Wert geprüft, bevor er gilt."""
    assert 'doc("examiner/vorlage").set(' in _funktion("exVorlageSpeichern")
    start = _funktion("starteExaminerDaten")
    assert 'doc.id === "vorlage"' in start and "exVorlagePruefen(vorlage)" in start
    pruefen = _funktion("exVorlagePruefen")
    assert "exZahl(r.woerter, 2, 30" in pruefen and "exZahl(r.schwer, 0, woerter" in pruefen
    # Ohne die Platzhalter für die Links wäre der Text nutzlos.
    assert "{link_A}" in _funktion("exVorlageSpeichern")


# ---------------------------------------------------------------------------
# Die Wortwahl: A die schwersten, B die zugänglichsten und drei mittelschwere
# ---------------------------------------------------------------------------
def _wortwahl_in_node(eingaben: list[dict]) -> list[dict]:
    knoten = shutil.which("node")
    if not knoten:
        pytest.skip("node fehlt - die Rechnung der Seite lässt sich nicht ausführen")
    skript = _funktion("exWortwahl") + (
        "\nconst eingaben = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n"
        "process.stdout.write(JSON.stringify(eingaben.map(e => "
        "exWortwahl(e.teil, e.echtA, e.echtB, e.n, e.k))));\n")
    lauf = subprocess.run([knoten, "-e", skript], input=json.dumps(eingaben),
                          capture_output=True, text=True, check=True)
    return json.loads(lauf.stdout)


def test_die_wortwahl_an_allen_listen(daten):
    """Die Rechnung der Seite, ausgeführt an jeder Liste und jedem Part."""
    eingaben, wo = [], []
    for db in daten["datenbanken"]:
        for u in db["units"]:
            for li in u["listen"]:
                for teil in (1, 2):
                    eingaben.append({
                        "teil": [w for w in li["woerter"] if w["test"] == teil],
                        "echtA": li["echt"][f"t{teil}A"]["woerter"],
                        "echtB": li["echt"][f"t{teil}B"]["woerter"],
                        "n": 12, "k": 3})
                    wo.append((db["name"], u["unit"], li["version"], teil))
    assert eingaben
    for ort, e, wahl in zip(wo, eingaben, _wortwahl_in_node(eingaben), strict=True):
        note = {w["en"]: w["score"] for w in e["teil"]}
        a, b, mittel = wahl["A"], wahl["B"], wahl["mittel"]
        assert len(a) == 12 and len(b) == 12, ort
        assert len(set(a)) == 12 and len(set(b)) == 12, ort
        # B ist kein Ausschnitt von A - keine Prüfung verrät die andere.
        assert not set(a) & set(b), ort
        assert len(mittel) == 3 and set(mittel) <= set(b), ort
        # A nimmt die schwersten: Kein Wort ausserhalb von A ist schwerer als
        # das leichteste in A - ausser die Auswahl der Anwendung hat es aus
        # gutem Grund weggelassen und A ist mit ihr voll geworden.
        leichte = [w for w in b if w not in mittel]
        assert min(note[w] for w in mittel) >= max(note[w] for w in leichte), ort
        assert sum(note[w] for w in a) / 12 > sum(note[w] for w in b) / 12, ort
        # Die Wörter der Anwendungsauswahl gehen vor.
        assert set(a) <= set(e["echtA"]) or len(set(e["echtA"])) < 12, ort


def test_die_wortwahl_haelt_sich_an_die_vorlage():
    """Andere Zahlen in der Vorlage, andere Prüfungen - und nie mehr
    mittelschwere als Wörter."""
    teil = [{"en": f"w{i:02d}", "score": i / 3} for i in range(30)]
    alle = [w["en"] for w in teil]
    wahl = _wortwahl_in_node([
        {"teil": teil, "echtA": alle[-12:], "echtB": alle[:12], "n": 10, "k": 2},
        {"teil": teil, "echtA": alle[-12:], "echtB": alle[:12], "n": 12, "k": 0},
        {"teil": teil, "echtA": alle[-12:], "echtB": alle[:12], "n": 4, "k": 9},
        {"teil": teil, "echtA": alle[-12:], "echtB": alle[:12], "n": 16, "k": 3},
    ])
    assert len(wahl[0]["A"]) == 10 and len(wahl[0]["mittel"]) == 2
    assert wahl[0]["A"] == alle[-10:][::-1]
    assert wahl[1]["mittel"] == [] and set(wahl[1]["B"]) == set(alle[:12])
    assert len(wahl[2]["B"]) == 4 and len(wahl[2]["mittel"]) == 4
    # 30 Wörter reichen nicht für zweimal 16: B wird mit den zugänglichsten
    # aus A aufgefüllt, statt kürzer zu werden.
    assert len(wahl[3]["A"]) == 16 and len(wahl[3]["B"]) == 16
    assert set(wahl[3]["geteilt"]) == set(wahl[3]["A"]) & set(wahl[3]["B"])
    assert len(wahl[3]["geteilt"]) == 2


# ---------------------------------------------------------------------------
# Die Links für den Safe Exam Browser
# ---------------------------------------------------------------------------
def test_die_links_kommen_ins_tool():
    befehl = _text(_funktion("exErstellenBefehl"))
    assert "Safe Exam Browser" in befehl
    assert "ergebnis.links.A und ergebnis.links.B" in befehl
    links = _funktion("exLinks")
    assert "ergebnis.links" in links.replace("quelle.ergebnis && quelle.ergebnis.links", "ergebnis.links")
    # Auch aus einem späteren Auftrag „Links holen" mit Bezug auf diesen.
    assert 'x.art === "examiner-links" && x.bezug === e.id' in links


def test_ein_link_wird_als_text_gezeigt_nie_als_verweis():
    """Ein Link kommt von aussen. Er steht als Text da, eine Zeile, und
    wird nie als Ersetzungsmuster gelesen."""
    link = _funktion("exLink")
    assert r"/[\s<>\"]/" in link or '/[\\s<>"]/' in link
    ankuendigung = _funktion("exAnkuendigung")
    assert '.replace("{link_A}", () =>' in ankuendigung
    bereit = _funktion("zeichneExBereit")
    assert 'querySelector("pre").textContent = exAnkuendigung(e, links)' in bereit
    assert "href" not in bereit


def test_nicht_freischalten():
    """Der Chat legt an und speichert. Entsteht der Link erst beim
    Freischalten, wartet er auf die Lehrperson."""
    befehl = _text(_funktion("exErstellenBefehl"))
    assert "Nicht freischalten" in befehl and "«wartet»" in befehl
    assert "Nichts freischalten" in _text(_funktion("exLinksHolenDaten"))


# ---------------------------------------------------------------------------
# Bestellen, nicht selbst tun
# ---------------------------------------------------------------------------
def test_alle_auftraege_gehen_durch_das_auftragsbuch():
    """Derselbe Weg wie jeder Auftrag: `ausloesen` legt ab und klingelt.
    Direkt geschrieben wird nur die eigene Vorlage."""
    skript = _skript()
    assert re.findall(r'\.doc\("([^"]+)"\)', skript) == ["examiner/vorlage"]
    assert "await ausloesen(daten, kennung, knopf, sagen);" in _funktion("exBestellen")
    for kennung in ("ex-pruefungen", "ex-korrektur", "ex-abgleich", "ex-links"):
        assert f'"{kennung}"' in skript, kennung


def test_die_seite_greift_nie_selbst_nach_examiner():
    skript = _skript()
    for zugriff in ("fetch(", "XMLHttpRequest", "window.open", "WebSocket"):
        assert zugriff not in skript, zugriff


def test_kein_knopf_wird_abgeschaltet():
    """Ein Einwand antwortet laut und setzt den Cursor ins Feld - auch in
    einer zugeklappten Aufgabe."""
    skript = _skript()
    assert not re.search(r"\.disabled\s*=\s*true", skript)
    stockt = _funktion("exStockt")
    assert "focus()" in stockt and "ex-merken" in stockt and "d.open = true" in stockt
    bestellen = _funktion("exBestellen")
    assert "if(einwand){ exStockt(einwand, statusId); return; }" in bestellen
    assert "if(!verbunden())" in bestellen and "clipboard.writeText" in bestellen


def test_das_auftragsbuch_kennt_die_examiner_auftraege():
    assert "istExaminerAuftrag(e)" in _funktion("auftragsTitel")
    assert "zeichneExAuftraege();" in _funktion("zeichneBuch")


def test_der_waechter_gilt_auch_hier():
    uhr = _funktion("zeichneExUhr")
    assert "wache(e, jetzt)" in uhr
    assert 'data-tun="klingeln"' in uhr and 'data-tun="kopieren"' in uhr
    assert "setInterval(zeichneExUhr, 1000);" in _seite()


# ---------------------------------------------------------------------------
# Was der Chat darf und was nicht
# ---------------------------------------------------------------------------
def test_die_korrektur_bereitet_voreingestellt_nur_vor():
    skript = _skript()
    assert 'modus:"vorbereiten"' in skript
    modi = _konstante("EX_MODI")
    assert modi.index('"vorbereiten"') < modi.index('"speichern"')
    assert "In eXaminer nichts speichern" in _text(_funktion("exKorrekturDaten"))


def test_keine_zugangsdaten_und_keine_namen_im_auftragsbuch():
    for name in ("exErstellenBefehl", "exLinksHolenDaten"):
        assert "Zugangsdaten gehören nie ins Auftragsbuch" in _text(_funktion(name)), name
    for name in ("exKorrekturDaten", "exAbgleichDaten"):
        assert "Namen von Schülerinnen und Schülern" in _text(_funktion(name)), name
    assert 'type="password"' not in _bereich()


def test_was_aus_examiner_kommt_wird_nur_gezeigt():
    start = _funktion("starteExaminerDaten")
    assert 'collection("examiner")' in start and 'doc.id === "pruefungen"' in start
    assert "esc(p.name" in _funktion("zeichneExKorrektur")
    assert 'querySelector("pre").textContent = text' in _funktion("exErgebnis")
