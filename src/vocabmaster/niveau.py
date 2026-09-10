"""Niveau A und Niveau B - zwei Fassungen desselben Unterrichtsstoffs.

Beide Gruppen lernen dieselbe Unit, aber nicht dieselbe Auswahl:

* **Niveau A** (leistungsstärkere Gruppe), Zielband **B1.2-B2.1**: die
  anspruchsvolleren Wörter der Unit - seltener, abstrakter, mehrteilig,
  weiter vom deutschen Wort entfernt.
* **Niveau B** (leistungsschwächere Gruppe), Zielband **A2.2-B1.1**: die
  zugänglicheren Wörter derselben Unit - häufiger, konkreter, meist
  einteilig - und ein kürzerer, klarer gebauter Lückentext.

Die beiden Listen sind **überschneidungsfrei**: Ein Wort steht entweder in
der Liste für Niveau A oder in der für Niveau B, nie in beiden. Das ist der
Grund für die getrennten Häufigkeitsfenster. Ein Wort mit Zipf 4.9 ist für
die stärkere Gruppe längst bekannt und deshalb kein Prüfstoff; für die
schwächere Gruppe ist es genau richtig. Umgekehrt ist ein Wort mit Zipf 2.8
für Niveau B zu exotisch und für Niveau A der eigentliche Zugewinn.

Wichtig ist, was **nicht** unterschieden wird: Beide Fassungen ziehen aus
demselben Hauptteil derselben Unit, beide schliessen den A1/A2-Grund\
wortschatz und blosse Kognate aus, und beide durchlaufen dieselben
Kontrollen. Ein Niveau-B-Test ist kein schlechterer Test, sondern ein Test
über die Wörter, an denen diese Gruppe wirklich etwas lernt.

Die Zahlen unten sind Zielbänder, keine harten Grenzen; die Prüfungen melden
Abweichungen als Warnung, damit sie bewusst entschieden werden.
"""

from __future__ import annotations

from dataclasses import dataclass, field

NIVEAUS = ("A", "B")


@dataclass(frozen=True)
class NiveauProfile:
    """Alles, was ein Niveau von dem anderen unterscheidet."""

    name: str
    label: str
    beschreibung: str
    #: Zielband nach GER, so wie es auf dem Deckblatt steht.
    cefr: str

    # --- Wortauswahl ------------------------------------------------------
    #: Gewicht der Schwierigkeit bei der Auswahl. Positiv = schwere Wörter
    #: zuerst, negativ = zugängliche Wörter zuerst.
    difficulty_weight: float
    #: Häufigkeitsfenster (Zipf, wordfreq: 7 = "the", 1 = sehr selten).
    #: Oberhalb von ``zipf_max`` gilt ein Wort für dieses Niveau als längst
    #: bekannt, unterhalb von ``zipf_min`` als zu exotisch. Die Fenster der
    #: beiden Niveaus überlappen sich in der Mitte; welche Fassung ein Wort
    #: aus dem Überlappungsbereich bekommt, entscheidet die Zuteilung in
    #: :mod:`vocabmaster.pool`.
    zipf_min: float
    zipf_max: float
    #: Mitte des Fensters - Massstab für die Zuteilung strittiger Wörter.
    zipf_centre: float
    #: Höchstanteil mehrteiliger Ausdrücke an einer Liste.
    max_multiword_share: float
    #: Höchstzahl Wörter, deren englische Form fast der deutschen gleicht.
    max_cognate_share: float

    # --- Beispielsätze der Vokabelliste ----------------------------------
    sentence_max_words: int

    # --- Lückentext der Prüfung ------------------------------------------
    level_targets: dict = field(default_factory=dict)
    selection_targets: dict = field(default_factory=dict)

    @property
    def dateisuffix(self) -> str:
        return f"Niv_{self.name}"


#: Zielband des Lückentextes für Niveau A: B1.2-B2.1, mittlere bis gehobene
#: Anforderung. Entspricht dem bisherigen Zielband des VocabTestMaker.
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
#: klar über der Lesbarkeitsschwelle. Weniger Nebensätze, weniger Wörter
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
#: Fassung. Eine Untergrenze bleibt trotzdem: Wörter, die man einfach aus
#: dem deutschen Stichwort abschreibt, prüfen auch hier nichts.
_SELECTION_B = {
    "min_mean_difficulty": 1.6,
    "min_item_difficulty": 0.8,
    "max_easy_cognates": 3,
    "max_multiword_items": 2,
    "max_share_one_word_class": 0.7,
}


PROFILES: dict[str, NiveauProfile] = {
    "A": NiveauProfile(
        name="A",
        label="Niveau A",
        beschreibung=(
            "Leistungsstärkere Gruppe, B1.2-B2.1: die anspruchsvolleren Wörter "
            "der Unit, längerer Lückentext mit mehr Nebensätzen."
        ),
        cefr="B1.2-B2.1",
        difficulty_weight=+0.55,
        zipf_min=2.45,
        zipf_max=4.60,
        zipf_centre=3.55,
        max_multiword_share=0.30,
        max_cognate_share=0.10,
        sentence_max_words=16,
        level_targets=_LEVEL_A,
        selection_targets=_SELECTION_A,
    ),
    "B": NiveauProfile(
        name="B",
        label="Niveau B",
        beschreibung=(
            "Leistungsschwächere Gruppe, A2.2-B1.1: die zugänglicheren Wörter "
            "derselben Unit, kürzerer Lückentext mit kurzen Hauptsätzen."
        ),
        cefr="A2.2-B1.1",
        difficulty_weight=-0.45,
        zipf_min=3.20,
        zipf_max=5.35,
        zipf_centre=4.35,
        max_multiword_share=0.15,
        max_cognate_share=0.15,
        sentence_max_words=13,
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
        if key == candidate or key.endswith(f" {candidate}") or key.endswith(f".{candidate}"):
            return PROFILES[candidate]
    raise ValueError(
        f"Unbekanntes Niveau {name!r}. Erlaubt sind 'A' (stärkere Gruppe) "
        "und 'B' (schwächere Gruppe)."
    )


def other(name: str | NiveauProfile) -> NiveauProfile:
    """Das jeweils andere Niveau - für den Kontrastvergleich."""
    return PROFILES["B" if profile(name).name == "A" else "A"]
