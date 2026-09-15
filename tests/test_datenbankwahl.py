"""Wer eine Datenbank wählt, sieht ihre Units — nicht die einer anderen.

`daten.json` trug einmal genau **eine** Unit-Liste: die der Grunddatenbank.
Das Auswahlfeld schrieb nur eine Zeile in den Auftrag, die Units darunter
blieben dieselben. Wer English Plus 3 wählte, las die Themen von English
Plus 4 — und nichts sagte ihm, dass er das Falsche ansieht.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
WERKSTATT = WURZEL / "werkstatt"

pytestmark = pytest.mark.skipif(
    not (WERKSTATT / "daten.json").exists(), reason="keine Werkstatt-Daten"
)


@pytest.fixture(scope="module")
def daten() -> dict:
    return json.loads((WERKSTATT / "daten.json").read_text("utf-8"))


def test_jede_datenbank_bringt_ihre_eigenen_units_mit(daten):
    vorhanden = [d for d in daten["datenbanken"] if d["vorhanden"]]
    assert len(vorhanden) >= 2, "der Test braucht zwei importierte Datenbanken"
    for d in vorhanden:
        assert d["units"], f"{d['name']} bringt keine Units mit"


def test_zwei_datenbanken_zeigen_nicht_dieselben_themen(daten):
    """Der Fehler selbst: zweimal dasselbe Lehrmittel unter zwei Namen."""
    vorhanden = [d for d in daten["datenbanken"] if d["vorhanden"]]
    themen = {
        d["name"]: {u["unit"]: u["thema"] for u in d["units"] if u["thema"]}
        for d in vorhanden
    }
    namen = sorted(themen)
    for i, eins in enumerate(namen):
        for zwei in namen[i + 1:]:
            gemeinsam = set(themen[eins]) & set(themen[zwei])
            gleich = [u for u in gemeinsam if themen[eins][u] == themen[zwei][u]]
            assert not gleich, (
                f"{eins} und {zwei} tragen dasselbe Thema in Unit {gleich} — "
                "eine der beiden hat es von der anderen geerbt"
            )


def test_eine_unit_ohne_vokabelliste_faellt_nicht_weg(daten):
    """Ein frisch eingelesenes Lehrmittel hat noch keine einzige Liste.

    Seine Units gibt es trotzdem — aus ihnen wird die erste bestellt. Fielen
    sie weg, stünde das Auswahlfeld leer da.
    """
    ohne = [(d["name"], u["unit"]) for d in daten["datenbanken"]
            for u in d.get("units", []) if not u["listen"]]
    assert ohne, "keine Unit ohne Liste — der Test misst nichts"
    for name, unit in ohne:
        eintrag = next(d for d in daten["datenbanken"] if d["name"] == name)
        u = next(x for x in eintrag["units"] if x["unit"] == unit)
        # Sie muss trotzdem alles tragen, was die Seite zeigt.
        assert u["hauptteil"], f"{name} Unit {unit} hat keinen Hauptteil"
        assert "herkunft" in u


def test_die_seite_nimmt_die_units_der_gewaehlten_datenbank():
    """Eine Stelle entscheidet das, und alle drei Leser gehen über sie."""
    # `vorlage.html`, nicht die gebaute Seite: Die trägt die Vorlage ein
    # zweites Mal in sich, und dann zählt jedes Vorkommen doppelt.
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    assert "function einheiten()" in seite
    # `DATA.units` darf nur noch in `einheiten()` selbst vorkommen: als
    # Rückfall für eine Datenbank, die keine eigenen mitbringt.
    koerper = seite[seite.index("function einheiten()"):]
    koerper = koerper[:koerper.index("\n}")]
    assert seite.count("DATA.units") == koerper.count("DATA.units") == 1, (
        "es liest noch jemand DATA.units direkt — der sieht beim Wechsel der "
        "Datenbank die Units der falschen"
    )


def test_der_datenbankwechsel_verwirft_die_handarbeit():
    """Sie bezöge sich sonst auf Wörter, die es dort gar nicht gibt."""
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    koerper = seite[seite.index('$("datenbank").addEventListener'):]
    koerper = koerper[:koerper.index("\n});")]
    assert "handarbeitVerwerfen()" in koerper
    assert "state.liste = null" in koerper
    # Und das Unit-Feld muss neu gefüllt werden, sonst steht darin eine
    # Nummer, die das andere Lehrmittel nicht hat.
    assert "alles()" in koerper
    lauf = seite[seite.index("function alles()"):]
    lauf = lauf[:lauf.index("\n")]
    assert "zeichneUnitwahl()" in lauf


def test_eine_unit_ohne_liste_bricht_die_seite_nicht():
    """Ein frisch eingelesenes Lehrmittel hat für keine Unit eine Liste.

    Das ist ein echter Zustand, kein Fehler — und dort fängt man an. Vorher
    griff die Seite auf `u.listen[0].version` und warf einen TypeError, bei
    dem gar nichts mehr zu sehen war.
    """
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    assert "const OHNE_LISTE" in seite and "function hatListe()" in seite
    # Kein blinder Zugriff auf die erste Liste mehr.
    assert "u.listen[0].version" not in seite or \
        "hatListe() ? unitDaten().listen[0].version" in seite

    # Und „V0" darf nirgends stehen: Die erste Liste entsteht aus nichts.
    for stelle in ('function zeichneListenhinweis()', 'function zeichneHerkunft('):
        koerper = seite[seite.index(stelle):]
        koerper = koerper[:koerper.index("\n}")]
        assert "hatListe()" in koerper or "li.version ?" in koerper, (
            f"{stelle} zeigt die Version ungeprüft — bei einer Unit ohne "
            "Liste steht dort „V0“"
        )


def test_die_waage_wiegt_gegen_sechzig():
    """„0 von 0 — passt" wäre die Auskunft, alles sei in Ordnung."""
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    koerper = seite[seite.index("function wortwahlZeichnen()"):]
    koerper = koerper[:koerper.index("\n}")]
    assert "|| LISTENUMFANG" in koerper
    assert "const LISTENUMFANG = 60;" in seite
