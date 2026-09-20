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
            for aufgabe in data["pruefungen"][teil][niveau].get("aufgaben", []):
                _fuelle_aufgabe(aufgabe)
            # Ein Paket aus der Zeit vor der Aufgabenliste.
            alt = data["pruefungen"][teil][niveau]
            for schluessel, art in (("task1", "uebersetzen"),
                                    ("task2", "luecken"),
                                    ("task3", "wortwahl")):
                if isinstance(alt.get(schluessel), dict):
                    _fuelle_aufgabe({"art": art, **alt[schluessel]},
                                    ziel=alt[schluessel])
    return data


def _fuelle_aufgabe(aufgabe: dict, ziel: dict | None = None) -> None:
    """Die Handarbeit **einer** Aufgabe mit tragfähigem Platzhalter füllen."""
    ziel = aufgabe if ziel is None else ziel
    art = aufgabe.get("art")
    if art == "luecken":
        gaps = aufgabe.get("gaps", [])
        ziel["text"] = (
            "Last week the whole class went to the old museum near the river. "
            + " ".join(
                f"Our teacher showed us one {{{i + 1}}} and asked us to "
                "write about it."
                for i in range(len(gaps))
            )
        )
    elif art in ("wortwahl", "richtig_falsch"):
        for item in aufgabe.get("items", []):
            wort = item.get("english", "word")
            item["saetze"] = [
                f"The class used {wort} in sentence number {i + 1} today."
                for i in range(len(item.get("saetze", [])))
            ]
    elif art == "definition":
        for nr, item in enumerate(aufgabe.get("items", []), 1):
            item["umschreibung"] = (
                f"something people talk about in lesson number {nr}"
            )
    elif art == "schreiben":
        for nr, block in enumerate(aufgabe.get("items", []), 1):
            block["anstoss"] = f"Write about a school day, part {nr}."




def aufgabe(spec: dict, art: str = "luecken") -> dict:
    """Die Aufgabe dieser Art - **lebend**, nicht als Kopie.

    Die Tests bauen ihre Fehler dort hinein, wo sie im Betrieb entstünden:
    mitten in der Aufgabe. Eine Kopie zurückzugeben hiesse, den Fehler in
    etwas einzubauen, das danach weggeworfen wird.

    Liest beide Formen: die Aufgabenliste und die alten Schlüssel eines
    Pakets aus ``kuratiert/``.
    """
    for eintrag in spec.get("aufgaben") or []:
        if isinstance(eintrag, dict) and eintrag.get("art") == art:
            return eintrag
    for schluessel, kennung in (("task1", "uebersetzen"), ("task2", "luecken"),
                                ("task3", "wortwahl")):
        if kennung == art and isinstance(spec.get(schluessel), dict):
            return spec[schluessel]
    return {}


def gepruefte(spec: dict, *arten: str) -> list[str]:
    """Die englischen Wörter, die diese Prüfung abfragt."""
    from vocabmaster.pack import aufgaben_von, gepruefte_woerter
    gewaehlt = set(arten)
    return [
        e.get("english", "")
        for a in aufgaben_von(spec)
        if not gewaehlt or a.get("art") in gewaehlt
        for e in gepruefte_woerter(a)
    ]
