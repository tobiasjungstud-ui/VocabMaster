"""Die Oberfläche muss zeigen, was in den Paketen wirklich steht.

Der klassische Fehler ist hier, dass jemand ein Paket ändert und die
Oberfläche danach eine Auswahl anzeigt, die es so nicht mehr gibt. Die
Seite ist gebaut, nicht von Hand geschrieben - also lässt sich das prüfen,
indem die Daten neu erzeugt und verglichen werden.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
WERKSTATT = WURZEL / "werkstatt"
sys.path.insert(0, str(WERKSTATT))

pytestmark = pytest.mark.skipif(
    not (WERKSTATT / "daten.json").exists(), reason="keine Werkstatt-Daten"
)


@pytest.fixture
def frisch(db, settings):
    from export import baue

    return baue(WURZEL / "kuratiert", db, settings)


@pytest.fixture(scope="module")
def abgelegt():
    return json.loads((WERKSTATT / "daten.json").read_text("utf-8"))


def test_daten_sind_auf_dem_stand_der_pakete(frisch, abgelegt):
    """``werkstatt/daten.json`` ist gebaut - also muss es neu gebaut gleich sein."""
    assert frisch == abgelegt, (
        "werkstatt/daten.json ist veraltet - "
        "`python werkstatt/export.py` ausführen und mitcommitten."
    )


def test_angezeigte_auswahl_steht_so_in_den_paketen(abgelegt):
    """Jedes Wort der vier Prüfungen kommt in der Liste vor, die es zeigt.

    Je Unit kann es mehrere Vokabellisten geben (V1, V2, ...). Geprüft wird
    jede für sich - eine Prüfung von V2 darf nicht gegen V1 gehalten werden,
    das ist gerade der Fehler, den `listenbezug` verhindern soll.
    """
    for unit in abgelegt["units"]:
        assert unit["listen"], f"Unit {unit['unit']} ohne Vokabelliste"
        for li in unit["listen"]:
            wo = f"Unit {unit['unit']} V{li['version']}"
            for schluessel, auswahl in li["echt"].items():
                test = int(schluessel[1])
                liste = {w["en"] for w in li["woerter"] if w["test"] == test}
                fremd = [w for w in auswahl["woerter"] if w not in liste]
                assert not fremd, f"{wo} {schluessel}: {fremd}"
                offen = [w for w in auswahl["luecken"]
                         if w not in auswahl["woerter"]]
                assert not offen, f"{wo} {schluessel} Lücken: {offen}"


def test_jede_liste_hat_ihre_eigene_kennung(abgelegt):
    """V1, V2 ... müssen sich unterscheiden - sonst zeigt die Auswahl Unsinn."""
    for unit in abgelegt["units"]:
        versionen = [li["version"] for li in unit["listen"]]
        assert len(versionen) == len(set(versionen)), (
            f"Unit {unit['unit']}: doppelte Listenversion {versionen}"
        )
        abdruecke = [li["abdruck"] for li in unit["listen"] if li["abdruck"]]
        assert len(abdruecke) == len(set(abdruecke)), (
            f"Unit {unit['unit']}: zwei Listen mit demselben Abdruck"
        )


def test_niveau_a_ist_schwerer_als_niveau_b(abgelegt):
    for unit in abgelegt["units"]:
        for li in unit["listen"]:
            for teil in ("1", "2"):
                a = li["echt"]["t" + teil + "A"]["schnitt"]
                b = li["echt"]["t" + teil + "B"]["schnitt"]
                assert a > b, (
                    f"Unit {unit['unit']} V{li['version']} Teil {teil}: "
                    f"A {a} <= B {b}"
                )


def test_gebaute_seite_ist_vollstaendig():
    seite = _ohne_mitgetragene_vorlage()
    assert "__DATEN__" not in seite, "bauen.py lief nicht"
    assert seite.count("<title>") == 1
    daten = json.loads((WERKSTATT / "daten.json").read_text("utf-8"))
    kompakt = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    assert kompakt.replace("</", "<\\/") in seite, (
        "vokabelwerkstatt.html passt nicht zu daten.json - "
        "`python werkstatt/bauen.py` ausführen."
    )


def test_die_drei_arten_stehen_auch_auf_der_seite():
    """Was `neue_liste` bestellen kann, muss die Werkstatt anbieten können.

    Die Wendungen waren einmal in der Anwendung fertig und auf der Seite
    nicht vorhanden - da nützen sie niemandem.
    """
    seite = (WERKSTATT / "vokabelwerkstatt.html").read_text("utf-8")
    for feld in ("fancy", "ausdruecke", "chunks"):
        assert f'id="{feld}"' in seite, f"Zählfeld {feld} fehlt"
        assert f'state.{feld}' in seite, f"{feld} landet nicht im Auftrag"


# ---------------------------------------------------------------------------
# Der Auslöser: die Seite veröffentlicht sich selbst neu
# ---------------------------------------------------------------------------
def _ohne_mitgetragene_vorlage() -> str:
    """Die gebaute Seite ohne die Vorlage, die sie für den Auslöser mitträgt.

    Die mitgetragene Vorlage ist eine JSON-Zeichenkette und enthält
    naturgemäss alles noch einmal - Platzhalter, <title>, jedes Element.
    Wer die Seite prüft, meint die Seite, nicht ihre Blaupause.
    """
    seite = (WERKSTATT / "vokabelwerkstatt.html").read_text("utf-8")
    anfang = seite.index('<script id="vorlagenquelle"')
    ende = seite.index("</script>", anfang) + len("</script>")
    return seite[:anfang] + seite[ende:]


def _eingebettete_vorlage() -> str:
    """Die Vorlage, wie die gebaute Seite sie mitträgt."""
    seite = (WERKSTATT / "vokabelwerkstatt.html").read_text("utf-8")
    anfang = seite.index('<script id="vorlagenquelle"')
    anfang = seite.index(">", anfang) + 1
    return json.loads(seite[anfang:seite.index("</script>", anfang)])


def test_die_seite_traegt_ihre_eigene_vorlage_unversehrt():
    """Ohne die eigene Vorlage kann die Seite sich nicht neu veröffentlichen.

    Und sie muss **alle drei** Platzhalter behalten: Eine Fassung, in der
    einer schon ersetzt ist, kann die nächste nicht mehr bauen.
    """
    from bauen import PLATZHALTER

    eingebettet = _eingebettete_vorlage()
    assert eingebettet == (WERKSTATT / "vorlage.html").read_text("utf-8")
    for platzhalter in PLATZHALTER:
        assert eingebettet.count(platzhalter) == 1, (
            f"{platzhalter} fehlt in der mitgetragenen Vorlage - "
            "die nächste Fassung könnte sich nicht mehr bauen."
        )


def test_die_quelle_wird_zuletzt_eingesetzt(tmp_path):
    """Sonst trifft die Klingel die eingebettete Vorlage statt die Seite.

    Genau das ging beim ersten Versuch schief: Die zweite Fassung liess
    sich noch bauen, die dritte nicht mehr.
    """
    from bauen import baue

    erste = tmp_path / "erste.html"
    baue(WERKSTATT / "vorlage.html", WERKSTATT / "daten.json", erste,
         {"auftrag": "u01-1", "zeit": "2026-01-01T00:00:00.000Z"})
    text = erste.read_text("utf-8")
    anfang = text.index(">", text.index('<script id="vorlagenquelle"')) + 1
    eingebettet = json.loads(text[anfang:text.index("</script>", anfang)])
    assert "__KLINGEL__" in eingebettet, "die Klingel hat die Vorlage getroffen"
    assert eingebettet == (WERKSTATT / "vorlage.html").read_text("utf-8")


def test_die_seite_setzt_in_derselben_reihenfolge_zusammen_wie_bauen_py():
    """Zwei Umsetzungen desselben Handgriffs - eine in Python, eine in JS.

    Byteweise vergleichen lässt sich das nur mit einem Browser; die
    Reihenfolge, an der es tatsächlich scheiterte, steht aber im Quelltext
    und wird hier gelesen.
    """
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    körper = seite[seite.index("function bauePlatte("):]
    körper = körper[:körper.index("\n}")]
    reihenfolge = re.findall(r'\.replace\(P\("(\w+)"\)', körper)
    assert reihenfolge == ["DATEN", "KLINGEL", "QUELLE"], (
        "Die Seite setzt anders zusammen als bauen.py - siehe dessen "
        "Docstring."
    )


def test_der_ausloeser_haelt_sich_an_die_datenbank():
    """Der Knopf legt erst ab und klingelt dann - nie umgekehrt.

    Andersherum wachte die Sitzung auf und fände nichts vor.
    """
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    körper = seite[seite.index('$("ausloesen").addEventListener'):]
    körper = körper[:körper.index("\n});")]
    assert körper.index('db.doc("auftraege/"') < körper.index("selbst.publish("), (
        "erst ablegen, dann klingeln"
    )
    # Ohne beide Fähigkeiten muss der Knopf aus sein, statt ins Leere zu greifen.
    assert "!db || !selbst" in körper
