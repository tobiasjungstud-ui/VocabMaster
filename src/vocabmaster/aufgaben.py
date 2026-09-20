"""Welche Aufgabentypen eine Prüfung haben kann - und wie sich die Wörter
auf sie verteilen.

Eine Prüfung war einmal zwei feste Aufgaben: übersetzen und einsetzen. Das
ist eine Form, keine Notwendigkeit. Übersetzen prüft, **was** ein Wort
heisst; einsetzen, **wo** es hingehört. Was eine Klasse darüber hinaus
können muss - das Wort erkennen, wenn es umschrieben wird, es richtig
gebrauchen, es selbst in einen Satz bringen -, prüft keines von beiden.

Deshalb steht hier ein **Katalog**: je Art ein Name, ein Gewicht bei der
Verteilung, eine Mindestzahl und die Form ihrer Überschrift. Die Prüfung
selbst ist dann nur noch eine Liste solcher Aufgaben.

Was **nicht** hier steht, ist der Inhalt: kein Beispielsatz, keine
Umschreibung, kein Mini-Text. Die entstehen im Chat, wie alles andere
Unterrichtsmaterial in diesem Repository auch.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Die klassischen zwei - so hiessen sie, als es nur sie gab.
UEBERSETZEN = "uebersetzen"
LUECKEN = "luecken"
#: Welcher von drei Sätzen verwendet das Wort richtig?
WORTWAHL = "wortwahl"
#: Eine englische Umschreibung, das Wort ist hinzuschreiben.
DEFINITION = "definition"
#: Zwei Sätze, einer verwendet das Wort richtig.
RICHTIG_FALSCH = "richtig_falsch"
#: Zwei bis drei Wörter in einem Mini-Text unterbringen.
SCHREIBEN = "schreiben"


@dataclass(frozen=True)
class Aufgabenart:
    """Alles, was eine Aufgabenart von den anderen unterscheidet."""

    kennung: str
    titel: str
    #: Eine Zeile für die Oberfläche - was die Aufgabe von der Klasse verlangt.
    beschreibung: str
    #: Anteil an der Wortzahl. Die beiden klassischen stehen auf 4 zu 2,
    #: damit zwölf Wörter weiterhin acht zum Übersetzen und vier Lücken
    #: ergeben - wer nur sie ankreuzt, bekommt die Prüfung von bisher.
    gewicht: int
    #: Unter dieser Zahl ist die Aufgabe keine mehr: ein Lückentext mit
    #: einer Lücke, ein Mini-Text mit einem Wort.
    mindestens: int
    #: Punkte je geprüftem Wort.
    punkte_je_wort: int = 1
    #: Wie viele Tabulatoren zwischen Überschrift und Punktzahl stehen.
    #: Die Vorlage setzt die Punktzahl rechtsbündig; die Zahl hängt an der
    #: Länge des Aufgabentextes.
    tabs: int = 5
    #: Wie viele Wörter höchstens in **einen** Block gehören. Nur
    #: Micro-Writing bündelt; alles andere prüft ein Wort je Aufgabe.
    je_block: int = 1


#: Der Katalog. Die Reihenfolge ist die Reihenfolge auf dem Blatt.
ARTEN: dict[str, Aufgabenart] = {
    a.kennung: a
    for a in (
        Aufgabenart(
            UEBERSETZEN, "Tabellen-Übersetzung",
            "deutsches Stichwort, englisches Wort hinschreiben",
            gewicht=4, mindestens=1, tabs=5,
        ),
        Aufgabenart(
            LUECKEN, "Lückentext",
            "ein Text mit Lücken, dazu die Wörter als Bank",
            gewicht=2, mindestens=2, tabs=4,
        ),
        Aufgabenart(
            WORTWAHL, "Wortbedeutung — welcher von drei Sätzen stimmt?",
            "drei Sätze je Wort, zwei davon mit falscher Verwendung",
            gewicht=2, mindestens=1, tabs=5,
        ),
        Aufgabenart(
            DEFINITION, "Definition — welches Wort ist gemeint?",
            "eine englische Umschreibung, das Wort ist hinzuschreiben",
            gewicht=2, mindestens=1, tabs=5,
        ),
        Aufgabenart(
            RICHTIG_FALSCH, "Correct / Incorrect Use",
            "zwei Sätze je Wort, nur einer verwendet es richtig",
            gewicht=2, mindestens=1, tabs=5,
        ),
        Aufgabenart(
            SCHREIBEN, "Micro-Writing",
            "zwei bis drei Wörter in einem kurzen Text unterbringen",
            gewicht=1, mindestens=2, tabs=5, je_block=3,
        ),
    )
}

#: Die Prüfung, wie es sie immer gab. Wer nichts anderes ankreuzt, bekommt
#: sie unverändert.
KLASSISCH = (UEBERSETZEN, LUECKEN)

#: Wie viele Sätze die beiden Wahl-Arten vorlegen.
SAETZE_ZUR_WAHL = {WORTWAHL: 3, RICHTIG_FALSCH: 2}


def art(kennung: str) -> Aufgabenart:
    """Die Art zu ihrer Kennung - mit einer Fehlermeldung, die sie nennt."""
    if kennung not in ARTEN:
        raise KeyError(
            f"'{kennung}' ist keine Aufgabenart. Es gibt: "
            + ", ".join(ARTEN)
        )
    return ARTEN[kennung]


def sortiert(kennungen) -> list[str]:
    """Die angegebenen Arten in der Reihenfolge des Blattes, ohne Doppel."""
    gewaehlt = {str(k) for k in kennungen}
    return [k for k in ARTEN if k in gewaehlt]


def verteile(gesamt: int, kennungen) -> dict[str, int]:
    """Die Wortzahl der Prüfung auf ihre Aufgaben verteilen.

    Proportional zum Gewicht, der Rest nach dem grössten Bruchteil - und
    was darunter unter seine Mindestzahl fiele, wird darauf angehoben,
    zulasten der grössten Aufgabe. Das Ergebnis hängt nur an der Eingabe;
    zweimal dasselbe gibt zweimal dasselbe.

    Für die beiden klassischen Arten kommt bei zwölf Wörtern weiterhin
    **acht und vier** heraus. Das ist kein Zufall, sondern der Grund für
    die Gewichte 4 und 2 - ein Test wacht darüber.

    Reicht ``gesamt`` nicht einmal für die Mindestzahlen, bekommt jede Art
    ihre Mindestzahl. Die Summe liegt dann über ``gesamt``; das zu
    verschweigen hiesse, eine Aufgabe ohne Wörter zu bauen.
    """
    arten = sortiert(kennungen)
    if not arten:
        return {}
    minima = {k: ARTEN[k].mindestens for k in arten}
    if gesamt <= sum(minima.values()):
        return minima

    gewichte = {k: ARTEN[k].gewicht for k in arten}
    summe = sum(gewichte.values())
    genau = {k: gesamt * gewichte[k] / summe for k in arten}
    anteil = {k: int(genau[k]) for k in arten}
    rest = gesamt - sum(anteil.values())
    # Der grösste Bruchteil zuerst; bei Gleichstand die Reihenfolge des
    # Blattes, damit zwei Durchläufe dasselbe ergeben.
    nach_rest = sorted(arten, key=lambda k: (-(genau[k] - anteil[k]), arten.index(k)))
    for k in nach_rest[:rest]:
        anteil[k] += 1

    # Mindestzahlen durchsetzen - genommen wird bei der grössten Aufgabe,
    # solange sie dabei selbst nicht unter ihre Mindestzahl fällt.
    for k in arten:
        while anteil[k] < minima[k]:
            geber = max(
                (g for g in arten if anteil[g] - 1 >= minima[g]),
                key=lambda g: (anteil[g], -arten.index(g)),
                default=None,
            )
            if geber is None:
                break
            anteil[geber] -= 1
            anteil[k] += 1
    return anteil
