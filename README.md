# VocabMaster

Aus **einer** Wortliste entstehen für jede Unit neun fertige Word-Dateien:
**eine** Vokabelliste mit Test 1 und Test 2 — für beide Gruppen dieselbe —
und vier Prüfungen dazu, für Niveau A und Niveau B, jeweils mit Lösungsblatt.

VocabMaster führt zwei bisher getrennte Anwendungen zusammen: den
**VocabListMaker** (Wortauswahl, Beispielsätze, Vokabelliste) und den
**VocabTestMaker** (Prüfung mit Übersetzungsteil und Lückentext). Beide
arbeiten jetzt auf derselben Datenbank und derselben Datei — Liste und
Prüfung können nicht mehr auseinanderdriften.

Es wird **kein API-Schlüssel und kein Netzzugang** gebraucht.

---

## Der ganze Ablauf in vier Zeilen

```bash
vocabmaster gerüst 3                      # die 60 Wörter der Unit auswählen
#   → kuratiert/unit_03.json
#   → die 60 Felder 'satz' und die vier Lückentexte im Chat ausfüllen lassen
vocabmaster prüfen kuratiert/unit_03.json # Selbstcheck, bis 0 Fehler
vocabmaster bauen  kuratiert/unit_03.json # Dokumente schreiben und kontrollieren
```

Im Chat genügt: **„Generiere mir Test und Vocabulary List für Unit 3,
Niveau A und B.“**

---

## Was dabei herauskommt

Je Unit:

| Datei | Inhalt |
|---|---|
| `Unit03_VocabularyList.docx` | Vokabelliste, Test 1 und Test 2 (je 30 Wörter) — für beide Gruppen |
| `Unit03_Test_PartI_NiveauA.docx` | Prüfung zu Test 1, stärkere Gruppe (12 Punkte) |
| `Unit03_Test_PartI_NiveauB.docx` | Prüfung zu Test 1, schwächere Gruppe (12 Punkte) |
| `Unit03_Test_PartII_NiveauA.docx` | Prüfung zu Test 2, stärkere Gruppe |
| `Unit03_Test_PartII_NiveauB.docx` | Prüfung zu Test 2, schwächere Gruppe |
| `…_Loesung.docx` | je Prüfung ein Lösungsblatt |

Jedes Dokument nennt in seinen Eigenschaften, aus welcher Fassung der
Wortliste es stammt (Dateiname, Importdatum, SHA-256) und wann es erzeugt
wurde.

---

## Niveau A und Niveau B — eine Liste, zwei Prüfungen

**Es gibt je Unit genau eine Vokabelliste.** Beide Gruppen lernen dieselben
60 Wörter derselben Unit. Es gibt keinen Wortschatz, den nur eine Gruppe zu
Gesicht bekommt, und keine zwei Listen, die man auseinanderhalten müsste.

Unterschieden wird erst bei der Prüfung:

| Niveau | GER | Zielgruppe | prüft |
|---|---|---|---|
| **A** | B1.2 – B2.1 | leistungsstärkere Gruppe | die zwölf **schwersten** Wörter des Tests |
| **B** | A2.2 – B1.1 | leistungsschwächere Gruppe | die zwölf **zugänglichsten** Wörter desselben Tests |

Für Unit 6 sieht das so aus:

```
Prüfung Teil I:
  Niveau A (B1.2-B2.1), Ø 3.1/10: beneficial, socialize, voluntary, chill out,
                                  nerd, chore, bully, brave, stand out …
  Niveau B (A2.2-B1.1), Ø 1.6/10: leader, expect, involve, crowd, breathe,
                                  extrovert, opposite, suitable …
```

Ein Überschnitt zwischen den beiden Prüfungen ist **erlaubt** — es sind
verschiedene Gruppen. Er wird im Bericht vermerkt; ab der Hälfte gemeinsamer
Wörter gibt es eine Warnung, weil sich die beiden Fassungen dann nicht mehr
unterscheiden.

Wörter, die man aus dem deutschen Stichwort einfach abschreibt („Anekdote" →
`anecdote`), kommen in **keine** Prüfung — auch nicht in die für Niveau B.
Sie prüfen nichts, auf keinem Niveau.

Die **Prüfungsform** ist für beide gleich (8× Übersetzen + Lückentext mit
4 Lücken und Wortbank, 12 Punkte) — so wie in der Vorlage. Unterschiedlich
ist der Lückentext:

| | Niveau A | Niveau B |
|---|---|---|
| Textlänge | 70–130 Wörter | 50–95 Wörter |
| längster Satz | max. 28 Wörter | max. 18 Wörter |
| Sätze im Schnitt | 9–20 Wörter | 7–14 Wörter |
| Flesch-Lesbarkeit | ≥ 55 | ≥ 70 |
| Nebensätze je Satz | max. 2 | max. 1 |
| Wörter ausserhalb des Grundwortschatzes | max. 3 | max. 1 |

Die Beispielsätze der Vokabelliste lernen **beide** Gruppen, deshalb gilt für
sie das engere Mass: höchstens 13 Wörter je Satz.

---

## Der Selbstcheck

Vor jeder Ausgabe laufen alle Kontrollen. Bei einem Fehler wird **nicht**
geschrieben. Der Kurzbericht sieht so aus:

```
Unit 1 - Erinnerungen und Gegenstände (eine Liste, Prüfungen für Niveau A
B1.2-B2.1 und Niveau B A2.2-B1.1)

Selbstcheck
  ✓ thema                0 ergänzte Wörter, 0 ohne Themenbezug
  ✓ neuwoerter           0 von 60 ergänzt = 0% (Grenze 40%)
  ✓ cefr                 Liste (A2.2-B2.1): Sätze Ø 8.7 Wörter (max 10), Lesbarkeit 74
  ✓ dubletten            60 verschiedene Wörter, 0 Doppelungen
  ✓ altbestand           Quelle english_plus_2e_level_4…xls, 0 nicht belegte Einträge
  ✓ loesungsschluessel   48 Aufgaben gegen die Liste geprüft
  ✓ niveau_konsistenz    Teil 1: A 3.2/10 gegen B 1.6/10; Teil 2: A 3.0/10 gegen B 1.5/10
  ✓ vorlage              0 offene Felder, 0 Platzhalter
  ✓ herkunft             english_plus_2e_level_4…xls, importiert 2026-09-10
  ✓ liste                30+30 Wörter, Schwierigkeitsdifferenz 0.000
  ✓ pruefung             T1/A: 79 W., Lesbarkeit 79, Grad 6.1; T1/B: 54 W., …
  ✓ dokument             9 Dateien geschrieben und nachkontrolliert
```

| Kontrolle | findet |
|---|---|
| `thema` | ergänzte Wörter, die nicht zum Wortfeld der Unit gehören |
| `neuwoerter` | mehr als 40 % selbst ergänzt |
| `cefr` | Beispielsätze zu lang oder zu schwer für die gemeinsame Liste |
| `dubletten` | dasselbe Wort zweimal, widersprüchliche Übersetzung oder Wortart |
| `altbestand` | Wörter aus einer alten Wortliste, falsche Excel-Fassung |
| `loesungsschluessel` | Prüfung und Liste sagen Verschiedenes; Wort in beiden Teilen geprüft |
| `niveau_konsistenz` | Prüfungswort nicht aus der Liste, A nicht schwerer als B, zu grosser Überschnitt |
| `vorlage` | offene Felder, `TODO`, falsche Zahl an Lückenmarkern |
| `herkunft` | fehlende Quellangabe |
| `liste` | die Kontrollen des VocabListMaker: Auswahl, Balance, Beispielsätze, A4-Seite |
| `pruefung` | die zwanzig Kontrollen des VocabTestMaker, für jede der vier Prüfungen |
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
vocabmaster db pool 3                     # Auswahl und A/B-Prüfungen der Unit
vocabmaster db pool 3 --wörter            # mit allen 60 Wörtern

vocabmaster gerüst 3                      # Gerüst für Unit 3

vocabmaster offen  kuratiert/unit_03.json     # was noch auszufüllen ist
vocabmaster prüfen kuratiert/unit_03.json     # Selbstcheck ohne zu schreiben
vocabmaster prüfen … -a                       # auch Hinweise zeigen
vocabmaster bauen  kuratiert/unit_03.json     # prüfen und alles schreiben
vocabmaster bauen  … --nur test --niveau B    # nur Prüfung B neu erzeugen
vocabmaster bauen  … --nur liste              # nur die Vokabelliste
```

`--nur` und `--niveau` sind der Weg für Teilanfragen: Sie schreiben nur, was
verlangt ist, und lassen alles andere unberührt. „Nur Test B für Unit 3 neu"
rührt weder die Vokabelliste noch Niveau A an.

Der Rückgabewert ist `0`, wenn keine Fehler gefunden wurden, sonst `1`.

---

## Weboberfläche

```bash
pip install -e ".[ui]"
streamlit run app.py
```

Vier Bereiche: **Unit ansehen** (die 60 Wörter und woraus die beiden
Prüfungen schöpfen), **Gerüst erzeugen** (Download als JSON), **Paket prüfen
und bauen** (Upload, vollständiger Selbstcheck, wahlweise nur Liste oder nur
ein Niveau, alles als ZIP) und **Wortliste** (Suche über den ganzen Bestand).

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

Reicht der Hauptteil nicht für 60 Wörter, gilt **genau diese** Reihenfolge:

1. **Im Chat ergänzen** — thematisch passende, im Englischen gebräuchliche
   Wörter, bis zu 40 % der Liste.
2. **Erst wenn selbst das nicht reicht**, zieht die Anwendung Wörter aus den
   Zusatzteilen derselben Unit nach — nur so viele wie nötig, und jedes
   einzelne wird im Bericht mit seinem Bereich genannt.

Über 40 % ist eine Ausnahme, kein Abbruch: Es wird gebaut, der Anteil aber
als Warnung gemeldet.

**Mit der aktuellen Wortliste kommt jede Unit allein aus ihrem Hauptteil auf
60 Wörter** — weder Ergänzungen noch Zusatzteile werden gebraucht. Ein Test
wacht darüber. `vocabmaster db pool <unit>` sagt es vorab.

---

## Aufbau

```
VocabMaster/
├── app.py                        Weboberfläche (Streamlit)
├── data/                         die Excel-Wortliste des Lehrmittels
├── kuratiert/                    ein Paket je Unit
├── src/vocabmaster/
│   ├── config.py                 Einstellungen
│   ├── niveau.py                 Niveau A und B: Bänder und Zielwerte
│   ├── importer.py               Excel → Datenbank
│   ├── database.py               Zugriff auf die Wortliste (JSON + SQLite)
│   ├── pool.py                   Wortauswahl einer Unit (eine Liste)
│   ├── pack.py                   das Unit-Paket: Gerüst, vier Prüfungen
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
Sektionsformen), dafür dass **kein** Wort aus Culture oder Project in eine
Liste rutscht, dass die Prüfung für Niveau A in **jeder** Unit messbar
schwerer ist als die für Niveau B, und dass die erzeugte Prüfung die Vorlage
byteweise übernimmt.

---

## Häufige Fragen

**Bekommen beide Gruppen dieselbe Vokabelliste?**
Ja. Eine Liste je Unit, 60 Wörter, für alle gleich. Unterschiedlich ist nur,
welche davon in der Prüfung abgefragt werden.

**Eine Unit meldet zu wenig Material.**
Der Hauptteil gibt keine 60 geeigneten Wörter her. Dann im Chat ergänzen
(bis 40 %); erst wenn auch das nicht reicht, greift die Anwendung auf die
Zusatzteile derselben Unit zurück und weist sie einzeln aus.

**Kann ich nur die Prüfung für Niveau B neu erzeugen?**
`vocabmaster bauen … --nur test --niveau B`. Vokabelliste und Niveau A
bleiben unberührt.

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
| `VM_MAX_INVENTED` | `0.40` | Anteil ergänzter Wörter, ab dem gewarnt wird |
| `VM_EXAM_WORDS` | `12` | Wörter je Prüfung |
| `VM_EXAM_GAPS` | `4` | Lücken im Lückentext |
| `VM_FONT` | `Century Gothic` | Schriftart der Vokabelliste |
| `VM_FONT_SIZE` | `10` | Schriftgrad der Vokabelliste |
| `VM_ROW_HEIGHT` | `340` | Mindesthöhe einer Tabellenzeile in Twips |
| `VM_SEED` | `20240607` | Zufallsstartwert der Auswahl |

---

## Lizenz

MIT — siehe [LICENSE](LICENSE).
