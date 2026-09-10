"""Every quality check that runs on an exam before it is printed.

The checks exist because the same mistakes keep coming back when an exam is
written quickly, and because a printed exam cannot be corrected afterwards.
They are grouped into five areas:

    spec        is the exam file itself complete and consistent?
    selection   are the twelve words a fair, non-overlapping, hard enough set?
    source      does every word really come from the vocabulary list?
    cloze       is the gap text solvable, unambiguous and free of giveaways?
    language    is the English correct, British and at B1.2 level?

Levels:
    ERROR  the exam is broken - `build` refuses to write it
    WARN   very probably a problem, look at it
    INFO   worth knowing, printed in the report
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import english
from .difficulty import score_item
from .lexicon import (
    ADJ_TRIGGERS,
    BASE_VERB_TRIGGERS,
    DEFAULT_CONFUSABLE_GROUPS,
    DERIVATION_SUFFIXES,
    FUNCTION_WORDS,
    GERMAN_MARKERS,
    GERUND_TRIGGERS,
    NOUN_TRIGGERS,
    TOPIC_CARRIER_WORDS,
)
from .vocab import VocabTest, guess_pos, normalise

ERROR, WARN, INFO = "ERROR", "WARN", "INFO"

#: Default target band for the cloze text: Niveau A (B1.2-B2.1).
#: :mod:`vocabmaster.niveau` passes a different band for Niveau B; these
#: values stay the fallback when no profile is given.
LEVEL_TARGETS = {
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

#: Selection targets.
SELECTION_TARGETS = {
    "min_mean_difficulty": 2.5,
    "min_item_difficulty": 1.0,
    "max_easy_cognates": 2,      # similarity >= 0.7 to the German prompt
    "max_multiword_items": 3,
    "max_share_one_word_class": 0.7,
}

SPEC_SCHEMA = {
    "meta": dict,
    "total_words": int,
    "header": dict,
    "task1": dict,
    "task2": dict,
}
TASK1_KEYS = {"instruction", "items"}
TASK2_KEYS = {"instruction", "word_bank_label", "word_bank", "gaps", "text"}
ITEM_KEYS = {"german", "english", "pos", "note"}
GAP_KEYS = {"german", "english", "answer", "pos", "unique_because", "note"}
HEADER_KEYS = {"title", "unit", "name_label", "grade_label"}


@dataclass
class Finding:
    level: str
    check: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level:5}] {self.check}: {self.message}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == WARN]

    def ok(self) -> bool:
        return not self.errors


# --------------------------------------------------------------------- helpers
def stem(word: str) -> str:
    word = re.sub(r"[^a-z]", "", word.lower())
    for suffix in DERIVATION_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def similarity(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    if a == b:
        return 1.0
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


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text)


def content_tokens(text: str) -> list[str]:
    return [t.lower() for t in tokens(text)
            if t != "GAP" and t.lower() not in FUNCTION_WORDS and len(t) > 2]


def entry_pos(entry: dict) -> str:
    return entry.get("pos") or guess_pos(entry.get("german", ""))


GAP_RE = r"\{\d*\}|_{3,}"


class ExamChecker:
    def __init__(self, spec: dict, vocab: VocabTest | None = None,
                 all_tests: list[VocabTest] | None = None,
                 confusable_groups: list[list[str]] | None = None,
                 level_targets: dict | None = None,
                 selection_targets: dict | None = None):
        self.spec = spec if isinstance(spec, dict) else {}
        self.vocab = vocab
        self.all_tests = all_tests or ([vocab] if vocab else [])
        self.groups = confusable_groups or DEFAULT_CONFUSABLE_GROUPS
        # Zielbänder des Niveaus; ohne Angabe gilt das Band für Niveau A.
        self.level = {**LEVEL_TARGETS, **(level_targets or {})}
        self.selection = {**SELECTION_TARGETS, **(selection_targets or {})}
        self.report = Report()
        self.task1 = self.spec.get("task1") or {}
        self.task2 = self.spec.get("task2") or {}
        self.items1 = self.task1.get("items") or []
        self.gaps = self.task2.get("gaps") or []

    # ------------------------------------------------------------------ utils
    def add(self, level: str, check: str, message: str) -> None:
        self.report.findings.append(Finding(level, check, message))

    @property
    def all_entries(self) -> list[dict]:
        return list(self.items1) + [
            dict(g, gap=i + 1) for i, g in enumerate(self.gaps)
        ]

    def where(self, entry: dict) -> str:
        return f"gap {entry['gap']}" if "gap" in entry else "task 1"

    def raw_text(self) -> str:
        return self.task2.get("text", "") or ""

    def plain_text(self) -> str:
        """Cloze text with every gap placeholder replaced by one word."""
        return re.sub(GAP_RE, "GAP", self.raw_text())

    def slot_sequence(self) -> list[str]:
        return re.findall(rf"{GAP_RE}|[A-Za-z']+|[.,;:!?]", self.raw_text())

    def gap_positions(self) -> list[int]:
        return [i for i, t in enumerate(self.slot_sequence())
                if re.fullmatch(GAP_RE, t)]

    def answers(self) -> list[str]:
        return [g.get("answer", "") for g in self.gaps]

    def allowed_words(self) -> set[str]:
        """Everything that may legitimately appear without being flagged."""
        allowed = set()
        for entry in self.all_entries:
            for word in tokens(entry.get("english", "")):
                allowed.add(word.lower())
        if self.vocab:
            for item in self.vocab.items:
                for word in tokens(item.english):
                    allowed.add(word.lower())
        allowed.add("gap")
        return allowed

    # ------------------------------------------------------------- spec checks
    def check_spec_schema(self) -> None:
        for key, kind in SPEC_SCHEMA.items():
            if key not in self.spec:
                if key in ("meta",):
                    continue
                self.add(ERROR, "spec", f"the spec has no '{key}' section")
            elif not isinstance(self.spec[key], kind):
                self.add(ERROR, "spec",
                         f"'{key}' should be a {kind.__name__}, "
                         f"not {type(self.spec[key]).__name__}")
        for name, keys, block in (("header", HEADER_KEYS, self.spec.get("header") or {}),
                                  ("task1", TASK1_KEYS, self.task1),
                                  ("task2", TASK2_KEYS, self.task2)):
            unknown = set(block) - keys
            if unknown:
                self.add(WARN, "spec",
                         f"{name} has unknown key(s) {sorted(unknown)} - typo?")
        for index, item in enumerate(self.items1, start=1):
            unknown = set(item) - ITEM_KEYS
            if unknown:
                self.add(WARN, "spec",
                         f"task 1 item {index} has unknown key(s) {sorted(unknown)}")
        for index, gap in enumerate(self.gaps, start=1):
            unknown = set(gap) - GAP_KEYS - {"gap"}
            if unknown:
                self.add(WARN, "spec",
                         f"gap {index} has unknown key(s) {sorted(unknown)}")
            if gap.get("english") and gap.get("answer") and \
                    normalise(gap["english"]) != normalise(gap["answer"]):
                self.add(ERROR, "spec",
                         f"gap {index}: 'english' is '{gap['english']}' but "
                         f"'answer' is '{gap['answer']}'")

    def check_structure(self) -> None:
        n1, n2 = len(self.items1), len(self.gaps)
        total = self.spec.get("total_words", 12)
        if n1 + n2 != total:
            self.add(ERROR, "structure",
                     f"{n1} + {n2} = {n1 + n2} words tested, expected {total}")
        if not self.items1:
            self.add(ERROR, "structure", "task 1 has no items")
        if not self.gaps:
            self.add(ERROR, "structure", "task 2 has no gaps")
        bank = self.task2.get("word_bank") or []
        if len(bank) != n2:
            self.add(ERROR, "structure",
                     f"the word bank lists {len(bank)} words but there are "
                     f"{n2} gaps")
        for name, task in (("1", self.task1), ("2", self.task2)):
            instruction = task.get("instruction", "")
            if not instruction.strip().startswith(f"{name})"):
                self.add(WARN, "structure",
                         f"the instruction of task {name} does not start "
                         f"with '{name})'")
            for number in re.findall(r"\b(\d+)\s*P\b", instruction):
                self.add(WARN, "structure",
                         f"task {name}: the instruction contains a hard-coded "
                         f"point count ({number}P) - it is added automatically")

    def check_header_consistency(self) -> None:
        header = self.spec.get("header") or {}
        unit = re.sub(r"[|]", " ", header.get("unit", "")).lower()
        unit_words = [w for w in re.findall(r"[a-z0-9]+", unit) if w != "unit"]
        for name, task in (("1", self.task1), ("2", self.task2)):
            instruction = (task.get("instruction") or "").lower()
            missing = [w for w in unit_words if w not in instruction]
            if unit_words and missing:
                self.add(WARN, "header",
                         f"task {name} says '{task.get('instruction', '').strip()}' "
                         f"but the header says '{header.get('unit', '')}' "
                         f"- {missing} is missing")

    # ----------------------------------------------------------- source checks
    def check_against_vocabulary(self) -> None:
        if self.vocab is None:
            self.add(INFO, "source",
                     "no vocabulary list given - the source checks were skipped")
            return
        for entry in self.all_entries:
            where = self.where(entry)
            item = self.vocab.by_german(entry.get("german", ""))
            if item is None:
                by_en = self.vocab.by_english(entry.get("english", ""))
                if by_en is None:
                    self.add(ERROR, "source",
                             f"{where}: '{entry.get('german')}' / "
                             f"'{entry.get('english')}' is not in "
                             f"{self.vocab.name}")
                else:
                    self.add(ERROR, "source",
                             f"{where}: the list writes the German prompt as "
                             f"'{by_en.german}', not '{entry.get('german')}'")
                continue
            if normalise(item.english) != normalise(entry.get("english", "")):
                self.add(ERROR, "source",
                         f"{where}: '{entry['german']}' is '{item.english}' in "
                         f"the list, not '{entry.get('english')}'")

    def check_source_ambiguity(self) -> None:
        """A prompt that fits two entries of the list cannot be marked fairly."""
        if self.vocab is None:
            return
        for entry in self.all_entries:
            german = normalise(entry.get("german", ""))
            english = normalise(entry.get("english", ""))
            same_german = [i for i in self.vocab.items
                           if normalise(i.german) == german]
            if len(same_german) > 1:
                self.add(ERROR, "ambiguity",
                         f"{self.where(entry)}: '{entry['german']}' appears "
                         f"{len(same_german)} times in the list "
                         f"({', '.join(i.english for i in same_german)})")
            same_english = [i for i in self.vocab.items
                            if normalise(i.english) == english]
            if len(same_english) > 1:
                self.add(WARN, "ambiguity",
                         f"{self.where(entry)}: '{entry['english']}' is the "
                         f"translation of {len(same_english)} entries "
                         f"({', '.join(i.german for i in same_english)})")
            variants = [v for v in entry.get("german", "").split("/") if v.strip()]
            for variant in variants:
                hits = [i for i in self.vocab.items
                        if normalise(i.german) != german
                        and normalise(variant) in
                        [normalise(v) for v in i.german.split("/")]]
                if hits:
                    self.add(WARN, "ambiguity",
                             f"{self.where(entry)}: the variant "
                             f"'{variant.strip()}' also belongs to "
                             f"'{hits[0].german}' ({hits[0].english})")

    def check_other_test_overlap(self) -> None:
        """A word that is also in the other test section will be tested twice
        across the two exams."""
        if not self.all_tests or self.vocab is None:
            return
        others = [t for t in self.all_tests if t.name != self.vocab.name]
        for entry in self.all_entries:
            for other in others:
                hit = other.by_english(entry.get("english", ""))
                if hit:
                    self.add(WARN, "overlap",
                             f"{self.where(entry)}: '{entry['english']}' is also "
                             f"entry {hit.number} of '{other.name}'")

    # -------------------------------------------------------- selection checks
    def check_duplicates(self) -> None:
        seen_de: dict[str, str] = {}
        seen_en: dict[str, str] = {}
        for entry in self.all_entries:
            where = self.where(entry)
            de, en = normalise(entry.get("german", "")), normalise(entry.get("english", ""))
            if de in seen_de:
                self.add(ERROR, "duplicate",
                         f"'{entry['german']}' is tested twice "
                         f"({seen_de[de]} and {where})")
            if en in seen_en:
                self.add(ERROR, "duplicate",
                         f"'{entry['english']}' is tested twice "
                         f"({seen_en[en]} and {where})")
            seen_de[de], seen_en[en] = where, where
        bank = [normalise(w) for w in self.task2.get("word_bank") or []]
        for word in set(bank):
            if bank.count(word) > 1:
                self.add(ERROR, "duplicate",
                         f"the word bank lists '{word}' {bank.count(word)} times")

    def check_similar_words(self) -> None:
        entries = self.all_entries
        for i, a in enumerate(entries):
            for b in entries[i + 1:]:
                self._compare(a, b)

    def _compare(self, a: dict, b: dict) -> None:
        label = (f"'{a.get('german')}' ({a.get('english')}) / "
                 f"'{b.get('german')}' ({b.get('english')})")
        en_a, en_b = a.get("english", "").lower(), b.get("english", "").lower()
        de_a, de_b = a.get("german", "").lower(), b.get("german", "").lower()

        if stem(en_a) and stem(en_a) == stem(en_b):
            self.add(ERROR, "word-family",
                     f"{label}: same English word family ('{stem(en_a)}')")
            return
        for x, y in ((en_a, en_b), (en_b, en_a)):
            if len(y) >= 5 and y in x:
                self.add(ERROR, "word-family",
                         f"{label}: '{y}' is contained in '{x}'")
                return
        if similarity(en_a, en_b) >= 0.75:
            self.add(WARN, "similar", f"{label}: the English words look very similar")
            return
        for x, y in ((de_a, de_b), (de_b, de_a)):
            if len(y) >= 6 and y in x:
                self.add(WARN, "similar",
                         f"{label}: the German prompts overlap ('{y}' in '{x}')")
                return
        if similarity(de_a.split("/")[0].strip(), de_b.split("/")[0].strip()) >= 0.8:
            self.add(WARN, "similar", f"{label}: the German prompts look very similar")
            return
        for group in self.groups:
            g = {w.lower() for w in group} | {stem(w) for w in group}
            if {en_a, stem(en_a)} & g and {en_b, stem(en_b)} & g:
                self.add(WARN, "confusable",
                         f"{label}: known confusable pair - testing both in one "
                         f"exam is unfair")
                return
        self._compare_examples(a, b, label)

    def _compare_examples(self, a: dict, b: dict, label: str) -> None:
        """Two words whose example sentences talk about the same thing are
        probably from the same semantic field."""
        if self.vocab is None:
            return
        item_a = self.vocab.by_german(a.get("german", ""))
        item_b = self.vocab.by_german(b.get("german", ""))
        if not (item_a and item_b and item_a.example and item_b.example):
            return
        shared = ({stem(t) for t in content_tokens(item_a.example)}
                  & {stem(t) for t in content_tokens(item_b.example)}
                  - {stem(item_a.english), stem(item_b.english)})
        shared -= {stem(w) for w in TOPIC_CARRIER_WORDS}
        if len(shared) >= 2:
            self.add(INFO, "semantic-field",
                     f"{label}: their example sentences share "
                     f"{sorted(shared)} - check they are not too close")

    def check_difficulty(self) -> None:
        scored = [(e, score_item(e)) for e in self.all_entries]
        if not scored:
            return
        mean = sum(d.score for _, d in scored) / len(scored)
        self.report.stats["difficulty"] = {
            "mean": round(mean, 2),
            "items": [{"english": e.get("english"), "score": d.score,
                       "similarity": d.similarity, "notes": d.notes}
                      for e, d in scored],
        }
        target = self.selection["min_mean_difficulty"]
        if mean < target:
            self.add(WARN, "difficulty",
                     f"average word difficulty {mean:.1f}/10 is below the "
                     f"target of {target} - prefer harder words")
        easy = [(e, d) for e, d in scored
                if d.similarity >= 0.7]
        if len(easy) > self.selection["max_easy_cognates"]:
            self.add(WARN, "difficulty",
                     f"{len(easy)} words can simply be copied from the German "
                     f"prompt ({', '.join(e['english'] for e, _ in easy)})")
        for entry, d in scored:
            if d.score < self.selection["min_item_difficulty"]:
                self.add(WARN, "difficulty",
                         f"{self.where(entry)}: '{entry['english']}' scores only "
                         f"{d.score}/10 - {'; '.join(d.notes) or 'nothing hard about it'}")
        hardest = max(scored, key=lambda p: p[1].score)
        self.add(INFO, "difficulty",
                 f"average {mean:.1f}/10, hardest '{hardest[0]['english']}' "
                 f"({hardest[1].score})")

    def check_balance(self) -> None:
        counts: dict[str, int] = {}
        for entry in self.all_entries:
            pos = entry_pos(entry)
            counts[pos] = counts.get(pos, 0) + 1
        self.report.stats["word_classes"] = counts
        self.add(INFO, "balance",
                 ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
        total = sum(counts.values())
        if total and max(counts.values()) / total > self.selection["max_share_one_word_class"]:
            biggest = max(counts, key=counts.get)
            self.add(WARN, "balance",
                     f"{counts[biggest]} of {total} words are {biggest}s - "
                     f"mix the word classes")
        multiword = [e["english"] for e in self.all_entries
                     if " " in e.get("english", "").strip()]
        if len(multiword) > self.selection["max_multiword_items"]:
            self.add(WARN, "balance",
                     f"{len(multiword)} multi-word items ({', '.join(multiword)}) "
                     f"- they take a long time to write")

    def check_coverage(self) -> None:
        if self.vocab is None:
            return
        numbers = []
        for entry in self.all_entries:
            item = self.vocab.by_german(entry.get("german", ""))
            if item:
                numbers.append(item.number)
        if len(numbers) < 4:
            return
        self.report.stats["entry_numbers"] = sorted(numbers)
        span = max(numbers) - min(numbers) + 1
        if span < 0.5 * len(self.vocab.items):
            self.add(WARN, "coverage",
                     f"all tested words come from entries {min(numbers)}-"
                     f"{max(numbers)} of {len(self.vocab.items)} - spread the "
                     f"selection over the whole list")
        pairs = [(a, b) for a, b in zip(sorted(numbers), sorted(numbers)[1:], strict=False)
                 if b - a == 1]
        if len(pairs) > 2:
            self.add(INFO, "coverage",
                     f"{len(pairs)} pairs of neighbouring list entries were "
                     f"chosen - neighbours are often thematically linked")

    # -------------------------------------------------------------- gap checks
    def check_word_bank(self) -> None:
        # The bank is printed as one comma-separated line, so a prompt that
        # itself contains a comma splits into two on the sheet: four gaps but
        # five words to choose from.  Alternatives belong behind a slash.
        for word in self.task2.get("word_bank") or []:
            if "," in str(word):
                self.add(ERROR, "word-bank",
                         f"the prompt {word!r} contains a comma - printed in "
                         f"the bank it reads as two separate words. Write "
                         f"alternatives with a slash ('spielen / auftreten').")

        bank = [normalise(w) for w in self.task2.get("word_bank") or []]
        wanted = [normalise(g.get("german", "")) for g in self.gaps]
        if sorted(bank) != sorted(wanted):
            missing = [w for w in wanted if w not in bank]
            extra = [w for w in bank if w not in wanted]
            if missing:
                self.add(ERROR, "word-bank",
                         f"gap answers missing from the word bank: {missing}")
            if extra:
                self.add(ERROR, "word-bank",
                         f"the word bank has words that fit no gap: {extra}")
        elif bank == wanted and len(bank) > 1:
            self.add(ERROR, "word-bank",
                     "the word bank is in gap order - shuffle it, otherwise the "
                     "task can be solved without reading")
        elif len(bank) > 2 and bank == list(reversed(wanted)):
            self.add(WARN, "word-bank",
                     "the word bank is the gap order reversed - shuffle it properly")

    def check_gaps(self) -> None:
        text = self.raw_text()
        numbered = [int(m) for m in re.findall(r"\{(\d+)\}", text)]
        anonymous = len(re.findall(r"\{\}|_{3,}", text))
        total = len(numbered) + anonymous
        if total != len(self.gaps):
            self.add(ERROR, "gaps",
                     f"the text contains {total} gap markers but "
                     f"{len(self.gaps)} gaps are declared")
        if numbered and anonymous:
            self.add(ERROR, "gaps",
                     "the text mixes numbered and unnumbered gap markers")
        if numbered and sorted(numbered) != list(range(1, len(numbered) + 1)):
            self.add(ERROR, "gaps",
                     f"the gap markers are numbered {numbered}, expected "
                     f"1..{len(numbered)} once each")
        sequence = self.slot_sequence()
        positions = self.gap_positions()
        for a, b in zip(positions, positions[1:], strict=False):
            if b - a < self.level["min_gap_distance"]:
                self.add(WARN, "gaps",
                         f"two gaps are only {b - a} words apart - spread them out")
        for order, index in enumerate(positions, start=1):
            lead_in = len([t for t in sequence[:index] if t.isalpha()])
            tail = len([t for t in sequence[index + 1:] if t.isalpha()])
            if lead_in < self.level["min_lead_in"]:
                self.add(WARN, "gaps",
                         f"gap {order} comes after only {lead_in} words - the "
                         f"reader has no context yet")
            if tail < self.level["min_tail"]:
                self.add(WARN, "gaps",
                         f"gap {order} has only {tail} words after it")
            if index == 0 or sequence[index - 1] in ".!?":
                self.add(ERROR, "gaps",
                         f"gap {order} starts a sentence - the capital letter "
                         f"would be part of the answer")

    def check_gap_grammar(self) -> None:
        sequence = self.slot_sequence()
        for order, index in enumerate(self.gap_positions(), start=1):
            if order > len(self.gaps):
                break
            gap = self.gaps[order - 1]
            answer, german = gap.get("answer", ""), gap.get("german", "")
            pos = entry_pos(gap)
            before = sequence[index - 1].lower() if index else ""
            after = sequence[index + 1].lower() if index + 1 < len(sequence) else ""
            label = f"gap {order} ('{answer}')"

            if before in BASE_VERB_TRIGGERS and pos != "verb":
                self.add(ERROR, "grammar",
                         f"{label}: '{before}' needs a verb, but '{german}' is "
                         f"a {pos}")
            if before in NOUN_TRIGGERS and pos != "noun":
                self.add(ERROR, "grammar",
                         f"{label}: '{before}' needs a noun, but '{german}' is "
                         f"a {pos}")
            if before in ADJ_TRIGGERS and before not in NOUN_TRIGGERS and pos == "verb":
                self.add(WARN, "grammar",
                         f"{label}: '{before}' usually takes an adjective or a "
                         f"noun, but '{german}' is a verb")
            if before == "an":
                self.add(ERROR, "grammar",
                         f"{label}: 'an' right before the gap gives away that "
                         f"the answer starts with a vowel - rephrase")
            if before == "a" and answer[:1].lower() in "aeiou":
                self.add(ERROR, "grammar",
                         f"{label}: 'a {answer}' is wrong - use 'an' or rephrase")
            if before == "a" and pos == "noun" and answer.lower().endswith("s"):
                self.add(ERROR, "grammar",
                         f"{label}: 'a {answer}' - the answer is plural")
            if pos == "noun" and after in ("is", "was", "has") and \
                    answer.lower().endswith("s") and not answer.lower().endswith("ss"):
                self.add(ERROR, "grammar",
                         f"{label}: '{answer} {after}' - plural noun with a "
                         f"singular verb")
            if pos == "noun" and after in ("are", "were", "have") and \
                    not answer.lower().endswith("s"):
                self.add(ERROR, "grammar",
                         f"{label}: '{answer} {after}' - singular noun with a "
                         f"plural verb")
            if before in GERUND_TRIGGERS and before != "to" and pos == "verb":
                self.add(WARN, "grammar",
                         f"{label}: after '{before}' the answer needs an -ing "
                         f"form, but the word bank gives the base form")
            if before in ("he", "she", "it") and pos == "verb":
                self.add(WARN, "grammar",
                         f"{label}: after '{before}' the verb needs an -s, but "
                         f"the word bank gives the base form")
            if before in ("have", "has", "had") and pos == "verb":
                self.add(WARN, "grammar",
                         f"{label}: after '{before}' the answer needs a past "
                         f"participle, but the word bank gives the base form")

    def check_gap_uniqueness(self) -> None:
        """Could another word from the bank be written into this gap?

        Only a real problem when two gaps could be swapped - if the fit works
        in one direction only, the remaining gap settles it.
        """
        sequence = self.slot_sequence()
        positions = self.gap_positions()
        slots = []
        for index in positions:
            before = sequence[index - 1].lower() if index else ""
            accepts = set()
            if before in BASE_VERB_TRIGGERS:
                accepts = {"verb"}
            elif before in NOUN_TRIGGERS:
                accepts = {"noun"}
            elif before in ADJ_TRIGGERS:
                accepts = {"adj", "noun"}
            slots.append(accepts)

        for i, gap_i in enumerate(self.gaps):
            if i >= len(slots):
                break
            for j, gap_j in enumerate(self.gaps):
                if j <= i or j >= len(slots):
                    continue
                pos_i, pos_j = entry_pos(gap_i), entry_pos(gap_j)
                fits_ij = not slots[i] or pos_j in slots[i]
                fits_ji = not slots[j] or pos_i in slots[j]
                if not (fits_ij and fits_ji):
                    continue
                reason = gap_i.get("unique_because") or gap_j.get("unique_because")
                message = (f"gaps {i + 1} ('{gap_i.get('answer')}') and "
                           f"{j + 1} ('{gap_j.get('answer')}') could be swapped "
                           f"as far as word class goes")
                if reason:
                    self.add(INFO, "uniqueness", f"{message} - accepted: {reason}")
                else:
                    self.add(WARN, "uniqueness",
                             f"{message} - make the context decide, or record "
                             f"why it already does in 'unique_because'")

    def check_giveaways(self) -> None:
        text_stems = {stem(t) for t in content_tokens(self.plain_text())}
        for order, gap in enumerate(self.gaps, start=1):
            answer = gap.get("answer", "")
            if stem(answer) in text_stems:
                self.add(ERROR, "giveaway",
                         f"gap {order}: '{answer}' (or a form of it) also "
                         f"appears in the text itself")
        task1_stems = {stem(i.get("english", "")): i.get("english")
                       for i in self.items1}
        for token in content_tokens(self.plain_text()):
            if stem(token) in task1_stems:
                self.add(ERROR, "giveaway",
                         f"the cloze text contains '{token}', which is the "
                         f"answer to task 1 item '{task1_stems[stem(token)]}'")
        lowered = self.plain_text().lower()
        for entry in self.all_entries:
            for variant in entry.get("german", "").split("/"):
                variant = variant.strip().lower()
                if len(variant) > 4 and variant in lowered:
                    self.add(ERROR, "giveaway",
                             f"the German prompt '{variant}' appears in the "
                             f"English text")
        if self.vocab:
            for gap in self.gaps:
                item = self.vocab.by_german(gap.get("german", ""))
                if item and item.example and normalise(item.example) in \
                        normalise(self.plain_text()):
                    self.add(WARN, "giveaway",
                             f"the example sentence of '{item.english}' was "
                             f"copied from the vocabulary list - the students "
                             f"have seen it")

    def check_text_synonyms(self) -> None:
        """A near-synonym of a task 1 answer in the cloze text is a hint the
        students should not get."""
        text_words = {stem(t) for t in content_tokens(self.plain_text())}
        for item in self.items1:
            english_word = item.get("english", "").lower()
            for group in self.groups:
                members = {w.lower() for w in group} | {stem(w) for w in group}
                if not ({english_word, stem(english_word)} & members):
                    continue
                hit = sorted(members & text_words - {stem(english_word)})
                if hit:
                    self.add(WARN, "giveaway",
                             f"the cloze text uses '{hit[0]}', which is close to "
                             f"the task 1 answer '{item['english']}'")

    def check_repetition(self) -> None:
        counts: dict[str, list[str]] = {}
        for token in content_tokens(self.plain_text()):
            counts.setdefault(stem(token), []).append(token)
        carriers = {stem(w) for w in TOPIC_CARRIER_WORDS}
        for key, forms in counts.items():
            if key in carriers:
                continue
            if len(forms) > 2:
                self.add(WARN, "repetition",
                         f"'{forms[0]}' appears {len(forms)} times in the "
                         f"cloze text")

    # --------------------------------------------------------- language checks
    def check_language(self) -> None:
        text = self.plain_text()
        allowed = self.allowed_words()

        for problem in english.mechanics(text):
            self.add(WARN, "mechanics", problem)

        bad = english.misspellings(text, allowed)
        if bad:
            self.add(ERROR, "spelling",
                     f"not in the dictionary: {', '.join(bad)}")

        for american, british in english.american_spellings(text):
            self.add(WARN, "variety",
                     f"'{american}' is American - the vocabulary list is "
                     f"British ('{british}')")

        for word, warning in english.false_friends_used(text):
            self.add(INFO, "false-friend",
                     f"'{word}' is a false friend for German speakers ({warning})")

        german = sorted({t.lower() for t in tokens(text)
                         if t.lower() in GERMAN_MARKERS})
        if german:
            self.add(ERROR, "language",
                     f"German words in the English cloze text: {', '.join(german)}")
        if re.search(r"[ÄÖÜäöüß]", text):
            self.add(WARN, "language",
                     "the English cloze text contains German characters")

        for structure in english.structures_above_level(text):
            self.add(WARN, "level", f"{structure} is above B1.2")

        unknown = english.unknown_words(text, allowed)
        if len(unknown) > self.level["max_unknown_words"]:
            self.add(WARN, "level",
                     f"{len(unknown)} words are probably unknown at B1 and are "
                     f"not being tested: {', '.join(unknown)}")
        elif unknown:
            self.add(INFO, "level",
                     f"words outside the core B1 list: {', '.join(unknown)}")

    def check_level(self) -> None:
        text = self.plain_text()
        stats = english.readability(text)
        stats["gaps"] = len(self.gaps)
        self.report.stats["readability"] = stats
        t = self.level
        n_words, n_sent = stats["words"], stats["sentences"]

        if not t["min_words"] <= n_words <= t["max_words"]:
            self.add(WARN, "level",
                     f"the text has {n_words} words, target "
                     f"{t['min_words']}-{t['max_words']}")
        if not t["min_sentences"] <= n_sent <= t["max_sentences"]:
            self.add(WARN, "level",
                     f"the text has {n_sent} sentences, target "
                     f"{t['min_sentences']}-{t['max_sentences']}")
        if stats["longest_sentence"] > t["max_sentence_length"]:
            self.add(WARN, "level",
                     f"the longest sentence has {stats['longest_sentence']} "
                     f"words - split it (max {t['max_sentence_length']})")
        if n_sent and not t["min_avg_sentence"] <= stats["words_per_sentence"] \
                <= t["max_avg_sentence"]:
            self.add(WARN, "level",
                     f"average sentence length {stats['words_per_sentence']} "
                     f"words, target {t['min_avg_sentence']}-{t['max_avg_sentence']}")
        if stats["flesch_reading_ease"] < t["min_flesch_ease"]:
            self.add(WARN, "level",
                     f"Flesch reading ease {stats['flesch_reading_ease']} is "
                     f"below {t['min_flesch_ease']} - the text reads too hard")
        if stats["flesch_kincaid_grade"] > t["max_flesch_grade"]:
            self.add(WARN, "level",
                     f"Flesch-Kincaid grade {stats['flesch_kincaid_grade']} is "
                     f"above {t['max_flesch_grade']}")
        if n_sent and stats["subordinators"] / n_sent > \
                t["max_subordinators_per_sentence"]:
            self.add(WARN, "level",
                     f"{stats['subordinators']} subordinate clauses in "
                     f"{n_sent} sentences - simplify")
        used = english.structures_used(text)
        if used:
            self.add(INFO, "level", f"structures used: {', '.join(used)}")
        self.add(INFO, "level",
                 f"{n_words} words, {n_sent} sentences, "
                 f"{stats['words_per_sentence']} words per sentence, "
                 f"reading ease {stats['flesch_reading_ease']}, "
                 f"grade {stats['flesch_kincaid_grade']}")

    # ------------------------------------------------------------------- run
    CHECKS = (
        "check_spec_schema",
        "check_structure",
        "check_header_consistency",
        "check_against_vocabulary",
        "check_source_ambiguity",
        "check_other_test_overlap",
        "check_duplicates",
        "check_similar_words",
        "check_difficulty",
        "check_balance",
        "check_coverage",
        "check_word_bank",
        "check_gaps",
        "check_gap_grammar",
        "check_gap_uniqueness",
        "check_giveaways",
        "check_text_synonyms",
        "check_repetition",
        "check_language",
        "check_level",
    )

    def run(self) -> Report:
        self.report = Report()
        for name in self.CHECKS:
            try:
                getattr(self, name)()
            except Exception as exc:                      # never hide a crash
                self.add(ERROR, "internal", f"{name} failed: {exc!r}")
        order = {ERROR: 0, WARN: 1, INFO: 2}
        self.report.findings.sort(key=lambda f: (order[f.level], f.check))
        self.report.stats["counts"] = {
            "errors": len(self.report.errors),
            "warnings": len(self.report.warnings),
            "checks": len(self.CHECKS),
        }
        return self.report


def check_spec(spec: dict, vocab: VocabTest | None = None,
               all_tests: list[VocabTest] | None = None,
               confusable_groups: list[list[str]] | None = None,
               level_targets: dict | None = None,
               selection_targets: dict | None = None) -> list[Finding]:
    """Backwards-compatible entry point returning just the findings."""
    return ExamChecker(spec, vocab, all_tests, confusable_groups,
                       level_targets, selection_targets).run().findings


def check_report(spec: dict, vocab: VocabTest | None = None,
                 all_tests: list[VocabTest] | None = None,
                 confusable_groups: list[list[str]] | None = None,
                 level_targets: dict | None = None,
                 selection_targets: dict | None = None) -> Report:
    return ExamChecker(spec, vocab, all_tests, confusable_groups,
                       level_targets, selection_targets).run()
