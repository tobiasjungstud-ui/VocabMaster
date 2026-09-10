# Arbeitsanweisungen für dieses Repository

## Was hier zusammengeführt ist

VocabMaster vereint zwei zuvor getrennte Anwendungen über einer gemeinsamen
Datenbank:

* **VocabListMaker** → `src/vocabmaster/list/` — Wortauswahl, Niveau- und
  Doppelungsprüfung, Beispielsätze, Vokabelliste als Word-Datei.
* **VocabTestMaker** → `src/vocabmaster/exam/` — Prüfung mit
  Übersetzungsteil und Lückentext, zwanzig Kontrollen, Layout der
  Referenzprüfung.

Beide sind bewusst **nahe am Original** übernommen. Wer dort etwas ändert,
ändert gefeintuntes Verhalten — im Zweifel nicht.

## Wie die Inhalte entstehen

Beispielsätze, Lückentexte und ergänzte Wörter werden **im Chat vom Modell
selbst geschrieben**, nicht von der Anwendung erzeugt. Es gibt keine
Mustersätze und keine hartkodierten Beispiele. Die Anwendung wählt aus,
prüft und setzt — sie formuliert nicht.

Ablauf je Unit und Niveau:

1. `vocabmaster gerüst 3` — schreibt `kuratiert/unit_03_A.json` und
   `kuratiert/unit_03_B.json` mit der geprüften Wortauswahl.
2. Im Chat ausfüllen: alle Felder `satz`, fehlende Wörter, die beiden
   Lückentexte in `pruefungen.teil1/teil2 → task2.text`.
3. Die eigenen Sätze selbst noch einmal auf Grammatik, Natürlichkeit,
   Niveau und verratene Lösung durchsehen.
4. `vocabmaster prüfen kuratiert/unit_03_A.json` — bis null Fehler.
5. `vocabmaster bauen kuratiert/unit_03_A.json` — schreibt die Dokumente
   und kontrolliert sie danach.

## Pflicht: Herkunft immer im Chat berichten

Bei **jedem** Durchlauf gehört in die Chat-Antwort, ohne dass danach gefragt
werden muss:

* **Weggelassen** — welche Wörter der Unit nicht in die Listen kamen,
  gruppiert nach Grund (zu einfach für dieses Niveau, Kognat,
  Grundwortschatz, früher gelernt, …).
* **Herkunftsabschnitt** — aus welchem Abschnitt jedes Wort stammt.
  „Steht in der Excel-Datei“ genügt nicht: Ein Wort aus `Culture 7` ist
  etwas anderes als eines aus dem Hauptteil `Unit 7`.
* **Eigene Ergänzungen** — als **eindeutige Tabelle** (Englisch | Deutsch),
  mit Anteil in Prozent. Steht keines darin, wird das ausdrücklich gesagt.
* **Geänderte Übersetzungen** — jede Abweichung von der deutschen Glosse
  der Wortliste, mit Vorher/Nachher.
* **Prüfbericht** — die Zeile je Kontrolle aus `vocabmaster prüfen`.

Das Feld `herkunft` je Eintrag (`"wortliste"` oder `"ergänzt"`) und das Feld
`abschnitt` liefern diese Angaben. Sie stammen aus dem Abgleich mit der
Datenbank, nicht aus dem Gedächtnis.

## Datengrundlage — nur die neue Wortliste

Einzige Quelle ist `data/english_plus_2e_level_4_german_wordlist.xls`
(English Plus 2nd edition, Level 4), importiert nach
`src/vocabmaster/data/wortliste/`. Ältere Wortlisten sind **vollständig
verworfen**; es gibt in diesem Repository keine Rückstände davon.

Der Import löscht Unit-Dateien, die in der neuen Quelle nicht mehr
vorkommen. Die Prüfung `altbestand` schlägt an, sobald ein Wort als
„aus der Wortliste“ ausgegeben wird, das dort nicht steht, oder sobald
die Prüfsumme des Pakets nicht zur Datenbank passt.

Wortliste neu einlesen:

```bash
vocabmaster db import data/english_plus_2e_level_4_german_wordlist.xls
```

Thema und Titel je Unit stehen in `src/vocabmaster/data/themen.json` und
dürfen von Hand geändert werden — der Import liest sie, überschreibt sie nie.

## Umfang einer Unit — verbindlich: nur der Hauptteil

Es zählt **ausschliesslich der Hauptteil** einer Unit, also der Block
`Unit N`. `Culture N`, `Curriculum extra N`, `Project N`, `Literature N` und
`Extra Listening and Speaking Unit N` gehören **nicht** dazu. Das ist die
Voreinstellung (`VM_CORE_ONLY=true`).

Reicht der Hauptteil für zwei überschneidungsfreie Listen nicht aus, gilt
diese Reihenfolge:

1. **Zusatzteile derselben Unit zulassen** — `--mit-zusatzteilen`. Das ist
   immer noch Material des Lehrmittels.
2. Erst danach **im Chat ergänzen**. Ergänzte Wörter müssen:
   * zum Thema der Unit passen (steht in `themen.json`),
   * im Englischen wirklich gebräuchlich sein,
   * im Häufigkeitsfenster des Niveaus liegen,
   * mit keinem Wort beider Listen kollidieren.

**Höchstens 40 % der 60 Wörter einer Liste dürfen ergänzt sein.** Darüber
bricht `vocabmaster prüfen` mit einem Fehler ab.

Stand mit der aktuellen Wortliste, nur Hauptteil: Unit 1 und 2 kommen ohne
Ergänzung aus, Unit 3–8 brauchen 13–47 %. Mit Zusatzteilen bleibt nur
Unit 6 bei wenigen Prozent.

## Niveau A und Niveau B

| Niveau | GER | Zielgruppe | Häufigkeitsfenster (Zipf) |
|---|---|---|---|
| **A** | B1.2–B2.1 | leistungsstärkere Gruppe | 2.45 – 4.60 |
| **B** | A2.2–B1.1 | leistungsschwächere Gruppe | 3.20 – 5.35 |

Die beiden Listen einer Unit sind **überschneidungsfrei** — kein Wort steht
in beiden. Beide behandeln dasselbe Thema, beide schliessen den
A1/A2-Grundwortschatz und blosse Kognate aus.

Die Prüfungsform ist für beide Niveaus dieselbe (8× Übersetzen + 4 Lücken,
12 Punkte), wie in der Vorlage. Unterschiedlich sind Wortauswahl,
Satzlänge, Textlänge und Nebensatzdichte des Lückentextes.

## Layout

Jede Vokabelliste muss auf **eine A4-Seite** passen. Voreingestellt sind
10 pt und Zeilenhöhe 340; die Seitenprüfung rechnet das vorher aus und
meldet Überlauf als Fehler. Beispielsätze möglichst unter 55 Zeichen.

Die Prüfung übernimmt **jeden** Teil des Word-Pakets der Referenzprüfung
(`src/vocabmaster/templates/exam_template.docx`) und schreibt nur
`word/document.xml` neu. Das Layout ist damit byteweise identisch; ein Test
wacht darüber. An der Vorlage wird nichts geändert.

## Tests

`pytest` und `ruff check src app.py tests` müssen grün sein. Die Tests bauen
je genau einen klassischen Fehler ein und verlangen, dass der Selbstcheck
ihn findet. Die mitgelieferten Pakete unter `kuratiert/` werden mitgeprüft
und dürfen keine Fehler zeigen.
