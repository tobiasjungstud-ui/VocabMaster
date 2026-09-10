"""Read a vocabulary list (.docx) into structured entries.

The expected source layout is the one used in the Unit vocabulary sheets:
a paragraph naming the test ("Test 1", "Test 2 (updated)", ...) followed by a
table with the columns  Nr. | Deutsch | English | Example sentence.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass
class VocabItem:
    number: int
    german: str
    english: str
    example: str = ""
    test: str = ""

    @property
    def german_variants(self) -> list[str]:
        """'Schauplatz / Handlungsort' -> ['Schauplatz', 'Handlungsort']"""
        return [p.strip() for p in self.german.split("/") if p.strip()]

    @property
    def pos(self) -> str:
        """Part of speech, derived from the German prompt.

        German orthography makes this reliable enough for exam checking:
        nouns are capitalised, verbs end in -en/-eln/-ern (or are reflexive),
        everything else is treated as an adjective/adverb.
        """
        return guess_pos(self.german)

    def as_dict(self) -> dict:
        return {
            "number": self.number,
            "german": self.german,
            "english": self.english,
            "example": self.example,
            "test": self.test,
            "pos": self.pos,
        }


@dataclass
class VocabTest:
    """One test section of a vocabulary sheet (e.g. everything under 'Test 2')."""

    name: str
    items: list[VocabItem] = field(default_factory=list)

    def by_german(self, german: str) -> VocabItem | None:
        target = normalise(german)
        for item in self.items:
            if normalise(item.german) == target:
                return item
        return None

    def by_english(self, english: str) -> VocabItem | None:
        target = normalise(english)
        for item in self.items:
            if normalise(item.english) == target:
                return item
        return None


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


VERB_ENDINGS = ("en", "ern", "eln", "n")


def guess_pos(german: str) -> str:
    """noun | verb | adj  - guessed from the German prompt."""
    first = german.split("/")[0].strip()
    if not first:
        return "unknown"
    if first.lower().startswith(("sich ", "etwas ", "an etwas ", "jemanden ", "jemandem ")):
        return "verb"
    words = first.split()
    head = words[-1]
    if head[:1].isupper():
        return "noun"
    if len(words) > 1 and any(w[:1].isupper() for w in words):
        # "in einer Hauptrolle spielen", "Regie führen"
        return "verb" if head.lower().endswith(VERB_ENDINGS) else "noun"
    if head.lower().endswith(VERB_ENDINGS) and len(head) > 3:
        return "verb"
    return "adj"


def _cell_text(cell: ET.Element) -> str:
    parts = []
    for para in cell.iter(f"{W}p"):
        runs = "".join(t.text or "" for t in para.iter(f"{W}t"))
        parts.append(runs)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _para_text(para: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(t.text or "" for t in para.iter(f"{W}t"))).strip()


def read_document_xml(path: str) -> ET.Element:
    with zipfile.ZipFile(path) as zf:
        return ET.fromstring(zf.read("word/document.xml"))


def parse_vocabulary(path: str) -> list[VocabTest]:
    """Parse a vocabulary .docx into its test sections, in document order."""
    body = read_document_xml(path).find(f"{W}body")
    tests: list[VocabTest] = []
    pending_name = ""

    for child in body:
        if child.tag == f"{W}p":
            text = _para_text(child)
            if text:
                pending_name = text
        elif child.tag == f"{W}tbl":
            name = pending_name or f"Test {len(tests) + 1}"
            test = VocabTest(name=name)
            for row in child.findall(f"{W}tr"):
                cells = [_cell_text(tc) for tc in row.findall(f"{W}tc")]
                if len(cells) < 3:
                    continue
                number_raw = cells[0]
                if not number_raw.isdigit():
                    continue  # header row
                test.items.append(
                    VocabItem(
                        number=int(number_raw),
                        german=cells[1],
                        english=cells[2],
                        example=cells[3] if len(cells) > 3 else "",
                        test=name,
                    )
                )
            if test.items:
                tests.append(test)
            pending_name = ""
    return tests


def find_test(tests: list[VocabTest], wanted: str) -> VocabTest:
    """Find a test section by (partial, case-insensitive) name, e.g. 'Test 2'."""
    target = normalise(wanted)
    for test in tests:
        if normalise(test.name) == target:
            return test
    for test in tests:
        if target in normalise(test.name):
            return test
    names = ", ".join(repr(t.name) for t in tests)
    raise KeyError(f"No test section matching {wanted!r}. Available: {names}")
