"""Der Selbstcheck vor der Ausgabe - nachvollziehbar, nicht behauptet.

Jede Prüfung hat eine Kennung, eine Stufe und eine Begründung, die den
konkreten Befund nennt. Bei ``FEHLER`` wird nicht gebaut.

Die zehn geforderten Kontrollmechanismen und wo sie stattfinden:

===  ==========================  ==================================================
 1   ``thema``                   Passt jedes Wort zum Unit-Thema?
 2   ``neuwoerter``              Höchstens 40 % selbst ergänzt.
 3   ``cefr``                    Sätze und Lückentexte im Band des Niveaus.
 4   ``dubletten``               Keine Doppelung, kein Widerspruch in Wortart
                                 oder Übersetzung.
 5   ``altbestand``              Kein Wort aus einer alten Wortliste.
 6   ``loesungsschluessel``      Prüfung und Liste sagen dasselbe.
 7   ``niveau_konsistenz``       A und B: dasselbe Thema, andere Komplexität.
 8   ``vorlage``                 Keine leeren Platzhalter, Layout unverändert.
 9   ``herkunft``                Quelle und Datum am Dokument.
10   ``unabhaengigkeit``         Teilanfragen ändern keine fremden Dateien.
===  ==========================  ==================================================

Dazu laufen unverändert die Prüfungen der beiden Ursprungsanwendungen: die
Listenkontrolle aus :mod:`vocabmaster.list.validation` (Wortauswahl,
Balance, Beispielsätze, Seitenumfang) und die zwanzig Prüfungen aus
:mod:`vocabmaster.exam.check` (Spec, Auswahl, Lückentext, Englisch, Niveau).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import Settings
from .database import Database
from .exam import english as exam_english
from .exam.check import ExamChecker
from .exam.vocab import guess_pos, normalise
from .list.leveling import score_candidate
from .list.models import Candidate, Severity
from .list.normalize import headword, normalize_key
from .list.validation import validate_all
from .niveau import (
    LIST_BOUNDS,
    NIVEAUS,
    NORMAL_TEXTSTUFE,
    PROFILES,
    SENTENCE_MAX_WORDS,
    textstufe,
    ziele_fuer_textstufe,
)
from .pack import Pack

FEHLER, WARNUNG, HINWEIS = "FEHLER", "WARNUNG", "HINWEIS"
_RANK = {FEHLER: 0, WARNUNG: 1, HINWEIS: 2}

#: Inhaltswörter, die für die Themenprüfung nichts aussagen.
_STOPWORDS = set(
    """a an the and or but if then than that this these those there here of in on at to
    for with from by as is are was were be been being have has had do does did will
    would can could should may might must not no yes it its he she they them his her
    their you your we our i me my so very too also just about into over under out up
    down when what which who how why some any all most more much many few both each
    every other another such same own new old good bad big small get got make made take
    go went come came see saw know knew think thought say said one two three first
    second last next people person thing things time day week year""".split()
)


@dataclass
class Befund:
    stufe: str
    pruefung: str
    text: str

    def __str__(self) -> str:
        return f"[{self.stufe:<7}] {self.pruefung}: {self.text}"


@dataclass
class Pruefbericht:
    """Das Ergebnis des Selbstchecks."""

    befunde: list[Befund] = field(default_factory=list)
    kennzahlen: dict = field(default_factory=dict)
    gelaufen: list[str] = field(default_factory=list)

    def add(self, stufe: str, pruefung: str, text: str) -> None:
        self.befunde.append(Befund(stufe, pruefung, text))

    @property
    def fehler(self) -> list[Befund]:
        return [b for b in self.befunde if b.stufe == FEHLER]

    @property
    def warnungen(self) -> list[Befund]:
        return [b for b in self.befunde if b.stufe == WARNUNG]

    @property
    def ok(self) -> bool:
        return not self.fehler

    def sortieren(self) -> Pruefbericht:
        self.befunde.sort(key=lambda b: (_RANK[b.stufe], b.pruefung))
        return self

    def bestanden(self, pruefung: str) -> bool:
        return not any(
            b.pruefung == pruefung and b.stufe == FEHLER for b in self.befunde
        )

    def uebersicht(self) -> list[str]:
        """Eine Zeile je Prüfung - der Kurzbericht für die Lehrperson."""
        lines = []
        for name in self.gelaufen:
            treffer = [b for b in self.befunde if b.pruefung == name]
            fehler = sum(1 for b in treffer if b.stufe == FEHLER)
            warn = sum(1 for b in treffer if b.stufe == WARNUNG)
            mark = "✗" if fehler else ("!" if warn else "✓")
            detail = self.kennzahlen.get(name, "")
            lines.append(
                f"  {mark} {name:<20} {detail}"
                + (f"  ({fehler} Fehler, {warn} Warnungen)" if fehler or warn else "")
            )
        return lines


# ---------------------------------------------------------------------------
# 1  Themenkongruenz
# ---------------------------------------------------------------------------
#: Ab so vielen anderen Units gilt ein Wort als allgemein und taugt nicht
#: mehr als Beleg für Themenzugehörigkeit.
_GENERISCH_AB = 4


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]{4,}", text.lower()) if t not in _STOPWORDS}


def _topic_vocabulary(db: Database, unit: int) -> set[str]:
    """Das **unterscheidende** Wortfeld der Unit, aus ihren eigenen Daten.

    Grundlage sind die englischen Stichwörter der Unit, ihre Beispielsätze
    aus der Wortliste des Lehrmittels und die Leitwörter aus ``themen.json``.
    Wörter, die in vielen anderen Units genauso vorkommen ("people", "school",
    "water"), werden abgezogen: Sie belegen keine Themenzugehörigkeit,
    sondern nur, dass der Satz auf Englisch ist. Leitwörter bleiben immer
    drin - sie beschreiben das Thema per Definition.
    """
    eigen: set[str] = set()
    for row in db.unit_pool(unit, core_only=False):
        eigen |= _tokens(f"{row.english} {row.example}")

    verbreitung: dict[str, int] = {}
    for other_unit in db.units():
        if other_unit == unit:
            continue
        fremd = set()
        for row in db.unit_pool(other_unit, core_only=False):
            fremd |= _tokens(f"{row.english} {row.example}")
        for token in fremd & eigen:
            verbreitung[token] = verbreitung.get(token, 0) + 1

    words = {t for t in eigen if verbreitung.get(t, 0) < _GENERISCH_AB}
    words |= {str(lead).lower() for lead in db.theme(unit).get("leitwoerter", [])}
    return words


def _stemlike(word: str) -> str:
    w = re.sub(r"[^a-z]", "", word.lower())
    for suffix in ("ations", "ation", "ments", "ment", "ness", "ities", "ity",
                   "ings", "ing", "ers", "er", "ies", "ed", "es", "s", "ly", "al"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            return w[: -len(suffix)]
    return w


def pruefe_thema(pack: Pack, db: Database, bericht: Pruefbericht) -> None:
    """Jedes Wort muss zum Thema der Unit passen.

    Wörter aus der Wortliste des Lehrmittels passen per Definition. Selbst
    ergänzte Wörter müssen sich am Wortfeld der Unit messen lassen: entweder
    das Wort selbst gehört dazu, oder sein Beispielsatz trägt mindestens zwei
    Inhaltswörter aus dem Wortfeld.
    """
    bericht.gelaufen.append("thema")
    topic = {_stemlike(w) for w in _topic_vocabulary(db, pack.unit)}
    fremd = []
    for entry in pack.ergaenzt:
        english = entry.get("englisch", "")
        if not english:
            continue
        if any(_stemlike(t) in topic for t in re.findall(r"[A-Za-z]{3,}", english)):
            continue
        treffer = {_stemlike(t) for t in _tokens(entry.get("satz", ""))} & topic
        if len(treffer) >= 2:
            continue
        if str(entry.get("begruendung", "")).strip():
            bericht.add(
                HINWEIS, "thema",
                f"'{english}' liegt ausserhalb des Wortfelds der Unit, ist aber "
                f"begründet: {entry['begruendung']}",
            )
            continue
        fremd.append(english)
    bericht.kennzahlen["thema"] = (
        f"{len(pack.ergaenzt)} ergänzte Wörter, {len(fremd)} ohne Themenbezug"
    )
    for english in fremd:
        bericht.add(
            FEHLER, "thema",
            f"'{english}' ist ergänzt, passt aber nicht erkennbar zum Thema "
            f"'{pack.thema}'. Entweder ersetzen oder im Feld 'begruendung' "
            "erklären, warum es dazugehört.",
        )


# ---------------------------------------------------------------------------
# 2  Neuwort-Limite
# ---------------------------------------------------------------------------
def pruefe_neuwoerter(pack: Pack, settings: Settings, bericht: Pruefbericht) -> None:
    """Höchstens 40 Prozent selbst ergänzt - und Zusatzteile immer ausweisen."""
    bericht.gelaufen.append("neuwoerter")
    anteil = pack.ergaenzt_anteil
    grenze = settings.max_invented_share
    zusatz = pack.aus_zusatzteilen
    bericht.kennzahlen["neuwoerter"] = (
        f"{len(pack.ergaenzt)} von {len(pack.all_entries)} ergänzt = {anteil:.0%} "
        f"(Grenze {grenze:.0%})"
        + (f", {len(zusatz)} aus Zusatzteilen" if zusatz else "")
    )
    if anteil > grenze + 1e-9:
        bericht.add(
            WARNUNG, "neuwoerter",
            f"Ausnahme: {anteil:.0%} der Wörter sind ergänzt, vorgesehen sind "
            f"höchstens {grenze:.0%}. Der Hauptteil dieser Unit gibt nicht mehr "
            "her. Bitte die ergänzten Wörter besonders sorgfältig gegenlesen.",
        )
    elif anteil > grenze * 0.75:
        bericht.add(
            WARNUNG, "neuwoerter",
            f"{anteil:.0%} ergänzt - nahe an der Grenze von {grenze:.0%}.",
        )

    # Culture, Project und Curriculum extra sind die letzte Reserve. Wenn sie
    # gezogen wurde, muss das sichtbar sein - jedes Wort einzeln.
    if zusatz:
        bereiche = ", ".join(
            f"{e['englisch']} ({e.get('abschnitt', 'Zusatzteil')})" for e in zusatz
        )
        bericht.add(
            WARNUNG, "neuwoerter",
            f"Ausnahme: {len(zusatz)} Wörter stammen nicht aus dem Hauptteil, "
            f"sondern aus Zusatzteilen derselben Unit - {bereiche}. Das geschieht "
            "nur, wenn Hauptteil und erlaubte Ergänzung zusammen keine Liste "
            "ergeben.",
        )
    hinweis = pack.data.get("herkunft_uebersicht", {}).get("ausnahme")
    if hinweis:
        bericht.add(WARNUNG, "neuwoerter", str(hinweis))


# ---------------------------------------------------------------------------
# 3  CEFR-Konformität
# ---------------------------------------------------------------------------
def pruefe_cefr(pack: Pack, bericht: Pruefbericht) -> None:
    """Beispielsätze und Lückentexte müssen zum Zielband passen.

    Die Vokabelliste lernen **beide** Gruppen, deshalb gilt für ihre
    Beispielsätze das engere Mass der schwächeren Gruppe. Die Lückentexte
    werden je Prüfung gegen das Band ihres eigenen Niveaus geprüft; das
    besorgt :func:`pruefe_pruefungen`.
    """
    bericht.gelaufen.append("cefr")
    saetze = [e["satz"] for e in pack.all_entries if e.get("satz")]
    if not saetze:
        bericht.kennzahlen["cefr"] = "keine Sätze vorhanden"
        return

    laengen = [len(s.split()) for s in saetze]
    schnitt = sum(laengen) / len(laengen)
    stats = exam_english.readability(" ".join(saetze))
    bericht.kennzahlen["cefr"] = (
        f"Liste (A2.2-B2.1): Sätze Ø {schnitt:.1f} Wörter (max {max(laengen)}), "
        f"Lesbarkeit {stats['flesch_reading_ease']:.0f}"
    )

    zu_lang = [s for s in saetze if len(s.split()) > SENTENCE_MAX_WORDS]
    if zu_lang:
        bericht.add(
            WARNUNG if len(zu_lang) <= 3 else FEHLER, "cefr",
            f"{len(zu_lang)} Beispielsätze sind länger als "
            f"{SENTENCE_MAX_WORDS} Wörter. Die Liste lernen auch die "
            "schwächeren Schülerinnen und Schüler. Zum Beispiel: "
            f"„{max(zu_lang, key=lambda s: len(s.split()))}“",
        )
    untergrenze = PROFILES["B"].level_targets["min_flesch_ease"]
    if stats["flesch_reading_ease"] < untergrenze:
        bericht.add(
            WARNUNG, "cefr",
            f"Die Beispielsätze erreichen Lesbarkeit "
            f"{stats['flesch_reading_ease']:.0f}; für die gemeinsame Liste "
            f"sind mindestens {untergrenze:.0f} vorgesehen.",
        )
    ueber = exam_english.structures_above_level(" ".join(saetze))
    if ueber:
        bericht.add(
            WARNUNG, "cefr",
            f"Strukturen über dem Zielband in den Beispielsätzen: "
            f"{', '.join(sorted(set(ueber))[:4])}.",
        )


# ---------------------------------------------------------------------------
# 4  Dubletten und Widersprüche
# ---------------------------------------------------------------------------
def pruefe_dubletten(pack: Pack, bericht: Pruefbericht) -> None:
    bericht.gelaufen.append("dubletten")
    gesehen: dict[str, dict] = {}
    deutsch: dict[str, str] = {}
    doppelt = 0
    for entry in pack.all_entries:
        english = entry.get("englisch", "")
        if not english:
            continue
        key = normalize_key(headword(english))
        if key in gesehen:
            doppelt += 1
            bericht.add(
                FEHLER, "dubletten",
                f"'{english}' steht zweimal in der Liste "
                f"(Nr. {gesehen[key].get('nr')} und Nr. {entry.get('nr')}).",
            )
            if normalise(gesehen[key].get("deutsch", "")) != normalise(entry.get("deutsch", "")):
                bericht.add(
                    FEHLER, "dubletten",
                    f"'{english}' hat zwei verschiedene Übersetzungen: "
                    f"„{gesehen[key].get('deutsch')}“ und „{entry.get('deutsch')}“.",
                )
        else:
            gesehen[key] = entry
        gloss = normalize_key(entry.get("deutsch", ""))
        if gloss and gloss in deutsch and deutsch[gloss] != english:
            bericht.add(
                WARNUNG, "dubletten",
                f"'{english}' und '{deutsch[gloss]}' haben dieselbe deutsche "
                f"Übersetzung „{entry.get('deutsch')}“ - eine davon ist nicht "
                "eindeutig prüfbar.",
            )
        elif gloss:
            deutsch[gloss] = english
    bericht.kennzahlen["dubletten"] = (
        f"{len(gesehen)} verschiedene Wörter, {doppelt} Doppelungen"
    )


# ---------------------------------------------------------------------------
# 5  Altbestand
# ---------------------------------------------------------------------------
def pruefe_altbestand(pack: Pack, db: Database, bericht: Pruefbericht) -> None:
    """Kein Wort darf aus einer früheren Wortliste stammen.

    Ein Wort ist zulässig, wenn es entweder in der aktuellen Datenbank steht
    oder ausdrücklich als Ergänzung gekennzeichnet ist. Ein Wort, das sich
    als „aus der Wortliste“ ausgibt, aber dort nicht vorkommt, ist ein Rest
    aus einem alten Bestand - genau das soll diese Prüfung finden.
    """
    bericht.gelaufen.append("altbestand")
    if pack.quelle.get("pruefsumme_sha256") and db.quelle.get("pruefsumme_sha256") and \
            pack.quelle["pruefsumme_sha256"] != db.quelle["pruefsumme_sha256"]:
        bericht.add(
            FEHLER, "altbestand",
            f"Das Paket wurde aus einer anderen Fassung der Wortliste erzeugt "
            f"({pack.quelle.get('datei')}, {pack.quelle['pruefsumme_sha256'][:12]}) "
            f"als der aktuellen ({db.quelle.get('datei')}, "
            f"{db.quelle['pruefsumme_sha256'][:12]}). Gerüst neu erzeugen.",
        )
    in_unit = {r.headword.lower() for r in db.unit_pool(pack.unit, core_only=False)}
    irgendwo = {r.headword.lower() for r in db.rows}
    falsch = 0
    for entry in pack.all_entries:
        english = entry.get("englisch", "")
        if not english or entry.get("herkunft") != "wortliste":
            continue
        key = headword(english).lower()
        if key in in_unit:
            continue
        falsch += 1
        woher = "einer anderen Unit" if key in irgendwo else "keiner aktuellen Unit"
        bericht.add(
            FEHLER, "altbestand",
            f"'{english}' ist als 'wortliste' gekennzeichnet, steht aber in "
            f"{woher} der aktuellen Wortliste. Entweder als 'ergänzt' "
            "kennzeichnen oder entfernen.",
        )
    bericht.kennzahlen["altbestand"] = (
        f"Quelle {db.quelle.get('datei', '?')}, {falsch} nicht belegte Einträge"
    )


# ---------------------------------------------------------------------------
# 6  Lösungsschlüssel
# ---------------------------------------------------------------------------
def pruefe_loesungsschluessel(pack: Pack, bericht: Pruefbericht) -> None:
    """Jede Prüfungsaufgabe muss zur Vokabelliste desselben Pakets passen."""
    bericht.gelaufen.append("loesungsschluessel")
    geprueft = 0
    for (teil, niveau), spec in sorted(pack.exams.items()):
        wo = f"Teil {teil}, Niveau {niveau}"
        liste = pack.vocab_test(teil)
        eintraege = list(spec.get("task1", {}).get("items", [])) + list(
            spec.get("task2", {}).get("gaps", [])
        )
        for entry in eintraege:
            geprueft += 1
            english = entry.get("english", "")
            german = entry.get("german", "")
            item = liste.by_german(german) or liste.by_english(english)
            if item is None:
                bericht.add(
                    FEHLER, "loesungsschluessel",
                    f"{wo}: '{german}' / '{english}' steht nicht in "
                    f"{liste.name} der Vokabelliste dieses Pakets.",
                )
                continue
            if normalise(item.english) != normalise(english):
                bericht.add(
                    FEHLER, "loesungsschluessel",
                    f"{wo}: Die Liste schreibt „{german}“ als "
                    f"'{item.english}', die Prüfung als '{english}'.",
                )
            if normalise(item.german) != normalise(german):
                bericht.add(
                    FEHLER, "loesungsschluessel",
                    f"{wo}: Die Liste schreibt '{english}' als "
                    f"„{item.german}“, die Prüfung als „{german}“.",
                )
            answer = entry.get("answer")
            if answer is not None and normalise(answer) != normalise(english):
                bericht.add(
                    FEHLER, "loesungsschluessel",
                    f"{wo}: Lücke '{english}' hat die Lösung '{answer}'.",
                )
            pos_spec = entry.get("pos")
            pos_liste = pack.wortart(english) or guess_pos(item.german)
            if pos_spec and pos_liste and pos_spec != pos_liste:
                bericht.add(
                    HINWEIS, "loesungsschluessel",
                    f"{wo}: '{english}' ist in der Prüfung als "
                    f"'{pos_spec}' geführt, aus der Liste ergäbe sich "
                    f"'{pos_liste}'.",
                )
    # Innerhalb eines Niveaus darf kein Wort zweimal geprüft werden. Zwischen
    # den Niveaus ist das kein Fehler - es sind verschiedene Gruppen -, aber
    # die Auswahl soll es trotzdem vermeiden; das prüft `niveau_konsistenz`.
    for niveau in NIVEAUS:
        seen: dict[str, int] = {}
        for (teil, n), spec in sorted(pack.exams.items()):
            if n != niveau:
                continue
            for entry in list(spec.get("task1", {}).get("items", [])) + list(
                spec.get("task2", {}).get("gaps", [])
            ):
                key = normalise(entry.get("english", ""))
                if key and key in seen:
                    bericht.add(
                        FEHLER, "loesungsschluessel",
                        f"Niveau {niveau}: '{entry.get('english')}' wird in "
                        f"Teil {seen[key]} und in Teil {teil} geprüft.",
                    )
                elif key:
                    seen[key] = teil
    bericht.kennzahlen["loesungsschluessel"] = f"{geprueft} Aufgaben gegen die Liste geprüft"


# ---------------------------------------------------------------------------
# 7  Konsistenz zwischen den Niveaus
# ---------------------------------------------------------------------------
def pruefe_niveau_konsistenz(pack: Pack, bericht: Pruefbericht) -> None:
    """Beide Prüfungen eines Teils: dieselbe Liste, aber andere Schwierigkeit.

    Da beide Niveaus aus **einer** Vokabelliste geprüft werden, ist das Thema
    per Bauart dasselbe. Zu prüfen bleibt zweierlei: Jede Aufgabe stammt aus
    der Liste dieses Teils, und die Prüfung für Niveau A ist tatsächlich die
    schwerere. Ein Überschnitt zwischen den beiden Auswahlen ist erlaubt - es
    sind verschiedene Gruppen - und wird nur vermerkt.
    """
    bericht.gelaufen.append("niveau_konsistenz")

    def woerter(teil: int, niveau: str) -> list[dict]:
        spec = pack.exam(teil, niveau)
        return list(spec.get("task1", {}).get("items", [])) + list(
            spec.get("task2", {}).get("gaps", [])
        )

    kennzahlen = []
    for teil in (1, 2):
        a, b = woerter(teil, "A"), woerter(teil, "B")
        if not a or not b:
            continue

        erlaubt = {
            normalise(e.get("englisch", "")) for e in pack.entries(f"test{teil}")
        }
        for niveau, eintraege in (("A", a), ("B", b)):
            fremd = [
                e.get("english") for e in eintraege
                if normalise(e.get("english", "")) not in erlaubt
            ]
            if fremd:
                bericht.add(
                    FEHLER, "niveau_konsistenz",
                    f"Teil {teil}, Niveau {niveau}: {fremd} steht nicht in "
                    f"Test {teil} der Vokabelliste. Beide Niveaus müssen aus "
                    "derselben Liste geprüft werden.",
                )

        gemeinsam = sorted(
            {normalise(e.get("english", "")) for e in a}
            & {normalise(e.get("english", "")) for e in b}
        )
        if gemeinsam:
            # Erlaubt: Es sind verschiedene Gruppen, und beide lernen dieselbe
            # Liste. Vermerkt wird es trotzdem - wächst der Überschnitt, prüfen
            # die beiden Fassungen am Ende dasselbe.
            bericht.add(
                WARNUNG if len(gemeinsam) > len(a) // 2 else HINWEIS,
                "niveau_konsistenz",
                f"Teil {teil}: {len(gemeinsam)} von {len(a)} Wörtern werden in "
                f"beiden Niveaus geprüft ({', '.join(gemeinsam[:6])}). Das ist "
                "zulässig; ab der Hälfte lohnt ein Blick, ob sich die beiden "
                "Fassungen noch unterscheiden.",
            )

        ma = _mittlere_schwierigkeit(a)
        mb = _mittlere_schwierigkeit(b)
        kennzahlen.append(f"Teil {teil}: A {ma:.1f}/10 gegen B {mb:.1f}/10")
        if ma <= mb:
            bericht.add(
                FEHLER, "niveau_konsistenz",
                f"Teil {teil}: Die Prüfung für Niveau A ist mit Ø {ma:.1f}/10 "
                f"nicht schwerer als die für Niveau B (Ø {mb:.1f}/10).",
            )
        elif ma - mb < 0.5:
            bericht.add(
                WARNUNG, "niveau_konsistenz",
                f"Teil {teil}: Der Abstand zwischen den Niveaus ist gering "
                f"(A {ma:.1f}/10 gegen B {mb:.1f}/10).",
            )
    if kennzahlen:
        auskunft = "; ".join(kennzahlen)
    elif pack.exams:
        # Ein Fassungspaket enthält genau eine der vier Prüfungen. Dann gibt
        # es nichts zu vergleichen - was aber nicht heisst, dass nichts drin
        # ist. Dass die geprüften Wörter aus der Liste dieses Pakets stammen,
        # sichert `loesungsschluessel` unabhängig davon.
        vorhanden = ", ".join(
            f"Teil {teil} Niveau {niveau}" for teil, niveau in sorted(pack.exams)
        )
        auskunft = (
            f"nur {vorhanden} im Paket - ohne Gegenstück kein Niveauvergleich"
        )
    else:
        auskunft = "keine Prüfungen im Paket"
    bericht.kennzahlen["niveau_konsistenz"] = auskunft


def _mittlere_schwierigkeit(eintraege: list[dict]) -> float:
    from .exam.difficulty import score_item

    werte = [score_item(e).score for e in eintraege if e.get("english")]
    return sum(werte) / len(werte) if werte else 0.0


# ---------------------------------------------------------------------------
# 8  Vorlagenintegrität (vor dem Schreiben)
# ---------------------------------------------------------------------------
def pruefe_platzhalter(
    pack: Pack, bericht: Pruefbericht, mit_pruefungen: bool = True
) -> None:
    """Kein Platzhalter darf ins fertige Dokument gelangen."""
    bericht.gelaufen.append("vorlage")
    offen = [
        text for text in pack.offen()
        if mit_pruefungen or not text.startswith("Prüfung ")
    ]
    reste = []
    for (teil, niveau), spec in (sorted(pack.exams.items()) if mit_pruefungen else []):
        wo = f"Teil {teil}, Niveau {niveau}"
        text = spec.get("task2", {}).get("text", "")
        if "TODO" in text:
            reste.append(f"{wo}: Lückentext ist noch der Platzhalter")
        marker = re.findall(r"\{(\d*)\}", text)
        erwartet = len(spec.get("task2", {}).get("gaps", []))
        if text and "TODO" not in text and len(marker) != erwartet:
            reste.append(
                f"{wo}: {len(marker)} Lückenmarker im Text, "
                f"aber {erwartet} Lücken"
            )
    for entry in pack.all_entries:
        if re.search(r"\bTODO\b|\{\d*\}", f"{entry.get('satz','')} {entry.get('englisch','')}"):
            reste.append(f"Nr. {entry.get('nr')}: Platzhalter im Eintrag stehengeblieben")
    bericht.kennzahlen["vorlage"] = (
        f"{len(offen)} offene Felder, {len(reste)} Platzhalter"
    )
    for text in offen[:12]:
        bericht.add(FEHLER, "vorlage", f"Noch offen - {text}")
    if len(offen) > 12:
        bericht.add(FEHLER, "vorlage", f"… und {len(offen) - 12} weitere offene Felder.")
    for text in reste:
        bericht.add(FEHLER, "vorlage", text)


# ---------------------------------------------------------------------------
# 9  Herkunft
# ---------------------------------------------------------------------------
def pruefe_herkunft(pack: Pack, bericht: Pruefbericht) -> None:
    bericht.gelaufen.append("herkunft")
    quelle = pack.quelle
    fehlt = [k for k in ("datei", "importiert", "pruefsumme_sha256") if not quelle.get(k)]
    bericht.kennzahlen["herkunft"] = (
        f"{quelle.get('datei', '?')}, importiert {quelle.get('importiert', '?')}"
    )
    if fehlt:
        bericht.add(
            FEHLER, "herkunft",
            f"Im Paket fehlen Quellangaben ({', '.join(fehlt)}). Jedes Dokument "
            "muss auf eine benannte Fassung der Wortliste zurückführbar sein.",
        )


# ---------------------------------------------------------------------------
# Die geerbten Prüfungen der beiden Ursprungsanwendungen
# ---------------------------------------------------------------------------
def pruefe_liste(pack: Pack, settings: Settings, bericht: Pruefbericht) -> None:
    """Die Listenkontrolle aus dem VocabListMaker, unverändert."""
    bericht.gelaufen.append("liste")

    def to_candidates(block: str) -> list[Candidate]:
        out = []
        for entry in pack.entries(block):
            if not entry.get("englisch"):
                continue
            c = Candidate(english=entry["englisch"], german=entry.get("deutsch", ""))
            score_candidate(c, None, bounds)
            c.sentence = entry.get("satz", "")
            c.sentence_form = entry.get("form", "")
            out.append(c)
        return out

    bounds = LIST_BOUNDS
    test1, test2 = to_candidates("test1"), to_candidates("test2")
    report = validate_all(test1, test2, settings.words_per_test, bounds=bounds)
    for issue in report.issues:
        stufe = {
            Severity.ERROR: FEHLER,
            Severity.WARNING: WARNUNG,
            Severity.INFO: HINWEIS,
        }[issue.severity]
        bericht.add(stufe, "liste", str(issue.message))
    bericht.kennzahlen["liste"] = (
        f"{len(test1)}+{len(test2)} Wörter, Schwierigkeitsdifferenz "
        f"{report.stats.get('schwierigkeit_differenz', 0):.3f}"
    )

    # Seitenumfang: jede Liste muss auf eine A4-Seite passen.
    from .list.docx_writer import check_page_fit

    pair = _pair_from_pack(pack)
    for name, items in (("Test 1", pair.test1), ("Test 2", pair.test2)):
        if not items:
            continue
        fit = check_page_fit(items, settings)
        bericht.kennzahlen[f"seite_{name}"] = f"{fit.usage:.0%} gefüllt"
        if not fit.fits:
            laengster = max(items, key=lambda i: len(i.sentence))
            bericht.add(
                FEHLER, "liste",
                f"{name} passt nicht auf eine A4-Seite ({fit.usage:.0%}). "
                f"Längster Satz: „{laengster.sentence}“ "
                f"({len(laengster.sentence)} Zeichen).",
            )
        elif fit.usage > 0.97:
            bericht.add(
                WARNUNG, "liste",
                f"{name} füllt die Seite zu {fit.usage:.0%} - wenig Reserve.",
            )


def _pair_from_pack(pack: Pack):
    from .list.models import TestItem, TestPair
    from .list.sentences import find_form_in_sentence

    pair = TestPair(unit=pack.unit, unit_label=pack.unit_label)
    for block, target in (("test1", "test1"), ("test2", "test2")):
        items = []
        for number, entry in enumerate(pack.entries(block), 1):
            if not entry.get("englisch"):
                continue
            satz = entry.get("satz", "")
            items.append(
                TestItem(
                    number=number,
                    german=entry.get("deutsch", ""),
                    english=entry["englisch"],
                    sentence=satz,
                    sentence_form=find_form_in_sentence(
                        satz, entry["englisch"], entry.get("form", "")
                    )
                    or entry.get("form", "")
                    or entry["englisch"],
                )
            )
        setattr(pair, target, items)
    return pair


def pruefe_pruefungen(pack: Pack, bericht: Pruefbericht) -> None:
    """Die zwanzig Prüfungen aus dem VocabTestMaker, für jede der vier Prüfungen.

    Die Zielbänder für Lückentext und Auswahl kommen aus dem Niveauprofil -
    das ist die einzige Änderung gegenüber der Ursprungsanwendung. Der
    Lückentext für Niveau B wird damit gegen ein anderes Band gemessen als
    der für Niveau A, obwohl beide aus derselben Vokabelliste stammen.
    """
    bericht.gelaufen.append("pruefung")
    zusammen = []
    for (teil, niveau), spec in sorted(pack.exams.items()):
        prof = PROFILES[niveau]
        # Steht im Paket eine abweichende Textstufe, wird der Lückentext
        # gegen deren Bänder gemessen - sonst gegen die des Niveaus.
        gewuenscht = pack.textstufe(teil, niveau)
        ziele = ziele_fuer_textstufe(prof, gewuenscht)
        report = ExamChecker(
            spec,
            vocab=pack.vocab_test(teil),
            all_tests=pack.all_vocab_tests,
            level_targets=ziele,
            selection_targets=prof.selection_targets,
        ).run()
        for finding in report.findings:
            stufe = {"ERROR": FEHLER, "WARN": WARNUNG, "INFO": HINWEIS}[finding.level]
            bericht.add(
                stufe, "pruefung",
                f"Teil {teil} Niveau {niveau} - {finding.check}: {finding.message}",
            )
        stats = report.stats.get("readability", {})
        if stats:
            ist = textstufe(stats)
            soll = gewuenscht if gewuenscht is not None else NORMAL_TEXTSTUFE[niveau]
            zusammen.append(
                f"T{teil}/{niveau}: {stats['words']} W., Lesbarkeit "
                f"{stats['flesch_reading_ease']:.0f}, Grad "
                f"{stats['flesch_kincaid_grade']:.1f}, Textstufe {ist:.1f}"
            )
            if abs(ist - soll) > 1.0:
                bericht.add(
                    WARNUNG, "pruefung",
                    f"Teil {teil} Niveau {niveau} - textstufe: Der Lückentext "
                    f"liest sich auf Stufe {ist:.1f}/10, verlangt war "
                    f"{soll:.1f}/10.",
                )
    bericht.kennzahlen["pruefung"] = "; ".join(zusammen) or "keine Prüfungen im Paket"


# ---------------------------------------------------------------------------
# Gesamtlauf
# ---------------------------------------------------------------------------
def pruefe_paket(
    pack: Pack,
    db: Database,
    settings: Settings | None = None,
    teile: tuple[str, ...] = ("liste", "test"),
) -> Pruefbericht:
    """Der Selbstcheck eines Pakets.

    ``teile`` sagt, was gebaut werden soll. Wer nur die Vokabelliste braucht,
    bekommt auch nur deren Kontrollen - die Prüfungen bleiben dann ungeprüft
    und ungebaut, statt mit leeren Lückentexten den Bau zu blockieren.
    """
    settings = settings or Settings()
    mit_pruefungen = "test" in teile
    bericht = Pruefbericht()
    bericht.kennzahlen["_kopf"] = (
        f"{pack.unit_label} - {pack.thema} "
        f"(eine Liste, Prüfungen für Niveau A {PROFILES['A'].cefr} und "
        f"Niveau B {PROFILES['B'].cefr})"
    )
    pruefe_thema(pack, db, bericht)
    pruefe_neuwoerter(pack, settings, bericht)
    pruefe_cefr(pack, bericht)
    pruefe_dubletten(pack, bericht)
    pruefe_altbestand(pack, db, bericht)
    if mit_pruefungen:
        pruefe_loesungsschluessel(pack, bericht)
        pruefe_niveau_konsistenz(pack, bericht)
    pruefe_platzhalter(pack, bericht, mit_pruefungen)
    pruefe_herkunft(pack, bericht)
    pruefe_liste(pack, settings, bericht)
    if mit_pruefungen:
        pruefe_pruefungen(pack, bericht)
    return bericht.sortieren()
