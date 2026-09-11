"""Die Oberfläche muss zeigen, was in den Paketen wirklich steht.

Der klassische Fehler ist hier, dass jemand ein Paket ändert und die
Oberfläche danach eine Auswahl anzeigt, die es so nicht mehr gibt. Die
Seite ist gebaut, nicht von Hand geschrieben - also lässt sich das prüfen,
indem die Daten neu erzeugt und verglichen werden.
"""

from __future__ import annotations

import json
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
    """Jedes Wort der vier Prüfungen kommt in der Liste derselben Unit vor."""
    for unit in abgelegt["units"]:
        for schluessel, auswahl in unit["echt"].items():
            test = int(schluessel[1])
            liste = {w["en"] for w in unit["woerter"] if w["test"] == test}
            fremd = [w for w in auswahl["woerter"] if w not in liste]
            assert not fremd, f"Unit {unit['unit']} {schluessel}: {fremd}"
            offen = [w for w in auswahl["luecken"] if w not in auswahl["woerter"]]
            assert not offen, f"Unit {unit['unit']} {schluessel} Lücken: {offen}"


def test_niveau_a_ist_schwerer_als_niveau_b(abgelegt):
    for unit in abgelegt["units"]:
        for teil in ("1", "2"):
            a = unit["echt"]["t" + teil + "A"]["schnitt"]
            b = unit["echt"]["t" + teil + "B"]["schnitt"]
            assert a > b, f"Unit {unit['unit']} Teil {teil}: A {a} <= B {b}"


def test_gebaute_seite_ist_vollstaendig():
    seite = (WERKSTATT / "vokabelwerkstatt.html").read_text("utf-8")
    assert "__DATEN__" not in seite, "bauen.py lief nicht"
    assert seite.count("<title>") == 1
    daten = json.loads((WERKSTATT / "daten.json").read_text("utf-8"))
    kompakt = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    assert kompakt.replace("</", "<\\/") in seite, (
        "vokabelwerkstatt.html passt nicht zu daten.json - "
        "`python werkstatt/bauen.py` ausführen."
    )
