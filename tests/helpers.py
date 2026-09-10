"""Hilfen für die Tests - kein Bestandteil der Anwendung."""

from __future__ import annotations


def fill(data: dict, satz: str = "The class talked about {} in the lesson.") -> dict:
    """Füllt ein Gerüst mit tragfähigen Platzhalterinhalten - nur für Tests.

    Diese Sätze sind ausdrücklich **keine** Unterrichtsinhalte: Sie sollen
    nur die Prüfkette durchlaufen lassen. Im Betrieb entstehen die Sätze im
    Chat; die Anwendung selbst erzeugt keine.
    """
    for block in ("test1", "test2"):
        for entry in data["liste"][block]:
            if not entry.get("englisch"):
                entry["englisch"] = "placeholder"
                entry["deutsch"] = "Platzhalter"
            entry["satz"] = satz.format(entry["englisch"])
    for teil in ("teil1", "teil2"):
        for niveau in ("A", "B"):
            exam = data["pruefungen"][teil][niveau]
            gaps = exam["task2"]["gaps"]
            exam["task2"]["text"] = (
                "Last week the whole class went to the old museum near the river. "
                + " ".join(
                    f"Our teacher showed us one {{{i + 1}}} and asked us to "
                    "write about it."
                    for i in range(len(gaps))
                )
            )
    return data


