# VocabMaster

Aus **einer** Wortliste entstehen für jede Unit und jedes Niveau vier fertige
Word-Dateien: die Vokabelliste mit Test 1 und Test 2, und die beiden
Prüfungen dazu — jeweils mit Lösungsblatt.

VocabMaster führt zwei bisher getrennte Anwendungen zusammen: den
**VocabListMaker** (Wortauswahl, Beispielsätze, Vokabelliste) und den
**VocabTestMaker** (Prüfung mit Übersetzungsteil und Lückentext). Beide
arbeiten jetzt auf derselben Datenbank und derselben Datei — Liste und
Prüfung können nicht mehr auseinanderdriften.

Es wird **kein API-Schlüssel und kein Netzzugang** gebraucht.

---

## Der ganze Ablauf in vier Zeilen

```bash
vocabmaster gerüst 3                        # Auswahl für Niveau A und B
#   → kuratiert/unit_03_A.json, kuratiert/unit_03_B.json
#   → die Felder 'satz' und die Lückentexte im Chat ausfüllen lassen
vocabmaster prüfen kuratiert/unit_03_A.json # Selbstcheck, bis 0 Fehler
vocabmaster bauen  kuratiert/unit_03_A.json # Dokumente schreiben und kontrollieren
```

Im Chat genügt: **„Generiere mir Test und Vocabulary List für Unit 3,
Niveau A und B.“**

---

## Was dabei herauskommt

Je Unit und Niveau:

| Datei | Inhalt |
|---|---|
| `Unit03_VocabularyList_NiveauA.docx` | Vokabelliste, Test 1 und Test 2 (je 30 Wörter) |
| `Unit03_Test_PartI_NiveauA.docx` | Prüfung zu Test 1 (12 Punkte) |
| `Unit03_Test_PartII_NiveauA.docx` | Prüfung zu Test 2 (12 Punkte) |
| `…_Loesung.docx` | je Prüfung ein Lösungsblatt |

Jedes Dokument nennt in seinen Eigenschaften, aus welcher Fassung der
Wortliste es stammt (Dateiname, Importdatum, SHA-256) und wann es erzeugt
wurde.

---

## Niveau A und Niveau B

| Niveau | GER | Zielgruppe |
|---|---|---|
| **A** | B1.2 – B2.1 | leistungsstärkere Gruppe |
| **B** | A2.2 – B1.1 | leistungsschwächere Gruppe |

Beide Niveaus behandeln **dasselbe Unit-Thema**, aber die beiden Listen sind
**überschneidungsfrei**: Kein Wort steht in beiden.

Das gelingt über getrennte Häufigkeitsfenster. Ein Wort wie *memory*
(Zipf 4.9) ist für die stärkere Gruppe längst bekannt und damit kein
Prüfstoff — für die schwächere Gruppe ist es genau richtig. Umgekehrt ist
*memorize* (Zipf 3.4) für Niveau B zu weit weg und für Niveau A der
eigentliche Zugewinn. Wörter im Überlappungsbereich werden so verteilt, dass
beide Listen möglichst voll werden.

Was für **beide** gilt: kein A1/A2-Grundwortschatz, keine blossen Kognate
(`Protein`/`protein`), nichts aus früheren Units, dieselben Kontrollen.
Ein Niveau-B-Test ist kein schlechterer Test, sondern ein Test über die
Wörter, an denen diese Gruppe wirklich etwas lernt.

Die **Prüfungsform** ist für beide gleich (8× Übersetzen + Lückentext mit
4 Lücken und Wortbank, 12 Punkte) — so wie in der Vorlage. Unterschiedlich
sind Wortauswahl und Lückentext:

| | Niveau A | Niveau B |
|---|---|---|
| Textlänge | 70–130 Wörter | 50–95 Wörter |
| längster Satz | max. 28 Wörter | max. 18 Wörter |
| Sätze im Schnitt | 9–20 Wörter | 7–14 Wörter |
| Flesch-Lesbarkeit | ≥ 55 | ≥ 70 |
| Nebensätze je Satz | max. 2 | max. 1 |
| Wörter ausserhalb des Grundwortschatzes | max. 3 | max. 1 |
| Beispielsätze der Liste | max. 16 Wörter | max. 13 Wörter |

---

## Der Selbstcheck

Vor jeder Ausgabe laufen alle Kontrollen. Bei einem Fehler wird **nicht**
geschrieben. Der Kurzbericht sieht so aus:

```
Unit 3, Niveau A (B1.2-B2.1) - Werbung, Marketing und Konsum

Selbstcheck
  ✓ thema                12 ergänzte Wörter, 0 ohne Themenbezug
  ✓ neuwoerter           12 von 60 = 20% (Grenze 40%)
  ✓ cefr                 B1.2-B2.1: Sätze Ø 9.8 Wörter (max 14), Lesbarkeit 71
  ✓ dubletten            60 verschiedene Wörter, 0 Doppelungen
  ✓ altbestand           Quelle english_plus_2e_level_4…xls, 0 nicht belegte Einträge
  ✓ loesungsschluessel   24 Aufgaben gegen die Liste geprüft
  ✓ niveau_konsistenz    Ø Schwierigkeit A 0.53 gegen B 0.25, 0 gemeinsame Wörter
  ✓ vorlage              0 offene Felder, 0 Platzhalter
  ✓ herkunft             english_plus_2e_level_4…xls, importiert 2026-09-10
  ✓ liste                30+30 Wörter, Schwierigkeitsdifferenz 0.004
  ✓ pruefung             Teil 1: 96 Wörter, Lesbarkeit 74, Grad 5.9; Teil 2: …
  ✓ dokument             5 Dateien geschrieben und nachkontrolliert
```

| Kontrolle | findet |
|---|---|
| `thema` | ergänzte Wörter, die nicht zum Wortfeld der Unit gehören |
| `neuwoerter` | mehr als 40 % selbst ergänzt |
| `cefr` | Sätze und Lückentexte ausserhalb des Bandes des Niveaus |
| `dubletten` | dasselbe Wort zweimal, widersprüchliche Übersetzung oder Wortart |
| `altbestand` | Wörter aus einer alten Wortliste, falsche Excel-Fassung |
| `loesungsschluessel` | Prüfung und Liste sagen Verschiedenes; Wort in beiden Teilen geprüft |
| `niveau_konsistenz` | gemeinsame Wörter, verschiedene Themen, A nicht schwerer als B |
| `vorlage` | offene Felder, `TODO`, falsche Zahl an Lückenmarkern |
| `herkunft` | fehlende Quellangabe |
| `liste` | die Kontrollen des VocabListMaker: Auswahl, Balance, Beispielsätze, A4-Seite |
| `pruefung` | die zwanzig Kontrollen des VocabTestMaker, je Prüfungsteil |
| `dokument` | Nachkontrolle der geschriebenen Word-Datei gegen die Vorlage |

Die Naht zwischen den beiden Anwendungen sitzt bei `loesungsschluessel`:
Der Prüfungs-Checker vergleicht nicht mehr gegen ein separat gelesenes
Word-Dokument, sondern gegen genau die Liste, die in derselben Datei steht.

---

## Installation

Python 3.10 oder neuer.

```bash
git clone https://github.com/tobiasjungstud-ui/VocabMaster.git
cd VocabMaster

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e .
```

Die Datenbank ist mitgeliefert; `wordfreq` wird nur zum Neu-Einlesen einer
Wortliste gebraucht.

---

## Kommandozeile

```bash
vocabmaster db units                      # Übersicht über alle Units
vocabmaster db units -a                   # mit allen Zusatzbereichen
vocabmaster db suche "Publikum"           # in der Wortliste suchen
vocabmaster db pool 3                     # wie Unit 3 auf A und B aufgeht
vocabmaster db pool 3 --wörter            # mit allen gewählten Wörtern

vocabmaster gerüst 3                      # Gerüste für A und B
vocabmaster gerüst 3 --niveau B           # nur Niveau B
vocabmaster gerüst 6 --mit-zusatzteilen   # Culture 6, Project 6 … mitzählen

vocabmaster offen  kuratiert/unit_03_A.json   # was noch auszufüllen ist
vocabmaster prüfen kuratiert/unit_03_A.json   # Selbstcheck ohne zu schreiben
vocabmaster prüfen … -a                       # auch Hinweise zeigen
vocabmaster bauen  kuratiert/unit_03_A.json   # prüfen und schreiben
vocabmaster bauen  … --nur test               # nur die Prüfungen neu erzeugen
vocabmaster bauen  … --nur liste              # nur die Vokabelliste
```

`--nur test` und `--nur liste` sind der Weg für Teilanfragen: Sie schreiben
nur, was verlangt ist, und lassen alles andere unberührt. Auch die Gerüste
liegen je Niveau in einer eigenen Datei — Niveau B neu zu erzeugen ändert
`unit_03_A.json` nicht.

Der Rückgabewert ist `0`, wenn keine Fehler gefunden wurden, sonst `1`.

---

## Weboberfläche

```bash
pip install -e ".[ui]"
streamlit run app.py
```

Vier Bereiche: **Unit ansehen** (wie die Unit auf A und B aufgeht, mit allen
Wörtern), **Gerüst erzeugen** (Download als JSON), **Paket prüfen und bauen**
(Upload, vollständiger Selbstcheck, alle Dokumente als ZIP) und
**Wortliste** (Suche über den ganzen Bestand).

Sätze schreiben kann die Oberfläche nicht — die entstehen im Chat. Sie prüft
sie und setzt sie.

---

## Die Datenbank

Quelle ist die Wortliste des Lehrmittels (English Plus 2nd edition, Level 4),
1722 Einträge:

| Unit | Hauptteil | gesamt | Thema |
|---:|---:|---:|---|
| Starter | 65 | 65 | Medien, Geräte und Online-Leben |
| 1 | 213 | 294 | Erinnerungen und Gegenstände |
| 2 | 186 | 277 | Entscheidungen, Zukunft und Engagement |
| 3 | 133 | 200 | Werbung, Marketing und Konsum |
| 4 | 136 | 205 | Gefühle und Verständigung zwischen Mensch und Tier |
| 5 | 128 | 187 | Wissenschaft, Forschung und Biomimikry |
| 6 | 88 | 151 | Persönlichkeit und soziale Rollen |
| 7 | 100 | 162 | Bauwerke und Wahrzeichen |
| 8 | 119 | 181 | Verbrechen, Sicherheit und Krimis |

### Warum JSON je Unit und nicht eine SQLite-Datei

Die Wortliste wird von Hand nachgepflegt und im Git-Verlauf gelesen. Eine
Binärdatei zeigt im Diff nur „binary files differ“; eine JSON-Datei je Unit
zeigt genau, welches Wort dazukam. Für Abfragen wird beim Öffnen daraus eine
SQLite-Datenbank **im Arbeitsspeicher** gebaut — bei 1722 Zeilen dauert das
keine messbare Zeit. So bleibt der Verlauf lesbar und SQL trotzdem
verfügbar:

```python
from vocabmaster.database import Database
db = Database.load()
db.query("SELECT english, german, zipf FROM woerter WHERE unit = 7 AND zipf < 3")
```

Eine spätere API-Anbindung ist dadurch nicht blockiert: Die Struktur ist
zeilenweise und vollständig typisiert.

```
src/vocabmaster/data/
├── themen.json          Thema, Titel und Leitwörter je Unit (von Hand pflegbar)
└── wortliste/
    ├── index.json       Quelle, Importdatum, SHA-256, Zählung je Unit
    ├── unit_00.json     Starter Unit
    ├── unit_01.json     …
    └── unit_08.json
```

Jede Unit-Datei nennt Unit-Nummer, Titel, Thema, Seitenbereich, Quelldatei,
Importdatum und Prüfsumme — jedes Dokument ist damit auf eine benannte
Fassung der Wortliste zurückführbar.

### Wortliste austauschen

```bash
vocabmaster db import pfad/zur/neuen_wortliste.xls
```

Gelesen werden `.xls` und `.xlsx`. Erkannt werden Blocküberschriften,
Sektionsangaben mit Seitenzahl (`Starter Unit, p.4` — die `4` ist die Seite,
nicht die Unit), Zusatzbereiche (`Culture 7`, `CE - Unit 5`, `WB, Unit 4`)
und doppelte Zeilen. Unit-Dateien, die in der neuen Quelle nicht mehr
vorkommen, werden gelöscht — aus einer alten Wortliste bleibt nichts stehen.

---

## Der Umfang einer Unit

Verbindlich zählt nur der **Hauptteil** `Unit N`. `Culture N`,
`Curriculum extra N`, `Project N`, `Literature N` und `Extra Listening and
Speaking Unit N` gehören nicht dazu.

Reicht das für zwei überschneidungsfreie Listen nicht, gilt diese Reihenfolge:

1. `--mit-zusatzteilen` — die Zusatzteile derselben Unit zulassen. Immer noch
   Material des Lehrmittels.
2. Erst danach im Chat ergänzen, höchstens 40 % je Liste.

Wie viel jeweils fehlt, sagt `vocabmaster db pool <unit>` vorab.

---

## Aufbau

```
VocabMaster/
├── app.py                        Weboberfläche (Streamlit)
├── data/                         die Excel-Wortliste des Lehrmittels
├── kuratiert/                    ein Paket je Unit und Niveau
├── src/vocabmaster/
│   ├── config.py                 Einstellungen
│   ├── niveau.py                 Niveau A und B: Bänder und Zielwerte
│   ├── importer.py               Excel → Datenbank
│   ├── database.py               Zugriff auf die Wortliste (JSON + SQLite)
│   ├── pool.py                   Zuteilung auf A und B, Wortauswahl
│   ├── pack.py                   das Unit-Paket: Gerüst, Lesen, Kennzahlen
│   ├── checks.py                 der Selbstcheck
│   ├── documents.py              die vier Word-Dateien
│   ├── cli.py                    Kommandozeile
│   ├── list/                     ← VocabListMaker, nahe am Original
│   ├── exam/                     ← VocabTestMaker, nahe am Original
│   ├── templates/                Referenzprüfung als Layoutvorlage
│   └── data/                     Datenbank und Themen
└── tests/
```

---

## Entwicklung

```bash
pip install -e ".[dev]"
pytest
ruff check src app.py tests
```

Die Tests bauen je genau einen klassischen Fehler ein und verlangen, dass der
Selbstcheck ihn findet — ein Prüfmechanismus, der nur behauptet zu prüfen,
fällt dort auf. Dazu kommen Tests für den Import (Seitenzahl-Falle,
Sektionsformen), für die Überschneidungsfreiheit der Niveaus in **jeder**
Unit und dafür, dass die erzeugte Prüfung die Vorlage byteweise übernimmt.

---

## Häufige Fragen

**Warum stehen in Liste A und Liste B verschiedene Wörter?**
Weil beide Gruppen an verschiedenen Wörtern etwas lernen. Das Thema ist
dasselbe; der Selbstcheck prüft das ausdrücklich.

**Eine Unit meldet zu wenig Material.**
Der Hauptteil gibt keine 120 geeigneten Wörter her. Zuerst
`--mit-zusatzteilen`, dann im Chat ergänzen (höchstens 40 %).

**Kann ich nur die Prüfung neu erzeugen?**
`vocabmaster bauen … --nur test`. Die Vokabelliste bleibt unberührt.

**Passt eine Liste wirklich auf eine Seite?**
Die Höhe wird vor der Ausgabe gerechnet; über 100 % gibt es einen Fehler.

**Ich möchte ein Wort nie in einer Liste sehen.**
In `src/vocabmaster/list/data/a1_a2_core.txt` eintragen.

**Bekomme ich bei gleichem Vorgehen dieselbe Auswahl?**
Ja — die Auswahl ist über `VM_SEED` reproduzierbar. Die Sätze schreibt das
Modell bei jedem Lauf neu.

---

## Einstellungen

| Variable | Standard | Wirkung |
|---|---|---|
| `VM_DATABASE` | mitgeliefert | Verzeichnis der Wortlisten-Datenbank |
| `VM_CORE_ONLY` | `true` | nur den Hauptteil einer Unit verwenden |
| `VM_WORDS_PER_TEST` | `30` | Wörter je Test der Vokabelliste |
| `VM_MAX_INVENTED` | `0.40` | Höchstanteil ergänzter Wörter |
| `VM_EXAM_WORDS` | `12` | Wörter je Prüfung |
| `VM_EXAM_GAPS` | `4` | Lücken im Lückentext |
| `VM_FONT` | `Century Gothic` | Schriftart der Vokabelliste |
| `VM_FONT_SIZE` | `10` | Schriftgrad der Vokabelliste |
| `VM_ROW_HEIGHT` | `340` | Mindesthöhe einer Tabellenzeile in Twips |
| `VM_SEED` | `20240607` | Zufallsstartwert der Auswahl |

---

## Lizenz

MIT — siehe [LICENSE](LICENSE).
