"""Weboberfläche von VocabMaster.

    streamlit run app.py

Was die Oberfläche kann, ohne Sprachmodell und ohne Netz:

* die Wortliste des Lehrmittels durchsuchen und je Unit ansehen
* zeigen, wie eine Unit auf Niveau A und Niveau B aufgeht
* Gerüste erzeugen und herunterladen
* ein ausgefülltes Paket hochladen, den vollständigen Selbstcheck laufen
  lassen und die vier Dokumente als ZIP herunterladen

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
from vocabmaster.pack import Pack, pack_filename, scaffold
from vocabmaster.pool import near_duplicates, plan_both

st.set_page_config(page_title="VocabMaster", page_icon="📗", layout="wide")


@st.cache_resource
def lade_datenbank(pfad: str) -> Database:
    return Database.load(pfad)


def einstellungen() -> Settings:
    s = Settings()
    s.core_sections_only = not st.session_state.get("zusatzteile", False)
    return s


# ---------------------------------------------------------------- Seitenleiste
st.sidebar.title("📗 VocabMaster")
settings = Settings()
try:
    db = lade_datenbank(str(settings.database))
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.caption(db.herkunft)
st.sidebar.checkbox(
    "Zusatzteile mitzählen",
    key="zusatzteile",
    help="Culture, Curriculum extra, Project und Literature derselben Unit "
    "einbeziehen. Normalerweise zählt nur der Hauptteil.",
)
settings = einstellungen()

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

    plans = plan_both(db, unit, settings)
    spalten = st.columns(2)
    for spalte, name in zip(spalten, NIVEAUS, strict=False):
        plan, prof = plans[name], PROFILES[name]
        bal = plan.balance
        with spalte:
            st.subheader(f"Niveau {name}")
            st.caption(f"{prof.cefr} · {prof.beschreibung}")
            a, b, c = st.columns(3)
            a.metric("aus der Wortliste", plan.report.gewaehlt)
            b.metric("zu ergänzen", plan.report.fehlend,
                     delta=f"{plan.report.fehlend / 60:.0%}" if plan.report.fehlend else None,
                     delta_color="inverse")
            c.metric("Ø Schwierigkeit",
                     f"{(bal['schwierigkeit_test1'] + bal['schwierigkeit_test2']) / 2:.2f}")
            if plan.report.fehlend / 60 > settings.max_invented_share:
                st.warning(
                    f"{plan.report.fehlend / 60:.0%} müssten ergänzt werden — mehr "
                    f"als die erlaubten {settings.max_invented_share:.0%}. "
                    "Zuerst die Zusatzteile zulassen (Seitenleiste)."
                )
            for label, words in (("Test 1", plan.test1), ("Test 2", plan.test2)):
                with st.expander(f"{label} ({len(words)} Wörter)"):
                    st.dataframe(
                        [
                            {
                                "Englisch": c_.headword,
                                "Deutsch": c_.german,
                                "Wortart": c_.pos.value,
                                "Zipf": round(c_.zipf, 2),
                                "Schwierigkeit": round(c_.difficulty, 2),
                            }
                            for c_ in words
                        ],
                        use_container_width=True, hide_index=True,
                    )

    familien = near_duplicates(plans)
    if familien:
        st.info(
            f"{len(familien)} Wortfamilien verteilen sich über beide Niveaus — "
            "erlaubt, aber gut zu wissen: "
            + ", ".join(f"{a} (A) / {b} (B)" for a, b, _ in familien[:6])
        )

# ------------------------------------------------------------ Gerüst erzeugen
elif seite == "Gerüst erzeugen":
    st.header(f"Gerüst für {db.unit_label(unit)}")
    st.write(
        "Das Gerüst enthält die geprüfte Wortauswahl und leere Felder für die "
        "Beispielsätze und die beiden Lückentexte. **Diese Felder werden im "
        "Chat ausgefüllt** — die Anwendung erzeugt keine Sätze."
    )
    gewaehlt = st.multiselect("Niveaus", list(NIVEAUS), default=list(NIVEAUS))
    if st.button("Gerüste erzeugen", type="primary") and gewaehlt:
        plans = plan_both(db, unit, settings)
        for name in gewaehlt:
            data = scaffold(db, unit, name, settings, plans[name])
            fehlt = data["fehlbestand"]
            st.download_button(
                f"⬇ {pack_filename(unit, name)}  "
                f"({60 - fehlt} Wörter, {fehlt} zu ergänzen)",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name=pack_filename(unit, name),
                mime="application/json",
                key=f"dl_{name}",
            )

# --------------------------------------------------- Paket prüfen und bauen
elif seite == "Paket prüfen und bauen":
    st.header("Paket prüfen und bauen")
    hochgeladen = st.file_uploader(
        "Ausgefülltes Paket (.json)", type="json", accept_multiple_files=True,
        help="Beide Niveaus einer Unit zusammen hochladen, dann wird auch der "
        "Vergleich zwischen A und B geprüft.",
    )
    if hochgeladen:
        pakete = {}
        for datei in hochgeladen:
            pack = Pack(data=json.loads(datei.getvalue().decode("utf-8")))
            pakete[pack.niveau.name] = pack

        for name, pack in sorted(pakete.items()):
            gegen = pakete.get("B" if name == "A" else "A")
            bericht = pruefe_paket(pack, db, settings, gegen)
            st.subheader(f"{pack.unit_label}, Niveau {name} ({pack.niveau.cefr})")
            st.caption(pack.thema)

            a, b = st.columns(2)
            a.metric("Fehler", len(bericht.fehler))
            b.metric("Warnungen", len(bericht.warnungen))
            st.code("\n".join(bericht.uebersicht()), language=None)

            for stufe, box in ((FEHLER, st.error), (WARNUNG, st.warning),
                               (HINWEIS, st.info)):
                treffer = [b_ for b_ in bericht.befunde if b_.stufe == stufe]
                if not treffer:
                    continue
                with st.expander(f"{stufe} ({len(treffer)})",
                                 expanded=stufe == FEHLER):
                    for befund in treffer:
                        box(f"{befund.pruefung}: {befund.text}")

            if bericht.ok:
                if st.button(f"Dokumente für Niveau {name} bauen", key=f"b_{name}",
                             type="primary"):
                    with TemporaryDirectory() as tmp:
                        ergebnis = baue_alles(pack, tmp, settings)
                        puffer = io.BytesIO()
                        with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
                            for pfad in ergebnis.dateien:
                                z.write(pfad, Path(pfad).name)
                        if ergebnis.ok:
                            st.success(
                                f"{len(ergebnis.dateien)} Dokumente geschrieben "
                                "und nachkontrolliert."
                            )
                        else:
                            st.error("Die Nachkontrolle hat Fehler gefunden.")
                            for befund in ergebnis.bericht.fehler:
                                st.error(str(befund))
                        st.download_button(
                            f"⬇ Unit{pack.unit:02d}_Niveau{name}.zip",
                            data=puffer.getvalue(),
                            file_name=f"Unit{pack.unit:02d}_Niveau{name}.zip",
                            mime="application/zip", key=f"z_{name}",
                        )
            else:
                st.error(
                    "Es wird nichts gebaut, solange Fehler offen sind. "
                    "Die offenen Stellen im Chat ausfüllen und erneut hochladen."
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
        rows = db.unit_pool(unit, core_only=settings.core_sections_only)
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
