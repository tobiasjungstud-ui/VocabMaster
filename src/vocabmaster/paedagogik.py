"""Pädagogisches Ranking - die **zuschaltbare** zweite Sortierung.

Die bestehende Auswahl ordnet nach Lernwert und Häufigkeit (Zipf). Sie
bleibt unverändert und ist weiterhin die Voreinstellung; dieses Modul wird
nur betreten, wenn es ausdrücklich verlangt wird. Kein Aufruf von hier
ändert etwas an :mod:`vocabmaster.list.leveling` oder am Pfad, der ohne
diese Option läuft.

**Wie gerankt wird - und warum nicht als Punktesumme.**

Sieben Kriterien gegeneinander zu verrechnen ergäbe eine Zahl, die niemand
mehr nachvollzieht, und die bei jedem Durchlauf anders ausfiele, weil schon
ein Hundertstel die Reihenfolge kippt. Stattdessen:

1. **Harter Vorfilter.** Die Schwierigkeitsstufe legt ein Zipf-Band fest.
   Was nicht hineinfällt, kommt gar nicht erst in die Wertung. Damit
   verschwinden "good" und "bad" aus jedem Durchlauf - ausser die Unit
   führt sie selbst als neuen Stoff.
2. **Feste Rangfolge innerhalb des Bandes.** Die Kriterien werden der
   Reihe nach abgefragt, nicht gemittelt. Erst wenn zwei Wörter im ersten
   gleichauf liegen, entscheidet das zweite. So bleibt die Reihenfolge
   über Durchläufe stabil und jede Entscheidung lässt sich benennen.

Die Rangfolge (`_RANGFOLGE`) beginnt mit dem, was die Unit vorgibt, und
endet mit dem, was nur noch feinjustiert.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .exam.difficulty import cognate_similarity
from .list.models import Candidate


# ---------------------------------------------------------------------------
# Stufen
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Stufe:
    """Eine Schwierigkeitsstufe mit ihrem harten Zipf-Band."""

    name: str
    titel: str
    zipf_min: float
    zipf_max: float
    beschreibung: str
    #: Untergrenze der beiden Schwierigkeits-Dimensionen zusammen. Ein Wort
    #: im richtigen Häufigkeitsband, das weder zu schreiben noch zu
    #: verwenden Mühe macht, ist trotzdem kein Lernstoff.
    mindest_schwierigkeit: float = 0.0


#: Die drei Stufen des Reglers. Die Bänder überlappen bewusst: Ein Wort
#: soll nicht deshalb herausfallen, weil es am Rand liegt.
#:
#: Zur Einordnung: Zipf 5.0 ist "good", 4.5 "lock", 4.1 "happily", 3.5
#: "orphanage", 2.8 "proclamation". Die Obergrenze von *basic* liegt
#: deshalb unter dem Grundwortschatz der Klasse, nicht darüber.
STUFEN: dict[str, Stufe] = {
    "basic": Stufe(
        "basic", "zugänglich", 3.60, 4.75,
        "Wörter, die eine Klasse auf B1.1 noch nicht sicher hat, aber oft "
        "wiedersieht.",
        mindest_schwierigkeit=0.10,
    ),
    "intermediate": Stufe(
        "intermediate", "mittel", 2.90, 4.40,
        "Der Bereich, in dem sich der Wortschatz einer Unit normalerweise "
        "bewegt.",
        mindest_schwierigkeit=0.16,
    ),
    "advanced": Stufe(
        "advanced", "anspruchsvoll", 2.45, 4.00,
        "Seltener, dafür ausdrucksstark - für Gruppen, die schon sicher sind.",
        mindest_schwierigkeit=0.24,
    ),
}

#: Die Voreinstellung des Reglers, wenn das Ranking eingeschaltet wird.
STUFE_VORGABE = "intermediate"

#: Was die Bänder in der Praxis durchlassen (Hauptteil, alle acht Units):
#: basic 15-31 Wörter je Unit, intermediate 5-18, advanced 1-9.
#:
#: Dass die oberen Bänder klein sind, ist kein Fehler der Grenzen, sondern
#: eine Eigenschaft dieses Lehrmittels: Wörter, die **zugleich** schwer zu
#: schreiben und schwer zu verwenden sind, gibt es darin wenige. Deshalb
#: wirft `ranken` nichts weg - das Band bestimmt die Rangfolge, nicht die
#: Mitgliedschaft. Der Regler verschiebt den Schwerpunkt einer Liste; er
#: kann keinen Wortschatz herbeiführen, den die Unit nicht hat.


# ---------------------------------------------------------------------------
# Die beiden Dimensionen der Schwierigkeit
# ---------------------------------------------------------------------------
#: Schreibfallen: stumme Buchstaben, Doppelungen, ie/ei, -ough.
_SCHREIBFALLEN = (
    r"ough", r"augh", r"[^aeiou]ie[^aeiou]", r"ei", r"(.)\1",
    r"^(kn|wr|ps|gn)", r"[^aeiou]{4}", r"tion$", r"ph",
)
#: Unregelmässige Formen, die man nicht ableiten kann.
_UNREGELMAESSIG = {
    "come across", "be worth", "be held", "come", "go", "take", "get",
    "make", "keep", "leave", "lie", "lay", "rise", "raise", "hang",
}
#: Was die Verwendung schwer macht: Präposition fest am Wort, reflexiv,
#: mehrdeutig, gehobenes Register.
_VERWENDUNGSFALLEN = re.compile(
    r"\b(of|to|for|with|about|on|in|at|from|into|after|up|out|off|down)\b",
    re.IGNORECASE,
)


#: Ab dieser Ähnlichkeit zum deutschen Stichwort schreibt man das englische
#: Wort ab, statt es zu können. "Teddybär" -> "teddy bear" ist keine
#: Rechtschreibleistung, wie selten das Wort auch sein mag.
ABSCHREIBBAR = 0.62


def schwer_zu_schreiben(c: Candidate) -> float:
    """0 bis 1: Rechtschreibung, Länge, unregelmässige Form.

    Wer das englische Wort aus dem deutschen Stichwort abschreiben kann,
    hat nichts zu schreiben gelernt - deshalb drückt die Ähnlichkeit zum
    Deutschen diesen Wert nach unten, unabhängig von allem anderen.
    """
    wort = (c.headword or c.english or "").lower()
    if not wort:
        return 0.0
    punkte = sum(1 for muster in _SCHREIBFALLEN if re.search(muster, wort))
    if len(wort) >= 11:
        punkte += 1
    if wort in _UNREGELMAESSIG:
        punkte += 2
    roh = min(1.0, punkte / 5.0)
    naehe = cognate_similarity(wort, c.german or "")
    if naehe >= ABSCHREIBBAR:
        # Vom Deutschen ablesbar: bleibt höchstens ein Rest.
        roh *= max(0.0, 1.0 - naehe)
    return round(roh, 3)


def schwer_zu_verwenden(c: Candidate) -> float:
    """0 bis 1: Grammatik, Kollokation, Register, Mehrdeutigkeit."""
    wort = (c.headword or c.english or "").lower()
    deutsch = (c.german or "").lower()
    punkte = 0.0
    if _VERWENDUNGSFALLEN.search(wort):
        punkte += 2          # feste Präposition - die häufigste Fehlerquelle
    if len(wort.split()) > 1:
        punkte += 1
    if "sich " in deutsch:
        punkte += 1          # reflexiv im Deutschen, nicht im Englischen
    if "," in deutsch or "/" in deutsch:
        punkte += 1          # mehrdeutig: mehrere Entsprechungen
    if c.zipf and c.zipf < 3.2:
        punkte += 1          # selten heisst meist: gehobenes Register
    return min(1.0, punkte / 5.0)


def fehleranfaelligkeit(c: Candidate) -> float:
    """Wie leicht man es falsch macht - beide Dimensionen zusammen."""
    return round((schwer_zu_schreiben(c) + schwer_zu_verwenden(c)) / 2, 3)


# ---------------------------------------------------------------------------
# Die übrigen Kriterien
# ---------------------------------------------------------------------------
def _woerter(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z]{3,}", text.lower())}


def unit_relevanz(c: Candidate, leitwoerter: list[str]) -> float:
    """Wie nah das Wort am Wortfeld der Unit liegt.

    Der Hauptteil der Unit zählt voll: Wer dort steht, ist per Definition
    Stoff dieser Unit. Ein ergänztes Wort muss sich über die Leitwörter
    ausweisen.
    """
    if str(c.section or "").strip().lower().startswith("unit"):
        return 1.0
    if not leitwoerter:
        return 0.5
    eigene = _woerter(f"{c.headword} {c.english} {c.topic}")
    treffer = sum(1 for leit in leitwoerter if _woerter(leit) & eigene)
    return min(1.0, 0.5 + 0.25 * treffer)


def kommunikativer_nutzen(c: Candidate) -> float:
    """Was man damit sagen kann - Verben und Adjektive tragen am meisten."""
    nach_wortart = {"verb": 1.0, "adj": 0.9, "noun": 0.7, "adv": 0.6}
    grund = nach_wortart.get(str(getattr(c.pos, "value", c.pos)), 0.6)
    if c.oxford3000:
        grund = min(1.0, grund + 0.1)
    return round(grund, 3)


def produktiver_nutzen(c: Candidate) -> float:
    """Nutzen fürs Sprechen und Schreiben, nicht nur fürs Verstehen.

    Ein Wort, das man selbst verwenden kann, ist mehr wert als eines, das
    man nur wiedererkennt. Häufigere Wörter und solche mit klarer Wortart
    sind eher produktiv.
    """
    wert = 0.5
    if c.zipf >= 3.4:
        wert += 0.3
    if str(getattr(c.pos, "value", c.pos)) in {"verb", "adj"}:
        wert += 0.2
    return round(min(1.0, wert), 3)


#: Die Rangfolge, in der entschieden wird. Vorn steht, was die Unit
#: vorgibt; hinten, was nur noch feinjustiert. Jede Stelle ist ein eigener
#: Vergleich - es wird nicht gemittelt.
_RANGFOLGE = (
    ("unit_relevanz", "Relevanz für die Unit"),
    ("fehleranfaelligkeit", "Fehleranfälligkeit"),
    ("lernwert", "Lernwert"),
    ("kommunikativer_nutzen", "kommunikativer Nutzen"),
    ("produktiver_nutzen", "Nutzen fürs Sprechen und Schreiben"),
    ("schwierigkeit", "Schwierigkeit"),
    ("zipf", "Häufigkeit (nur als Stichentscheid)"),
)


@dataclass(frozen=True)
class Bewertung:
    """Die Einzelwerte eines Wortes - damit jede Reihung erklärbar bleibt."""

    wort: str
    unit_relevanz: float
    fehleranfaelligkeit: float
    lernwert: float
    kommunikativer_nutzen: float
    produktiver_nutzen: float
    schwierigkeit: float
    zipf: float

    def schluessel(self) -> tuple:
        """Der Sortierschlüssel: Rangfolge statt Punktesumme."""
        return tuple(-round(getattr(self, feld), 2) for feld, _ in _RANGFOLGE)

    def begruendung(self) -> str:
        stark = [name for feld, name in _RANGFOLGE
                 if getattr(self, feld) >= 0.75]
        return ", ".join(stark) or "keine Stärke sticht heraus"


def bewerte(c: Candidate, leitwoerter: list[str]) -> Bewertung:
    return Bewertung(
        wort=c.headword or c.english,
        unit_relevanz=unit_relevanz(c, leitwoerter),
        fehleranfaelligkeit=fehleranfaelligkeit(c),
        lernwert=round(min(1.0, c.learning_value / 2.0), 3),
        kommunikativer_nutzen=kommunikativer_nutzen(c),
        produktiver_nutzen=produktiver_nutzen(c),
        schwierigkeit=round(c.difficulty, 3),
        zipf=round(c.zipf, 2),
    )


def im_band(c: Candidate, stufe: Stufe) -> bool:
    """Der harte Vorfilter: Häufigkeit **und** Schwierigkeit.

    Die Häufigkeit hält den Grundwortschatz draussen ("good", "bad" liegen
    über jedem Band). Die Schwierigkeit hält das andere Extrem draussen:
    ein seltenes Wort, das man aus dem Deutschen abschreibt und ohne
    Stolperstelle verwendet - "Teddybär", "Ohrring". Beides sind Wörter,
    die in jedem Durchlauf wieder auftauchen würden, ohne etwas zu lehren.

    Ohne Häufigkeitsangabe entscheidet allein die Schwierigkeit.
    """
    if c.zipf and not (stufe.zipf_min <= c.zipf <= stufe.zipf_max):
        return False
    return fehleranfaelligkeit(c) >= stufe.mindest_schwierigkeit


def ranken(
    kandidaten: list[Candidate],
    leitwoerter: list[str] | None = None,
    stufe: str = STUFE_VORGABE,
) -> tuple[list[Candidate], list[Bewertung]]:
    """Sortiert nach pädagogischen Kriterien - im Band der Stufe zuerst.

    Wörter ausserhalb des Bandes werden **nicht weggeworfen**: Sie rücken
    ans Ende, damit die Auswahl auch dann auf ihre 60 kommt, wenn das Band
    zu eng war. Der Bericht weist beide Gruppen getrennt aus.
    """
    gewaehlt = STUFEN.get(str(stufe).lower(), STUFEN[STUFE_VORGABE])
    leit = list(leitwoerter or [])

    drin, draussen = [], []
    for c in kandidaten:
        (drin if im_band(c, gewaehlt) else draussen).append(c)

    def sortiere(gruppe: list[Candidate]) -> list[tuple[Candidate, Bewertung]]:
        paare = [(c, bewerte(c, leit)) for c in gruppe]
        # Der Wortlaut entscheidet Gleichstände bis zum Schluss, damit
        # zwei Durchläufe dieselbe Reihenfolge ergeben.
        paare.sort(key=lambda p: (*p[1].schluessel(), p[1].wort.lower()))
        return paare

    geordnet = sortiere(drin) + sortiere(draussen)
    return [c for c, _ in geordnet], [b for _, b in geordnet]


def ausgewogen(kandidaten: list[Candidate]) -> dict[str, int]:
    """Wie sich eine Auswahl über die Wortarten verteilt."""
    return dict(Counter(
        str(getattr(c.pos, "value", c.pos)) for c in kandidaten
    ))
