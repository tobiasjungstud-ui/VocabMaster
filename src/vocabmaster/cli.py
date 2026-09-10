"""Kommandozeile von VocabMaster.

    vocabmaster db import wortliste.xls     Datenbank aus der Excel-Datei bauen
    vocabmaster db units                    Übersicht über die Units
    vocabmaster db suche "Publikum"         in der Wortliste suchen

    vocabmaster gerüst 3                    Gerüste für Niveau A und B
    vocabmaster gerüst 3 --niveau B         nur Niveau B
    vocabmaster offen kuratiert/unit_03_A.json    was noch auszufüllen ist
    vocabmaster prüfen kuratiert/unit_03_A.json   Selbstcheck ohne zu schreiben
    vocabmaster bauen kuratiert/unit_03_A.json    prüfen und Dokumente schreiben
    vocabmaster bauen … --nur test          nur die Prüfungen neu erzeugen

Der Rückgabewert ist 0, wenn keine Fehler gefunden wurden, sonst 1.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks import FEHLER, WARNUNG, gegenstueck_pfad, pruefe_paket
from .config import Settings
from .database import Database
from .documents import baue_alles
from .importer import import_wordlist, write_database
from .niveau import NIVEAUS, PROFILES, profile
from .pack import Pack, pack_filename, scaffold
from .pool import allocate, near_duplicates, plan_both

KURATIERT = Path("kuratiert")
AUSGABE = Path("out")


def _settings(args) -> Settings:
    s = Settings()
    if getattr(args, "datenbank", None):
        s.database = Path(args.datenbank)
    if getattr(args, "mit_zusatzteilen", False):
        s.core_sections_only = False
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
    """Zeigt, wie die Unit auf die beiden Niveaus aufgeteilt wird."""
    db = _db(args)
    settings = _settings(args)
    unit = db.require_unit(args.unit)
    verteilung = allocate(db, unit, settings)
    plans = plan_both(db, unit, settings)
    theme = db.theme(unit)
    print(f"{db.unit_label(unit)} - {theme.get('thema', '')}")
    print(f"Hauptteil: {plans['A'].report.roh} Wörter"
          f"{'' if settings.core_sections_only else ' (mit Zusatzteilen)'}\n")
    print(f"  nur für Niveau A geeignet: {verteilung.nur_a}")
    print(f"  nur für Niveau B geeignet: {verteilung.nur_b}")
    print(f"  für beide geeignet (verteilt): {verteilung.strittig}")
    print(f"  für keins geeignet: {len(verteilung.ungenutzt)}\n")
    for name in NIVEAUS:
        plan = plans[name]
        bal = plan.balance
        print(f"  Niveau {name} ({PROFILES[name].cefr}): {plan.report.gewaehlt}/60 "
              f"gewählt, {plan.report.fehlend} zu ergänzen "
              f"({plan.report.fehlend / 60:.0%}), Ø Schwierigkeit "
              f"{(bal['schwierigkeit_test1'] + bal['schwierigkeit_test2']) / 2:.2f}, "
              f"Ø Zipf {(bal['zipf_test1'] + bal['zipf_test2']) / 2:.2f}")
    familien = near_duplicates(plans)
    if familien:
        print(f"\n  Wortfamilien über beide Niveaus verteilt ({len(familien)}):")
        for a, b, why in familien[:8]:
            print(f"    {a} (A) / {b} (B) - {why}")
    if args.woerter:
        for name in NIVEAUS:
            print(f"\n--- Niveau {name} ---")
            for label, words in (("Test 1", plans[name].test1), ("Test 2", plans[name].test2)):
                print(f"  {label}: " + ", ".join(c.headword for c in words))
    return 0


# ------------------------------------------------------------------- Gerüst
def cmd_geruest(args) -> int:
    db = _db(args)
    settings = _settings(args)
    unit = db.require_unit(args.unit)
    ziel = Path(args.verzeichnis)
    niveaus = [args.niveau] if args.niveau else list(NIVEAUS)
    plans = plan_both(db, unit, settings)

    for name in niveaus:
        prof = profile(name)
        pfad = ziel / pack_filename(unit, prof)
        if pfad.exists() and not args.ueberschreiben:
            print(f"{pfad} besteht bereits - mit --überschreiben neu erzeugen.")
            continue
        data = scaffold(db, unit, prof, settings, plans[prof.name])
        Pack(data=data).save(pfad)
        fehlt = data["fehlbestand"]
        print(f"{pfad} geschrieben - Niveau {prof.name} ({prof.cefr}), "
              f"{60 - fehlt} Wörter aus der Wortliste, {fehlt} zu ergänzen "
              f"({fehlt / 60:.0%}).")
    print("\nJetzt im Chat ausfüllen: die Felder 'satz', fehlende Wörter und "
          "die beiden Lückentexte. Danach 'vocabmaster prüfen <datei>'.")
    return 0


def cmd_offen(args) -> int:
    pack = Pack.load(args.paket)
    offen = pack.offen()
    print(f"{pack.unit_label}, Niveau {pack.niveau.name} - {pack.thema}")
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


def _gegenstueck(args, pack: Pack) -> Pack | None:
    pfad = gegenstueck_pfad(args.paket, pack.niveau.name)
    return Pack.load(pfad) if Path(pfad).exists() else None


def cmd_pruefen(args) -> int:
    pack = Pack.load(args.paket)
    bericht = pruefe_paket(pack, _db(args), _settings(args), _gegenstueck(args, pack))
    print(bericht.kennzahlen.get("_kopf", ""))
    _bericht_zeigen(bericht, args.ausfuehrlich)
    if args.streng and bericht.warnungen:
        return 1
    return 1 if bericht.fehler else 0


def cmd_bauen(args) -> int:
    pack = Pack.load(args.paket)
    settings = _settings(args)
    db = _db(args)
    bericht = pruefe_paket(pack, db, settings, _gegenstueck(args, pack))
    print(bericht.kennzahlen.get("_kopf", ""))
    _bericht_zeigen(bericht, args.ausfuehrlich)

    if bericht.fehler and not args.trotzdem:
        print("\nEs wird nichts geschrieben, solange Fehler offen sind "
              "(Notausgang: --trotzdem).")
        return 1
    if bericht.warnungen and args.streng and not args.trotzdem:
        print("\n--streng: es wird nichts geschrieben, solange Warnungen offen sind.")
        return 1

    teile = ("liste", "test") if args.nur == "alles" else (args.nur,)
    ergebnis = baue_alles(pack, args.ausgabe, settings, teile, not args.ohne_loesung)
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

    p = dbsub.add_parser("pool", help="zeigen, wie eine Unit auf A und B aufgeht")
    p.add_argument("unit", type=_unit)
    p.add_argument("-w", "--woerter", action="store_true", help="alle Wörter zeigen")
    p.add_argument("--mit-zusatzteilen", action="store_true",
                   dest="mit_zusatzteilen",
                   help="Culture, Curriculum extra, Project … mitzählen")
    p.set_defaults(func=cmd_db_pool)

    for name in ("gerüst", "geruest"):
        p = sub.add_parser(name, help="Gerüst für eine Unit erzeugen")
        p.add_argument("unit", type=_unit)
        p.add_argument("--niveau", choices=list(NIVEAUS),
                       help="nur dieses Niveau (Standard: beide)")
        p.add_argument("-o", "--verzeichnis", default=str(KURATIERT))
        p.add_argument("--mit-zusatzteilen", action="store_true",
                       dest="mit_zusatzteilen")
        p.add_argument("--überschreiben", "--ueberschreiben", action="store_true",
                       dest="ueberschreiben")
        p.set_defaults(func=cmd_geruest)

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
        p.add_argument("--mit-zusatzteilen", action="store_true",
                       dest="mit_zusatzteilen")
        p.set_defaults(func=cmd_pruefen)

    p = sub.add_parser("bauen", help="prüfen und die Word-Dateien schreiben")
    p.add_argument("paket")
    p.add_argument("-o", "--ausgabe", default=str(AUSGABE))
    p.add_argument("--nur", choices=("alles", "liste", "test"), default="alles",
                   help="nur einen Teil neu erzeugen")
    p.add_argument("--ohne-loesung", action="store_true", dest="ohne_loesung")
    p.add_argument("-a", "--ausfuehrlich", action="store_true")
    p.add_argument("--streng", action="store_true")
    p.add_argument("--trotzdem", action="store_true",
                   help="trotz Fehlern schreiben (Notausgang)")
    p.add_argument("--mit-zusatzteilen", action="store_true", dest="mit_zusatzteilen")
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
