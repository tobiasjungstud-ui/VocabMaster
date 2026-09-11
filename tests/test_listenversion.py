"""Welche Liste meint dieser Test?

Das ist die Frage, die sich zwei Tage nach dem Bauen stellt und die vorher
niemand stellt. Jede Prüfung trägt deshalb den Fingerabdruck ihrer Liste.
Der klassische Fehler ist, dass eine Liste still ausgetauscht wird und der
Lösungsschlüssel danach auf Wörter zeigt, die nicht mehr darin stehen.
"""

from __future__ import annotations

import pytest

from vocabmaster.checks import pruefe_paket
from vocabmaster.documents import dateiname
from vocabmaster.pack import (
    _wortangabe,
    liste_fingerabdruck,
    neue_liste,
    pack_filename,
)


def test_abdruck_haengt_an_den_woertern_nicht_an_den_saetzen():
    a = [{"englisch": "orphanage", "deutsch": "Waisenhaus", "satz": "Ein Satz."}]
    b = [{"englisch": "orphanage", "deutsch": "Waisenhaus", "satz": "Ganz anders."}]
    c = [{"englisch": "orphanage", "deutsch": "Heim", "satz": "Ein Satz."}]
    assert liste_fingerabdruck(a) == liste_fingerabdruck(b), "Sätze zählen nicht mit"
    assert liste_fingerabdruck(a) != liste_fingerabdruck(c), "Glossen zählen mit"


def test_jede_pruefung_haengt_an_der_liste_im_paket(pack, db, settings):
    bericht = pruefe_paket(pack, db, settings)
    assert not [b for b in bericht.fehler if b.pruefung == "listenbezug"]
    for spec in pack.exams.values():
        assert spec["meta"]["liste_fingerabdruck"] == pack.liste_abdruck


def test_vertauschte_liste_faellt_auf(pack, db, settings):
    """Der eigentliche Zweck: ein ausgetauschtes Wort macht den Bezug kaputt."""
    pack.data["liste"]["test1"][0]["englisch"] = "something-else"
    bericht = pruefe_paket(pack, db, settings)
    befunde = [b for b in bericht.fehler if b.pruefung == "listenbezug"]
    assert len(befunde) == len(pack.exams), "jede Prüfung muss sich melden"


def test_neue_liste_wertet_die_zugaenglichsten_woerter_auf(pack, db, settings):
    """Das aufgewertete Wort tritt an die Stelle des zugänglichsten."""
    from vocabmaster.pack import _schwierigkeit

    neu = neue_liste(pack, db, fancy=0, eigene=["misleading=irreführend"],
                     settings=settings)
    assert neu.liste_version == pack.liste_version + 1
    assert len(neu.all_entries) == len(pack.all_entries), "die Liste bleibt bei 60"
    assert "misleading" in {e["englisch"] for e in neu.all_entries}

    ersetzt = neu.data["abgeleitet_von"]["ersetzt"]
    assert len(ersetzt) == 1
    gewichen = ersetzt[0]["raus"]
    geblieben = [_schwierigkeit(e) for e in neu.all_entries
                 if e.get("englisch") and e.get("herkunft") != "fancy"]
    weg = next(e for e in pack.all_entries if e["englisch"] == gewichen)
    assert _schwierigkeit(weg) <= min(geblieben) + 0.01


def test_neue_liste_bindet_die_pruefungen_neu(pack, db, settings):
    neu = neue_liste(pack, db, fancy=2, settings=settings)
    assert neu.exams, "die Prüfungen müssen mitkommen"
    for spec in neu.exams.values():
        assert spec["meta"]["liste_fingerabdruck"] == neu.liste_abdruck
        assert spec["meta"]["liste_version"] == neu.liste_version
    offen = [e for e in neu.all_entries
             if e.get("herkunft") == "fancy" and not e.get("englisch")]
    assert len(offen) == 2, "die Anwendung erfindet die Wörter nicht selbst"
    for e in offen:
        # Das Fach liefert die Lage, nicht das Ergebnis.
        assert pack.thema in e["hinweis"], "das Wortfeld der Unit muss dabeistehen"
        assert e["ersetzt"], "wofür der Platz frei wurde, gehört dazu"
        assert "begruendung" in e, "die Begründung wird im Paket festgehalten"


def test_neue_liste_setzt_die_luckentexte_neu_an(pack, db, settings):
    """Andere Liste, andere Prüfungswörter - ein alter Text passte nicht.

    Beispielsätze wandern mit (sie gehören zum Wort), Lückentexte nicht
    (sie gehören zu ihren vier Lücken).
    """
    neu = neue_liste(pack, db, fancy=1, settings=settings)
    for schluessel, spec in neu.exams.items():
        alt = pack.exams[schluessel]["task2"]["text"]
        assert spec["task2"]["text"] != alt, (
            f"{schluessel}: der Text von V1 darf nicht stehen bleiben"
        )


def test_neue_liste_verweigert_unsinn(pack, db, settings):
    with pytest.raises(ValueError):
        neue_liste(pack, db, fancy=99, settings=settings)


@pytest.mark.parametrize("text,erwartet", [
    ("dreadful=schrecklich", ("dreadful", "schrecklich")),
    ("schrecklich=dreadful", ("dreadful", "schrecklich")),
    ("en:crucial=entscheidend", ("crucial", "entscheidend")),
    ("exhausted=erschöpft", ("exhausted", "erschöpft")),
])
def test_wortangabe_erkennt_die_seiten(text, erwartet):
    assert _wortangabe(text) == erwartet


def test_wortangabe_raet_nicht_wenn_sie_es_nicht_weiss():
    """Lieber eine Rückfrage als eine vertauschte Vokabel."""
    with pytest.raises(ValueError, match="en:"):
        _wortangabe("rot=red")
    with pytest.raises(ValueError):
        _wortangabe("dreadful")


def test_dateinamen_trennen_die_listenversionen():
    assert pack_filename(1) == "unit_01.json"
    assert pack_filename(1, liste_version=2) == "unit_01_v2.json"
    assert pack_filename(1, fassung=3, liste_version=2) == "unit_01_v2_fassung3.json"
    assert dateiname(1, "VocabularyList", liste_version=2) != dateiname(
        1, "VocabularyList", liste_version=1
    )


def test_das_fach_gibt_die_lage_vor_nicht_die_antwort(pack, db, settings):
    """Zwei Units, zwei verschiedene Lagen - sonst wäre es eine Schablone."""
    neu = neue_liste(pack, db, fancy=1, settings=settings)
    fach = next(e for e in neu.all_entries
                if e.get("herkunft") == "fancy" and not e.get("englisch"))
    hinweis = fach["hinweis"]
    assert pack.thema in hinweis
    assert "Prüfnote" in hinweis, "warum dieser Platz frei wurde, gehört dazu"
    # Und kein fertiges Wort, das die Auswahl vorwegnimmt.
    assert not any(w in hinweis.lower() for w in
                   ("dreadful", "packed", "exhausted", "crucial", "fascinating"))


def test_uebernommener_lueckentext_wird_als_ueberholt_erkannt():
    """Ein Text ist für *bestimmte* Lücken geschrieben.

    Werden die Prüfungswörter neu gesetzt, passt er nicht mehr: Der Satz,
    der 'checkout' erschliessbar machte, steht dann über einer anderen
    Lösung. Das lief lange still durch - hier nicht mehr.
    """
    from vocabmaster.pack import _text_uebernehmen

    alt = {"task2": {"text": "Ein Satz mit {1}.",
                     "gaps": [{"answer": "checkout"}]}}
    gleich = {"task2": {"text": "TODO", "gaps": [{"answer": "checkout"}]}}
    anders = {"task2": {"text": "TODO", "gaps": [{"answer": "downside"}]}}

    _text_uebernehmen(alt, gleich)
    assert gleich["task2"]["text"] == "Ein Satz mit {1}."
    assert "text_ueberholt" not in gleich["task2"], "gleiche Lücken, alles gut"

    _text_uebernehmen(alt, anders)
    assert anders["task2"]["text"] == "Ein Satz mit {1}.", "Handarbeit bleibt"
    assert anders["task2"]["text_ueberholt"] == ["checkout"]


def test_ueberholter_lueckentext_ist_ein_fehler(pack, db, settings):
    """Und der Selbstcheck lässt ihn nicht durch."""
    from vocabmaster.checks import pruefe_paket

    spec = pack.data["pruefungen"]["teil1"]["A"]["task2"]
    spec["text_ueberholt"] = ["irgendein", "anderes", "wort"]
    bericht = pruefe_paket(pack, db, settings)
    passend = [b for b in bericht.fehler if "text_ueberholt" in b.text]
    assert passend, "ein Text für andere Lücken muss ein Fehler sein"


def test_neue_liste_waehlt_frisch_aus_der_datenbank(pack, db, settings):
    """Eine zweite Liste wird gewählt, nicht aus der ersten geflickt.

    Der klassische Fehler wäre, V1 zu kopieren und ein paar Wörter zu
    tauschen: Dann bliebe die Frage "welche 60 Wörter dieser Unit sind die
    lehrreichsten?" für immer einmal beantwortet.
    """
    neu = neue_liste(pack, db, fancy=0, settings=settings)
    alt_w = {e["englisch"] for e in pack.all_entries}
    neu_w = {e["englisch"] for e in neu.all_entries if e.get("englisch")}

    herkunft = neu.data["abgeleitet_von"]
    assert set(herkunft["neu_gewaehlt"]) == neu_w - alt_w
    assert herkunft["neu_gewaehlt"], (
        "Unit 1 hat Reserve im Hauptteil - davon muss etwas ankommen"
    )
    assert len(neu.all_entries) == len(pack.all_entries)


def test_neue_liste_uebernimmt_die_beispielsaetze(pack, db, settings):
    """Ein Satz gehört zum Wort, nicht zur Liste."""
    neu = neue_liste(pack, db, fancy=0, settings=settings)
    alt_saetze = {e["englisch"]: e["satz"] for e in pack.all_entries if e.get("satz")}
    for e in neu.all_entries:
        if e.get("englisch") in alt_saetze and e.get("herkunft") != "fancy":
            assert e["satz"] == alt_saetze[e["englisch"]], (
                f"{e['englisch']}: der Satz war schon geschrieben"
            )
    assert neu.data["abgeleitet_von"]["saetze_uebernommen"] > 40


def test_neue_liste_verschlechtert_die_auswahl_nicht(pack, db, settings):
    """Neuheit darf nicht auf Kosten des Lernwerts gehen.

    Die Vorliebe für ungenutzte Wörter entscheidet Gleichstände; sie darf
    die Liste nicht spürbar absacken lassen.
    """
    from vocabmaster.pack import _schwierigkeit

    neu = neue_liste(pack, db, fancy=0, settings=settings)
    alt_m = sum(_schwierigkeit(e) for e in pack.all_entries) / len(pack.all_entries)
    neu_eintraege = [e for e in neu.all_entries if e.get("englisch")]
    neu_m = sum(_schwierigkeit(e) for e in neu_eintraege) / len(neu_eintraege)
    assert neu_m > alt_m - 0.35, (
        f"V2 sackt ab: Ø {neu_m:.2f} gegen Ø {alt_m:.2f} in V1"
    )


def test_niveau_b_steht_im_kopf(pack):
    """Wer austeilt, muss die B-Blätter auf einen Blick erkennen."""
    for (teil, niveau), spec in pack.exams.items():
        kopf = spec["header"]["unit"]
        if niveau == "B":
            assert kopf.endswith("Niv. B"), kopf
        else:
            assert "Niv." not in kopf, f"Niveau A trägt keinen Zusatz: {kopf}"
        assert ("Part I" if teil == 1 else "Part II") in kopf
