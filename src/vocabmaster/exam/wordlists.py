"""Word lists loaded from ``data/`` plus the small hand-kept tables.

Everything here is data, not logic, so it can be extended without touching
the checks.
"""

from __future__ import annotations

import gzip
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

CORE_FILE = DATA / "core_english_a1_b1.txt"
DICT_FILE = DATA / "english_words_british.txt.gz"
SYSTEM_DICTS = (
    Path("/usr/share/dict/british-english"),
    Path("/usr/share/dict/words"),
)


@lru_cache(maxsize=1)
def core_vocabulary() -> frozenset[str]:
    """Everything a B1 learner may be assumed to know."""
    if not CORE_FILE.exists():
        return frozenset()
    words = set()
    for line in CORE_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        words.update(w.strip().lower() for w in line.split() if w.strip())
    return frozenset(words)


@lru_cache(maxsize=1)
def dictionary() -> frozenset[str]:
    """A full English dictionary, for spell checking. Bundled, so the check
    works without any system packages."""
    if DICT_FILE.exists():
        with gzip.open(DICT_FILE, "rt", encoding="utf-8") as fh:
            return frozenset(w.strip().lower() for w in fh if w.strip())
    for path in SYSTEM_DICTS:
        if path.exists():
            return frozenset(
                w.strip().lower()
                for w in path.read_text(encoding="utf-8", errors="ignore").split()
                if w.isalpha()
            )
    return frozenset()


# Regular inflections accepted when matching against the core list.
INFLECTIONS = ("s", "es", "ed", "d", "ing", "er", "est", "ly", "ies", "ied",
               "ier", "iest", "ily")


def _bases(word: str) -> set[str]:
    """The word plus every plausible base after stripping one regular ending."""
    forms = {word}
    for suffix in INFLECTIONS:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            base = word[: -len(suffix)]
            forms.update({base, base + "e", base + "y"})
            if suffix in ("ier", "iest", "ily", "ies", "ied"):
                forms.add(base + "y")         # earlier, easiest, happily
            if len(base) > 2 and base[-1] == base[-2]:
                forms.add(base[:-1])          # stopped, running
    return forms


def in_core(word: str) -> bool:
    """True if a B1 learner can be assumed to know the word.

    Two rounds of suffix stripping, so 'surprisingly' still reaches 'surprise'.
    """
    core = core_vocabulary()
    first = _bases(word.lower())
    if first & core:
        return True
    second: set[str] = set()
    for form in first:
        second |= _bases(form)
    return bool(second & core)


# --------------------------------------------------------------------- variety
#: American spelling -> the British spelling used in the vocabulary lists.
AMERICAN_SPELLINGS = {
    "color": "colour", "colors": "colours", "favorite": "favourite",
    "humor": "humour", "behavior": "behaviour", "neighbor": "neighbour",
    "theater": "theatre", "center": "centre", "centers": "centres",
    "meter": "metre", "liter": "litre", "realize": "realise",
    "realized": "realised", "organize": "organise", "organized": "organised",
    "recognize": "recognise", "apologize": "apologise", "analyze": "analyse",
    "practice": "practise (verb)", "traveled": "travelled",
    "traveling": "travelling", "canceled": "cancelled", "modeling": "modelling",
    "program": "programme (TV)", "gray": "grey", "airplane": "aeroplane",
    "movie": "film", "movies": "films", "vacation": "holiday",
    "apartment": "flat", "elevator": "lift", "soccer": "football",
    "candy": "sweets", "cookie": "biscuit", "fall": "autumn",
    "defense": "defence", "license": "licence (noun)", "jewelry": "jewellery",
}

# ---------------------------------------------------------------- false friends
#: English word -> what a German speaker is likely to read into it.
FALSE_FRIENDS = {
    "actual": "not 'aktuell' (current)", "actually": "not 'aktuell'",
    "eventually": "not 'eventuell' (possibly)",
    "sensible": "not 'sensibel' (sensitive)",
    "become": "not 'bekommen' (to get)",
    "gift": "not 'Gift' (poison)",
    "chef": "not 'Chef' (boss)",
    "brave": "not 'brav' (well-behaved)",
    "spend": "not 'spenden' (to donate)",
    "handy": "not 'Handy' (mobile phone)",
    "rent": "not 'Rente' (pension)",
    "meaning": "not 'Meinung' (opinion)",
    "note": "not 'Note' (mark, grade)",
    "figure": "not 'Figur' (character)",
    "novel": "not 'Novelle'",
    "serious": "not 'seriös'",
    "sympathetic": "not 'sympathisch'",
    "engaged": "not 'engagiert'",
    "curious": "not 'kurios'",
    "billion": "not 'Billion'",
    "art": "not 'Art' (kind, sort)",
    "also": "not 'also' (so, therefore)",
    "bald": "not 'bald' (soon)",
    "fast": "not 'fast' (almost)",
    "list": "not 'List' (cunning)",
    "map": "not 'Mappe' (folder)",
    "mist": "not 'Mist'",
    "receipt": "not 'Rezept' (recipe)",
    "stadium": "not 'Stadium' (stage)",
    "undertaker": "not 'Unternehmer' (entrepreneur)",
    "warehouse": "not 'Warenhaus' (department store)",
    "wink": "not 'Winken' (to wave)",
}

# ------------------------------------------------------------- spelling traps
#: pattern -> why German learners get it wrong when writing the word
SPELLING_TRAPS = (
    # pattern, weight, why a German speaker gets it wrong when writing it
    (r"ough", 1.0, "the -ough- spelling"),
    (r"augh|eigh", 1.0, "the -augh-/-eigh- spelling"),
    (r"^kn|^wr|^gn|^ps|^pn", 1.0, "a silent first letter"),
    (r"que\b|gue\b", 1.0, "a French-looking ending"),
    (r"sc[ei]", 1.0, "silent c after s"),
    (r"[aeiou]{3}", 0.8, "three vowels in a row"),
    (r"ie|ei", 0.8, "ie / ei, which German speakers read the other way round"),
    (r"([bcdfglmnprstz])\1", 0.6, "a double consonant"),
    (r"tion\b|sion\b|ssion\b", 0.6, "the -tion/-sion ending"),
    (r"ph", 0.6, "ph for the f sound"),
    (r"[^aeiou]le\b", 0.6, "the final -le"),
    (r"dg|tch", 0.6, "the dg / tch cluster"),
    (r"c[ei]", 0.5, "c pronounced as s"),
    (r"^wh|^h[aeiou]", 0.25, "h / wh at the start"),
    (r"[^aeiou]y\b", 0.25, "final y"),
    (r"ck", 0.25, "ck"),
    (r"th", 0.25, "th"),
    (r"w", 0.25, "w, which is a v sound in German"),
)

#: suffixes that mark an abstract, harder-to-picture word
ABSTRACT_SUFFIXES = ("tion", "sion", "ment", "ness", "ity", "ance", "ence",
                     "ship", "hood", "ism", "ure", "age", "al", "cy")

# --------------------------------------------------- structures above B1 level
#: regex -> name of a structure that is too hard for a B1.2 cloze text
ABOVE_B1_STRUCTURES = (
    (r"\bhad been \w+ing\b", "past perfect continuous"),
    (r"\bwould have (been )?\w+(ed|en)\b", "third conditional"),
    (r"\bhad (I|he|she|they|we|you)\b", "inversion after 'had'"),
    (r"\bwere (I|he|she|they|we|you) to\b", "'were ... to' conditional"),
    (r"\bshould (I|he|she|they|we|you) \w+", "inversion after 'should'"),
    (r"\bnot only (did|had|was|were|is|are)\b", "inversion after 'not only'"),
    (r"\bwhom\b", "'whom'"),
    (r"\bwhereby\b|\bthereby\b|\bhenceforth\b|\bnotwithstanding\b",
     "formal connector"),
    (r"\bhaving \w+(ed|en)\b", "perfect participle clause"),
    (r"\bcould have been \w+", "modal perfect passive"),
    (r"\bmust have been \w+", "modal perfect passive"),
    (r"\bbeen being\b", "double passive"),
)

#: tense / structure fingerprints reported for information
STRUCTURE_MARKERS = (
    (r"\b(am|is|are) \w+ing\b", "present continuous"),
    (r"\b(was|were) \w+ing\b", "past continuous"),
    (r"\b(have|has) \w+(ed|en)\b", "present perfect"),
    (r"\bhad \w+(ed|en)\b", "past perfect"),
    (r"\bwill \w+\b", "will future"),
    (r"\bgoing to \w+\b", "going-to future"),
    (r"\bwould \w+\b", "conditional"),
    (r"\bif .*\bwould\b", "conditional sentence"),
    (r"\b(is|are|was|were) \w+(ed|en) by\b", "passive"),
    (r"\b(who|which|that) \w+", "relative clause"),
)


def strip_inflection(word: str) -> str:
    for suffix in ("ies", "ied", "ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def syllables(word: str) -> int:
    """Rough syllable count - good enough for a readability index."""
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and not word.endswith(("le", "ee", "ye")) and count > 1:
        count -= 1
    return max(1, count)
