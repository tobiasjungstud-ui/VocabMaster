"""Mechanical checks on the English of the cloze text.

Nothing here knows anything about exams - it only answers: is this text
correctly written English at the intended level?
"""

from __future__ import annotations

import re

from .wordlists import (
    ABOVE_B1_STRUCTURES,
    AMERICAN_SPELLINGS,
    FALSE_FRIENDS,
    STRUCTURE_MARKERS,
    dictionary,
    in_core,
    syllables,
)

WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

#: contractions and forms a plain dictionary does not always carry
EXTRA_OK = {
    "ok", "okay", "tv", "dvd", "online", "website", "email", "smartphone",
    "cannot", "everyday", "gonna", "wanna", "doesn't", "don't", "didn't",
    "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't", "hadn't",
    "won't", "wouldn't", "can't", "couldn't", "shouldn't", "mustn't",
    "i'm", "i've", "i'd", "i'll", "it's", "he's", "she's", "that's",
    "there's", "we're", "they're", "you're", "we've", "they've", "you've",
    "he'd", "she'd", "we'd", "they'd", "you'd", "i", "a",
}


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def misspellings(text: str, allowed: set[str]) -> list[str]:
    """Words that are in no dictionary, not in the vocabulary and not names."""
    lexicon = dictionary()
    if not lexicon:
        return []
    allowed = {a.lower() for a in allowed} | EXTRA_OK
    bad = []
    for token in words(text):
        lowered = token.lower()
        if lowered in allowed or lowered in lexicon:
            continue
        if token[:1].isupper() and token not in ("I",):
            continue  # a name or the start of a sentence, judged elsewhere
        if lowered.replace("'", "") in lexicon:
            continue
        bad.append(token)
    return sorted(set(bad))


def unknown_words(text: str, allowed: set[str]) -> list[str]:
    """Content words a B1 learner probably does not know and that the exam
    does not intend to test."""
    allowed = {a.lower() for a in allowed}
    out = []
    for token in words(text):
        lowered = token.lower()
        if lowered in allowed or token[:1].isupper():
            continue
        if len(lowered) < 5 or in_core(lowered):
            continue
        out.append(lowered)
    return sorted(set(out))


def american_spellings(text: str) -> list[tuple[str, str]]:
    found = []
    for token in words(text):
        british = AMERICAN_SPELLINGS.get(token.lower())
        if british:
            found.append((token, british))
    return found


def false_friends_used(text: str) -> list[tuple[str, str]]:
    return [(t, FALSE_FRIENDS[t.lower()]) for t in words(text)
            if t.lower() in FALSE_FRIENDS]


def mechanics(text: str) -> list[str]:
    """Typography and punctuation problems a proofreader would mark."""
    problems = []
    if " " in text:
        problems.append("non-breaking space in the text")
    if re.search(r"[“”‘’]", text):
        problems.append("curly quotation marks - Word will handle these itself")
    if text != text.strip():
        problems.append("leading or trailing whitespace")
    if "  " in text:
        problems.append("double space")
    if re.search(r"\s[,.;:!?]", text):
        problems.append("space before a punctuation mark")
    if re.search(r"[,;:](?=[A-Za-z])", text):
        problems.append("missing space after a comma or colon")
    if re.search(r"\.{2,}|,{2,}|!{2,}|\?{2,}", text):
        problems.append("repeated punctuation")
    for match in re.finditer(r"\b(\w+)\s+\1\b", text, re.IGNORECASE):
        problems.append(f"the word '{match.group(1)}' appears twice in a row")
    if text.count("(") != text.count(")"):
        problems.append("unbalanced brackets")
    if text.count('"') % 2:
        problems.append("unbalanced quotation marks")
    for sentence in sentences(text):
        first = re.match(r"[A-Za-z]", sentence)
        if first and not sentence[0].isupper():
            problems.append(f"sentence does not start with a capital: "
                            f"'{sentence[:35]}...'")
    if not text.rstrip().endswith((".", "!", "?")):
        problems.append("the text does not end with a full stop")
    if re.search(r"\ba\s+[aeiouAEIOU]", text):
        problems.append("'a' before a vowel - should this be 'an'?")
    if re.search(r"\ban\s+[^aeiouAEIOU\s{_]", text):
        problems.append("'an' before a consonant - should this be 'a'?")
    return problems


def structures_above_level(text: str) -> list[str]:
    return [name for pattern, name in ABOVE_B1_STRUCTURES
            if re.search(pattern, text, re.IGNORECASE)]


def structures_used(text: str) -> list[str]:
    return [name for pattern, name in STRUCTURE_MARKERS
            if re.search(pattern, text, re.IGNORECASE)]


def readability(text: str) -> dict:
    """Flesch-Kincaid grade and Flesch reading ease, plus the raw counts."""
    tokens = words(text)
    sents = sentences(text)
    n_words, n_sent = len(tokens), max(1, len(sents))
    n_syll = sum(syllables(t) for t in tokens)
    wps = n_words / n_sent
    spw = n_syll / max(1, n_words)
    return {
        "words": n_words,
        "sentences": len(sents),
        "syllables": n_syll,
        "words_per_sentence": round(wps, 1),
        "syllables_per_word": round(spw, 2),
        "flesch_reading_ease": round(206.835 - 1.015 * wps - 84.6 * spw, 1),
        "flesch_kincaid_grade": round(0.39 * wps + 11.8 * spw - 15.59, 1),
        "longest_sentence": max((len(words(s)) for s in sents), default=0),
        "subordinators": sum(
            len(re.findall(r"\b(because|although|while|when|which|that|who|if|"
                           r"before|after|since|unless|whether)\b", s, re.I))
            for s in sents),
    }
