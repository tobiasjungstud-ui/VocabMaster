"""Normalisierung: Grundform, Stamm, Wortart und deutsch-englische Ähnlichkeit."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from .models import POS

# "gave (give)" -> Grundform ist "give"; "ate (eat)" -> "eat"
_INFLECTED_WITH_BASE = re.compile(r"^\s*([\w'’-]+)\s*\(\s*([\w'’-]+)\s*\)\s*$")
_PARENTHESES = re.compile(r"\s*\([^)]*\)")
_BRACKETS = re.compile(r"\s*\[[^\]]*\]")

# Verbpartikel, die im Englischen zum Wort gehören.
_PARTICLES = {
    "up", "down", "in", "out", "on", "off", "away", "back", "over", "through",
    "along", "around", "after", "into", "with", "for", "to", "at", "of",
}

_GERMAN_VERB_SUFFIXES = ("en", "ern", "eln", "ieren", "sein", "haben")
_GERMAN_ADJ_SUFFIXES = (
    "ig", "lich", "isch", "sam", "bar", "haft", "los", "voll", "iv", "al",
    "ell", "ös", "end", "ant", "ent",
)

_DERIVATIONAL = (
    "tion", "sion", "ment", "ness", "ity", "ance", "ence", "ship", "hood",
    "able", "ible", "ious", "eous", "ous", "ive", "ful", "less", "ise", "ize",
    "ify", "ate", "al", "ic", "ary", "ory",
)


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def headword(english: str) -> str:
    """Die Form, die im Test abgefragt wird.

    ``"gave (give)"`` -> ``"give"``, ``"chat (v)"`` -> ``"chat"``,
    ``"have a “good ear”"`` -> ``"have a good ear"``.
    """
    s = str(english).replace("\n", " ").strip()
    s = s.replace("“", "").replace("”", "").replace("„", "").replace("“", "")
    m = _INFLECTED_WITH_BASE.match(s)
    if m:
        # Nur wenn die Klammer eine echte Grundform enthält (nicht "(v)"/"(sth)").
        base = m.group(2)
        if len(base) > 2 and base.lower() not in {"sth", "sb", "etw", "jdn", "adj", "adv"}:
            return base.strip()
    s = _PARENTHESES.sub("", s)
    s = _BRACKETS.sub("", s)
    s = re.split(r"\s*[/;]\s*|\s*,\s*", s)[0]
    return re.sub(r"\s+", " ", s).strip(" -–—")


def first_gloss(german: str) -> str:
    """Erste, prägnanteste deutsche Bedeutung (für Vergleiche, nicht für die Ausgabe)."""
    s = str(german).replace("\n", " ").strip()
    s = _PARENTHESES.sub("", s)
    s = re.split(r"\s*[/;,]\s*", s)[0]
    return re.sub(r"\s+", " ", s).strip().lower()


def german_glosses(german: str) -> list[str]:
    """Alle deutschen Bedeutungsvarianten eines Eintrags."""
    s = str(german).replace("\n", " ")
    s = s.replace("(", " ").replace(")", " ")
    parts = re.split(r"\s*[/;,]\s*", s)
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip().lower()
        if p and p not in out:
            out.append(p)
    return out


def _stem_token(token: str) -> str:
    """Sehr einfacher, aber vorhersagbarer englischer Stemmer."""
    t = token.lower()
    if len(t) <= 3:
        return t
    for suffix, keep in (
        ("ingly", 5), ("edly", 4), ("ing", 3), ("ied", 3), ("ies", 3),
        ("ied", 3), ("es", 2), ("ed", 2), ("s", 1),
    ):
        if t.endswith(suffix) and len(t) - keep >= 3:
            base = t[: len(t) - keep]
            if suffix in ("ied", "ies"):
                base += "y"
            # "running" -> "run", "stopped" -> "stop"
            if len(base) > 3 and base[-1] == base[-2] and base[-1] not in "aeiousl":
                base = base[:-1]
            return base
    return t


_REDUCE_SUFFIXES = (
    "ation", "ition", "ness", "ment", "ance", "ence", "able", "ible", "ious",
    "eous", "tion", "sion", "ship", "hood", "ise", "ize", "ify", "ous", "ive",
    "ful", "less", "ist", "ism", "ity", "ate", "or", "er", "ic", "al", "y",
)


def _reduce(word: str) -> str:
    """Ableitungssuffixe abtragen, solange ein tragfähiger Rest bleibt."""
    w = word
    changed = True
    while changed:
        changed = False
        for suf in _REDUCE_SUFFIXES:
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[: -len(suf)]
                changed = True
                break
    return w


def stem(english: str) -> str:
    """Stamm der gesamten Wendung - erkennt Wortfamilien wie recycle/recycling."""
    hw = headword(english).lower()
    tokens = [t for t in re.findall(r"[a-z'’-]+", hw)]
    if not tokens:
        return hw
    content = [t for t in tokens if t not in _PARTICLES] or tokens
    stems = [_stem_token(t) for t in content]
    return " ".join(stems)


def word_family(english: str) -> str:
    """Schlüssel, unter dem verwandte Formen desselben Begriffs zusammenfallen."""
    return stem(english)


def same_family(a: str, b: str) -> bool:
    """Gehören zwei Einträge zur selben Wortfamilie?

    Fängt sowohl Flexions- als auch Ableitungsvarianten ab
    (``recycle``/``recycling``/``recycled``, ``pollute``/``pollution``)
    sowie Mehrwortausdrücke, die einen Einzelbegriff enthalten
    (``resource`` in ``natural resource``).
    """
    sa, sb = stem(a), stem(b)
    if not sa or not sb:
        return False
    if sa == sb:
        return True

    ta, tb = sa.split(), sb.split()
    # Einwortstämme: nach Abtragen der Ableitungssuffixe vergleichen.
    if len(ta) == 1 and len(tb) == 1:
        ra, rb = _reduce(sa), _reduce(sb)
        if ra == rb:
            return True
        short, long_ = sorted((ra, rb), key=len)
        return len(short) >= 4 and long_.startswith(short)

    # Mehrwortausdruck, der den anderen Begriff vollständig enthält.
    set_a, set_b = set(ta), set(tb)
    if set_a <= set_b or set_b <= set_a:
        return True

    # Ein Inhaltswort deckungsgleich und eine Seite ist einteilig.
    if min(len(ta), len(tb)) == 1:
        single = ta[0] if len(ta) == 1 else tb[0]
        other = set_b if len(ta) == 1 else set_a
        return len(single) >= 4 and any(
            t == single or t.startswith(single) or single.startswith(t) and len(t) >= 4
            for t in other
        )
    return False


def is_multiword(english: str) -> bool:
    return len(headword(english).split()) > 1


def pos_from_german(german: str, english: str = "") -> POS:
    """Wortart aus der deutschen Übersetzung ableiten.

    Deutsch ist hier das verlässlichere Signal als Englisch: Nomen werden
    grossgeschrieben, Verben enden auf ``-en``/``-eln``/``-ern``, Adverbien
    häufig auf ``-weise``. Die Grossschreibung hat Vorrang vor der Wortzahl
    im Englischen, damit Mehrwortnomen wie ``car boot sale`` nicht
    fälschlich als Wendung gelten.
    """
    raw = _PARENTHESES.sub("", str(german).replace("\n", " ")).strip()
    raw_first = re.split(r"\s*[/;,]\s*", raw)[0].strip()
    tokens = [t for t in raw_first.split() if t]
    if not tokens:
        return POS.OTHER

    skip = {"sich", "etw.", "etw", "jdn.", "jdn", "jdm.", "jdm", "der", "die", "das", "zu"}
    meaningful = [t for t in tokens if t.lower().strip(".,;:") not in skip] or tokens
    word = meaningful[0]
    clean = word.strip(".,;:!?»«\"'")
    lowered = strip_accents(clean.lower())
    en_head = headword(english).lower() if english else ""

    # 1. Nomen: deutsche Grossschreibung ist das stärkste Signal.
    if clean[:1].isupper() and not clean.isupper():
        return POS.NOUN

    # 2. Adverb
    if lowered.endswith(("weise", "falls", "dings", "mals")) or (
        en_head.endswith("ly") and len(en_head) > 4
    ):
        return POS.ADVERB

    # 3. Verb
    if lowered.endswith(_GERMAN_VERB_SUFFIXES) and len(lowered) > 3:
        return POS.VERB

    # 4. Adjektiv
    if lowered.endswith(_GERMAN_ADJ_SUFFIXES):
        return POS.ADJECTIVE

    # 5. Mehrgliedrige Wendungen ohne klares Signal
    if len(meaningful) > 1 or (en_head and len(en_head.split()) > 2):
        return POS.PHRASE

    return POS.ADJECTIVE if lowered.isalpha() else POS.OTHER


def cognate_similarity(english: str, german: str) -> float:
    """Wie stark ähnelt das englische Wort seiner deutschen Übersetzung?

    Hohe Werte bedeuten geringen Lernwert für deutschsprachige Lernende
    (``Protein``/``protein``, ``Slogan``/``slogan``, ``ideal``/``ideal``).
    """
    en = strip_accents(headword(english).lower()).replace("-", "").replace(" ", "")
    if not en:
        return 0.0
    best = 0.0
    for gloss in german_glosses(german):
        de = strip_accents(gloss).replace("-", "").replace(" ", "")
        if not de:
            continue
        # Einmal unverändert und einmal ohne deutsche Endung vergleichen:
        # "Protein" darf nicht zu "prote" verstümmelt werden, während
        # "Ressource"/"resource" die Endung verlieren soll.
        variants = {de}
        if len(de) > 5:
            variants.add(re.sub(r"(in|en|e|er|s)$", "", de))
        for variant in variants:
            if variant:
                best = max(best, SequenceMatcher(None, en, variant).ratio())
    return best


def normalize_key(text: str) -> str:
    """Vergleichsschlüssel ohne Interpunktion und Grossschreibung."""
    return re.sub(r"[^a-z0-9 ]", "", strip_accents(str(text).lower())).strip()
