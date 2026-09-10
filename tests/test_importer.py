"""Der Import muss die typischen Fallen der Lehrmittel-Wortlisten überstehen."""

from __future__ import annotations

import pytest

from vocabmaster.importer import (
    MAX_UNIT,
    normalise_pos,
    page_of,
    parse_section,
    strip_page_reference,
)


@pytest.mark.parametrize(
    "section, kind, unit",
    [
        ("Unit 7", "hauptteil", 7),
        ("Unit 1, p.13", "hauptteil", 1),
        ("Unit 1, pp. 12-13", "hauptteil", 1),
        ("Starter Unit, p.4", "starter", 0),
        ("Starter Unit, p. 4", "starter", 0),
        ("Culture 7", "culture", 7),
        ("Curriculum extra 8", "curriculum_extra", 8),
        ("CE - Unit 5", "curriculum_extra", 5),
        ("Extra Listening and Speaking Unit 3", "extra_listening", 3),
        ("Project 6", "project", 6),
        ("Literature 4", "literature", 4),
        ("Answer: Unit 4", "answer_key", 4),
        ("WB, Unit 6", "workbook", 6),
    ],
)
def test_sektion_wird_richtig_gelesen(section, kind, unit):
    assert parse_section(section)[:2] == (kind, unit)


def test_seitenzahl_wird_nicht_als_unit_gelesen():
    """Die häufigste Ursache falscher Zuordnungen: 'p.42' wird zu Unit 42."""
    kind, unit, label = parse_section("WB, Unit 4, p.42; WB, Unit 3, p.74;")
    assert (kind, unit) == ("workbook", 4)
    assert "42" not in label


def test_zu_grosse_zahl_gilt_nicht_als_unit():
    assert parse_section(f"Unit {MAX_UNIT + 5}")[1] is None


def test_seitenangabe_wird_erkannt():
    assert page_of("Unit 3, p.31") == 31
    assert page_of("Unit 3") is None
    assert strip_page_reference("Unit 3, p.31") == "Unit 3"


@pytest.mark.parametrize(
    "raw, expected",
    [("(n)", "noun"), ("(v)", "verb"), ("(adj)", "adj"), ("(adv)", "adv"),
     ("(phr v)", "verb"), ("(n pl)", "noun"), ("(n / v)", "noun"), ("", "")],
)
def test_wortart_wird_normalisiert(raw, expected):
    assert normalise_pos(raw) == expected
