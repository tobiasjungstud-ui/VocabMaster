"""Propose a fair selection of words for one exam.

Two rules drive the choice:

1. **Hard words first.** A word a German speaker can copy from the German
   prompt tests nothing, so candidates are ranked by :mod:`difficulty` and
   taken from the top.
2. **Nothing that the checker would reject.** Every candidate is run against
   the already chosen words with the same comparison the checker uses, so a
   scaffold never proposes two words of one family, two near-synonyms or a
   known confusable pair.

A word-class quota keeps the set from turning into twelve abstract nouns, and
the gaps are picked so that the four slots need different word classes.
"""

from __future__ import annotations

import random
import re

from .check import ExamChecker
from .difficulty import score_item
from .vocab import VocabItem, VocabTest

#: at least this many of each word class among the chosen words, if the list
#: offers them at all
QUOTA = {"verb": 3, "adj": 2}


def unit_in_sentence(unit: str) -> str:
    """'Unit 8 Part II' -> 'unit 8 part II' (Roman numerals keep their case)."""
    return " ".join(w if re.fullmatch(r"[IVXLC]+", w) else w.lower()
                    for w in unit.split())


def _clashes(candidate: VocabItem, chosen: list[VocabItem]) -> bool:
    probe = ExamChecker({"task1": {"items": []}, "task2": {"gaps": []}})
    for other in chosen:
        probe.report.findings = []
        probe._compare(
            {"german": candidate.german, "english": candidate.english},
            {"german": other.german, "english": other.english},
        )
        if any(f.level in ("ERROR", "WARN") for f in probe.report.findings):
            return True
    return False


def ranked(test: VocabTest) -> list[tuple[VocabItem, float]]:
    """Every word of the section, hardest first."""
    scored = [(item, score_item(item).score) for item in test.items]
    return sorted(scored, key=lambda pair: (-pair[1], pair[0].number))


def select_words(test: VocabTest, count: int = 12, gap_count: int = 4,
                 seed: int = 0) -> tuple[list[VocabItem], list[VocabItem]]:
    """Return (translation items, cloze items), hardest words first."""
    order = [item for item, _ in ranked(test)]
    chosen: list[VocabItem] = []

    # 1. fill the word-class quota from the hardest candidates of each class
    for pos, minimum in QUOTA.items():
        taken = 0
        for item in order:
            if taken >= minimum or len(chosen) >= count:
                break
            if item.pos == pos and item not in chosen and not _clashes(item, chosen):
                chosen.append(item)
                taken += 1

    # 2. top up with the hardest remaining words
    for item in order:
        if len(chosen) >= count:
            break
        if item not in chosen and not _clashes(item, chosen):
            chosen.append(item)

    # 3. gaps: one slot per word class, so the four gaps cannot be swapped
    gaps: list[VocabItem] = []
    by_score = sorted(chosen, key=lambda i: -score_item(i).score)
    for pos in ("verb", "noun", "adj"):
        for item in by_score:
            if len(gaps) >= gap_count:
                break
            if item.pos == pos and item not in gaps:
                gaps.append(item)
                break
    for item in by_score:
        if len(gaps) >= gap_count:
            break
        if item not in gaps:
            gaps.append(item)

    translation = [i for i in chosen if i not in gaps]
    translation.sort(key=lambda i: i.number)
    return translation, gaps


def build_scaffold(test: VocabTest, unit: str, count: int = 12,
                   gap_count: int = 4, seed: int = 0) -> dict:
    translation, gaps = select_words(test, count, gap_count, seed)
    rng = random.Random(seed + 1)
    bank = [g.german for g in gaps]
    while len(bank) > 1 and bank == [g.german for g in gaps]:
        rng.shuffle(bank)
    placeholder = " ".join(
        f"TODO sentence {i + 1} with the gap {{{i + 1}}} in it."
        for i in range(gap_count)
    )
    sentence_unit = unit_in_sentence(unit)
    head, _, tail = unit.partition(" Part")
    return {
        "meta": {
            "title": f"{unit} - Vocabulary test",
            "source": test.name,
            "note": "Replace task2.text with a real B1.2 text, then run `check`.",
            "difficulty": {
                i.english: score_item(i).score for i in translation + gaps
            },
        },
        "total_words": count,
        "header": {
            "title": " Vocabulary",
            "unit": f"{head} |{('Part' + tail) if tail else ''}".strip(),
            "name_label": "Name:",
            "grade_label": "Grade :",
        },
        "task1": {
            "instruction": f"1) Translate using the vocabulary from {sentence_unit}.",
            "items": [{"german": i.german, "english": i.english, "pos": i.pos}
                      for i in translation],
        },
        "task2": {
            "instruction": f"2)  Fill in the gaps using the vocabulary from {sentence_unit}. ",
            "word_bank_label": "Words:",
            "word_bank": bank,
            "gaps": [{"german": g.german, "english": g.english,
                      "answer": g.english, "pos": g.pos} for g in gaps],
            "text": placeholder,
        },
    }
