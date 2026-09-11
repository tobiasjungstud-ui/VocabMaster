"""Niveau A und Niveau B - eine Liste, zwei Prüfungen.

Beide Gruppen lernen **dieselbe** Vokabelliste der Unit: 60 Wörter, Test 1
und Test 2. Es gibt keine zwei Wortlisten und keinen Wortschatz, den nur
eine Gruppe zu Gesicht bekommt.

Unterschieden wird erst bei der **Prüfung**:

* **Niveau A** (leistungsstärkere Gruppe, B1.2-B2.1) wird über die
  anspruchsvolleren Wörter der Liste geprüft und bekommt einen längeren
  Lückentext mit Nebensätzen.
* **Niveau B** (leistungsschwächere Gruppe, A2.2-B1.1) wird über die
  zugänglicheren Wörter derselben Liste geprüft und bekommt einen kürzeren
  Text mit kurzen Hauptsätzen.

Die beiden Prüfungen eines Teils sind überschneidungsfrei: Aus den 30
Wörtern eines Tests nimmt Niveau A die zwölf schwersten, Niveau B die
nächsten zwölf. Die sechs leichtesten bleiben ungeprüft.

Die Zahlen unten sind Zielbänder, keine harten Grenzen; die Prüfungen melden
Abweichungen als Warnung, damit sie bewusst entschieden werden.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .list.leveling import Bounds

NIVEAUS = ("A", "B")

#: Häufigkeitsfenster der **gemeinsamen** Vokabelliste.
#:
#: Der Klassenschnitt liegt bei B1.1-B1.2, also ist die Obergrenze dieselbe
#: wie im ursprünglichen VocabListMaker: Was häufiger vorkommt, kennen die
#: Lernenden im sechsten Englischjahr längst.
#:
#: Häufigkeit ist dabei nur das grobe Sieb. Sie trennt "marry" (4.40) nicht
#: von "fragile" (3.86), obwohl das eine bekannt und das andere Lernstoff
#: ist. Die eigentliche Arbeit leistet der Grundwortschatz in
#: ``list/data/a1_a2_core.txt`` samt seinen Ableitungsregeln.
LIST_BOUNDS = Bounds(too_easy=4.75, too_rare=2.45, label="B1.1-B2.1")

#: Höchstlänge eines Beispielsatzes in der Vokabelliste. Die Liste wird von
#: beiden Gruppen gelernt, also gilt das engere Mass der schwächeren.
SENTENCE_MAX_WORDS = 13


@dataclass(frozen=True)
class NiveauProfile:
    """Alles, was die Prüfung eines Niveaus von der anderen unterscheidet."""

    name: str
    label: str
    cefr: str
    beschreibung: str

    #: Aus welchem Teil der nach Schwierigkeit sortierten 30 Wörter eines
    #: Tests die Prüfung schöpft: Niveau A von Rang 1 an, Niveau B von dort,
    #: wo Niveau A aufgehört hat.
    zuerst: bool

    #: Zielband des Lückentextes.
    level_targets: dict = field(default_factory=dict)
    #: Zielband der Wortauswahl innerhalb der Prüfung.
    selection_targets: dict = field(default_factory=dict)

    @property
    def dateisuffix(self) -> str:
        return f"Niveau{self.name}"


#: Zielband des Lückentextes für Niveau A: B1.2-B2.1. Entspricht dem
#: bisherigen Zielband des VocabTestMaker.
_LEVEL_A = {
    "min_words": 70,
    "max_words": 130,
    "min_sentences": 4,
    "max_sentences": 8,
    "min_avg_sentence": 9.0,
    "max_avg_sentence": 20.0,
    "max_sentence_length": 28,
    "max_unknown_words": 3,
    "min_gap_distance": 6,
    "min_lead_in": 4,
    "min_tail": 3,
    "min_flesch_ease": 55.0,
    "max_flesch_grade": 9.5,
    "max_subordinators_per_sentence": 2.0,
}

#: Zielband für Niveau B: kürzer, kürzere Sätze, mehr Kontext um jede Lücke,
#: klar über der Lesbarkeitsschwelle, weniger Nebensätze und weniger Wörter
#: ausserhalb des Grundwortschatzes.
_LEVEL_B = {
    "min_words": 50,
    "max_words": 95,
    "min_sentences": 4,
    "max_sentences": 9,
    "min_avg_sentence": 7.0,
    "max_avg_sentence": 14.0,
    "max_sentence_length": 18,
    "max_unknown_words": 1,
    "min_gap_distance": 7,
    "min_lead_in": 4,
    "min_tail": 3,
    "min_flesch_ease": 70.0,
    "max_flesch_grade": 6.5,
    "max_subordinators_per_sentence": 1.0,
}

_SELECTION_A = {
    "min_mean_difficulty": 2.5,
    "min_item_difficulty": 1.0,
    "max_easy_cognates": 2,
    "max_multiword_items": 3,
    "max_share_one_word_class": 0.7,
}

#: Für Niveau B darf der Durchschnitt tiefer liegen - das ist der Zweck der
#: Fassung. Eine Untergrenze je Einzelwort gibt es hier nicht: Ein Wort wie
#: "repair", das im A1-B1-Grundwortschatz steht, ist für die stärkere Gruppe
#: kein Prüfstoff mehr, für die schwächere sehr wohl. Was auch hier nichts
#: prüft, sind Wörter zum Abschreiben ("Anekdote" -> "anecdote"); die hält
#: schon die Auswahl in `vocabmaster.pack` heraus, und `max_easy_cognates`
#: fängt den Rest.
_SELECTION_B = {
    "min_mean_difficulty": 1.4,
    "min_item_difficulty": 0.0,
    "max_easy_cognates": 3,
    "max_multiword_items": 2,
    "max_share_one_word_class": 0.7,
}


PROFILES: dict[str, NiveauProfile] = {
    "A": NiveauProfile(
        name="A",
        label="Niveau A",
        cefr="B1.2-B2.1",
        beschreibung=(
            "Leistungsstärkere Gruppe: geprüft werden die anspruchsvolleren "
            "Wörter der Liste, der Lückentext ist länger und darf Nebensätze "
            "enthalten."
        ),
        zuerst=True,
        level_targets=_LEVEL_A,
        selection_targets=_SELECTION_A,
    ),
    "B": NiveauProfile(
        name="B",
        label="Niveau B",
        cefr="A2.2-B1.1",
        beschreibung=(
            "Leistungsschwächere Gruppe: geprüft werden die zugänglicheren "
            "Wörter derselben Liste, der Lückentext ist kürzer und besteht "
            "aus kurzen Hauptsätzen."
        ),
        zuerst=False,
        level_targets=_LEVEL_B,
        selection_targets=_SELECTION_B,
    ),
}


def profile(name: str | NiveauProfile | None) -> NiveauProfile:
    """Liest 'A', 'a', 'Niveau B', 'niv. b' - oder gibt ein Profil durch."""
    if isinstance(name, NiveauProfile):
        return name
    if name is None:
        return PROFILES["A"]
    key = str(name).strip().upper()
    for candidate in NIVEAUS:
        if key == candidate or key.endswith((f" {candidate}", f".{candidate}")):
            return PROFILES[candidate]
    raise ValueError(
        f"Unbekanntes Niveau {name!r}. Erlaubt sind 'A' (stärkere Gruppe) "
        "und 'B' (schwächere Gruppe)."
    )


def other(name: str | NiveauProfile) -> NiveauProfile:
    """Das jeweils andere Niveau - für den Kontrastvergleich."""
    return PROFILES["B" if profile(name).name == "A" else "A"]


# ---------------------------------------------------------------------------
# Textstufe: wie schwer der Lückentext liest
# ---------------------------------------------------------------------------
#: Wie weit jede Messgrösse reicht, wenn die Textstufe von 0 auf 10 geht.
#:
#: Die Stufe ist absichtlich auf **derselben** Skala wie die Wortnote der
#: Prüfung (0-10), damit die beiden Regler vergleichbar bleiben. Die Anker
#: sind so gewählt, dass die 32 mitgelieferten Lückentexte dort landen, wo
#: sie hingehören: Niveau A im Schnitt bei 3.0, Niveau B bei 1.7, ohne eine
#: einzige Überlappung.
_TEXT_ANKER = {
    "laenge": (40.0, 140.0),        # Wörter im Text
    "satzlaenge": (6.0, 24.0),      # Wörter je Satz
    "lesbarkeit": (100.0, 45.0),    # Flesch-Lesbarkeit, fallend
    "nebensaetze": (0.0, 2.0),      # Nebensätze je Satz
}

#: Die gemessene Normallage der mitgelieferten Texte. Das ist der Punkt, auf
#: dem der Regler steht, solange niemand ihn anfasst - kein Richtwert,
#: sondern der Durchschnitt dessen, was tatsächlich im Paket liegt.
NORMAL_TEXTSTUFE = {"A": 3.0, "B": 1.7}

#: Wieviel Schulstufe (Flesch-Kincaid) eine ganze Reglerbreite ausmacht.
_GRAD_SPANNE = 9.0


def _anteil(wert: float, anker: tuple[float, float]) -> float:
    von, bis = anker
    if bis == von:
        return 0.0
    return max(0.0, min(10.0, (wert - von) / (bis - von) * 10.0))


def textstufe(stats: dict) -> float:
    """Wie schwer ein Lückentext liest, von 0 bis 10.

    ``stats`` ist das Ergebnis von :func:`vocabmaster.exam.english.readability`.
    Gewichtet wird, was die Prüfungen ohnehin messen: Länge, Satzlänge,
    Lesbarkeit und Nebensatzdichte - zu gleichen Teilen, damit sich keine
    einzelne Grösse verstecken kann.
    """
    saetze = max(1, int(stats.get("sentences", 0)) or 1)
    teile = (
        _anteil(float(stats.get("words", 0)), _TEXT_ANKER["laenge"]),
        _anteil(float(stats.get("words_per_sentence", 0)), _TEXT_ANKER["satzlaenge"]),
        _anteil(float(stats.get("flesch_reading_ease", 0)), _TEXT_ANKER["lesbarkeit"]),
        _anteil(float(stats.get("subordinators", 0)) / saetze,
                _TEXT_ANKER["nebensaetze"]),
    )
    return round(sum(teile) / len(teile), 2)


def ziele_fuer_textstufe(prof: NiveauProfile, stufe: float | None) -> dict:
    """Die Zielwerte des Lückentexts, verschoben auf eine andere Stufe.

    Auf der Normalstufe des Niveaus kommt **unverändert** heraus, was im
    Profil steht - der Regler in der Mitte ändert nichts. Von dort weg
    wandern alle vier Grössen gemeinsam: ein längerer Text hat auch längere
    Sätze, liest sich schwerer und verträgt mehr Nebensätze.

    Was nicht mitwandert, ist die Mechanik der Lücken (Abstand, Vorlauf,
    Auslauf): Sie hält den Text lösbar und hat mit Anspruch nichts zu tun.
    """
    ziele = dict(prof.level_targets)
    if stufe is None:
        return ziele
    delta = (float(stufe) - NORMAL_TEXTSTUFE[prof.name]) / 10.0
    if not delta:
        return ziele

    def spanne(anker: str) -> float:
        von, bis = _TEXT_ANKER[anker]
        return bis - von

    ziele["min_words"] = max(25, round(ziele["min_words"] + delta * spanne("laenge")))
    ziele["max_words"] = max(
        ziele["min_words"] + 20,
        round(ziele["max_words"] + delta * spanne("laenge")),
    )
    for schluessel in ("min_avg_sentence", "max_avg_sentence"):
        ziele[schluessel] = round(
            max(5.0, ziele[schluessel] + delta * spanne("satzlaenge")), 1
        )
    ziele["max_sentence_length"] = max(
        int(ziele["max_avg_sentence"]) + 4,
        round(ziele["max_sentence_length"] + delta * spanne("satzlaenge")),
    )
    ziele["min_flesch_ease"] = round(
        max(20.0, min(100.0, ziele["min_flesch_ease"] + delta * spanne("lesbarkeit"))), 1
    )
    ziele["max_flesch_grade"] = round(
        max(1.0, ziele["max_flesch_grade"] + delta * _GRAD_SPANNE), 1
    )
    ziele["max_subordinators_per_sentence"] = round(
        max(0.0, ziele["max_subordinators_per_sentence"] + delta * spanne("nebensaetze")),
        2,
    )
    return ziele
