"""How hard is a word - to understand, and to write.

Harder words earn their place in an exam; a word a German speaker can simply
copy from the German prompt tests nothing.  The score is a sum of components
that can each be named in a report, so every number can be explained:

    transparency  0-3    distance from the German prompt (film / Film = 0,
                         script / Drehbuch = 3)
    spelling      0-3    weighted spelling traps: silent letters, -ough,
                         ie / ei, doubles, -tion, ph ...
    length        0-1.5  long word, four or more syllables
    morphology    0-1.5  multi-word item, derived form
    abstractness  0-1.5  an abstract noun or state is harder than an object
    false_friend  0-2    the word invites a German misreading
    german_side   0-1    separable / reflexive verb, long German compound
    familiar     -1.5-0  already core A1-B1 vocabulary, so probably known

The total is clamped and reported on a 0-10 scale.  Near-perfect cognates are
damped afterwards: whatever else is true of 'animation', a German speaker who
sees 'Animation' will write it correctly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .wordlists import (
    ABSTRACT_SUFFIXES,
    FALSE_FRIENDS,
    SPELLING_TRAPS,
    in_core,
    syllables,
)

RAW_MAX = 13.5


def _levenshtein_ratio(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    if not a or not b:
        return 0.0
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (ca != cb)))
        previous = current
    return 1.0 - previous[-1] / max(len(a), len(b))


@dataclass
class Difficulty:
    score: float
    similarity: float
    parts: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def explain(self) -> str:
        active = ", ".join(f"{k} {v:+g}" for k, v in self.parts.items() if v)
        return f"{self.score:.1f}/10 ({active})"


def cognate_similarity(english: str, german: str) -> float:
    """Best match between the English word and any word of the German prompt."""
    english_clean = re.sub(r"[^a-z]", "", english.lower())
    best = 0.0
    for variant in german.split("/"):
        for token in re.findall(r"[\wäöüß]+", variant.lower()):
            if len(token) < 3:
                continue
            best = max(best, _levenshtein_ratio(english_clean, token))
    return best


def _transparency(similarity: float) -> float:
    """Unrelated words (below 0.35, which is chance level) score the full 3."""
    if similarity <= 0.35:
        return 3.0
    if similarity >= 0.75:
        return 0.0
    return round(3.0 * (0.75 - similarity) / 0.40, 2)


def spelling_load(word: str) -> tuple[float, list[str]]:
    total, notes = 0.0, []
    lowered = word.lower()
    for pattern, weight, why in SPELLING_TRAPS:
        if re.search(pattern, lowered):
            total += weight
            notes.append(why)
    return min(3.0, total), notes


def score(english: str, german: str, pos: str = "") -> Difficulty:
    parts: dict[str, float] = {}
    notes: list[str] = []
    lowered = english.lower().strip()

    similarity = cognate_similarity(english, german)
    parts["transparency"] = _transparency(similarity)
    if similarity >= 0.7:
        notes.append(f"looks almost like the German word ({similarity:.2f})")

    load, spelling_notes = spelling_load(lowered)
    parts["spelling"] = round(load, 2)
    notes.extend(spelling_notes[:3])

    length = 0.0
    if len(lowered.replace(" ", "")) > 9:
        length += 0.75
        notes.append("a long word")
    if syllables(lowered) >= 4:
        length += 0.75
        notes.append("four or more syllables")
    parts["length"] = length

    morphology = 0.0
    if " " in lowered or "-" in lowered:
        morphology += 1.0
        notes.append("more than one word")
    if any(lowered.endswith(s) for s in ABSTRACT_SUFFIXES):
        morphology += 0.5
    parts["morphology"] = min(1.5, morphology)

    abstract = 0.0
    if any(lowered.endswith(s) for s in ABSTRACT_SUFFIXES):
        abstract = 1.5
        notes.append("an abstract noun")
    elif pos == "verb" and not in_core(lowered):
        abstract = 0.5
    parts["abstractness"] = abstract

    friend = FALSE_FRIENDS.get(lowered.split()[0] if lowered else "")
    parts["false_friend"] = 2.0 if friend else 0.0
    if friend:
        notes.append(f"false friend - {friend}")

    german_side = 0.0
    first = german.split("/")[0].strip()
    if len(first.split()) > 1:
        german_side += 0.5
        notes.append("a multi-word German prompt")
    if len(re.sub(r"[^\wäöüß]", "", first)) > 12:
        german_side += 0.5
        notes.append("a long German compound")
    parts["german_side"] = min(1.0, german_side)

    if in_core(lowered.split()[-1] if lowered else ""):
        parts["familiar"] = -1.5
        notes.append("already core A1-B1 vocabulary")

    raw = max(0.0, sum(parts.values()))
    result = 10.0 * raw / RAW_MAX
    if similarity >= 0.8:  # the German prompt hands the spelling over
        result *= 0.4
    elif similarity >= 0.7:
        result *= 0.7
    return Difficulty(round(min(10.0, result), 1), round(similarity, 2), parts, notes)


def score_item(item) -> Difficulty:
    """Score a VocabItem or a plain {'german':.., 'english':.., 'pos':..} dict."""
    if isinstance(item, dict):
        return score(item.get("english", ""), item.get("german", ""),
                     item.get("pos", ""))
    return score(item.english, item.german, item.pos)
