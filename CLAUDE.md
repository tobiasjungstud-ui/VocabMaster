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

Ablauf je Unit:

1. `vocabmaster gerüst 3` — schreibt `kuratiert/unit_03.json` mit der
   geprüften Wortauswahl.
2. Im Chat ausfüllen: alle 60 Felder `satz`, fehlende Wörter und die **vier**
   Lückentexte in `pruefungen.teil1/teil2 → A/B → task2.text`.
3. Die eigenen Sätze selbst noch einmal auf Grammatik, Natürlichkeit,
   Niveau und verratene Lösung durchsehen.
4. `vocabmaster prüfen kuratiert/unit_03.json` — bis null Fehler.
5. `vocabmaster bauen kuratiert/unit_03.json` — schreibt die neun Dokumente
   und kontrolliert sie danach.

## Pflicht: Herkunft immer im Chat berichten

Bei **jedem** Durchlauf gehört in die Chat-Antwort, ohne dass danach gefragt
werden muss:

* **Weggelassen** — welche Wörter der Unit nicht in die Liste kamen,
  gruppiert nach Grund (Grundwortschatz, Kognat, zu selten, früher
  gelernt, …).
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

Reicht der Hauptteil für 60 Wörter nicht aus, gilt **genau diese**
Reihenfolge:

1. **Im Chat ergänzen** — thematisch passende, im Englischen gebräuchliche
   Wörter, die den Wortschatz sinnvoll erweitern und mit keinem Wort der
   Liste kollidieren. Bis zu **40 %** der 60 Wörter.
2. **Erst wenn selbst das nicht reicht**, zieht die Anwendung Wörter aus den
   Zusatzteilen derselben Unit nach — nur so viele wie nötig, um wieder unter
   40 % zu kommen. Jedes einzelne davon steht mit seinem Bereich im
   Prüfbericht und gehört in die Chat-Antwort.

Über 40 % ist eine Ausnahme, kein Fehler: Die Anwendung baut trotzdem, meldet
den Anteil aber als Warnung. Dann besonders sorgfältig gegenlesen.

Stand mit der aktuellen Wortliste: **Jede Unit kommt allein aus ihrem
Hauptteil auf 60 Wörter.** Weder Ergänzungen noch Zusatzteile werden
gebraucht. Ein Test wacht darüber.

## Niveau A und Niveau B — eine Liste, zwei Prüfungen

**Es gibt je Unit genau eine Vokabelliste.** Beide Gruppen lernen dieselben
60 Wörter (Test 1 und Test 2). Es gibt keinen Wortschatz, den nur eine
Gruppe zu Gesicht bekommt.

Unterschieden wird erst bei der **Prüfung**:

| Niveau | GER | Zielgruppe | prüft |
|---|---|---|---|
| **A** | B1.2–B2.1 | leistungsstärkere Gruppe | die zwölf schwersten Wörter des Tests |
| **B** | A2.2–B1.1 | leistungsschwächere Gruppe | die zwölf zugänglichsten Wörter desselben Tests |

Ein **Überschnitt zwischen den beiden Prüfungen ist erlaubt** — es sind
verschiedene Gruppen. Er wird vermerkt; ab der Hälfte gemeinsamer Wörter
gibt es eine Warnung, weil sich die beiden Fassungen dann nicht mehr
unterscheiden.

Wörter, die man aus dem deutschen Stichwort abschreibt („Anekdote" →
`anecdote`), kommen in **keine** Prüfung — auch nicht in die für Niveau B.

Die Prüfungsform ist für beide dieselbe (8× Übersetzen + 4 Lücken,
12 Punkte), wie in der Vorlage. Unterschiedlich sind Wortauswahl,
Satzlänge, Textlänge und Nebensatzdichte des Lückentextes.

Die Beispielsätze der Liste lernen beide Gruppen, deshalb gilt für sie das
engere Mass: **höchstens 13 Wörter je Satz.**

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
und dürfen weder Fehler noch Warnungen zeigen.

Eigene Tests wachen ausserdem darüber, dass **kein Wort aus Culture, Project
oder Curriculum extra** in eine Liste rutscht, dass jede Unit ohne
Ergänzungen auf 60 Wörter kommt, und dass die Prüfung für Niveau A in jeder
Unit messbar schwerer ist als die für Niveau B.
