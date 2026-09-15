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


# ---------------------------------------------------------------------------
# Nur zeigen, was zur Bestellung gehört
# ---------------------------------------------------------------------------
#: Welche Einstellung an welcher Bedingung hängt. Ein Regler für den Anspruch
#: der Prüfung, wenn keine Prüfung bestellt ist, stellt eine Frage, die
#: niemand gestellt hat - und wer ihn verschiebt, glaubt danach, etwas
#: eingestellt zu haben.
SICHTBARKEIT = {
    "gruppePruefung": "b.pruefungen",
    "gruppeListe": "b.liste",
    "anspruchA": "b.A",
    "anspruchB": "b.B",
    "textreglerA": "b.A",
    "textreglerB": "b.B",
    "teile": "b.pruefungen",
}


def test_prueferei_verschwindet_ohne_pruefung():
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    körper = seite[seite.index("function zeichneSichtbarkeit()"):]
    körper = körper[:körper.index("\n}")]
    for kennung, bedingung in SICHTBARKEIT.items():
        zeile = f'$("{kennung}").hidden = !{bedingung};'
        assert zeile in körper, f"{kennung} hängt nicht an {bedingung}"
    # Und jedes Feld, das die Seite versteckt, steht auch in der Tabelle -
    # sonst wächst die eine Liste und die andere nicht.
    versteckt = set(re.findall(r'\$\("(\w+)"\)\.hidden', körper))
    assert versteckt == set(SICHTBARKEIT)


def test_ein_kreuz_zeichnet_die_ganze_seite_neu():
    """Sonst bleiben Regler stehen, die es nicht mehr gibt.

    Der Haken ändert nicht nur den Auftragssatz: Er entscheidet auch, ob
    eine neue Liste zur Wahl steht und welche Teile das Lineal zeigt.
    """
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    assert '$(id).addEventListener("change", alles));' in seite
    assert "zeichneSichtbarkeit();" in seite[seite.index("function alles()"):]


def test_die_uebersicht_fuehrt_nur_was_es_gibt():
    """Eine Zeile „＋ neue Liste" wäre dieselbe Bestellung zweimal.

    Bestellt wird mit dem Häkchen „Neue Vokabelliste"; die Übersicht oben
    zeigt den Bestand und sagt, welche Liste die Grundlage ist.
    """
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    körper = seite[seite.index("function zeichneListenwahl()"):]
    körper = körper[:körper.index("\n}\n")]
    # Die Übersicht führt nur, was es gibt - bestellt wird nebenan.
    assert "neuzeile" not in seite, "die Übersicht darf nichts anbieten"
    assert 'function legtNeueListeAn(){ return $("bLi").checked; }' in seite
    # Und eine Wahl, die es nicht mehr gibt, darf nicht stehenbleiben.
    assert "if(!u.listen.some(li => li.version === state.listeVersion))" in körper


# ---------------------------------------------------------------------------
# Wortauswahl von Hand: dabei und nicht dabei
# ---------------------------------------------------------------------------
def _schluessel(englisch: str) -> str:
    """Wie die Seite zwei Schreibungen desselben Wortes zusammenbringt.

    Die Wortliste schreibt den Klammerzusatz mit, das Paket nicht. Wer
    stumpf vergleicht, sieht dasselbe Wort in beiden Spalten.
    """
    return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", " ", englisch.lower())).strip()


def test_der_hauptteil_kommt_vollstaendig_mit(abgelegt):
    """Links die Liste, rechts der Rest - dafür braucht es den ganzen Rest."""
    for u in abgelegt["units"]:
        haupt = u["hauptteil"]
        assert len(haupt) == u["herkunft"]["hauptteil"], f"Unit {u['unit']}"
        assert len({w["en"].lower() for w in haupt}) == len(haupt), "doppelte Einträge"
        for wort in haupt:
            assert wort["en"] and wort["de"], f"leerer Eintrag in Unit {u['unit']}"


def test_das_urteil_gehoert_zur_unit_nicht_zur_liste(abgelegt):
    """Ob ein Wort Grundwortschatz ist, hängt nicht an der gewählten Liste.

    Der klassische Fehler wäre, das Urteil gegen *alle* Listen der Unit zu
    rechnen: Ein Wort, das nur in V2 steht, fehlte dann in beiden Spalten,
    sobald man V1 ansieht.
    """
    for u in abgelegt["units"]:
        nach_en = {_schluessel(w["en"]): w for w in u["hauptteil"]}
        for liste in u["listen"]:
            for wort in liste["woerter"]:
                if wort["quelle"] != "wortliste":
                    continue  # ergänzte Wörter stehen nicht im Hauptteil
                eintrag = nach_en.get(_schluessel(wort["en"]))
                assert eintrag is not None, (
                    f"{wort['en']} steht in V{liste['version']}, "
                    f"aber nicht im Hauptteil von Unit {u['unit']}"
                )
                assert eintrag["grund"] == "", (
                    f"{wort['en']} ist in V{liste['version']} gewählt, trägt "
                    f"aber das Urteil {eintrag['grund']!r}"
                )


def test_die_waage_misst_gegen_die_gewaehlte_liste():
    """Sonst steht dort eine Zahl, die zu einer anderen Liste gehört."""
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    körper = seite[seite.index("function wortwahlZeichnen()"):]
    körper = körper[:körper.index("\n}")]
    assert "const ziel = anzeigeListe().woerter.length;" in körper
    assert "links.length - ziel" in körper


def test_handarbeit_faellt_beim_wechsel_weg():
    """Ein herübergeholtes Wort der einen Unit ist in der nächsten keines."""
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    for stelle in ('$("unit").addEventListener', "function listeWaehlen("):
        körper = seite[seite.index(stelle):]
        körper = körper[:körper.index("\n}")]
        assert "handarbeitVerwerfen()" in körper, f"{stelle} vergisst die Handarbeit"


def test_die_seite_blendet_aus_wie_der_veroeffentlichte_rahmen():
    """`hidden` muss auch beim lokalen Öffnen wirken.

    Die Regel dafür setzt sonst erst der Veröffentlichungsdienst um die
    Seite - wer sie lokal prüft, sähe Abschnitte, die ausgeblendet sein
    sollten, und prüfte etwas anderes als das, was später dasteht.
    """
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    assert "[hidden]{display:none!important}" in seite


def test_jeder_handgriff_schreibt_den_auftrag_neu():
    """Auch das Festnageln. Sonst steht die Zeile erst da, wenn zufällig
    noch etwas anderes geklickt wird - und wer nur ein Wort festnagelt,
    kopiert einen Auftrag ohne seine Vorgabe."""
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    körper = seite[seite.index("function wortzeile("):]
    körper = körper[:körper.index("\n}")]
    for handgriff in ("umschalten(state.fest", "wegnehmen(en)", "aufnehmen(en)"):
        assert handgriff in körper
    # Alle drei gehen durch `nachHandgriff`, und das zeichnet die ganze
    # Seite neu - der Handgriff kann ja auch das Häkchen umlegen.
    for name in ("function aufnehmen(", "function wegnehmen("):
        block = seite[seite.index(name):]
        assert "nachHandgriff();" in block[:block.index("\n}")]
    assert "umschalten(state.fest, en); nachHandgriff();" in seite
    nach = seite[seite.index("function nachHandgriff()"):]
    assert "alles();" in nach[:nach.index("\n}")]


# ---------------------------------------------------------------------------
# Eine bestehende Liste wird nie verändert
# ---------------------------------------------------------------------------
def test_handarbeit_erzwingt_eine_neue_liste():
    """Der teuerste Fehler dieses Programms, in der Oberfläche verhindert.

    An V1 hängen ihre Prüfungen — über den Listenabdruck und über die
    Word-Dateien, die längst ausgeteilt sein können. Wer ein Wort aus V1
    nähme, hätte einen Lösungsschlüssel, der auf ein Wort zeigt, das es
    dort nicht mehr gibt; gemerkt wird das beim Korrigieren.
    """
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    körper = seite[seite.index("function neueListeErzwingen()"):]
    körper = körper[:körper.index("\n}")]
    assert 'if(handarbeitVorhanden() && !$("bLi").checked){' in körper
    assert '$("bLi").checked = true;' in körper
    # Jeder Handgriff muss da durch.
    for name in ("function aufnehmen(", "function wegnehmen("):
        block = seite[seite.index(name):]
        assert "nachHandgriff();" in block[:block.index("\n}")]
    assert "umschalten(state.fest, en); nachHandgriff();" in seite
    nach = seite[seite.index("function nachHandgriff()"):]
    assert "neueListeErzwingen();" in nach[:nach.index("\n}")]


def test_das_haekchen_ist_gesperrt_solange_handarbeit_vorliegt():
    """Sonst nimmt man es wieder weg und ändert doch die bestehende Liste."""
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    assert '$("bLi").disabled = geaendert > 0;' in seite
    # Und der Grund steht an beiden Orten, an denen man ihn braucht.
    assert '["wortwahlwarnung", "neuhinweis"]' in seite


def test_ein_erzwungenes_haekchen_geht_mit_der_handarbeit_wieder_weg():
    """Es war eine Folge, keine Bestellung — ein selbst gesetztes bleibt."""
    seite = (WERKSTATT / "vorlage.html").read_text("utf-8")
    körper = seite[seite.index("function handarbeitVerwerfen()"):]
    körper = körper[:körper.index("\n}")]
    assert 'if(state.autoNeu){ $("bLi").checked = false; state.autoNeu = false; }' in körper
