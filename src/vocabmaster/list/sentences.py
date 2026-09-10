"""Beispielsätze: regelbasierte Erzeugung und sprachliche Prüfung.

Die Prüffunktionen laufen immer - auch wenn die Sätze vom Sprachmodell
stammen. Sie fangen genau die Fehler ab, die im Unterricht auffallen würden:
das Zielwort fehlt, der Satz verrät die Lösung, der Satz ist zu lang oder
zu kurz, oder er endet ohne Satzzeichen.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path

from .models import POS, Candidate
from .normalize import german_glosses, headword, strip_accents

MIN_WORDS = 5
MAX_WORDS = 16

# Satzmuster, die eine Definition liefern statt eines Kontexts.
_DEFINITION_PATTERNS = (
    re.compile(r"\b(is|are|means?|refers? to)\s+(a|an|the)\b", re.I),
    re.compile(r"\bis\s+(when|someone|something|a\s+person|a\s+thing)\b", re.I),
    re.compile(r"\b(that is|which is|in other words|i\.e\.)\b", re.I),
    re.compile(r"\b(also called|also known as|another word for)\b", re.I),
)

# Deutsche Wörter, die im englischen Satz nichts zu suchen haben.
_GERMAN_MARKERS = re.compile(
    r"\b(der|die|das|und|nicht|ist|sind|ein|eine|mit|für|über|auch|sich)\b", re.I
)

_IRREGULAR_THIRD = {"be": "is", "have": "has", "do": "does", "go": "goes"}

#: Unregelmässige Verben mit ihren Vergangenheitsformen. Ohne diese Tabelle
#: findet die Fettschrift Formen wie "got" (get) oder "took" (take) nicht.
_IRREGULAR_FORMS = {
    "be": ("am", "is", "are", "was", "were", "been", "being"),
    "become": ("becomes", "became", "becoming"),
    "begin": ("begins", "began", "begun", "beginning"),
    "break": ("breaks", "broke", "broken", "breaking"),
    "bring": ("brings", "brought", "bringing"),
    "build": ("builds", "built", "building"),
    "buy": ("buys", "bought", "buying"),
    "catch": ("catches", "caught", "catching"),
    "choose": ("chooses", "chose", "chosen", "choosing"),
    "come": ("comes", "came", "coming"),
    "cost": ("costs", "costing"),
    "cut": ("cuts", "cutting"),
    "do": ("does", "did", "done", "doing"),
    "draw": ("draws", "drew", "drawn", "drawing"),
    "drink": ("drinks", "drank", "drunk", "drinking"),
    "drive": ("drives", "drove", "driven", "driving"),
    "eat": ("eats", "ate", "eaten", "eating"),
    "fall": ("falls", "fell", "fallen", "falling"),
    "feel": ("feels", "felt", "feeling"),
    "fight": ("fights", "fought", "fighting"),
    "find": ("finds", "found", "finding"),
    "fly": ("flies", "flew", "flown", "flying"),
    "forget": ("forgets", "forgot", "forgotten", "forgetting"),
    "get": ("gets", "got", "gotten", "getting"),
    "give": ("gives", "gave", "given", "giving"),
    "go": ("goes", "went", "gone", "going"),
    "grow": ("grows", "grew", "grown", "growing"),
    "have": ("has", "had", "having"),
    "hear": ("hears", "heard", "hearing"),
    "hide": ("hides", "hid", "hidden", "hiding"),
    "hold": ("holds", "held", "holding"),
    "keep": ("keeps", "kept", "keeping"),
    "know": ("knows", "knew", "known", "knowing"),
    "lead": ("leads", "led", "leading"),
    "leave": ("leaves", "left", "leaving"),
    "lend": ("lends", "lent", "lending"),
    "lose": ("loses", "lost", "losing"),
    "make": ("makes", "made", "making"),
    "mean": ("means", "meant", "meaning"),
    "meet": ("meets", "met", "meeting"),
    "pay": ("pays", "paid", "paying"),
    "put": ("puts", "putting"),
    "read": ("reads", "reading"),
    "ride": ("rides", "rode", "ridden", "riding"),
    "rise": ("rises", "rose", "risen", "rising"),
    "run": ("runs", "ran", "running"),
    "say": ("says", "said", "saying"),
    "see": ("sees", "saw", "seen", "seeing"),
    "sell": ("sells", "sold", "selling"),
    "send": ("sends", "sent", "sending"),
    "set": ("sets", "setting"),
    "shoot": ("shoots", "shot", "shooting"),
    "show": ("shows", "showed", "shown", "showing"),
    "sing": ("sings", "sang", "sung", "singing"),
    "sit": ("sits", "sat", "sitting"),
    "sleep": ("sleeps", "slept", "sleeping"),
    "speak": ("speaks", "spoke", "spoken", "speaking"),
    "spend": ("spends", "spent", "spending"),
    "stand": ("stands", "stood", "standing"),
    "steal": ("steals", "stole", "stolen", "stealing"),
    "swim": ("swims", "swam", "swum", "swimming"),
    "take": ("takes", "took", "taken", "taking"),
    "teach": ("teaches", "taught", "teaching"),
    "tell": ("tells", "told", "telling"),
    "think": ("thinks", "thought", "thinking"),
    "throw": ("throws", "threw", "thrown", "throwing"),
    "understand": ("understands", "understood", "understanding"),
    "wake": ("wakes", "woke", "woken", "waking"),
    "wear": ("wears", "wore", "worn", "wearing"),
    "win": ("wins", "won", "winning"),
    "write": ("writes", "wrote", "written", "writing"),
}


def _inflected_variants(word: str) -> list[str]:
    """Mögliche Wortformen eines Stichworts - für die Suche im Satz."""
    w = word.lower()
    forms: list[str] = []
    forms.extend(_IRREGULAR_FORMS.get(w, ()))
    # Konsonant + y -> -ies / -ied (marry/married, enemy/enemies)
    if len(w) > 2 and w.endswith("y") and w[-2] not in _VOWELS:
        forms += [w[:-1] + "ies", w[:-1] + "ied", w[:-1] + "ier", w[:-1] + "iest"]
    return forms

_VOWELS = "aeiou"

_DATA = Path(__file__).parent / "data"


@functools.lru_cache(maxsize=1)
def uncountable_nouns() -> frozenset[str]:
    """Nomen, die keinen unbestimmten Artikel bekommen."""
    path = _DATA / "uncountable.txt"
    words: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip().lower()
            words.update(t for t in line.split() if t)
    return frozenset(words)


def needs_article(noun: str) -> bool:
    """Braucht das Nomen im Beispielsatz einen unbestimmten Artikel?"""
    n = noun.lower().strip()
    if not n:
        return False
    if n.endswith("s") and not n.endswith("ss"):
        return False  # wirkt wie ein Plural
    head = n.split()[-1]
    return head not in uncountable_nouns() and n not in uncountable_nouns()


@dataclass
class SentenceIssue:
    code: str
    message: str


def inflect_third_person(verb: str) -> str:
    """Einfache 3. Person Singular - genügt für die regelbasierten Sätze."""
    v = verb.lower()
    if v in _IRREGULAR_THIRD:
        return _IRREGULAR_THIRD[v]
    if v.endswith(("s", "x", "z", "ch", "sh")):
        return v + "es"
    if v.endswith("y") and len(v) > 1 and v[-2] not in _VOWELS:
        return v[:-1] + "ies"
    return v + "s"


def article_for(word: str) -> str:
    return "an" if word[:1].lower() in _VOWELS else "a"


def _split_phrase_verb(hw: str) -> tuple[str, str]:
    """``run out of`` -> (``run``, ``out of``)."""
    parts = hw.split()
    return parts[0], " ".join(parts[1:])


def build_sentence(c: Candidate) -> tuple[str, str]:
    """Regelbasierter Beispielsatz als Rückfallebene.

    Diese Sätze sind bewusst neutral gebaut: Sie sind grammatikalisch korrekt,
    verraten die Übersetzung nicht und funktionieren unabhängig davon, ob ein
    Verb transitiv ist. Inhaltlich bleiben sie blass - für Unterrichtsmaterial
    ist der Weg über das Sprachmodell vorgesehen. Jeder so erzeugte Satz wird
    im Qualitätsbericht als "regelbasiert" ausgewiesen.

    Liefert ``(satz, verwendete_wortform)``.
    """
    hw = headword(c.english).strip()
    if not hw:
        return "", ""
    lower = hw.lower()

    if c.pos in (POS.VERB, POS.PHRASE):
        base = re.sub(r"^to\s+", "", lower)
        return f"In class we discussed what it means to {base}.", base

    if c.pos is POS.ADVERB:
        return f"Our teacher explained the second example {lower}.", lower

    if c.pos is POS.ADJECTIVE:
        return f"The teacher found the second example quite {lower}.", lower

    # Nomen und alles Übrige
    if not needs_article(lower) or " of " in lower:
        return f"We talked about {lower} in our lesson last week.", lower
    return f"We talked about {article_for(lower)} {lower} in our lesson last week.", lower


def find_form_in_sentence(sentence: str, target: str, declared: str = "") -> str:
    """Findet die Wortform des Zielworts im Satz - für die Fettschrift.

    Gibt einen leeren String zurück, wenn das Zielwort gar nicht vorkommt.
    """
    if declared:
        idx = sentence.lower().find(declared.lower())
        if idx >= 0:
            return sentence[idx : idx + len(declared)]

    hw = headword(target).strip()
    if not hw:
        return ""

    # Exakte Wendung
    pattern = re.compile(rf"\b{re.escape(hw)}\b", re.I)
    m = pattern.search(sentence)
    if m:
        return m.group(0)

    # Mehrwortausdruck mit flektiertem ersten Wort ("takes place", "got rid of")
    words = hw.split()
    if len(words) > 1:
        head, tail = words[0], " ".join(words[1:])
        heads = [head, *_inflected_variants(head)]
        for variant in heads:
            m = re.search(
                rf"\b{re.escape(variant)}\w{{0,3}}\s+{re.escape(tail)}\w{{0,3}}\b",
                sentence, re.I,
            )
            if m:
                return m.group(0)
        # Nur das Kopfwort flektiert vorhanden
        m = re.search(rf"\b{re.escape(head)}\w{{0,3}}\b", sentence, re.I)
        if m:
            return m.group(0)
        return ""

    # Unregelmässige Formen und y-Wechsel (got, took, married, enemies)
    for variant in _inflected_variants(hw):
        m = re.search(rf"\b{re.escape(variant)}\b", sentence, re.I)
        if m:
            return m.group(0)

    # Einzelwort mit Endung (played, playing, plays, easier ...)
    stem_ = hw[:-1] if hw.endswith("e") and len(hw) > 3 else hw
    m = re.search(rf"\b{re.escape(stem_)}\w{{0,4}}\b", sentence, re.I)
    return m.group(0) if m else ""


def gives_away_answer(sentence: str, c: Candidate) -> bool:
    """Verrät der Satz die Lösung?

    Zwei Fälle: eine Definition des Zielworts, oder eine deutsche Übersetzung
    bzw. ein Internationalismus, der direkt daneben steht.
    """
    for pattern in _DEFINITION_PATTERNS:
        m = pattern.search(sentence)
        if not m:
            continue
        # Nur problematisch, wenn das Zielwort links davon steht.
        before = sentence[: m.start()].lower()
        if headword(c.english).lower().split()[0] in before:
            return True

    # Das Zielwort selbst wird ausgeblendet: Bei Internationalismen
    # (protein/Protein) wäre sonst jeder Satz ein vermeintlicher Verrat.
    masked = sentence
    form = find_form_in_sentence(sentence, c.english, c.sentence_form)
    if form:
        masked = masked.replace(form, " ")
    for token in headword(c.english).split():
        masked = re.sub(rf"\b{re.escape(token)}\w*\b", " ", masked, flags=re.I)

    lowered = strip_accents(masked.lower())
    for gloss in german_glosses(c.german):
        g = strip_accents(gloss)
        if len(g) >= 5 and g in lowered:
            return True
    return False


def check_sentence(c: Candidate, sentence: str | None = None) -> list[SentenceIssue]:
    """Alle regelbasierten Prüfungen eines Beispielsatzes."""
    text = (sentence if sentence is not None else c.sentence or "").strip()
    issues: list[SentenceIssue] = []

    if not text:
        issues.append(SentenceIssue("satz_fehlt", "Es wurde kein Beispielsatz erzeugt."))
        return issues

    words = text.split()
    if len(words) < MIN_WORDS:
        issues.append(SentenceIssue("satz_zu_kurz", f"Nur {len(words)} Wörter."))
    if len(words) > MAX_WORDS:
        issues.append(SentenceIssue("satz_zu_lang", f"{len(words)} Wörter - zu lang für B1.2."))
    if not text[0].isupper():
        issues.append(SentenceIssue("satz_klein", "Der Satz beginnt nicht mit einem Grossbuchstaben."))
    if text[-1] not in ".!?":
        issues.append(SentenceIssue("satz_ohne_punkt", "Der Satz endet ohne Satzzeichen."))
    if not find_form_in_sentence(text, c.english, c.sentence_form):
        issues.append(
            SentenceIssue("zielwort_fehlt", f"'{headword(c.english)}' kommt im Satz nicht vor.")
        )
    if gives_away_answer(text, c):
        issues.append(SentenceIssue("loesung_verraten", "Der Satz verrät die Übersetzung."))
    if _GERMAN_MARKERS.search(text):
        issues.append(SentenceIssue("deutsch_im_satz", "Der Satz enthält deutsche Wörter."))
    if re.search(r"\s{2,}", text):
        issues.append(SentenceIssue("satz_formatierung", "Doppelte Leerzeichen im Satz."))
    if text.count('"') % 2 or text.count("(") != text.count(")"):
        issues.append(SentenceIssue("satz_formatierung", "Unpaarige Anführungs- oder Klammerzeichen."))

    return issues


def ensure_sentence(c: Candidate) -> Candidate:
    """Sorgt dafür, dass ein Kandidat einen brauchbaren Satz besitzt."""
    if not c.sentence or check_sentence(c):
        sentence, form = build_sentence(c)
        if sentence and not check_sentence(c, sentence):
            c.sentence, c.sentence_form = sentence, form
        elif not c.sentence:
            c.sentence, c.sentence_form = sentence, form
    if c.sentence and not c.sentence_form:
        c.sentence_form = find_form_in_sentence(c.sentence, c.english) or headword(c.english)
    return c
