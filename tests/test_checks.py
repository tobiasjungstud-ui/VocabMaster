"""Die zehn Kontrollmechanismen.

Jeder Test baut genau einen Fehler ein und verlangt, dass der Selbstcheck ihn
findet. Ein Prüfmechanismus, der nur behauptet zu prüfen, fällt hier auf.
"""

from __future__ import annotations

import copy

import pytest

from vocabmaster.checks import FEHLER, pruefe_paket
from vocabmaster.pack import Pack, scaffold

from .helpers import fill


def befunde(bericht, pruefung):
    return [b for b in bericht.befunde if b.pruefung == pruefung]


def fehler_von(bericht, pruefung):
    return [b for b in befunde(bericht, pruefung) if b.stufe == FEHLER]


# --- 0  Der Normalfall ------------------------------------------------------
def test_vollstaendiges_paket_hat_keine_strukturfehler(db, settings, pack):
    bericht = pruefe_paket(pack, db, settings)
    for pruefung in ("thema", "neuwoerter", "dubletten", "altbestand",
                     "loesungsschluessel", "niveau_konsistenz", "herkunft", "vorlage"):
        assert not fehler_von(bericht, pruefung), (
            f"{pruefung}: {[str(b) for b in fehler_von(bericht, pruefung)]}"
        )


def test_alle_zehn_pruefungen_laufen(db, settings, pack):
    bericht = pruefe_paket(pack, db, settings)
    for name in ("thema", "neuwoerter", "cefr", "dubletten", "altbestand",
                 "loesungsschluessel", "niveau_konsistenz", "vorlage", "herkunft",
                 "liste", "pruefung"):
        assert name in bericht.gelaufen


# --- 1  Themenkongruenz -----------------------------------------------------
def test_fremdes_wort_wird_erkannt(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["liste"]["test1"][0].update(
        englisch="carburettor", deutsch="Vergaser", herkunft="ergänzt",
        satz="The old car needs a new carburettor before the winter.",
    )
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("carburettor" in b.text for b in fehler_von(bericht, "thema"))


def test_passendes_ergaenztes_wort_wird_akzeptiert(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["liste"]["test1"][0].update(
        englisch="keepsake", deutsch="Andenken", herkunft="ergänzt",
        satz="She kept the old photo as a keepsake from her childhood.",
    )
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert not any("keepsake" in b.text for b in fehler_von(bericht, "thema"))


def test_begruendung_hebt_den_fehler_auf(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["liste"]["test1"][0].update(
        englisch="carburettor", deutsch="Vergaser", herkunft="ergänzt",
        satz="The old car needs a new carburettor before the winter.",
        begruendung="Kommt im Lesetext der Unit vor.",
    )
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert not fehler_von(bericht, "thema")


# --- 2  Neuwort-Limite ------------------------------------------------------
def test_zu_viele_neuwoerter_werden_gemeldet(db, settings, pack):
    """Über 40 Prozent ist eine Ausnahme - sie wird gemeldet, nicht verboten."""
    data = copy.deepcopy(pack.data)
    for entry in data["liste"]["test1"]:
        entry["herkunft"] = "ergänzt"
    for entry in data["liste"]["test2"][:5]:
        entry["herkunft"] = "ergänzt"
    bericht = pruefe_paket(Pack(data=data), db, settings)
    treffer = befunde(bericht, "neuwoerter")
    assert any("Ausnahme" in b.text for b in treffer)
    assert "58%" in bericht.kennzahlen["neuwoerter"]


def test_woerter_aus_zusatzteilen_werden_einzeln_ausgewiesen(db, settings, pack):
    """Culture und Project sind die letzte Reserve - das muss man sehen."""
    data = copy.deepcopy(pack.data)
    data["liste"]["test1"][0]["herkunft"] = "zusatzteil"
    data["liste"]["test1"][0]["abschnitt"] = "Culture 1"
    bericht = pruefe_paket(Pack(data=data), db, settings)
    treffer = befunde(bericht, "neuwoerter")
    assert any("Zusatzteilen" in b.text and "Culture 1" in b.text for b in treffer)
    assert "1 aus Zusatzteilen" in bericht.kennzahlen["neuwoerter"]


def test_anteil_unter_der_grenze_ist_in_ordnung(db, settings, pack):
    data = copy.deepcopy(pack.data)
    for entry in data["liste"]["test1"][:10]:
        entry["herkunft"] = "ergänzt"
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert not fehler_von(bericht, "neuwoerter")


# --- 3  CEFR ----------------------------------------------------------------
def test_zu_lange_saetze_fallen_auf(db, settings):
    data = fill(
        scaffold(db, 1, settings),
        satz=(
            "Although the weather had already become considerably worse during "
            "the afternoon, the visitors who had travelled from abroad decided "
            "that they would nevertheless continue with {}."
        ),
    )
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert befunde(bericht, "cefr")
    assert any("länger als" in b.text for b in befunde(bericht, "cefr"))


def test_niveau_b_hat_ein_engeres_band_als_a():
    from vocabmaster.niveau import PROFILES

    a, b = PROFILES["A"].level_targets, PROFILES["B"].level_targets
    assert b["max_sentence_length"] < a["max_sentence_length"]
    assert b["min_flesch_ease"] > a["min_flesch_ease"]
    assert b["max_flesch_grade"] < a["max_flesch_grade"]
    assert b["max_words"] < a["max_words"]


# --- 4  Dubletten -----------------------------------------------------------
def test_doppeltes_wort_wird_gefunden(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["liste"]["test2"][0]["englisch"] = data["liste"]["test1"][0]["englisch"]
    data["liste"]["test2"][0]["deutsch"] = data["liste"]["test1"][0]["deutsch"]
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert fehler_von(bericht, "dubletten")


def test_widerspruechliche_uebersetzung_wird_gefunden(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["liste"]["test2"][0]["englisch"] = data["liste"]["test1"][0]["englisch"]
    data["liste"]["test2"][0]["deutsch"] = "etwas völlig anderes"
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("verschiedene Übersetzungen" in b.text
               for b in fehler_von(bericht, "dubletten"))


# --- 5  Altbestand ----------------------------------------------------------
def test_wort_aus_alter_wortliste_wird_gefunden(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["liste"]["test1"][0].update(
        englisch="pendant", deutsch="Anhänger", herkunft="wortliste",
        satz="She wore a silver pendant from her grandmother.",
    )
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("pendant" in b.text for b in fehler_von(bericht, "altbestand"))


def test_andere_excel_fassung_wird_abgelehnt(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["quelle"]["pruefsumme_sha256"] = "0" * 64
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("anderen Fassung" in b.text for b in fehler_von(bericht, "altbestand"))


# --- 6  Lösungsschlüssel ----------------------------------------------------
def test_prueffrage_ohne_wort_in_der_liste(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil1"]["A"]["task1"]["items"][0] = {
        "german": "Zahnrad", "english": "cogwheel", "pos": "noun",
    }
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("cogwheel" in b.text for b in fehler_von(bericht, "loesungsschluessel"))


def test_abweichende_loesung_wird_gefunden(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil1"]["A"]["task2"]["gaps"][0]["answer"] = "somethingelse"
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert fehler_von(bericht, "loesungsschluessel")


def test_uebersetzung_darf_nicht_driften(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil1"]["A"]["task1"]["items"][0]["german"] = "eine andere Bedeutung"
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert fehler_von(bericht, "loesungsschluessel")


def test_wort_darf_nicht_in_beiden_teilen_geprueft_werden(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil2"]["A"]["task1"]["items"][0] = copy.deepcopy(
        data["pruefungen"]["teil1"]["A"]["task1"]["items"][0]
    )
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("Teil 1 und in Teil 2" in b.text
               for b in fehler_von(bericht, "loesungsschluessel"))


# --- 7  Konsistenz zwischen den Niveaus -------------------------------------
def test_gemeinsame_pruefungswoerter_werden_vermerkt(db, settings, pack):
    """Ein Überschnitt ist erlaubt - aber er wird ausgewiesen, nicht verschwiegen."""
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil1"]["B"]["task1"]["items"][0] = copy.deepcopy(
        data["pruefungen"]["teil1"]["A"]["task1"]["items"][0]
    )
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert not fehler_von(bericht, "niveau_konsistenz")
    assert any("in beiden Niveaus geprüft" in b.text
               for b in befunde(bericht, "niveau_konsistenz"))


def test_deckungsgleiche_pruefungen_werden_gewarnt(db, settings, pack):
    """Ab der Hälfte gemeinsamer Wörter sind es keine zwei Fassungen mehr."""
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil1"]["B"] = copy.deepcopy(data["pruefungen"]["teil1"]["A"])
    data["pruefungen"]["teil1"]["B"]["meta"]["niveau"] = "B"
    bericht = pruefe_paket(Pack(data=data), db, settings)
    treffer = befunde(bericht, "niveau_konsistenz")
    assert any(b.stufe == "WARNUNG" and "in beiden Niveaus" in b.text for b in treffer)


def test_pruefungswort_ausserhalb_der_liste_wird_gemeldet(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil1"]["B"]["task1"]["items"][0] = {
        "german": "Zahnrad", "english": "cogwheel", "pos": "noun",
    }
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("steht nicht in Test 1" in b.text
               for b in fehler_von(bericht, "niveau_konsistenz"))


def test_pruefung_a_muss_schwerer_sein(db, settings, pack):
    """Werden die beiden Prüfungen vertauscht, fällt das auf."""
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil1"]["A"], data["pruefungen"]["teil1"]["B"] = (
        copy.deepcopy(data["pruefungen"]["teil1"]["B"]),
        copy.deepcopy(data["pruefungen"]["teil1"]["A"]),
    )
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("nicht schwerer" in b.text
               for b in fehler_von(bericht, "niveau_konsistenz"))


def test_beide_niveaus_pruefen_dieselbe_unit(db, settings, pack):
    bericht = pruefe_paket(pack, db, settings)
    assert not fehler_von(bericht, "niveau_konsistenz")
    assert "Teil 1" in bericht.kennzahlen["niveau_konsistenz"]


# --- 8  Platzhalter und Vorlage ---------------------------------------------
def test_offener_platzhalter_verhindert_den_bau(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["liste"]["test1"][3]["satz"] = ""
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert fehler_von(bericht, "vorlage")


def test_stehengebliebenes_todo_wird_gefunden(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil1"]["A"]["task2"]["text"] = "TODO: Lückentext {1} {2} {3} {4}"
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("Platzhalter" in b.text for b in fehler_von(bericht, "vorlage"))


def test_falsche_zahl_an_luecken_wird_gefunden(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["pruefungen"]["teil1"]["A"]["task2"]["text"] = (
        "The class went to the museum and looked at one {1} for a long time."
    )
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert any("Lückenmarker" in b.text for b in fehler_von(bericht, "vorlage"))


# --- 9  Herkunft ------------------------------------------------------------
def test_fehlende_herkunft_wird_gemeldet(db, settings, pack):
    data = copy.deepcopy(pack.data)
    data["quelle"] = {}
    bericht = pruefe_paket(Pack(data=data), db, settings)
    assert fehler_von(bericht, "herkunft")


def test_herkunft_steht_im_geruest(db, settings):
    data = scaffold(db, 1, settings)
    for key in ("datei", "importiert", "pruefsumme_sha256"):
        assert data["quelle"].get(key)


# --- 10  Unabhängigkeit von Teilanfragen ------------------------------------
def test_nur_ein_paket_je_unit(db, settings, tmp_path):
    from vocabmaster.pack import pack_filename

    assert pack_filename(3) == "unit_03.json"
    Pack(data=scaffold(db, 3, settings)).save(tmp_path / pack_filename(3))
    assert (tmp_path / "unit_03.json").exists()
    assert not list(tmp_path.glob("unit_03_*.json"))


def test_teilanfrage_laesst_die_liste_unberuehrt(tmp_path, pack, settings):
    from vocabmaster.documents import baue_alles, dateiname

    baue_alles(pack, tmp_path, settings, teile=("liste",))
    liste = tmp_path / dateiname(pack.unit, "VocabularyList")
    vorher = liste.read_bytes()
    baue_alles(pack, tmp_path, settings, teile=("test",), niveaus=("B",))
    assert liste.read_bytes() == vorher
    assert (tmp_path / dateiname(pack.unit, "Test", 1, "B")).exists()
    assert not (tmp_path / dateiname(pack.unit, "Test", 1, "A")).exists()


def test_altes_paketformat_wird_abgelehnt(tmp_path):
    """Aus der Zeit mit zwei Listen je Unit darf nichts überleben."""
    import json

    alt = tmp_path / "unit_01_A.json"
    alt.write_text(json.dumps({"schema": 1, "unit": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="älteren Fassung"):
        Pack.load(alt)
