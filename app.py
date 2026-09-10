"""Weboberfläche von VocabMaster.

    streamlit run app.py

Was die Oberfläche kann, ohne Sprachmodell und ohne Netz:

* die Wortliste des Lehrmittels durchsuchen und je Unit ansehen
* zeigen, welche 60 Wörter eine Unit ergibt und wie die Prüfungen für
  Niveau A und Niveau B daraus schöpfen
* Gerüste erzeugen und herunterladen
* ein ausgefülltes Paket hochladen, den vollständigen Selbstcheck laufen
  lassen und alle neun Dokumente als ZIP herunterladen

Was sie nicht kann: Beispielsätze und Lückentexte schreiben. Die entstehen
im Chat - die Oberfläche prüft sie nur.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st

from vocabmaster.checks import FEHLER, HINWEIS, WARNUNG, pruefe_paket
from vocabmaster.config import Settings
from vocabmaster.database import Database
from vocabmaster.documents import baue_alles
from vocabmaster.niveau import NIVEAUS, PROFILES
from vocabmaster.pack import Pack, _schwierigkeit, pack_filename, scaffold, waehle_pruefungswoerter
from vocabmaster.pool import plan_unit

st.set_page_config(page_title="VocabMaster", page_icon="📗", layout="wide")


@st.cache_resource
def lade_datenbank(pfad: str) -> Database:
    return Database.load(pfad)




# ---------------------------------------------------------------- Seitenleiste
st.sidebar.title("📗 VocabMaster")
settings = Settings()
try:
    db = lade_datenbank(str(settings.database))
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.caption(db.herkunft)
st.sidebar.caption(
    "Es zählt nur der Hauptteil einer Unit. Culture, Project und Curriculum "
    "extra werden nur als letzte Reserve herangezogen - und dann einzeln "
    "ausgewiesen."
)

units = db.units()
unit = st.sidebar.selectbox(
    "Unit", units, format_func=lambda u: f"{db.unit_label(u)} — {db.theme(u)['thema']}"
)
seite = st.sidebar.radio(
    "Bereich", ["Unit ansehen", "Gerüst erzeugen", "Paket prüfen und bauen", "Wortliste"]
)

# ------------------------------------------------------------- Unit ansehen
if seite == "Unit ansehen":
    theme = db.theme(unit)
    st.header(f"{db.unit_label(unit)} — {theme['thema']}")
    st.caption(f"Seiten {theme.get('seiten', '?')} · {db.herkunft}")

    plan = plan_unit(db, unit, settings)
    r = plan.report
    a, b, c, d = st.columns(4)
    a.metric("im Hauptteil", r.hauptteil)
    b.metric("davon geeignet", r.brauchbar)
    c.metric("aus dem Hauptteil gewählt", r.aus_hauptteil)
    d.metric("im Chat zu ergänzen", r.fehlend,
             delta=f"{r.ergaenzt_anteil:.0%}" if r.fehlend else None,
             delta_color="inverse")

    if r.aus_zusatzteilen:
        st.warning(
            f"**Ausnahme:** {len(r.aus_zusatzteilen)} Wörter mussten aus "
            "Zusatzteilen derselben Unit nachgezogen werden — "
            + ", ".join(f"{w} ({bereich})" for w, bereich in r.aus_zusatzteilen)
        )
    if r.ausnahme:
        st.info(r.ausnahme)

    st.subheader("Die Vokabelliste — für beide Gruppen dieselbe")
    for label, words in (("Test 1", plan.test1), ("Test 2", plan.test2)):
        with st.expander(f"{label} ({len(words)} Wörter)", expanded=False):
            st.dataframe(
                [
                    {
                        "Englisch": w.headword,
                        "Deutsch": w.german,
                        "Wortart": w.pos.value,
                        "Zipf": round(w.zipf, 2),
                        "Schwierigkeit": round(w.difficulty, 2),
                    }
                    for w in words
                ],
                use_container_width=True, hide_index=True,
            )

    st.subheader("Woraus die beiden Prüfungen schöpfen")
    st.caption(
        "Aus den 30 Wörtern eines Tests nimmt Niveau A die zwölf schwersten, "
        "Niveau B die nächsten zwölf. Überschneidungsfrei."
    )
    for teil, words in ((1, plan.test1), (2, plan.test2)):
        eintraege = [
            {"englisch": w.headword or w.english, "deutsch": w.german,
             "wortart": "", "nr": i}
            for i, w in enumerate(words, 1)
        ]
        st.markdown(f"**Teil {'I' if teil == 1 else 'II'}** (aus Test {teil})")
        spalten = st.columns(2)
        for spalte, name in zip(spalten, NIVEAUS, strict=False):
            gewaehlt = waehle_pruefungswoerter(eintraege, PROFILES[name], settings)
            schnitt = (
                sum(_schwierigkeit(e) for e in gewaehlt) / len(gewaehlt)
                if gewaehlt else 0.0
            )
            with spalte:
                st.markdown(
                    f"Niveau **{name}** · {PROFILES[name].cefr} · "
                    f"Ø {schnitt:.1f}/10"
                )
                st.write(", ".join(e["englisch"] for e in gewaehlt))

# ------------------------------------------------------------ Gerüst erzeugen
elif seite == "Gerüst erzeugen":
    st.header(f"Gerüst für {db.unit_label(unit)}")
    st.write(
        "Das Gerüst enthält die geprüfte Wortauswahl und leere Felder für die "
        "60 Beispielsätze und die vier Lückentexte. **Diese Felder werden im "
        "Chat ausgefüllt** — die Anwendung erzeugt keine Sätze."
    )
    if st.button("Gerüst erzeugen", type="primary"):
        plan = plan_unit(db, unit, settings)
        data = scaffold(db, unit, settings, plan)
        fehlt = data["fehlbestand"]
        st.download_button(
            f"⬇ {pack_filename(unit)}  "
            f"({60 - fehlt} Wörter aus der Wortliste, {fehlt} zu ergänzen)",
            data=json.dumps(data, ensure_ascii=False, indent=2),
            file_name=pack_filename(unit),
            mime="application/json",
        )

# --------------------------------------------------- Paket prüfen und bauen
elif seite == "Paket prüfen und bauen":
    st.header("Paket prüfen und bauen")
    hochgeladen = st.file_uploader(
        "Ausgefülltes Paket (.json)", type="json",
        help="Eine Datei je Unit - sie enthält die Vokabelliste und alle vier "
        "Prüfungen.",
    )
    if hochgeladen:
        pack = Pack(data=json.loads(hochgeladen.getvalue().decode("utf-8")))
        bericht = pruefe_paket(pack, db, settings)
        st.subheader(f"{pack.unit_label} — {pack.thema}")

        a, b = st.columns(2)
        a.metric("Fehler", len(bericht.fehler))
        b.metric("Warnungen", len(bericht.warnungen))
        st.code("\n".join(bericht.uebersicht()), language=None)

        for stufe, box in ((FEHLER, st.error), (WARNUNG, st.warning),
                           (HINWEIS, st.info)):
            treffer = [x for x in bericht.befunde if x.stufe == stufe]
            if not treffer:
                continue
            with st.expander(f"{stufe} ({len(treffer)})", expanded=stufe == FEHLER):
                for befund in treffer:
                    box(f"{befund.pruefung}: {befund.text}")

        if not bericht.ok:
            st.error(
                "Es wird nichts gebaut, solange Fehler offen sind. Die offenen "
                "Stellen im Chat ausfüllen und erneut hochladen."
            )
        else:
            was = st.multiselect(
                "Was soll gebaut werden?",
                ["Vokabelliste", "Prüfung Niveau A", "Prüfung Niveau B"],
                default=["Vokabelliste", "Prüfung Niveau A", "Prüfung Niveau B"],
            )
            if st.button("Dokumente bauen", type="primary") and was:
                teile = tuple(
                    t for t, gewollt in (
                        ("liste", "Vokabelliste" in was),
                        ("test", any(w.startswith("Prüfung") for w in was)),
                    ) if gewollt
                )
                niveaus = tuple(
                    n for n in NIVEAUS if f"Prüfung Niveau {n}" in was
                )
                with TemporaryDirectory() as tmp:
                    ergebnis = baue_alles(
                        pack, tmp, settings, teile, True, niveaus or NIVEAUS
                    )
                    puffer = io.BytesIO()
                    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
                        for pfad in ergebnis.dateien:
                            z.write(pfad, Path(pfad).name)
                    if ergebnis.ok:
                        st.success(
                            f"{len(ergebnis.dateien)} Dokumente geschrieben und "
                            "nachkontrolliert."
                        )
                    else:
                        st.error("Die Nachkontrolle hat Fehler gefunden.")
                        for befund in ergebnis.bericht.fehler:
                            st.error(str(befund))
                    st.download_button(
                        f"⬇ Unit{pack.unit:02d}.zip",
                        data=puffer.getvalue(),
                        file_name=f"Unit{pack.unit:02d}.zip",
                        mime="application/zip",
                    )

# ---------------------------------------------------------------- Wortliste
else:
    st.header("Wortliste durchsuchen")
    st.caption(db.herkunft)
    suche = st.text_input("Suchen in Englisch und Deutsch")
    if suche:
        treffer = db.search(suche, limit=200)
        st.write(f"{len(treffer)} Treffer")
        rows = treffer
    else:
        rows = db.unit_pool(unit, core_only=True)
        st.write(f"{db.unit_label(unit)}: {len(rows)} Einträge")
    st.dataframe(
        [
            {
                "Englisch": r.english,
                "Deutsch": r.german,
                "Wortart": r.pos,
                "Unit": db.unit_label(r.unit) if r.unit is not None else "—",
                "Abschnitt": r.section,
                "Seite": r.page,
                "Oxford 3000": "✓" if r.oxford3000 else "",
                "Zipf": round(r.zipf, 2),
            }
            for r in rows
        ],
        use_container_width=True, hide_index=True, height=600,
    )
