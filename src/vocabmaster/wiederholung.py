"""Wiederholung aus dem vorherigen Vocabulary.

Eine Prüfung fragt die Liste ab, die gerade gelernt wurde. Mit der
Wiederholung kommen ein paar Wörter aus der Liste **davor** dazu - als
schlichte Übersetzungstabelle, deutsch vorgegeben, englisch hinzuschreiben.

Was "davor" heisst, folgt dem Gang durchs Lehrmittel, Part für Part::

    Unit 1 · Part I  ->  Unit 1 · Part II  ->  Unit 2 · Part I  ->  …

Part II wiederholt also Part I **derselben Liste**; Part I wiederholt
Part II der Unit davor - über den Unit-Wechsel hinweg. Welche Liste dieser
Unit behandelt wurde, weiss das Programm nicht sicher: Es kann mehrere
geben (V1, V2). Es schlägt deshalb vor, was die Spuren am ehesten
belegen, und nennt die übrigen als Wahl:

1. eine Liste, zu deren Part schon eine Prüfung gebaut wurde - die war
   sicher im Unterricht;
2. sonst eine, deren Vokabelliste gebaut wurde;
3. sonst die neueste.

Die beiden Niveaus unterscheiden sich in Menge und Gewicht:

* **Niveau A** - vier Wörter, sie zählen wie jede andere Aufgabe.
* **Niveau B** - zwei Wörter als **Bonus**: Sie können die Note
  verbessern, aber nicht verschlechtern. Die Höchstpunktzahl bleibt, wo
  sie ohne Wiederholung stand.

Welche Wörter es werden, entscheidet dieselbe Auswahl wie bei der Prüfung
selbst: Niveau A nimmt die schwersten, Niveau B die zugänglichsten. Was in
der aktuellen Liste steht - auch als Wortfamilie -, kommt nicht in Frage:
Es würde auf demselben Blatt zweimal abgefragt.

Die Quelle wird im Paket mit Dateiname, Part, Version und **Listenabdruck**
festgehalten. Die Kontrolle ``wiederholung`` liest das Quellpaket später
wieder ein und prüft jedes Wort gegen genau diese Liste.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import Settings
from .exam.vocab import normalise
from .list.normalize import same_family
from .niveau import NIVEAUS, PROFILES
from .pack import (
    GRUNDDATENBANK,
    TEIL_NAMEN,
    Pack,
    kennzeichen,
    pruefungswoerter,
    waehle_pruefungswoerter,
    wortart_von,
)

#: Wie viele Wörter wiederholt werden. Niveau B bekommt weniger - und die
#: zählen nur als Bonus.
ANZAHL = {"A": 4, "B": 2}
BONUS = {"A": False, "B": True}

#: Die Aufgabenstellung. Die Nummer setzt der Setzer, wie bei jeder Aufgabe.
_ANSAGE = {
    False: "1) Revision – translate using the vocabulary from {quelle}.",
    True: "1) Bonus – revision: translate using the vocabulary from {quelle}.",
}


def part_name(teil: int) -> str:
    """``Part I`` / ``Part II``."""
    return TEIL_NAMEN[int(teil)][0]


def einheit_name(unit: int) -> str:
    """``Unit 7`` - oder ``Starter Unit`` für die Unit 0."""
    return "Starter Unit" if int(unit) == 0 else f"Unit {int(unit)}"


def fehlender_vorgaenger(pack: Pack, teil: int,
                         vorschlaege_: list[Quelle]) -> str:
    """Ein Satz, falls der unmittelbar vorherige Part keine Liste hat."""
    if any(q.folge for q in vorschlaege_):
        return ""
    ziel = vorgaenger(pack.unit, teil, units_des_lehrmittels(pack))
    if ziel is None:
        return (f"Vor {pack.unit_label} · {part_name(teil)} gibt es in diesem "
                "Lehrmittel kein Vocabulary.")
    return (f"Unmittelbar vor {pack.unit_label} · {part_name(teil)} kommt "
            f"{einheit_name(ziel[0])} · {part_name(ziel[1])} - dazu gibt es "
            "in der Werkstatt keine Liste.")


def schritt(unit: int, teil: int) -> int:
    """Die Stelle eines Parts im Gang durch das Lehrmittel."""
    return int(unit) * 2 + (int(teil) - 1)


@dataclass(frozen=True)
class Quelle:
    """Eine Liste und ein Part, aus denen wiederholt werden kann."""

    paket: str
    unit: int
    teil: int
    liste_version: int
    abdruck: str
    pruefsumme: str
    lehrmittel: str
    unit_label: str
    #: Ist das der Part, der im Gang durchs Lehrmittel unmittelbar vor dem
    #: aktuellen Test kommt? Nur dann ist es die **Folge**.
    folge: bool
    #: Warum diese Quelle an dieser Stelle steht - in einem Satz.
    grund: str

    @property
    def bezeichnung(self) -> str:
        vorn = f"{self.lehrmittel} " if self.lehrmittel else ""
        return (f"{vorn}{self.unit_label} · {part_name(self.teil)} · "
                f"V{self.liste_version}")

    def als_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Welche Listen es gibt
# ---------------------------------------------------------------------------
def listenpakete(verzeichnis: str | Path) -> list[Pack]:
    """Alle Vokabellisten im Ordner - je Liste ihr Grundpaket.

    Fassungspakete tragen dieselbe Liste wie ihr Grundpaket und zählen
    deshalb nicht noch einmal. Ein Paket, das sich nicht lesen lässt, wird
    übergangen: Es kann ohnehin keine Quelle sein.
    """
    heraus = []
    for pfad in sorted(Path(verzeichnis).glob("unit_*.json")):
        try:
            pack = Pack.load(pfad)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if pack.fassung == 1:
            heraus.append(pack)
    return heraus


def _pruefsumme(pack: Pack) -> str:
    return str(pack.quelle.get("pruefsumme_sha256", ""))


def _gebaut(pack: Pack, teil: int, ausgabe: Path | None) -> tuple[bool, bool]:
    """Liegt zu diesem Part eine gebaute Prüfung, zur Liste ein Dokument?"""
    if ausgabe is None or not Path(ausgabe).is_dir():
        return False, False
    # Hier und nicht oben: `documents` liest die Kontrollen, und die lesen
    # dieses Modul - oben eingebunden wäre das ein Kreis.
    from .documents import dateiname

    ausgabe = Path(ausgabe)
    pruefung = any(
        (ausgabe / dateiname(pack.unit, "Test", teil, niveau,
                             liste_version=pack.liste_version,
                             lehrmittel=pack.lehrmittel)).exists()
        for niveau in NIVEAUS
    )
    liste = (ausgabe / dateiname(pack.unit, "VocabularyList",
                                 liste_version=pack.liste_version,
                                 lehrmittel=pack.lehrmittel)).exists()
    return pruefung, liste


def _quelle(pack: Pack, teil: int, folge: bool, grund: str) -> Quelle:
    return Quelle(
        paket=pack.pfad.name if pack.pfad else "",
        unit=pack.unit,
        teil=int(teil),
        liste_version=pack.liste_version,
        abdruck=pack.liste_abdruck,
        pruefsumme=_pruefsumme(pack),
        lehrmittel=kennzeichen(pack.lehrmittel),
        unit_label=pack.unit_label,
        folge=folge,
        grund=grund,
    )


# ---------------------------------------------------------------------------
# Was unmittelbar davor kam
# ---------------------------------------------------------------------------
def units_des_lehrmittels(pack: Pack) -> list[int]:
    """Die Units des Lehrmittels, aus dem ``pack`` stammt - alle, nicht nur
    die mit einer Liste.

    Gefunden wird das Lehrmittel an der Prüfsumme der Wortliste. Ist es
    nicht registriert, bleiben nur die Units, zu denen es Listen gibt; das
    sagt der Aufrufer dann selbst.
    """
    from . import datenbanken

    eigen = _pruefsumme(pack)
    for eintrag in datenbanken.alle():
        if not eintrag.vorhanden or str(
                eintrag.quelle.get("pruefsumme_sha256", "")) != eigen:
            continue
        try:
            index = json.loads((eintrag.verzeichnis / "index.json")
                               .read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return sorted(int(u["unit"]) for u in index.get("units", [])
                      if u.get("unit") is not None)
    return []


def vorgaenger(unit: int, teil: int, units: list[int]) -> tuple[int, int] | None:
    """Der Part, der im Gang durchs Lehrmittel unmittelbar vorher kommt.

    ``units`` sind **alle** Units des Lehrmittels, nicht nur die, zu denen
    es eine Liste gibt. Sonst hiesse der Vorgänger von Unit 8 Part I
    "Unit 1 Part II", bloss weil zu Unit 2 bis 7 keine Liste gebaut wurde -
    und die Wiederholung fragte Wörter ab, die sechs Units zurückliegen,
    während sie behauptet, es seien die von letzter Woche.

    Part II hat seinen Vorgänger immer: Part I derselben Unit. Part I hat
    ihn in Part II der Unit davor - auch der Starter Unit. Vor der ersten
    Unit gibt es keinen.
    """
    if int(teil) == 2:
        return int(unit), 1
    frueher = [u for u in units if u < int(unit)]
    return (max(frueher), 2) if frueher else None


def vorschlaege(pack: Pack, teil: int, verzeichnis: str | Path | None = None,
                ausgabe: str | Path | None = None) -> list[Quelle]:
    """Woraus die Prüfung zu ``pack``/``teil`` wiederholen kann - geordnet.

    Der erste Eintrag ist der Vorschlag, **sofern** er die Folge ist
    (``folge=True``). Gibt es im Lehrmittel keinen vorherigen Part - Unit 1
    Part I ohne Liste zur Starter Unit -, steht keine Folge vorn; die Liste
    enthält dann nur, was man stattdessen wählen könnte.

    Danach kommen die übrigen Parts desselben Lehrmittels, die **vor** dem
    aktuellen liegen, der nächste zuerst - und zuletzt die Listen anderer
    Lehrmittel. Was nach dem aktuellen Test kommt, ist keine Wiederholung
    und steht nicht darin.
    """
    verzeichnis = Path(verzeichnis) if verzeichnis else (
        pack.pfad.parent if pack.pfad else Path("kuratiert"))
    ausgabe = Path(ausgabe) if ausgabe else None
    alle = listenpakete(verzeichnis)
    eigen = _pruefsumme(pack)
    gleich = [p for p in alle if _pruefsumme(p) == eigen]
    fremd = [p for p in alle if _pruefsumme(p) != eigen]
    hier = schritt(pack.unit, teil)

    def ist_aktuell(p: Pack) -> bool:
        return (pack.pfad is not None and p.pfad is not None
                and p.pfad.resolve() == pack.pfad.resolve())

    units = units_des_lehrmittels(pack) or sorted({p.unit for p in gleich})
    ziel = vorgaenger(pack.unit, teil, units)
    vorn: list[Quelle] = []
    if ziel is not None:
        z_unit, z_teil = ziel
        kandidaten = [p for p in gleich if p.unit == z_unit]
        if int(teil) == 2:
            # Part II wiederholt Part I **derselben** Liste - sie wurde als
            # Ganzes ausgeteilt. Andere Versionen dieser Unit folgen danach.
            kandidaten.sort(key=lambda p: (not ist_aktuell(p),
                                           -p.liste_version))
            for p in kandidaten:
                grund = (f"Part I derselben Liste V{p.liste_version} - kommt "
                         "unmittelbar vor Part II"
                         if ist_aktuell(p) else
                         f"Part I der Liste V{p.liste_version} dieser Unit - "
                         "eine andere Liste als die geprüfte")
                vorn.append(_quelle(p, 1, True, grund))
        else:
            def rang(p: Pack):
                pruefung, liste = _gebaut(p, z_teil, ausgabe)
                return (pruefung, liste, p.liste_version)

            kandidaten.sort(key=rang, reverse=True)
            for i, p in enumerate(kandidaten):
                pruefung, liste = _gebaut(p, z_teil, ausgabe)
                beleg = ("zu diesem Part wurde schon eine Prüfung gebaut"
                         if pruefung else
                         "die Vokabelliste wurde gebaut" if liste else
                         "neueste Liste dieser Unit" if i == 0 else
                         "ältere Liste dieser Unit")
                grund = (f"{p.unit_label} · Part II ist der Part vor "
                         f"{pack.unit_label} · Part I; V{p.liste_version}: "
                         f"{beleg}")
                vorn.append(_quelle(p, 2, True, grund))

    schon = {(q.paket, q.teil) for q in vorn}
    davor: list[tuple[int, Quelle]] = []
    for p in gleich:
        for t in (1, 2):
            s = schritt(p.unit, t)
            if s >= hier or (p.pfad and (p.pfad.name, t) in schon):
                continue
            davor.append((s, _quelle(
                p, t, False,
                "früherer Part dieses Lehrmittels - nicht der unmittelbar "
                "vorherige")))
    davor.sort(key=lambda x: (-x[0], -x[1].liste_version))
    if ziel is not None and not vorn and davor:
        # Der unmittelbar vorherige Part hat keine Liste. Der nächste frühere
        # steht trotzdem vorn - er ist der naheliegendste -, sagt aber, dass
        # er **nicht** der Vorgänger ist.
        _, erster = davor[0]
        davor[0] = (davor[0][0], Quelle(**{
            **erster.als_dict(),
            "grund": (f"{einheit_name(ziel[0])} · {part_name(ziel[1])} käme "
                      "unmittelbar davor, hat aber keine Liste; dies ist der "
                      "nächste frühere Part mit Liste"),
        }))

    anderswo = []
    for p in sorted(fremd, key=lambda p: (-p.unit, -p.liste_version)):
        name = kennzeichen(p.lehrmittel) or GRUNDDATENBANK
        for t in (2, 1):
            q = _quelle(p, t, False, f"Liste eines anderen Lehrmittels ({name})")
            # Ein fremdes Lehrmittel steht immer mit Namen da - sonst liest
            # sich "Unit 8 · Part II" wie die Unit 8 des eigenen.
            anderswo.append(Quelle(**{**q.als_dict(), "lehrmittel": name}))

    return vorn + [q for _, q in davor] + anderswo


# ---------------------------------------------------------------------------
# Welche Wörter
# ---------------------------------------------------------------------------
def _schluessel(text: str) -> str:
    return normalise(str(text or ""))


def kollidiert(englisch: str, aktuelle: list[str]) -> bool:
    """Steht das Wort - oder seine Wortfamilie - in der aktuellen Liste?"""
    k = _schluessel(englisch)
    for a in aktuelle:
        if k == _schluessel(a) or same_family(englisch, a):
            return True
    return False


def aktuelle_woerter(pack: Pack, teil: int) -> list[str]:
    """Die Wörter, die der aktuelle Test abfragt: der Part, nicht die Liste.

    Gegen **beide** Parts zu prüfen wäre falsch: Part II wiederholt Part I
    derselben Liste, und dessen Wörter stehen selbstverständlich in der
    Liste - nur eben nicht im Part, der gerade geprüft wird.
    """
    return [e.get("englisch", "") for e in pack.entries(f"test{int(teil)}")
            if e.get("englisch")]


def gedruckter_text(spec: dict[str, Any]) -> str:
    """Alles, was auf dem Blatt einer Prüfung **gedruckt** steht.

    Lückentext, Wortbank, Sätze zur Wahl, Umschreibungen, Anstösse und die
    Wörter eines Mini-Textes. Steht ein Wiederholungswort darin, liegt seine
    Lösung offen - "the first to ___ a picnic" im Lückentext, und darunter
    soll "Picknick" übersetzt werden.
    """
    from .pack import aufgaben_von

    teile: list[str] = []
    for a in aufgaben_von(spec):
        teile.append(str(a.get("text", "")))
        teile += [str(w) for w in a.get("word_bank", [])]
        for item in a.get("items", []):
            if not isinstance(item, dict):
                continue
            teile += [str(x) for x in item.get("saetze", [])]
            teile.append(str(item.get("umschreibung", "")))
            teile.append(str(item.get("anstoss", "")))
            teile += [str(w.get("english", "")) for w in item.get("woerter", [])]
    return "\n".join(t for t in teile if t)


def steht_gedruckt(englisch: str, text: str) -> bool:
    """Steht das Wort - auch gebeugt - im gedruckten Text?"""
    import re

    wort = str(englisch or "").strip()
    if not wort or not text:
        return False
    muster = rf"\b{re.escape(wort)}(?:s|es|d|ed|ing)?\b"
    return re.search(muster, text, re.IGNORECASE) is not None


def waehle(pack: Pack, teil: int, niveau: str, quelle: Pack,
           quelle_teil: int, settings: Settings | None = None,
           anzahl: int | None = None) -> list[dict[str, Any]]:
    """Die Wiederholungswörter für ein Niveau.

    Dieselbe Auswahl wie bei der Prüfung selbst - Niveau A von oben, Niveau
    B von unten -, aber nur unter den Wörtern, die im aktuellen Part nicht
    vorkommen, auch nicht als Wortfamilie, und die nirgends auf dem Blatt
    gedruckt stehen. Was die frühere Prüfung zu
    diesem Part schon abgefragt hat, rückt bei gleicher Schwierigkeit nach
    hinten; ausgeschlossen ist es nicht.
    """
    settings = settings or Settings()
    aktuelle = aktuelle_woerter(pack, teil)
    gedruckt = gedruckter_text(pack.exam(int(teil), niveau))
    kandidaten = [
        e for e in quelle.entries(f"test{int(quelle_teil)}")
        if e.get("englisch") and e.get("deutsch")
        and not kollidiert(e["englisch"], aktuelle)
        # Was auf dem Blatt schon gedruckt steht, wäre verraten.
        and not steht_gedruckt(e["englisch"], gedruckt)
    ]
    frueher = pruefungswoerter(quelle.exam(int(quelle_teil), niveau))
    gewaehlt = waehle_pruefungswoerter(
        kandidaten, PROFILES[niveau], settings, frueher,
        anzahl=ANZAHL[niveau] if anzahl is None else int(anzahl),
    )
    return [{"english": e["englisch"], "german": e["deutsch"],
             "pos": wortart_von(e)} for e in gewaehlt]


def block(pack: Pack, teil: int, niveau: str, quelle: Pack,
          quelle_teil: int, folge: bool, grund: str,
          settings: Settings | None = None,
          anzahl: int | None = None) -> dict[str, Any]:
    """Der Wiederholungsblock einer Prüfung, so wie er im Paket steht."""
    bonus = BONUS[niveau]
    q = _quelle(quelle, quelle_teil, folge, grund)
    name = f"{quelle.unit_label.lower()} {part_name(quelle_teil).lower()}"
    return {
        "instruction": _ANSAGE[bonus].format(quelle=name),
        "bonus": bonus,
        "items": waehle(pack, teil, niveau, quelle, quelle_teil, settings,
                        anzahl),
        "quelle": {
            "paket": q.paket, "unit": q.unit, "teil": q.teil,
            "liste_version": q.liste_version, "abdruck": q.abdruck,
            "pruefsumme": q.pruefsumme, "lehrmittel": q.lehrmittel,
            "unit_label": q.unit_label,
        },
        "folge": folge,
        "grund": grund,
    }


def setze(pack: Pack, teil: int, quelle: Pack, quelle_teil: int,
          niveaus: tuple[str, ...] = NIVEAUS, folge: bool = True,
          grund: str = "", settings: Settings | None = None,
          anzahl: dict[str, int] | None = None) -> dict[str, dict]:
    """Trägt die Wiederholung in die Prüfungen eines Teils ein.

    Gibt je Niveau den eingetragenen Block zurück. Eine Prüfung, die es im
    Paket nicht gibt, bleibt unberührt.
    """
    if quelle.pfad is None:
        raise ValueError("Die Quellliste hat keinen Dateinamen - sie muss "
                         "als Paket vorliegen, sonst lässt sie sich später "
                         "nicht nachprüfen.")
    if (pack.pfad is not None and quelle.pfad.resolve() == pack.pfad.resolve()
            and int(quelle_teil) == int(teil)):
        raise ValueError(
            f"{part_name(teil)} kann sich nicht selbst wiederholen - das ist "
            "das Vocabulary, das die Prüfung ohnehin abfragt.")
    gesetzt = {}
    for niveau in niveaus:
        spec = pack.data.get("pruefungen", {}).get(f"teil{int(teil)}", {}).get(niveau)
        if not spec:
            continue
        b = block(pack, teil, niveau, quelle, quelle_teil, folge, grund,
                  settings, (anzahl or {}).get(niveau))
        spec["wiederholung"] = b
        gesetzt[niveau] = b
    return gesetzt


def entferne(pack: Pack, teil: int, niveaus: tuple[str, ...] = NIVEAUS) -> int:
    """Nimmt die Wiederholung aus den Prüfungen eines Teils wieder heraus."""
    weg = 0
    for niveau in niveaus:
        spec = pack.data.get("pruefungen", {}).get(f"teil{int(teil)}", {}).get(niveau)
        if spec and spec.pop("wiederholung", None) is not None:
            weg += 1
    return weg
