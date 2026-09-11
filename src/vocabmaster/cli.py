"""Kommandozeile von VocabMaster.

    vocabmaster db import wortliste.xls     Datenbank aus der Excel-Datei bauen
    vocabmaster db units                    Übersicht über die Units
    vocabmaster db suche "Publikum"         in der Wortliste suchen

    vocabmaster gerüst 3                    Gerüst für Unit 3 anlegen
    vocabmaster ausgleichen kuratiert/unit_03.json  nach dem Ergänzen neu aufteilen
    vocabmaster offen kuratiert/unit_03.json      was noch auszufüllen ist
    vocabmaster prüfen kuratiert/unit_03.json     Selbstcheck ohne zu schreiben
    vocabmaster bauen kuratiert/unit_03.json      prüfen und alles schreiben
    vocabmaster bauen … --nur test --niveau B     nur Prüfung B neu erzeugen
    vocabmaster bauen … --nur liste               nur die Vokabelliste

Der Rückgabewert ist 0, wenn keine Fehler gefunden wurden, sonst 1.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .checks import FEHLER, WARNUNG, pruefe_paket
from .config import Settings
from .database import Database
from .documents import baue_alles
from .importer import import_wordlist, write_database
from .niveau import (
    LIST_BOUNDS,
    NIVEAUS,
    NORMAL_TEXTSTUFE,
    PROFILES,
    profile,
    ziele_fuer_textstufe,
)
from .pack import (
    Pack,
    _schwierigkeit,
    ausgleichen,
    neue_fassung,
    neue_liste,
    pack_filename,
    pruefungswoerter,
    scaffold,
    waehle_pruefungswoerter,
)
from .pool import plan_unit

KURATIERT = Path("kuratiert")
AUSGABE = Path("out")


def _settings(args) -> Settings:
    s = Settings()
    if getattr(args, "datenbank", None):
        s.database = Path(args.datenbank)
    return s


def _db(args) -> Database:
    return Database.load(_settings(args).database)


def _unit(text: str) -> int:
    import re

    if re.search(r"starter", str(text), re.IGNORECASE):
        return 0
    m = re.search(r"\d{1,2}", str(text))
    if not m:
        raise argparse.ArgumentTypeError(
            f"'{text}' ist keine Unit. Beispiele: 3, 'Unit 3', 'Starter'."
        )
    return int(m.group(0))


# ---------------------------------------------------------------- Datenbank
def cmd_db_import(args) -> int:
    result = import_wordlist(args.quelle)
    ziel = Path(args.ziel) if args.ziel else _settings(args).database
    dateien = write_database(result, ziel)
    print(f"{len(result.rows)} Einträge aus {result.source} gelesen.")
    print(f"Prüfsumme SHA-256 {result.checksum[:16]}…, importiert {result.imported}")
    print(f"Geschrieben nach {ziel}/: {', '.join(p.name for p in dateien)}")
    for hinweis in result.warnings:
        print(f"  Hinweis: {hinweis}")
    return 0


def cmd_db_units(args) -> int:
    db = _db(args)
    print(f"{len(db)} Einträge - {db.herkunft}\n")
    print(f"{'Unit':<14}{'Hauptteil':>10}{'gesamt':>8}   Thema")
    for o in db.overview():
        print(f"{o['label']:<14}{o['hauptteil']:>10}{o['gesamt']:>8}   {o['thema']}")
    if args.ausfuehrlich:
        print()
        for o in db.overview():
            extra = ", ".join(f"{k}: {v}" for k, v in o["bereiche"].items())
            print(f"  {o['label']}: {extra}")
    for hinweis in db.hinweise:
        print(f"\nHinweis: {hinweis}")
    return 0


def cmd_db_suche(args) -> int:
    db = _db(args)
    treffer = db.search(args.text, args.limit)
    if not treffer:
        print(f"Keine Treffer für '{args.text}'.")
        return 1
    print(f"{len(treffer)} Treffer für '{args.text}':\n")
    for row in treffer:
        unit = db.unit_label(row.unit) if row.unit is not None else "ohne Unit"
        print(f"  {row.english:<26} {row.german:<32} {unit}, {row.section} "
              f"(Zipf {row.zipf:.2f})")
    return 0


def cmd_db_pool(args) -> int:
    """Zeigt die Wortauswahl einer Unit und wie die Prüfungen daraus schöpfen."""
    db = _db(args)
    settings = _settings(args)
    unit = db.require_unit(args.unit)
    plan = plan_unit(db, unit, settings)
    r = plan.report
    theme = db.theme(unit)

    print(f"{db.unit_label(unit)} - {theme.get('thema', '')}")
    print(f"{r.summary()}\n")
    if r.aus_zusatzteilen:
        print("  Ausnahme - aus Zusatzteilen nachgezogen:")
        for wort, bereich in r.aus_zusatzteilen:
            print(f"    {wort} ({bereich})")
        print()
    if r.ausnahme:
        print(f"  {r.ausnahme}\n")

    bal = plan.balance
    print(f"  Test 1: Ø Schwierigkeit {bal['schwierigkeit_test1']:.2f}, "
          f"Ø Zipf {bal['zipf_test1']:.2f}")
    print(f"  Test 2: Ø Schwierigkeit {bal['schwierigkeit_test2']:.2f}, "
          f"Ø Zipf {bal['zipf_test2']:.2f}\n")

    # Wie die beiden Prüfungen aus derselben Liste schöpfen
    from .pack import _schwierigkeit

    for teil, words in ((1, plan.test1), (2, plan.test2)):
        eintraege = [
            {"englisch": c.headword or c.english, "deutsch": c.german,
             "wortart": "", "nr": i}
            for i, c in enumerate(words, 1)
        ]
        print(f"  Prüfung Teil {teil}:")
        for name in NIVEAUS:
            gewaehlt = waehle_pruefungswoerter(eintraege, PROFILES[name], settings)
            schnitt = (
                sum(_schwierigkeit(e) for e in gewaehlt) / len(gewaehlt)
                if gewaehlt else 0.0
            )
            print(f"    Niveau {name} ({PROFILES[name].cefr}), "
                  f"Ø {schnitt:.1f}/10: "
                  + ", ".join(e["englisch"] for e in gewaehlt))
        print()

    if args.woerter:
        for label, words in (("Test 1", plan.test1), ("Test 2", plan.test2)):
            print(f"  {label}: " + ", ".join(c.headword for c in words))
    return 0


# ------------------------------------------------------------------- Gerüst
def cmd_geruest(args) -> int:
    db = _db(args)
    settings = _settings(args)
    unit = db.require_unit(args.unit)
    pfad = Path(args.verzeichnis) / pack_filename(unit)
    if pfad.exists() and not args.ueberschreiben:
        print(f"{pfad} besteht bereits - mit --überschreiben neu erzeugen.")
        return 1

    plan = plan_unit(db, unit, settings)
    Pack(data=scaffold(db, unit, settings, plan)).save(pfad)
    r = plan.report
    print(f"{pfad} geschrieben - {db.unit_label(unit)}, {r.summary()}")
    if r.aus_zusatzteilen:
        print("\n  Ausnahme - aus Zusatzteilen derselben Unit nachgezogen:")
        for wort, bereich in r.aus_zusatzteilen:
            print(f"    {wort} ({bereich})")
    if r.ausnahme:
        print(f"\n  {r.ausnahme}")
    print("\nJetzt im Chat ausfüllen: die Felder 'satz', fehlende Wörter und "
          "die vier Lückentexte.\nDanach 'vocabmaster prüfen " + str(pfad) + "'.")
    return 0


def cmd_offen(args) -> int:
    pack = Pack.load(args.paket)
    offen = pack.offen()
    print(f"{pack.unit_label} - {pack.thema}")
    if not offen:
        print("Nichts offen. Das Paket ist vollständig.")
        return 0
    print(f"{len(offen)} offene Stellen:\n")
    for text in offen:
        print(f"  {text}")
    return 1


# ------------------------------------------------------------------- Prüfen
def _bericht_zeigen(bericht, ausfuehrlich: bool) -> None:
    print("\nSelbstcheck")
    for line in bericht.uebersicht():
        print(line)
    zeigen = bericht.befunde if ausfuehrlich else [
        b for b in bericht.befunde if b.stufe in (FEHLER, WARNUNG)
    ]
    if zeigen:
        print()
        for befund in zeigen:
            print(f"  {befund}")
    print(f"\n{len(bericht.fehler)} Fehler, {len(bericht.warnungen)} Warnungen "
          f"aus {len(bericht.gelaufen)} Prüfungen.")


def cmd_ausgleichen(args) -> int:
    """Nach dem Ergänzen: die 60 Wörter neu auf beide Tests verteilen."""
    pack = Pack.load(args.paket)
    settings = _settings(args)
    vorher = [e["englisch"] for e in pack.entries("test1")]
    ausgleichen(pack, settings)
    pack.save()
    nachher = [e["englisch"] for e in pack.entries("test1")]
    gewechselt = sorted(set(vorher) ^ set(nachher))
    print(f"{args.paket} ausgeglichen.")
    print(f"  {len(gewechselt)} Wörter haben den Test gewechselt"
          + (f": {', '.join(gewechselt[:10])}" if gewechselt else ""))
    print("  Die vier Prüfungen wurden neu aufgesetzt; vorhandene Lückentexte "
          "sind erhalten.")
    return 0


def cmd_listen(args) -> int:
    """Welche Vokabellisten es je Unit gibt - und was daran hängt."""
    pfade = sorted(Path(args.verzeichnis).glob("unit_*.json"))
    if not pfade:
        print(f"In {args.verzeichnis}/ liegt kein Paket.")
        return 1
    nach_unit: dict[int, list[Pack]] = {}
    for pfad in pfade:
        pack = Pack.load(pfad)
        nach_unit.setdefault(pack.unit, []).append(pack)

    for unit in sorted(nach_unit):
        pakete = sorted(nach_unit[unit], key=lambda p: (p.liste_version, p.fassung))
        print(f"\nUnit {unit:02d} - {pakete[0].thema}")
        for pack in pakete:
            marke = f"V{pack.liste_version} · Fassung {pack.fassung}"
            fancy = sum(1 for e in pack.all_entries
                        if e.get("herkunft") == "fancy")
            offen = len(pack.offen())
            welche = ", ".join(
                f"T{teil}/{niv}" for teil, niv in sorted(pack.exams)
            )
            teile = [welche or "keine Prüfung",
                     f"Abdruck {pack.liste_abdruck}",
                     pack.data.get("erzeugt", "")]
            if fancy:
                teile.append(f"{fancy} aufgewertet")
            if offen:
                teile.append(f"{offen} offen")
            print(f"  {marke:<22} {pack.pfad.name:<28} "
                  f"{' · '.join(t for t in teile if t)}")
    print("\nJede Fassung ist mit Nummer, Datum und Listenabdruck hinterlegt. "
          "Eine Prüfung\ngehört zu der Liste, deren Abdruck in ihr steht; "
          "'vocabmaster prüfen' schlägt an,\nsobald das nicht mehr stimmt. "
          "Überschneidungen zwischen Fassungen sind erlaubt.")
    return 0


def cmd_liste_neu(args) -> int:
    """Eine neue Vokabelliste V2, V3 ... mit aufgewerteten Wörtern."""
    pack = Pack.load(args.paket)
    settings = _settings(args)
    try:
        neu = neue_liste(pack, args.fancy, args.wort or (), settings)
    except ValueError as fehler:
        print(str(fehler))
        return 1

    ziel = Path(args.verzeichnis) / pack_filename(
        neu.unit, liste_version=neu.liste_version
    )
    if ziel.exists() and not args.ueberschreiben:
        print(f"{ziel} besteht bereits - mit --überschreiben neu erzeugen.")
        return 1
    neu.save(ziel)

    ersetzt = neu.data["abgeleitet_von"]["ersetzt"]
    print(f"{ziel} geschrieben - {neu.unit_label}, Vokabelliste "
          f"V{neu.liste_version} (aus V{pack.liste_version}).")
    print(f"  Abdruck der neuen Liste: {neu.liste_abdruck}")
    print(f"  {len(ersetzt)} Wörter aufgewertet:")
    for e in ersetzt:
        print(f"    {e['raus']:<20} -> {e['rein']}")
    offen = [e for e in neu.all_entries if e.get("herkunft") == "fancy"
             and not e.get("englisch")]
    print(f"\n  Die vier Prüfungen wurden gegen V{neu.liste_version} neu "
          "aufgesetzt; ihre Lückentexte sind erhalten geblieben.")
    if offen:
        print(f"\nJetzt im Chat entscheiden: {len(offen)} offene Fächer "
              "(englisch, deutsch, satz, begruendung).")
        print(f"  Wortfeld: {neu.thema}")
        leit = neu.data.get("leitwoerter", [])
        if leit:
            print(f"  Leitwörter: {', '.join(leit)}")
        print(f"  Niveau der Liste: {LIST_BOUNDS.label}")
        print("  Wonach ausgewählt wird, entscheidet das Wortfeld dieser "
              "Unit - es steht nicht im Programm.")
    print(f"\nDanach 'vocabmaster prüfen {ziel}'.")
    return 0


def cmd_fassung(args) -> int:
    """Noch eine Fassung einer Prüfung anlegen - fortlaufend, hinterlegt."""
    pack = Pack.load(args.paket)
    settings = _settings(args)
    if args.woerter:
        settings = replace(settings, exam_words=args.woerter)
    if args.luecken:
        settings = replace(settings, exam_gaps=args.luecken)
    if settings.exam_gaps >= settings.exam_words:
        print(f"--luecken ({settings.exam_gaps}) muss kleiner sein als "
              f"--woerter ({settings.exam_words}): sonst bleibt für den "
              "Übersetzungsteil nichts übrig.")
        return 1
    prof = profile(args.niveau)

    # Alle Fassungen dieser Prüfung, die schon hinterlegt sind.
    vorhanden: dict[int, Pack] = {}
    for kandidat in sorted(Path(args.verzeichnis).glob("unit_*.json")):
        anderer = Pack.load(kandidat)
        if (anderer.unit == pack.unit
                and anderer.liste_version == pack.liste_version
                and anderer.fassung != pack.fassung
                and anderer.exam(args.teil, prof.name)):
            vorhanden[anderer.fassung] = anderer

    nummer = args.nummer
    if nummer is None:
        nummer = max([pack.fassung, *vorhanden]) + 1
    elif nummer in vorhanden and not args.ueberschreiben:
        print(f"Fassung {nummer} besteht bereits "
              f"({vorhanden[nummer].pfad.name}) - mit --überschreiben "
              "ersetzen oder --nummer weglassen für die nächste freie.")
        return 1

    ziel = Path(args.verzeichnis) / pack_filename(
        pack.unit, nummer, pack.liste_version
    )
    if ziel.exists() and not args.ueberschreiben:
        print(f"{ziel} besteht bereits - mit --überschreiben neu erzeugen.")
        return 1

    weitere = list(vorhanden.values())
    neu = neue_fassung(pack, args.teil, prof.name, nummer, settings, weitere)
    if args.textstufe is not None:
        neu.data["pruefungen"][f"teil{args.teil}"][prof.name]["textstufe"] = (
            args.textstufe
        )
    neu.save(ziel)

    spec = neu.exam(args.teil, prof.name)
    woerter = pruefungswoerter(spec)
    noten = [_schwierigkeit(e) for e in neu.entries(f"test{args.teil}")
             if e["englisch"] in woerter]
    schnitt = sum(noten) / len(noten) if noten else 0.0

    print(f"{ziel} geschrieben - {neu.unit_label} Teil {args.teil} "
          f"Niveau {prof.name}, Fassung {nummer} (Liste V{pack.liste_version}).")
    print(f"  Anspruch: Ø {schnitt:.2f}/10")
    print(f"  {len(spec['task1']['items'])}× übersetzen, "
          f"{len(spec['task2']['gaps'])} Lücken")

    # Überschnitt ist erlaubt - er wird berichtet, nicht begrenzt.
    for p_alt in sorted([pack, *weitere], key=lambda x: x.fassung):
        alt_w = set(pruefungswoerter(p_alt.exam(args.teil, prof.name)))
        gemeinsam = sorted(set(woerter) & alt_w)
        print(f"  gegenüber Fassung {p_alt.fassung}: {len(gemeinsam)} von "
              f"{len(woerter)} Wörtern gemeinsam"
              + (f" ({', '.join(gemeinsam)})" if gemeinsam else ""))

    verlangt = neu.textstufe(args.teil, prof.name)
    if verlangt is None:
        verlangt = NORMAL_TEXTSTUFE[prof.name]
    ziele = ziele_fuer_textstufe(PROFILES[prof.name],
                                 neu.textstufe(args.teil, prof.name))
    print(f"  Textstufe: {verlangt:.1f}/10 "
          f"(Normallage Niveau {prof.name}: {NORMAL_TEXTSTUFE[prof.name]:.1f})")
    print(f"    {ziele['min_words']}-{ziele['max_words']} Wörter, "
          f"Sätze Ø {ziele['min_avg_sentence']}-{ziele['max_avg_sentence']}, "
          f"Lesbarkeit ≥ {ziele['min_flesch_ease']}, "
          f"Grad ≤ {ziele['max_flesch_grade']}, "
          f"Nebensätze ≤ {ziele['max_subordinators_per_sentence']} je Satz")
    print(f"\nJetzt im Chat ausfüllen: der Lückentext in "
          f"pruefungen.teil{args.teil}.{prof.name}.task2.text "
          f"({len(spec['task2']['gaps'])} Lücken) - er ist es, der diese "
          "Fassung von den anderen unterscheidet.")
    print(f"Danach 'vocabmaster prüfen {ziel} --nur test'.")
    return 0


def cmd_pruefen(args) -> int:
    pack = Pack.load(args.paket)
    teile = ("liste", "test") if args.nur == "alles" else (args.nur,)
    bericht = pruefe_paket(pack, _db(args), _settings(args), teile)
    print(bericht.kennzahlen.get("_kopf", ""))
    _bericht_zeigen(bericht, args.ausfuehrlich)
    if args.streng and bericht.warnungen:
        return 1
    return 1 if bericht.fehler else 0


def cmd_bauen(args) -> int:
    pack = Pack.load(args.paket)
    settings = _settings(args)
    db = _db(args)
    teile = ("liste", "test") if args.nur == "alles" else (args.nur,)
    bericht = pruefe_paket(pack, db, settings, teile)
    print(bericht.kennzahlen.get("_kopf", ""))
    _bericht_zeigen(bericht, args.ausfuehrlich)

    if bericht.fehler and not args.trotzdem:
        print("\nEs wird nichts geschrieben, solange Fehler offen sind "
              "(Notausgang: --trotzdem).")
        return 1
    if bericht.warnungen and args.streng and not args.trotzdem:
        print("\n--streng: es wird nichts geschrieben, solange Warnungen offen sind.")
        return 1

    niveaus = (args.niveau,) if args.niveau else NIVEAUS
    ergebnis = baue_alles(
        pack, args.ausgabe, settings, teile, not args.ohne_loesung, niveaus
    )
    print(f"\nGeschrieben nach {args.ausgabe}/:")
    for pfad in ergebnis.dateien:
        print(f"  {pfad.name}")
    if ergebnis.bericht.befunde:
        print("\nNachkontrolle der geschriebenen Dokumente:")
        for befund in ergebnis.bericht.befunde:
            print(f"  {befund}")
    if not ergebnis.ok:
        print("\nDie Nachkontrolle hat Fehler gefunden - bitte nicht drucken.")
        return 1
    print("\nNachkontrolle bestanden.")
    return 0


# --------------------------------------------------------------------- main
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vocabmaster",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--datenbank", help="Verzeichnis der Wortlisten-Datenbank")
    sub = parser.add_subparsers(dest="befehl", required=True)

    db = sub.add_parser("db", help="Datenbank aufbauen und ansehen")
    dbsub = db.add_subparsers(dest="unterbefehl", required=True)

    p = dbsub.add_parser("import", help="Datenbank aus einer Excel-Wortliste bauen")
    p.add_argument("quelle", help="Excel-Datei (.xls oder .xlsx)")
    p.add_argument("-o", "--ziel", help="Zielverzeichnis der Datenbank")
    p.set_defaults(func=cmd_db_import)

    p = dbsub.add_parser("units", help="Übersicht über alle Units")
    p.add_argument("-a", "--ausfuehrlich", action="store_true")
    p.set_defaults(func=cmd_db_units)

    p = dbsub.add_parser("suche", help="in der Wortliste suchen")
    p.add_argument("text")
    p.add_argument("-n", "--limit", type=int, default=40)
    p.set_defaults(func=cmd_db_suche)

    p = dbsub.add_parser("pool", help="Wortauswahl einer Unit und die A/B-Prüfungen")
    p.add_argument("unit", type=_unit)
    p.add_argument("-w", "--woerter", action="store_true", help="alle Wörter zeigen")
    p.set_defaults(func=cmd_db_pool)

    for name in ("gerüst", "geruest"):
        p = sub.add_parser(name, help="Gerüst für eine Unit erzeugen")
        p.add_argument("unit", type=_unit)
        p.add_argument("-o", "--verzeichnis", default=str(KURATIERT))
        p.add_argument("--überschreiben", "--ueberschreiben", action="store_true",
                       dest="ueberschreiben")
        p.set_defaults(func=cmd_geruest)

    p = sub.add_parser(
        "ausgleichen",
        help="nach dem Ergänzen die 60 Wörter neu auf beide Tests verteilen")
    p.add_argument("paket")
    p.set_defaults(func=cmd_ausgleichen)

    p = sub.add_parser("offen", help="zeigen, was im Paket noch fehlt")
    p.add_argument("paket")
    p.set_defaults(func=cmd_offen)

    for name in ("prüfen", "pruefen"):
        p = sub.add_parser(name, help="Selbstcheck ohne zu schreiben")
        p.add_argument("paket")
        p.add_argument("-a", "--ausfuehrlich", action="store_true",
                       help="auch Hinweise zeigen")
        p.add_argument("--streng", action="store_true",
                       help="Warnungen wie Fehler behandeln")
        p.add_argument("--nur", choices=("alles", "liste", "test"),
                       default="alles",
                       help="nur die Kontrollen dieses Teils laufen lassen")
        p.set_defaults(func=cmd_pruefen)

    p = sub.add_parser("listen", help="welche Vokabellisten je Unit bestehen")
    p.add_argument("--verzeichnis", default="kuratiert")
    p.set_defaults(func=cmd_listen)

    p = sub.add_parser(
        "liste-neu",
        help="eine neue Vokabelliste V2, V3 ... mit aufgewerteten Wörtern",
    )
    p.add_argument("paket", help="das bestehende Paket, z. B. kuratiert/unit_01.json")
    p.add_argument("--fancy", type=int, default=0,
                   help="so viele Fächer für im Chat gewählte Wörter")
    p.add_argument("--wort", action="append", metavar="EN=DE",
                   help="selbst angegebenes Wort als 'englisch=deutsch' "
                        "(mehrfach möglich; bei Zweifel 'en:' voranstellen)")
    p.add_argument("--verzeichnis", default="kuratiert")
    p.add_argument("--überschreiben", "--ueberschreiben", dest="ueberschreiben",
                   action="store_true")
    p.set_defaults(func=cmd_liste_neu)

    p = sub.add_parser(
        "fassung",
        help="noch eine Fassung einer einzelnen Prüfung anlegen",
    )
    p.add_argument("paket", help="das bestehende Paket, z. B. kuratiert/unit_01.json")
    p.add_argument("--teil", type=int, choices=(1, 2), required=True)
    p.add_argument("--niveau", choices=list(NIVEAUS), required=True)
    p.add_argument("--nummer", type=int, default=None,
                   help="Nummer der Fassung (Vorgabe: die nächste freie)")
    p.add_argument("--woerter", type=int,
                   help="Wörter je Prüfung (Vorgabe aus den Einstellungen)")
    p.add_argument("--luecken", type=int,
                   help="davon Lücken (Vorgabe aus den Einstellungen)")
    p.add_argument("--textstufe", type=float,
                   help="Schwierigkeit des Lückentexts 0-10 (Normallage: "
                        "Niveau A 3.0, Niveau B 1.7)")
    p.add_argument("--verzeichnis", default="kuratiert")
    p.add_argument("--überschreiben", "--ueberschreiben", dest="ueberschreiben",
                   action="store_true")
    p.set_defaults(func=cmd_fassung)

    p = sub.add_parser("bauen", help="prüfen und die Word-Dateien schreiben")
    p.add_argument("paket")
    p.add_argument("-o", "--ausgabe", default=str(AUSGABE))
    p.add_argument("--nur", choices=("alles", "liste", "test"), default="alles",
                   help="nur einen Teil neu erzeugen")
    p.add_argument("--niveau", choices=list(NIVEAUS),
                   help="nur die Prüfungen dieses Niveaus schreiben")
    p.add_argument("--ohne-loesung", action="store_true", dest="ohne_loesung")
    p.add_argument("-a", "--ausfuehrlich", action="store_true")
    p.add_argument("--streng", action="store_true")
    p.add_argument("--trotzdem", action="store_true",
                   help="trotz Fehlern schreiben (Notausgang)")
    p.set_defaults(func=cmd_bauen)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
