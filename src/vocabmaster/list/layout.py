"""Abschätzung, ob ein Test auf eine A4-Seite passt.

Word bricht Zellen selbst um; hier wird die Höhe vorab berechnet, damit die
Anwendung warnen kann, bevor eine Datei ausgeliefert wird, die auf zwei
Seiten läuft.

Die Breitentabelle beschreibt Century Gothic in Bruchteilen der Schriftgrösse
(em). Century Gothic ist eine geometrische Grotesk mit auffällig breiten
Rundungen; die Werte sind daher grosszügiger als bei Calibri oder Arial.
"""

from __future__ import annotations

from dataclasses import dataclass

TWIPS_PER_POINT = 20
TWIPS_PER_INCH = 1440

# Zeichenbreiten in em, gemittelt für Century Gothic.
_NARROW = "ijlt.,;:!|'`()[]{}/\\ "
_WIDE = "mwMW@%"
_UPPER_MEDIUM = "ABCDEFGHKLNOPQRSTUVXYZ0123456789"

_WIDTHS = {
    **{c: 0.30 for c in "ijl.,;:!'|`"},
    **{c: 0.36 for c in "ft()[]{}/\\"},
    **{c: 0.28 for c in " "},
    **{c: 0.40 for c in "r"},
    **{c: 0.62 for c in "acegnopqsuvxyzbdhk"},
    **{c: 0.95 for c in "mw"},
    **{c: 0.72 for c in _UPPER_MEDIUM},
    **{c: 1.05 for c in "MW"},
    **{c: 0.55 for c in "-–—"},
}
_DEFAULT_WIDTH = 0.62


def text_width_points(text: str, font_size_pt: float) -> float:
    """Breite eines Textes in Punkt, ohne Umbruch."""
    return sum(_WIDTHS.get(ch, _DEFAULT_WIDTH) for ch in text) * font_size_pt


def line_count(text: str, column_width_twips: int, font_size_pt: float, cell_margin: int = 70) -> int:
    """Wie viele Zeilen belegt der Text in einer Tabellenspalte?

    Der Umbruch erfolgt an Leerzeichen, wie in Word.
    """
    if not text:
        return 1
    usable_pt = (column_width_twips - 2 * cell_margin) / TWIPS_PER_POINT
    if usable_pt <= 0:
        return 1

    lines, current = 1, 0.0
    space = text_width_points(" ", font_size_pt)
    for index, word in enumerate(text.split()):
        width = text_width_points(word, font_size_pt)
        addition = width if index == 0 else space + width
        if current + addition <= usable_pt or current == 0.0:
            current += addition
        else:
            lines += 1
            current = width
    return lines


@dataclass
class FitResult:
    """Ergebnis der Seitenprüfung."""

    height_twips: int
    available_twips: int
    rows: int
    wrapped_rows: int
    max_lines: int

    @property
    def fits(self) -> bool:
        return self.height_twips <= self.available_twips

    @property
    def usage(self) -> float:
        return self.height_twips / self.available_twips if self.available_twips else 0.0

    def describe(self) -> str:
        state = "passt" if self.fits else "PASST NICHT"
        return (
            f"{state} auf eine A4-Seite: {self.height_twips} von "
            f"{self.available_twips} Twips belegt ({self.usage:.0%}), "
            f"{self.wrapped_rows} von {self.rows} Zeilen umgebrochen"
        )


def estimate_test_height(
    rows: list[tuple[str, str, str, str]],
    column_widths: tuple[int, ...],
    font_size_pt: float,
    row_height_twips: int,
    cell_margin: int = 70,
    line_factor: float = 1.18,
) -> tuple[int, int, int]:
    """Höhe einer Tabelle in Twips sowie Zahl der umgebrochenen Zeilen.

    ``rows`` enthält Kopf- und Datenzeilen als Vierertupel.
    """
    total = 0
    wrapped = 0
    max_lines = 1
    line_height = int(font_size_pt * line_factor * TWIPS_PER_POINT)

    for row in rows:
        lines = max(
            line_count(cell, width, font_size_pt, cell_margin)
            for cell, width in zip(row, column_widths, strict=False)
        )
        max_lines = max(max_lines, lines)
        if lines > 1:
            wrapped += 1
        total += max(row_height_twips, lines * line_height)
    return total, wrapped, max_lines


def check_fits_page(
    rows: list[tuple[str, str, str, str]],
    *,
    column_widths: tuple[int, ...],
    font_size_pt: float,
    row_height_twips: int,
    page_height: int,
    margin_top: int,
    margin_bottom: int,
    heading_twips: int = 340,
    cell_margin: int = 70,
) -> FitResult:
    """Prüft, ob Überschrift und Tabelle zusammen auf eine Seite passen."""
    height, wrapped, max_lines = estimate_test_height(
        rows, column_widths, font_size_pt, row_height_twips, cell_margin
    )
    return FitResult(
        height_twips=height + heading_twips,
        available_twips=page_height - margin_top - margin_bottom,
        rows=len(rows),
        wrapped_rows=wrapped,
        max_lines=max_lines,
    )


def max_sentence_length(column_width_twips: int, font_size_pt: float, lines: int = 1,
                        cell_margin: int = 70) -> int:
    """Ungefähre Zeichenzahl, die in ``lines`` Zeilen der Spalte Platz findet."""
    usable_pt = (column_width_twips - 2 * cell_margin) / TWIPS_PER_POINT
    average = _DEFAULT_WIDTH * font_size_pt
    return int(usable_pt * lines / average)
