"""Wiederholung aus dem vorherigen Vocabulary - richtige Liste, richtige Wörter.

Die Wiederholung fragt Wörter aus einer **anderen** Liste ab als der Rest der
Prüfung. Was dabei schiefgehen kann, fällt sonst erst beim Korrigieren auf:
ein Wort, das es in der genannten Liste nicht gibt; eines, das auf dem Blatt
schon als aktuelles Vocabulary steht; eines, dessen Lösung im Lückentext
gedruckt ist; eine Quelle, die sich seit der Wahl geändert hat. Jeder Test
baut genau einen solchen Fehler ein und verlangt, dass die Kontrolle
``wiederholung`` ihn findet.

Gearbeitet wird auf **Kopien** der mitgelieferten Pakete - die echten bleiben
unberührt.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from vocabmaster import wiederholung as wh
from vocabmaster.checks import FEHLER, WARNUNG, Pruefbericht, pruefe_wiederholung
from vocabmaster.cli import main as cli_main
from vocabmaster.config import Settings
from vocabmaster.documents import baue_alles, dateiname
from vocabmaster.exam.builder import build_document_xml, hoechstpunktzahl
from vocabmaster.exam.verify import document_text, verify_document
from vocabmaster.pack import Pack, ausgleichen, neue_fassung, pruefungswoerter

WURZEL = Path(__file__).resolve().parent.parent
KURATIERT = WURZEL / "kuratiert"


@pytest.fixture
def ordner(tmp_path) -> Path:
    """Eine Kopie des Bestands - Listen und Fassungen."""
    ziel = tmp_path / "kuratiert"
    shutil.copytree(KURATIERT, ziel)
    return ziel


def _lade(ordner: Path, name: str) -> Pack:
    return Pack.load(ordner / name)


def _befunde(pack: Pack, stufe: str) -> list[str]:
    bericht = Pruefbericht()
    pruefe_wiederholung(pack, bericht)
    return [b.text for b in bericht.befunde if b.stufe == stufe]


def _mit_wiederholung(ordner: Path) -> Pack:
    """Unit 2 Part I mit Wiederholung aus Unit 1 Part II (V1) - beide Niveaus.

    Die Quelle steht hier fest: Welche der beiden Listen von Unit 1 der
    Vorschlag nimmt, hängt an den gebauten Dokumenten, und die gibt es in
    der Testkopie nicht. Das prüft ein eigener Test.
    """
    pack = _lade(ordner, "unit_02.json")
    wh.setze(pack, 1, _lade(ordner, "unit_01.json"), 2, folge=True,
             grund="Unit 1 · Part II ist der Part vor Unit 2 · Part I")
    pack.save()
    return Pack.load(pack.pfad)


# ---------------------------------------------------------------------------
# Die Folge: welcher Part kommt unmittelbar davor?
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("unit, teil, erwartet", [
    (1, 2, (1, 1)),     # Unit 1 Part II  <- Unit 1 Part I
    (2, 1, (1, 2)),     # Unit 2 Part I   <- Unit 1 Part II, über den Wechsel
    (2, 2, (2, 1)),     # Unit 2 Part II  <- Unit 2 Part I
    (1, 1, (0, 2)),     # Unit 1 Part I   <- Starter Unit Part II
    (8, 1, (7, 2)),
])
def test_die_folge_laeuft_ueber_units_und_parts(unit, teil, erwartet):
    assert wh.vorgaenger(unit, teil, list(range(0, 9))) == erwartet


def test_vor_der_ersten_unit_gibt_es_keinen_vorgaenger():
    assert wh.vorgaenger(1, 1, list(range(1, 9))) is None


def test_der_vorgaenger_richtet_sich_nach_dem_lehrmittel_nicht_nach_den_listen(ordner):
    """Zu Unit 2 bis 7 von English Plus 3 gibt es keine Liste.

    Der Vorgänger von Unit 8 Part I ist trotzdem Unit 7 Part II - und nicht
    Unit 1 Part II, bloss weil das die nächste Liste ist. Sonst fragte die
    Wiederholung Wörter ab, die sechs Units zurückliegen, und behauptete,
    es seien die von letzter Woche.
    """
    pack = _lade(ordner, "unit_08_englishplus3.json")
    vs = wh.vorschlaege(pack, 1, ordner)
    assert not any(q.folge for q in vs), "Unit 1 ist nicht der Vorgänger"
    satz = wh.fehlender_vorgaenger(pack, 1, vs)
    assert "Unit 7 · Part II" in satz and "keine Liste" in satz
    # Der naheliegendste steht trotzdem vorn - und sagt, dass er es nicht ist.
    assert "käme unmittelbar davor" in vs[0].grund


def test_part_zwei_wiederholt_part_eins_derselben_liste(ordner):
    for name in ("unit_01.json", "unit_01_v2.json", "unit_08_englishplus3.json"):
        pack = _lade(ordner, name)
        erster = wh.vorschlaege(pack, 2, ordner)[0]
        assert erster.folge
        assert (erster.paket, erster.teil) == (name, 1), name


def test_part_eins_wiederholt_part_zwei_der_unit_davor(ordner):
    pack = _lade(ordner, "unit_03.json")
    erster = wh.vorschlaege(pack, 1, ordner)[0]
    assert erster.folge and (erster.paket, erster.teil) == ("unit_02.json", 2)


def test_bei_mehreren_listen_zaehlt_die_gebaute_pruefung(ordner, tmp_path):
    """Unit 1 hat V1 und V2. Welche wurde behandelt?

    Ohne Spuren die neueste. Liegt zu Part II von V1 eine gebaute Prüfung,
    dann V1 - die war sicher im Unterricht.
    """
    pack = _lade(ordner, "unit_02.json")
    leer = tmp_path / "out_leer"
    leer.mkdir()
    ohne = wh.vorschlaege(pack, 1, ordner, leer)
    assert [(q.paket, q.folge) for q in ohne[:2]] == [
        ("unit_01_v2.json", True), ("unit_01.json", True)]

    gebaut = tmp_path / "out_gebaut"
    gebaut.mkdir()
    (gebaut / dateiname(1, "Test", 2, "A", liste_version=1)).write_bytes(b"x")
    mit = wh.vorschlaege(pack, 1, ordner, gebaut)
    assert mit[0].paket == "unit_01.json"
    assert "Prüfung gebaut" in mit[0].grund


def test_was_nach_dem_test_kommt_ist_keine_wiederholung(ordner):
    pack = _lade(ordner, "unit_03.json")
    for q in wh.vorschlaege(pack, 1, ordner):
        if q.pruefsumme == pack.quelle["pruefsumme_sha256"]:
            assert wh.schritt(q.unit, q.teil) < wh.schritt(3, 1), q


# ---------------------------------------------------------------------------
# Die Wörter
# ---------------------------------------------------------------------------
def test_die_woerter_stammen_aus_dem_genannten_part(ordner):
    pack = _mit_wiederholung(ordner)
    quelle = _lade(ordner, "unit_01.json")
    quell = {(e["englisch"], e["deutsch"]) for e in quelle.entries("test2")}
    aktuell = {e["englisch"] for e in pack.entries("test1")}
    for niveau, anzahl in wh.ANZAHL.items():
        block = pack.exam(1, niveau)["wiederholung"]
        assert len(block["items"]) == anzahl
        for item in block["items"]:
            assert (item["english"], item["german"]) in quell, item
            assert item["english"] not in aktuell
        assert block["bonus"] is wh.BONUS[niveau]
        assert block["quelle"]["abdruck"] == quelle.liste_abdruck
    assert not _befunde(pack, FEHLER) and not _befunde(pack, WARNUNG)


def test_niveau_a_nimmt_die_schwereren_woerter(ordner):
    from vocabmaster.pack import _schwierigkeit

    pack = _mit_wiederholung(ordner)
    quelle = {e["englisch"]: e for e in _lade(ordner, "unit_01.json").entries("test2")}

    def schnitt(niveau):
        items = pack.exam(1, niveau)["wiederholung"]["items"]
        return sum(_schwierigkeit(quelle[i["english"]]) for i in items) / len(items)

    assert schnitt("A") > schnitt("B")


def test_was_gedruckt_auf_dem_blatt_steht_wird_nicht_gewaehlt(ordner):
    """Der Lückentext von Unit 2 Part I (Niveau B) enthält "a picnic".

    'picnic' ist das zugänglichste Wort von Unit 1 Part II - ohne diese
    Regel wäre es gewählt worden, und die Lösung stünde im Text darüber.
    """
    pack = _lade(ordner, "unit_02.json")
    assert wh.steht_gedruckt("picnic", wh.gedruckter_text(pack.exam(1, "B")))
    woerter = wh.waehle(pack, 1, "B", _lade(ordner, "unit_01.json"), 2)
    assert "picnic" not in [w["english"] for w in woerter]


def test_eine_fremde_liste_kollidiert_nicht_mit_dem_aktuellen_part(ordner):
    """Aus einer anderen Liste gewählt: nichts, was hier ohnehin geprüft wird."""
    pack = _lade(ordner, "unit_01_v2.json")
    quelle = _lade(ordner, "unit_01.json")           # dieselbe Unit, V1
    aktuell = wh.aktuelle_woerter(pack, 2)
    for niveau in ("A", "B"):
        for w in wh.waehle(pack, 2, niveau, quelle, 2):
            assert not wh.kollidiert(w["english"], aktuell), w


def test_ein_part_wiederholt_sich_nicht_selbst(ordner):
    pack = _lade(ordner, "unit_02.json")
    with pytest.raises(ValueError, match="nicht selbst"):
        wh.setze(pack, 1, pack, 1)


# ---------------------------------------------------------------------------
# Die Kontrolle: je ein eingebauter Fehler
# ---------------------------------------------------------------------------
def _block(pack: Pack, niveau: str = "A") -> dict:
    return pack.data["pruefungen"]["teil1"][niveau]["wiederholung"]


def test_ein_wort_das_nicht_in_der_quelle_steht(ordner):
    pack = _mit_wiederholung(ordner)
    _block(pack)["items"][0] = {"english": "lighthouse", "german": "Leuchtturm",
                                "pos": "noun"}
    assert any("steht nicht in Unit 1 · Part II" in t
               for t in _befunde(pack, FEHLER))


def test_ein_wort_aus_dem_falschen_part(ordner):
    """Aus Part I statt aus dem genannten Part II derselben Liste."""
    pack = _mit_wiederholung(ordner)
    falsch = _lade(ordner, "unit_01.json").entries("test1")[0]
    _block(pack)["items"][0] = {"english": falsch["englisch"],
                                "german": falsch["deutsch"], "pos": "noun"}
    assert any("steht nicht in" in t for t in _befunde(pack, FEHLER))


def test_eine_andere_uebersetzung_als_in_der_quelle(ordner):
    pack = _mit_wiederholung(ordner)
    _block(pack)["items"][0]["german"] = "etwas ganz anderes"
    assert any("übersetzt" in t for t in _befunde(pack, FEHLER))


def test_ein_wort_aus_dem_aktuellen_part(ordner):
    pack = _mit_wiederholung(ordner)
    hier = pack.entries("test1")[0]
    _block(pack)["items"][0] = {"english": hier["englisch"],
                                "german": hier["deutsch"], "pos": "noun"}
    befunde = _befunde(pack, FEHLER)
    assert any("im Part I, den die Prüfung abfragt" in t
               or "schon als aktuelles Vocabulary" in t for t in befunde)


def test_ein_wort_das_im_lueckentext_steht(ordner):
    pack = _mit_wiederholung(ordner)
    block = _block(pack, "B")
    block["items"][0] = {"english": "picnic", "german": "Picknick", "pos": "noun"}
    assert any("gedruckt" in t for t in _befunde(pack, FEHLER))


def test_ein_wort_zweimal(ordner):
    pack = _mit_wiederholung(ordner)
    items = _block(pack)["items"]
    items[1] = dict(items[0])
    assert any("zweimal" in t for t in _befunde(pack, FEHLER))


def test_die_quelle_fehlt(ordner):
    pack = _mit_wiederholung(ordner)
    (ordner / "unit_01.json").unlink()
    assert any("liegt nicht im Ordner" in t for t in _befunde(pack, FEHLER))


def test_die_quelle_hat_sich_seither_geaendert(ordner):
    """Die Liste im Quellpaket ist nicht mehr die, aus der gewählt wurde."""
    pack = _mit_wiederholung(ordner)
    pfad = ordner / "unit_01.json"
    roh = json.loads(pfad.read_text("utf-8"))
    roh["liste"]["test2"][0]["deutsch"] = "verändert"
    pfad.write_text(json.dumps(roh, ensure_ascii=False), "utf-8")
    assert any("Abdruck" in t for t in _befunde(pack, FEHLER))


def test_bonus_auf_niveau_a_ist_ein_fehler(ordner):
    pack = _mit_wiederholung(ordner)
    _block(pack, "A")["bonus"] = True
    assert any("zählt die Wiederholung mit" in t for t in _befunde(pack, FEHLER))


def test_kein_bonus_auf_niveau_b_ist_ein_fehler(ordner):
    pack = _mit_wiederholung(ordner)
    _block(pack, "B")["bonus"] = False
    assert any("Höchstpunktzahl" in t for t in _befunde(pack, FEHLER))


def test_eine_andere_anzahl_wird_gesagt(ordner):
    pack = _mit_wiederholung(ordner)
    _block(pack, "A")["items"].pop()
    assert any("3 Wörter, vorgesehen sind 4" in t for t in _befunde(pack, WARNUNG))


def test_ein_anderer_part_als_der_vorherige_wird_gesagt(ordner):
    """Von Hand gewählt ist erlaubt - aber es steht im Bericht."""
    pack = _lade(ordner, "unit_02.json")
    wh.setze(pack, 1, _lade(ordner, "unit_01.json"), 1, folge=False,
             grund="von Hand gewählt")
    pack.save()
    pack = Pack.load(pack.pfad)
    assert not _befunde(pack, FEHLER)
    assert any("unmittelbar vor Unit 2 · Part I kommt Unit 1 · Part II" in t
               for t in _befunde(pack, WARNUNG))


def test_ein_block_der_sich_als_folge_ausgibt_und_es_nicht_ist(ordner):
    pack = _lade(ordner, "unit_02.json")
    wh.setze(pack, 1, _lade(ordner, "unit_01.json"), 1, folge=True, grund="x")
    pack.save()
    pack = Pack.load(pack.pfad)
    assert any("gibt sich als unmittelbar vorheriger Part aus" in t
               for t in _befunde(pack, FEHLER))


def test_ohne_wiederholung_laeuft_die_kontrolle_nicht(ordner):
    bericht = Pruefbericht()
    pruefe_wiederholung(_lade(ordner, "unit_02.json"), bericht)
    assert "wiederholung" not in bericht.gelaufen


# ---------------------------------------------------------------------------
# Auf dem Blatt
# ---------------------------------------------------------------------------
def test_ohne_wiederholung_bleibt_das_dokument_dasselbe(ordner):
    spec = _lade(ordner, "unit_02.json").exam(1, "A")
    vorher = build_document_xml(spec), build_document_xml(spec, True)
    assert build_document_xml({**spec, "wiederholung": {}}) == vorher[0]
    assert build_document_xml({**spec, "wiederholung": {}}, True) == vorher[1]


def test_die_hoechstpunktzahl(ordner):
    pack = _mit_wiederholung(ordner)
    assert hoechstpunktzahl(pack.exam(1, "A")) == (16, 0)     # 12 + 4
    assert hoechstpunktzahl(pack.exam(1, "B")) == (12, 2)     # Bonus obendrauf


def test_das_gebaute_blatt(ordner, tmp_path):
    pack = _mit_wiederholung(ordner)
    ergebnis = baue_alles(pack, tmp_path / "out", Settings(), teile=("test",),
                          pruefungsteile=(1,))
    assert not ergebnis.bericht.fehler, [str(b) for b in ergebnis.bericht.fehler]
    a = document_text(str(tmp_path / "out" / dateiname(2, "Test", 1, "A")))
    a_l = document_text(str(tmp_path / "out" / dateiname(2, "Test", 1, "A", loesung=True)))
    b_l = document_text(str(tmp_path / "out" / dateiname(2, "Test", 1, "B", loesung=True)))
    block = pack.exam(1, "A")["wiederholung"]
    assert "3) Revision" in a and "4P" in a
    for item in block["items"]:
        assert item["german"] in a
        assert item["english"] not in a, "die Lösung stünde auf dem Blatt"
        assert item["english"] in a_l
    assert "Höchstpunktzahl: 16P" in a_l
    assert "3) Bonus" in b_l and "+2P" in b_l
    assert "Höchstpunktzahl: 12P" in b_l and "bis +2P" in b_l


def test_die_nachkontrolle_findet_eine_gedruckte_loesung(ordner, tmp_path):
    """Steht ein Wiederholungswort auf dem Blatt, meldet es auch die
    Nachkontrolle des fertigen Dokuments - die letzte Stelle vor dem Druck."""
    from vocabmaster.exam.builder import build_docx

    pack = _mit_wiederholung(ordner)
    spec = json.loads(json.dumps(pack.exam(1, "B")))
    spec["wiederholung"]["items"][0] = {"english": "picnic", "german": "Picknick",
                                        "pos": "noun"}
    ziel = tmp_path / "b.docx"
    vorlage = str(Settings().exam_template)
    build_docx(spec, vorlage, str(ziel))
    befunde = verify_document(str(ziel), spec, vorlage, False)
    assert any(f.check == "leak" and "picnic" in f.message for f in befunde)


# ---------------------------------------------------------------------------
# Was die Wiederholung mitnimmt - und was nicht
# ---------------------------------------------------------------------------
def test_ausgleichen_behaelt_die_bestellte_wiederholung(ordner):
    pack = _mit_wiederholung(ordner)
    vorher = json.dumps(pack.exam(1, "A")["wiederholung"], sort_keys=True)
    # Ausgleichen setzt die Prüfungen neu auf - die Wiederholung bleibt.
    ausgleichen(pack, Settings())
    assert json.dumps(pack.exam(1, "A")["wiederholung"], sort_keys=True) == vorher


def test_eine_neue_fassung_nimmt_die_wiederholung_mit(ordner):
    pack = _mit_wiederholung(ordner)
    neu = neue_fassung(pack, 1, "A", 2, Settings())
    assert neu.exam(1, "A")["wiederholung"] == pack.exam(1, "A")["wiederholung"]


def test_die_wiederholung_zaehlt_nicht_zu_den_pruefungswoertern(ordner):
    """Die übrigen Kontrollen prüfen gegen die Liste **dieses** Pakets."""
    pack = _mit_wiederholung(ordner)
    geprueft = set(pruefungswoerter(pack.exam(1, "A")))
    for item in pack.exam(1, "A")["wiederholung"]["items"]:
        assert item["english"] not in geprueft


# ---------------------------------------------------------------------------
# Kommandozeile
# ---------------------------------------------------------------------------
def test_vorschlag_schreibt_nichts(ordner, capsys):
    pfad = ordner / "unit_02.json"
    vorher = pfad.read_bytes()
    assert cli_main(["wiederholung", str(pfad), "--teil", "1", "--vorschlag"]) == 0
    assert pfad.read_bytes() == vorher
    assert "Unit 1 · Part II" in capsys.readouterr().out


def test_ohne_vorgaenger_wird_nicht_geraten(ordner, capsys):
    """Unit 1 Part I: Zur Starter Unit gibt es keine Liste. Ohne Wahl wird
    nichts eingetragen - es wird gefragt."""
    pfad = ordner / "unit_01.json"
    vorher = pfad.read_bytes()
    assert cli_main(["wiederholung", str(pfad), "--teil", "1"]) == 1
    assert pfad.read_bytes() == vorher
    ausgabe = capsys.readouterr().out
    assert "Starter Unit · Part II" in ausgabe and "--wahl" in ausgabe


def test_uebernehmen_und_wieder_entfernen(ordner):
    pfad = ordner / "unit_02.json"
    assert cli_main(["wiederholung", str(pfad), "--teil", "1"]) == 0
    assert "wiederholung" in Pack.load(pfad).exam(1, "A")
    assert cli_main(["wiederholung", str(pfad), "--teil", "1", "--weg"]) == 0
    assert "wiederholung" not in Pack.load(pfad).exam(1, "A")
