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
2. Im Chat ausfüllen: alle 60 Felder `satz`, fehlende Wörter und die
   Handarbeit jeder Aufgabe unter `pruefungen.teil1/teil2 → A/B →
   aufgaben` — Lückentexte, Sätze zur Wahl, Umschreibungen, Anstösse.
   `vocabmaster offen <paket>` nennt jedes fehlende Feld mit Aufgabe und
   Nummer.
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

## Mehrere Vokabeldatenbanken

Die Datenbanken stehen in `src/vocabmaster/data/datenbanken.json`; jede ist
ein Name, ein Verzeichnis und eine Zeile zur Einordnung. Eine neue kommt
**ohne Codeänderung** dazu:

```bash
vocabmaster db import level3.xls --name EnglishPlus3 \
    --titel "English Plus 2nd edition, Level 3"
vocabmaster db liste                      # welche es gibt, welche aktiv ist
vocabmaster gerüst 3 --datenbank EnglishPlus3
```

`--datenbank` nimmt **beides**: den Namen einer registrierten Datenbank oder
weiterhin einen Verzeichnispfad. Jede bisherige Aufrufform bleibt damit
gültig, und ohne Angabe kommt wie immer `EnglishPlus4`.

Der Grundeintrag `EnglishPlus4` ist fest im Code hinterlegt und steht auch
dann zur Verfügung, wenn die Registratur fehlt oder unlesbar ist — ein
kaputtes JSON darf die Anwendung nicht lahmlegen. Ein Test wacht darüber.

Jede Datenbank hat ihr eigenes Verzeichnis; ein Import in eine neue fasst
die bestehende nicht an.

Ein **erneuter** Import in eine bestehende behält, was nicht mitgegeben
wird: Wer nur `--name` angibt, meint nicht, dass die von Hand geschriebene
Einordnung weg soll. Eine leere Angabe heisst „nichts gesagt", nicht „leer
machen". Auch die Reihenfolge der Registratur bleibt — sonst steht die
Auswahl nach jedem Import anders da. Zwei Tests wachen darüber.

### Eine Datenbank umbenennen

```bash
vocabmaster db umbenennen EnglishPlus3 --titel "English Plus 2nd edition, Level 3"
vocabmaster db umbenennen EnglishPlus3 --name EP3 --beschreibung ""
```

Geändert wird **nur die Registratur**: Das Verzeichnis bleibt, wo es ist,
die Wortliste darin wird nicht angefasst, und Vokabellisten und Prüfungen
hängen ohnehin an der Prüfsumme, nicht am Namen. `None` heisst „nicht
angegeben", `""` heisst „leer machen" — beim Umbenennen ist eine leere
Einordnung eine Absicht. Eine vergebene Kennung, eine mit Leerzeichen und
die Kennung des Grundeintrags werden abgewiesen: Der ist fest im Code
hinterlegt und käme beim nächsten Lesen unter seinem alten Namen zurück —
zwei Einträge auf dasselbe Verzeichnis. Titel und Einordnung des
Grundeintrags lassen sich ändern.

Auf der Seite steht unter der Datenbankwahl der Griff **„umbenennen"**. Er
öffnet ein Fenster mit den drei Feldern vorbelegt und schreibt daraus den
Auftrag (`art: "umbenennen"`) — die Seite ändert die Registratur nicht
selbst. Sieben Tests.

### Ein Import darf eine gute Datenbank nie beschädigen

Drei Wege, auf denen das passieren könnte, sind zu. Je einer ist als Test
eingebaut (`tests/test_import_sicherheit.py`, 15 Tests):

* **Was keine Wortliste ist, scheitert laut — mit Dateinamen.** Eine leere
  Datei, eine umbenannte Textdatei, eine `.csv`: „`leer.xlsx`: Die Datei ist
  leer." statt eines `BadZipFile`-Tracebacks aus einer Bibliothek. Und eine
  Datei, die zwar parst, aber **keiner einzigen Unit** zuordenbar ist, ist
  keine Wortliste eines Lehrmittels — eher das falsche Tabellenblatt. Daraus
  eine Datenbank zu schreiben hiesse, eine gute durch eine leere zu ersetzen.
* **Geschrieben wird daneben, getauscht wird zuletzt.** `write_database`
  schreibt in ein Schwesterverzeichnis `<name>.neu` und tauscht erst, wenn
  alles da ist. Ein Absturz mitten im Schreiben — Platte voll, Prozess
  abgebrochen — lässt die alte Datenbank Byte für Byte stehen und kein
  halbes `.neu` liegen. `themen.json` und alles, was zur Datenbank gehört,
  aber nicht zum Import, wandert beim Tausch mit.
* **Eine andere Wortliste unter einem Namen, an dem Pakete hängen, wird
  abgewiesen.** Ein Paket gehört zu der Wortliste, deren Prüfsumme es trägt.
  `db import level3.xlsx --name EnglishPlus4` sagt: „Dort liegt schon eine
  andere Wortliste, und 11 Pakete hängen daran: unit_01.json, … Ihre
  Prüfungen zeigten danach auf Wörter, die es nicht mehr gibt." Wer es
  wirklich will, sagt `--ersetzen`; die Pakete melden danach `altbestand`.
  Dieselbe Wortliste noch einmal — nach dem Eintragen der Themen — geht
  ohne Rückfrage. Eine `index.json`, die da ist, aber nicht lesbar, gilt
  als „dort liegt etwas, und man weiss nicht, was" — auch das nur mit
  `--ersetzen`.

Dieselbe Datei unter einem zweiten Namen ist kein Fehler, wird aber
gesagt: „Dieselbe Wortliste ist schon als 'EnglishPlus3' registriert."

### Thema und Leitwörter — je Datenbank eine Datei

`src/vocabmaster/data/<verzeichnis>/themen.json` — **in der Datenbank, zu
der sie gehört.** Das war einmal eine einzige gemeinsame Datei, und das ging
genau so schief, wie es musste: Die zweite importierte Datenbank erbte
Thema, Seitenbereich und Leitwörter der ersten. Unit 3 von English Plus 3
hiess dann „Werbung, Marketing und Konsum", obwohl in ihr `kayaking`,
`skydiving` und `orienteering` stehen — und die Themenkongruenz-Prüfung mass
ein ergänztes Wort am Wortfeld eines **anderen Lehrmittels**.

Der Fehler war nicht laut. Er sah aus wie eine Angabe. Ein Test baut ihn
jetzt nach.

Es gibt deshalb **keine Datei, die für alle gilt**, und keinen Rückfall auf
eine: `load_themes()` ohne Pfad findet nichts. Fehlt einer Datenbank ihre
Datei, bleiben Thema und Leitwörter leer — ehrlich leer ist besser als
fremd gefüllt.

#### Themen ableiten gehört zum Import — Standardverfahren

Die Wortliste eines Lehrmittels nennt kein Thema. Deshalb entsteht beim
Import die `themen.json` als **offene Fächer**, je Unit eines — nach
demselben Muster wie die aufgewerteten Wörter: Das Fach liefert die
**Lage**, nicht das Ergebnis. Darin steht, was in der Wortliste wirklich
steht: Unit-Nummer, Seitenbereich des Hauptteils und ein **Beleg**, die
achtzehn seltensten Wörter der Unit. `go` und `make` stehen in jeder Unit
und sagen nichts; `coasteering` und `orienteering` sagen alles.

Gefüllt werden die Fächer **im Chat**, und zwar bei jedem Import, ohne dass
danach gefragt werden muss:

```bash
vocabmaster --datenbank EnglishPlus3 db themen --offen   # die Fächer mit Beleg
```

Je Unit eine Zeile Thema und acht bis zwölf Leitwörter, die das Wortfeld
aufspannen. **Jedes Leitwort muss in seiner Unit vorkommen** — geprüft
gegen die Wortliste, nicht aus dem Gedächtnis. Dann eintragen und noch
einmal importieren, damit die Unit-Dateien es übernehmen; der Import sagt
selbst, wenn Fächer offen sind. So sind auch die Themen von English Plus 4
entstanden, und so sind die von English Plus 3 entstanden.

Ein geratenes Thema in den Quelltext zu schreiben wäre das Gegenteil davon:
Es sähe aus wie eine Angabe, und jede Unit bekäme dieselbe. Ein Test hält
fest, dass das Gerüst kein Thema erfindet. Eine bestehende Datei wird
**nie** überschrieben — eingetragene Themen sind das Wertvollste daran.

#### Jede Datenbank bringt ihre Units mit

`daten.json` trug einmal genau **eine** Unit-Liste: die der Grunddatenbank.
Das Auswahlfeld schrieb nur eine Zeile in den Auftrag, die Units darunter
blieben dieselben. Wer English Plus 3 wählte, las die Themen von English
Plus 4 — und nichts sagte ihm, dass er das Falsche ansieht.

Jetzt trägt jeder Eintrag in `datenbanken` seine eigenen Units (`units`),
und die Seite liest **eine** Stelle (`einheiten()`), die die der gewählten
Datenbank liefert. Ein Paket gehört zu der Datenbank, deren
**Prüfsumme** es trägt — nicht zu der, deren Unit-Nummer es hat; zwei
Lehrmittel dürfen dieselbe Unit 3 haben. Beim Wechsel fällt das Unit-Feld
auf die erste Unit zurück, die es dort gibt, und die Handarbeit geht weg —
sie bezöge sich sonst auf Wörter eines anderen Lehrmittels.

#### Dieselbe Unit-Nummer, aber nicht dieselbe Datei

Zwei Lehrmittel dürfen dieselbe Unit 1 haben — die Zuordnung hängt an der
Prüfsumme. Die **Dateinamen** hingen allein an der Unit-Nummer: Unit 1 von
English Plus 3 hätte `kuratiert/unit_01.json` und
`Unit01_V1_VocabularyList.docx` von English Plus 4 überschrieben. Paket,
Vokabelliste und vier Prüfungen, stillschweigend — gemerkt hätte man es,
wenn eine Klasse die Wörter eines anderen Lehrmittels abgefragt bekommt.

Ein zweites Lehrmittel trägt deshalb seine Kennung im Namen:

```
kuratiert/unit_01_englishplus3_v2.json
EnglishPlus3_Unit01_V1_VocabularyList.docx
```

Im Paket **hinter** der Unit, damit `unit_*.json` weiterhin greift — danach
sucht jede Stelle, die den Bestand durchgeht. Im Dokument **davor**, weil
man einen Ordner voller Blätter nach Lehrmittel sortiert.

**Die Grunddatenbank behält ihre Namen.** Sonst hiesse jede bestehende
Datei von heute auf morgen anders, und jedes schon ausgeteilte Blatt zeigte
auf einen Namen, den es nicht mehr gibt.

Das Feld `lehrmittel` im Paket ist **nur der Dateiname**; wozu ein Paket
gehört, sagt weiterhin die Prüfsumme. Es wird beim Gerüst einmal notiert
und danach nicht nachgeführt: `db umbenennen` ändert die Registratur, nicht
die Dateien — sonst hiessen die gebauten Blätter nach einer Umbenennung
anders als die, die das Programm sucht. Sieben Tests wachen darüber
(`tests/test_zwei_lehrmittel.py`).

**Eine Unit ohne Vokabelliste ist ein echter Zustand, kein Fehler.** Ein
frisch eingelesenes Lehrmittel hat für keine seiner Units eine, und genau
dort fängt man an. Die Seite zeigt sie trotzdem — mit Hauptteil,
Kennzahlen und der Wortwahl, in der rechts alles steht und links nichts.
Das Häkchen heisst dann „Neue Vokabelliste V1", der Auftrag sagt „die erste
Liste dieser Unit — frisch aus der Datenbank gewählt", nicht „entsteht aus
V0". Die Waage wiegt gegen die 60, auf die jede Liste kommt. Sieben Tests
wachen darüber.

Die Oberfläche liest die Themen nicht mehr aus einer Datei, sondern aus der
geladenen Datenbank (`Database.themen`); dort stehen sie ohnehin, weil der
Import sie in die Unit-Dateien schreibt.

## Schweizer Rechtschreibung — kein ß

Es gilt **Schweizer Rechtschreibung**: kein ß, sondern ss — in Glossen,
Sätzen, Aufgaben, auf der Seite und im Chat. Die Wortlisten der Verlage
schreiben „auf etw. stoßen"; der Import stellt beim Einlesen um
(`importer.schweizerisch`), so tragen Datenbank, Pakete und Blätter
dieselbe Schreibung. Der Listenabdruck rechnet ß und ss gleich — sonst
löste die Umstellung jede Prüfung von ihrer Liste. Ein Test wacht darüber.

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

Thema und Titel je Unit stehen in
`src/vocabmaster/data/wortliste/themen.json` — der Datei **dieser**
Datenbank — und dürfen von Hand geändert werden; der Import liest sie,
überschreibt sie nie.

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
den Anteil aber als Warnung. Dann besonders sorgfältig gegenlesen. Das gilt
auch, wenn die Grenze durch Wörter, Wendungen und Satzanfänge zusammen
überschritten wird — drei Sorten Fächer summieren sich schnell. Ein Test
wacht darüber, dass daraus kein Fehler wird.

Stand mit der aktuellen Wortliste: Unit 1, 2, 3, 7 und 8 kommen ohne
Ergänzung aus; Unit 4 braucht 2 Wörter, Unit 5 vier, Unit 6 fünfzehn (25 %).
Zusatzteile werden nirgends gebraucht. Ein Test wacht darüber.

## Niveau A und Niveau B — eine Liste, zwei Prüfungen

**Es gibt je Unit genau eine Vokabelliste.** Beide Gruppen lernen dieselben
60 Wörter (Test 1 und Test 2). Es gibt keinen Wortschatz, den nur eine
Gruppe zu Gesicht bekommt.

Unterschieden wird erst bei der **Prüfung**:

| Niveau | GER | Zielgruppe | prüft |
|---|---|---|---|
| **A** | B1.2–B2.1 | leistungsstärkere Gruppe | die zwölf schwersten Wörter des Tests |
| **B** | A2.2–B1.1 | leistungsschwächere Gruppe | die zwölf zugänglichsten Wörter desselben Tests |

### Was als bekannt gilt

Der Klassenschnitt liegt bei **B1.1–B1.2**, sechstes Englischjahr. Was eine
solche Klasse schon kann, ist kein Prüfstoff — und Häufigkeit allein trennt
das nicht: `happily` ist mit Zipf 4.11 **seltener** als `lock` mit 4.51, und
beide sind längst bekannt.

Die Arbeit leistet deshalb `src/vocabmaster/list/data/a1_a2_core.txt`
(rund 1500 Einträge, A1 bis B1.1) samt zwei Regeln:

* **Ableitungen sind gratis.** Wer `happy` kennt, kennt `happily`; wer
  `active` kennt, kennt `actively`. Ausnahmen, bei denen sich die Bedeutung
  verschiebt (`hardly`, `lately`), stehen in `_LY_AUSNAHMEN`.
* **Häufigkeitsgrenze 4.75** — das grobe Sieb darüber.

Ein Wort, das dennoch durchrutscht: eine Zeile in `a1_a2_core.txt`
ergänzen. Mehrwortausdrücke dort **kommagetrennt** schreiben, sonst
zerfallen sie in Einzelwörter.

Ein **Überschnitt zwischen den beiden Prüfungen ist erlaubt** — es sind
verschiedene Gruppen. Er wird vermerkt; ab der Hälfte gemeinsamer Wörter
gibt es eine Warnung, weil sich die beiden Fassungen dann nicht mehr
unterscheiden.

Wörter, die man aus dem deutschen Stichwort abschreibt („Anekdote" →
`anecdote`), kommen in **keine** Prüfung — auch nicht in die für Niveau B.

Das **Blatt für Niveau B trägt „Niv. B" im Kopf**, neben `Part I`
beziehungsweise `Part II`; das für Niveau A trägt keinen Zusatz. Es ist die
Normalform, dieselbe Klasse bekommt nie beide zu sehen, und wer austeilt,
muss die B-Blätter auf einen Blick erkennen.

Die Prüfungsform ist für beide dieselbe — voreingestellt 8× Übersetzen und
4 Lücken, 12 Punkte, wie in der Vorlage; welche Aufgaben sie hat, steht
unter „Der Aufbau der Prüfung". Unterschiedlich sind Wortauswahl,
Satzlänge, Textlänge und Nebensatzdichte des Lückentextes.

Die Beispielsätze der Liste lernen beide Gruppen, deshalb gilt für sie das
engere Mass: **höchstens 13 Wörter je Satz.**

## Eine Liste, die gegeben ist statt gewählt

Der Normalfall ist, dass die Anwendung die 60 Wörter aus der Datenbank
wählt. Eine Liste kann aber auch **fertig hereinkommen** — aus dem
Word-Dokument der Lehrperson, mit eigener Aufteilung in Test 1 und Test 2
und eigenen Beispielsätzen. Dann steht im Paket, woher:

```json
"liste_gegeben": "Word-Dokument 'Vocabulary Unit 8 (updated)' der Lehrperson …"
```

Das ist keine Formalie. Drei Kontrollen beurteilen die **Wahl** der Wörter —
wie viele auf einen Test kommen (`falsche_anzahl`) und ob zwei davon
dasselbe prüfen (`doppelung`, `ueberschneidung`). Bei einer gegebenen Liste
beurteilen sie eine Wahl, die niemand getroffen hat: Wer `adapt` und
`adaptation` nebeneinander auf die Liste setzt, meint das so, und 29 Wörter
in Test 1 sind 29 Wörter. Sie werden weiterhin **gesagt** — als Warnung mit
dem Zusatz „gegebene Liste — gesagt, nicht beanstandet" —, halten den Bau
aber nicht auf. Sonst liesse sich die eigene Liste der Lehrperson gar nicht
bauen.

**Alles andere bleibt ein Fehler.** Ein Eintrag ohne Wort, eine fehlende
Übersetzung, ein Satz, der die Lösung verrät, eine Liste, die nicht auf die
A4-Seite passt — das sind Mängel in jeder Liste, gewählt oder gegeben. Und
was an der Prüfung hängt (Listenabdruck, Lösungsschlüssel, Aufgabenformen,
Platzhalter) wird unverändert scharf geprüft.

`ausgleichen` wird auf eine gegebene Liste **nicht** angewendet: Es würde
die Aufteilung neu würfeln, und die stammt von der Lehrperson.

Ein Test hält fest, dass ein solches Paket nicht an der 60 scheitert,
sondern daran gemessen wird, ob jeder Eintrag Wort, Übersetzung und Satz
hat.

## Welche Liste meint dieser Test?

Das ist die Frage, die sich zwei Tage nach dem Bauen stellt. Jede
Vokabelliste trägt deshalb einen Code — **V1, V2, V3** — und zwar im
Dateinamen von allem, was zu ihr gehört:

```
Unit01_V1_VocabularyList.docx
Unit01_V1_Test_PartI_NiveauA.docx
Unit01_V2_VocabularyList.docx            ← andere Liste, eigene Prüfungen
Unit01_V2_Test_PartI_NiveauA_Fassung2.docx
```

Dazu trägt **jede Prüfung den Fingerabdruck ihrer Liste** im Paket
(`meta.liste_fingerabdruck`, eine Kurzform über alle 60 Wortpaare;
Beispielsätze zählen nicht mit). Die Kontrolle `listenbezug` schlägt an,
sobald eine Prüfung zu einer Liste gehört, die nicht mehr im Paket liegt —
denn dann zeigt ihr Lösungsschlüssel auf Wörter, die es dort nicht gibt.
Das ist der teuerste Fehler, den dieses Programm machen kann, und er fällt
sonst erst beim Korrigieren auf.

```bash
vocabmaster listen        # welche Listen es je Unit gibt, mit Abdruck
```

## Eine neue Vokabelliste — frisch gewählt, nicht geflickt

```bash
vocabmaster liste-neu kuratiert/unit_01.json --fancy 8
```

Das schreibt `kuratiert/unit_01_v2.json`. Entscheidend: Die Auswahl wird
**neu aus der Datenbank getroffen**. Würde stattdessen V1 kopiert und ein
paar Wörter getauscht, bliebe die Frage „welche 60 Wörter dieser Unit sind
die lehrreichsten?" für immer einmal beantwortet.

Wörter, die in einer früheren Liste der Unit schon vorkamen, werden dabei
leicht abgewertet (`pool._NEUHEITS_BONUS`) — **abgewertet, nicht
ausgeschlossen**. Denn der Hauptteil gibt selten viel mehr her als die 60
gebrauchten Wörter:

| Unit | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **Reserve im Hauptteil** | 8 | 17 | 8 | 0 | 0 | 0 | 1 | 0 |

In Unit 4, 5, 6 und 8 ist er ausgeschöpft: Dort unterscheidet sich eine
zweite Liste **nur** durch die aufgewerteten Wörter. Der Befehl schreibt
hin, wie viele Wörter tatsächlich neu sind.

Der Zuschlag ist gemessen, nicht geraten — 0.50 löst die Reserve
grösstenteils ein und kostet rund zwei Prozent Lernwert; darüber wird es
rasch teurer, ohne viel mehr zu bringen. Die Tabelle steht im Quelltext.

**Beispielsätze wandern mit**, wo dasselbe Wort schon einen hatte: Ein Satz
gehört zum Wort, nicht zur Liste. In Unit 1 sind das rund 53 von 60.
**Lückentexte wandern nicht mit** — sie gehören zu ihren vier Lücken, und
die sind bei einer anderen Liste andere.

## Aufgewertete Wörter („fancy")

Die Liste bleibt bei **60 Wörtern** — sie muss auf eine A4-Seite passen —,
also tritt jedes aufgewertete Wort an die Stelle des zugänglichsten der
frischen Auswahl. Das sind zuverlässig die Abschreibwörter: in Unit 1
`document`, `anecdote`, `theme park`, `picnic`, `romantic`.

### Der Massstab steht nicht im Programm

`--fancy N` öffnet N Fächer, die **im Chat** gefüllt werden. Das Fach
liefert die **Lage**, nicht das Ergebnis: Wortfeld der Unit, Leitwörter,
Niveauband, und welches Wort mit welcher Prüfnote gewichen ist.

### Drei Arten von Fächern

Ein Einzelwort, eine Wendung und ein Satzanfang werden nach denselben
Massstäben gewählt, aber es sind **verschiedene Bestellungen**: Wer acht
Wörter will, will nicht acht Redewendungen.

| Flagge | Art | was hineingehört |
|---|---|---|
| `--fancy N` | `wort` | ein einzelnes Wort |
| `--ausdrücke N` | `ausdruck` | eine Wendung aus mehreren Wörtern — Phrasal Verb, feste Verbindung, Redewendung |
| `--chunks N` | `chunk` | ein Satzanfang zum Weiterschreiben; die Fortsetzung schreibt die Klasse |

Jedes Fach trägt seine Art im Feld `art` und nennt sie in seinem `hinweis`.
Bei `--wort` wird die Art an der Schreibung erkannt: Auslassungspunkte am
Ende machen einen Satzanfang, mehrere Wörter eine Wendung, alles andere ein
Einzelwort. Auf der Werkstatt-Seite stehen dafür drei Zählfelder
nebeneinander.

Wonach ausgewählt wird, gehört ausdrücklich **nicht** in den Quelltext.
Steht dort erst einmal ein Kriterienkatalog mit Musterwörtern, bekommt jede
Unit dieselbe Antwort zurück — dieselben fünf Adjektive für Werbung wie für
Bauwerke. Was ein Wort hier verdient, entscheidet sich am Wortfeld dieser
Unit, an dem, was schon in der Liste steht, und daran, was der Klasse an
Ausdruck wirklich fehlt. Das ist eine Überlegung, keine Tabelle.

Ein Test wacht darüber (`tests/test_keine_schablonen.py`). Er hat schon
einmal angeschlagen.

Die Begründung je Wort gehört ins Feld `begruendung` — die Themenkontrolle
liest sie, und sie bleibt im Paket nachlesbar.

`--wort` nimmt die Angabe in beiden Richtungen (`englisch=deutsch` wie
`deutsch=englisch`); erkannt wird sie an der Schreibung. Wo das nicht reicht
(`rot=red`), wird **nicht geraten**, sondern zurückgefragt; eindeutig ist
`en:<wort>=<Wort>`.

## Nur bauen, was bestellt ist

Der Auftrag aus der Werkstatt nennt in seinem **ersten Satz**, was entstehen
soll, und in seinem letzten die Stückzahl. Steht dort „Unit 1: die
Vokabelliste. … Nur die Vokabelliste — keine Prüfungen, keine Lückentexte.
… Erwartet: die Vokabelliste — 1 Datei", dann ist genau **eine** Datei zu
bauen.

Sätze wie „künftige Prüfungen dieser Unit beziehen sich dann auf V2" sagen,
woran eine später bestellte Prüfung hängen wird — sie sind **keine
Bestellung**. Wer sie als eine liest, liefert acht ungefragte Dokumente. Das
ist einmal passiert; daher steht die Stückzahl jetzt ausgeschrieben im
Auftrag.

Ein Paket enthält immer die Gerüste aller vier Prüfungen — das ist seine
Form. Ob daraus Dokumente werden, entscheidet `bauen --nur liste`
beziehungsweise `--nur test`, nicht die Form der Datei.

`--niveau` und `--teil` grenzen weiter ein. Wer **eine** Prüfung bestellt
hat, baut sie einzeln:

```bash
vocabmaster bauen kuratiert/unit_01.json --nur liste
vocabmaster bauen kuratiert/unit_01.json --nur test --niveau A --teil 1
```

Das sind drei Dateien — die Vokabelliste, das Blatt und sein Lösungsblatt.
Ohne `--teil` wären es fünf gewesen. `--blatt a5` ändert daran nichts (das
Doppelblatt ersetzt das A4-Blatt), `--blatt beide` legt je Prüfung eine
Datei dazu.

## Der Bestand als Ganzes

`vocabmaster prüfen` sieht immer nur **ein** Paket. Was sich erst im
Nebeneinander zeigt, fällt dort durch. `vocabmaster listen` prüft deshalb
den ganzen Ordner:

* zwei Pakete, die auf dieselben Word-Dateien zielen (**Fehler** — sie
  überschreiben sich),
* eine Fassung zu einer Liste, die es nicht gibt (**Fehler**),
* eine Prüfung, die am Abdruck einer anderen Liste hängt (**Fehler**),
* zwei Listen einer Unit mit identischem Inhalt (**Warnung** — keine zwei
  Listen),
* eine Lücke in der Versionsnummerierung (**Warnung**).

## Fassungen einer Prüfung

Es gibt keine „Nachschreibfassung" und keine Sonderrolle für die erste. Es
sind fortlaufende Fassungen derselben Prüfung — **jede mit Nummer, Datum und
Listenabdruck hinterlegt**, jede in ihrer eigenen Datei:

```bash
vocabmaster fassung kuratiert/unit_01.json --teil 1 --niveau A
```

Ohne `--nummer` entsteht die nächste freie. Die Datei heisst
`kuratiert/unit_01_fassung3.json`, die Dokumente
`Unit01_V1_Test_PartI_NiveauA_Fassung3.docx`. Bestehende Fassungen werden
nie überschrieben; `vocabmaster listen` zeigt alle.

### Mehrere auf einmal — drei Reihen, drei Blätter

```bash
vocabmaster fassung kuratiert/unit_01.json --teil 1 --niveau A --anzahl 3
```

Das legt **Fassung 2, 3 und 4** an, fortlaufend ab der nächsten freien.
Jede bekommt die vorherigen als „frühere Fassungen" mit, deshalb teilt
jede **anders auf**: andere vier der zwölf Wörter werden Lücke. Der Befehl
sagt danach, ob das aufging — „Alle 3 Fassungen teilen verschieden auf"
oder, wenn die Unit nicht mehr hergibt, „Die Rotation ist ausgeschöpft;
dann muss der Lückentext den Unterschied allein tragen".

`--nummer` und `--anzahl` schliessen sich aus: Mehrere Fassungen bekommen
fortlaufende Nummern, nicht alle dieselbe.

**Der Lückentext ist die zweite Hälfte der Arbeit und bleibt Sache des
Chats.** Frisch angelegt tragen alle Fassungen denselben Platzhalter — das
ist der offene Zustand, kein Fehler. Sobald aber zwei geschriebene Texte
gleich sind, meldet `vocabmaster listen` **FEHLER**: „… haben denselben
Lückentext - das ist zweimal dieselbe Prüfung." Gleiche Aufteilung bei
verschiedenem Text ist eine **WARNUNG** — die Unit hat dann nicht mehr
hergegeben.

Auf der Seite steht das Zählfeld **„Wie viele Fassungen auf einmal"** unter
der Fassungswahl. Es erscheint überall dort, wo etwas Neues entsteht: bei
„＋ neue Fassung erstellen" und bei einer **neuen Vokabelliste**. Zu einer
neuen Liste ist die Fassungswahl selbst weg — ihre Prüfungen sind
zwangsläufig ihre ersten, und `naechsteFassung()` gibt dort die **1**
zurück. Ohne diese Regel bekäme eine frische V3 die Nummer „Fassung 4",
weitergezählt aus der Geschichte von **V1** — und ihr Lösungsschlüssel
zeigte auf Wörter einer anderen Liste. Die Stückzahl im Auftrag
vervielfacht die Prüfungen mit, die Vokabelliste nicht.

### Überschneidungen sind erlaubt

**Das ist keine Ausnahme, sondern die Regel.** Alle Fassungen prüfen
dieselbe Vokabelliste, und die zwölf schwersten Wörter bleiben die zwölf
schwersten — egal wie oft man sie abfragt. Es gibt deshalb **keine
Obergrenze** für den Überschnitt. Er wird berichtet, nicht verhindert.

Frühere Fassungen wirken nur noch als **Stichentscheid unter gleich schweren
Wörtern**: Bei gleicher Note kommt das noch nicht geprüfte zuerst. Sie
dürfen eine Fassung niemals leichter machen. Eine Prüfung, die `teddy bear`
(0.2/10) abfragt, weil die guten Wörter „schon vergeben" waren, ist keine
Prüfung für Niveau A mehr — das war der Fehler, aus dem diese Regel stammt.

Was eine Fassung unterscheidet, ist zweierlei:

* **der Lückentext** — im Chat neu geschrieben, und
* **die Aufteilung**: welche der zwölf Wörter Lücke werden und welche
  Übersetzung, wird je Fassung durchgeschoben. Ob ein Wort eingesetzt oder
  übersetzt wird, sagt über seine Schwierigkeit nichts — diese Variation
  kostet keinen Punkt Anspruch.

## Der Aufbau der Prüfung — sechs Aufgabenarten, eine Wortzahl

Eine Prüfung war einmal zwei feste Aufgaben. Das ist eine Form, keine
Notwendigkeit: Übersetzen prüft, **was** ein Wort heisst, Einsetzen,
**wo** es hingehört. Was eine Klasse darüber hinaus können muss, prüft
keines von beiden.

Die Prüfung ist deshalb eine **Liste von Aufgaben**. Angekreuzt wird, was
sie enthält; die Wortzahl verteilt sich darauf.

| Kennung | Aufgabe | Gewicht | mind. |
|---|---|---|---|
| `uebersetzen` | Tabellen-Übersetzung — deutsches Stichwort, englisches Wort hinschreiben | 4 | 1 |
| `luecken` | Lückentext mit Wortbank | 2 | 2 |
| `wortwahl` | Wortbedeutung — **drei** Sätze je Wort, zwei mit falscher Verwendung | 2 | 1 |
| `definition` | Definition — eine englische Umschreibung, das Wort ist hinzuschreiben | 2 | 1 |
| `richtig_falsch` | Correct / Incorrect Use — **zwei** Sätze, nur einer stimmt | 2 | 1 |
| `schreiben` | Micro-Writing — zwei bis drei Wörter in einem kurzen Text | 1 | 2 |

```bash
vocabmaster gerüst 3 --aufgaben uebersetzen,luecken,definition --woerter 15
vocabmaster gerüst 3 --aufgaben uebersetzen,luecken --je-aufgabe luecken=6
vocabmaster fassung kuratiert/unit_01.json --teil 1 --niveau A \
    --aufgaben uebersetzen,wortwahl,schreiben
```

### Wer nichts umstellt, bekommt die Prüfung von gestern

Voreingestellt sind die beiden klassischen Arten, und **die Gewichte 4 und
2 sind genau dafür gewählt**: Zwölf Wörter ergeben weiterhin acht zum
Übersetzen und vier Lücken. Die mitgelieferten Pakete tragen noch
`task1`/`task2`; sie werden über denselben Adapter gelesen wie die neue
Liste und ergeben **Byte für Byte dasselbe Dokument**. Zwei Tests wachen
darüber — einer über die Gewichte, einer über alle 76 Dokumente unter
`kuratiert/`.

### Der Aufbau steht im Paket, nicht in den Einstellungen

Jede Prüfung trägt ihren bestellten Aufbau in `aufgabenplan` — welche
Aufgaben, mit wie vielen Wörtern. Alles, was die Prüfungen später **neu
aufsetzt**, liest ihn von dort:

`vocabmaster ausgleichen` ist nach dem Ergänzen von Wörtern nötig und setzt
dabei alle vier Prüfungen neu. Es las den Aufbau aus den Einstellungen — und
die stehen ohne Flaggen auf der Vorgabe. Eine mit sechs Aufgaben bestellte
Prüfung fiel danach stillschweigend auf Übersetzen und Lückentext zurück;
gemerkt hätte man es erst am gebauten Blatt.

Gelesen wird der **bestellte** Plan, nicht das, was in den Aufgaben steht:
Ein Gerüst, dessen Wörter noch im Chat zu ergänzen sind, hat noch nicht
genug zu verteilen. Würde der Aufbau von dort abgelesen, schrumpfte die
Prüfung auf das, was sie im halbfertigen Zustand hatte. Ein Paket ohne das
Feld — eines von vor dieser Angabe — sagt es weiterhin über seine Aufgaben.
Zwei Tests wachen darüber.

### Zwei Lücken sind der Normalfall

Die Wortbank darf weder in Lückenreihenfolge noch in deren Umkehrung
stehen — beides liesse die Aufgabe lösen, ohne den Text zu lesen. Bei
**zwei** Lücken gibt es aber nur diese beiden Reihenfolgen: Die Schleife
lief fünfzigmal ins Leere und liess die Bank in Lückenreihenfolge stehen,
was der geerbte Checker als Fehler meldete. Unter drei Lücken wird deshalb
nur die Lückenreihenfolge gemieden; mehr gibt die Aufgabe nicht her. Ein
Test wacht darüber.

### Die Verteilung

Proportional zum Gewicht, der Rest nach dem grössten Bruchteil, und was
darunter unter seine Mindestzahl fiele, wird darauf angehoben. Zweimal
dieselbe Eingabe gibt zweimal dasselbe.

**Von Hand Gesetztes kommt aus der Gesamtzahl, nicht obendrauf.** Wer
`luecken=6` festnagelt, verschiebt die sechs aus dem Budget der übrigen;
die Summe bleibt, wo der Regler steht. Andernfalls stiege sie bei jedem
Festnageln, und die Zahl oben zeigte etwas anderes an als die Summe
darunter.

`--ohne-verteilung` schaltet das Verteilen ab: Dann zählt nur, was je
Aufgabe dasteht, und der Rest bekommt seine Mindestzahl.

### Kein Wort steht in zwei Aufgaben

Die eine Aufgabe fragt ein Wort ab (übersetzen, einsetzen, umschreiben),
die andere druckt es aus (Satzwahl, Micro-Writing). Stünde dasselbe Wort
in beiden, läge die Lösung der einen in der anderen offen — und das fällt
erst beim Korrigieren auf. Die Wörter werden deshalb **einmal** gewählt
und dann auf die Aufgaben verteilt.

Die Wortwahl der Lücken bleibt, wie sie war: je Lücke eine andere Wortart,
je Fassung durchgeschoben. Was sie übrig lässt, wird der Reihe nach
ausgeteilt.

### Was die Anwendung prüft und was nicht

Die Kontrolle `aufgabenformen` prüft die **Form**:

| Befund | Stufe |
|---|---|
| zu wenige Sätze zur Wahl (drei bzw. zwei) | FEHLER |
| die Lösung zeigt auf keinen der Sätze | FEHLER |
| ein Wort wird auf demselben Blatt zweimal geprüft | FEHLER |
| ein ausgedrucktes Wort ist anderswo die Lösung | FEHLER |
| zwei der Sätze sind derselbe | FEHLER |
| in **keinem** Satz steht das Wort | FEHLER |
| die Umschreibung enthält das gesuchte Wort | FEHLER |
| zweimal dieselbe Umschreibung | FEHLER |
| ein Mini-Text mit einem einzigen Wort | FEHLER |
| in einem Satz ist das Wort nicht zu erkennen | WARNUNG |
| ein Satz oder eine Umschreibung ist länger als das Niveauband | WARNUNG |
| mehr als drei Wörter in einem Mini-Text | WARNUNG |
| der richtige Satz fällt schon durch seine Länge auf | HINWEIS |

Die gebeugte Form bleibt bewusst eine **Warnung**: Die Anwendung
konjugiert nicht. Sie findet `begged` zu `beg`, aber nicht `came` zu
`come`, und ein Fehlalarm auf einem richtigen Satz wäre schlimmer als ein
übersehener.

**Was sie nicht prüfen kann, ist die Sache selbst**: ob die anderen Sätze
das Wort wirklich falsch verwenden, ob die Umschreibung genau dieses Wort
meint. Das sind Sprachentscheidungen und bleiben beim Gegenlesen im Chat.
Der Prüfbericht sagt das ausdrücklich, damit ein Häkchen nicht mehr
verspricht, als es hält.

Der geerbte Checker des VocabTestMaker bleibt **unangetastet**. Er hat
seine zwanzig Kontrollen für task1 und task2 geschrieben und bekommt
deshalb `klassische_sicht(spec)` — die Aufgabenliste, auf seine beiden
Schlüssel gestutzt, samt der Wortzahl, die zu **seiner** Sicht gehört.

### Auf dem Blatt

Die Aufgaben stehen in der Reihenfolge des Katalogs und werden beim Setzen
**neu nummeriert**: Fällt das Übersetzen weg, ist der Lückentext Aufgabe 1.
Geändert wird dabei nur die Ziffer, der Rest der Aufgabenstellung bleibt
Zeichen für Zeichen stehen — samt der Zahl der Leerzeichen dahinter, denn
ein Dokument, das sich in einem Leerzeichen unterscheidet, ist nicht mehr
dasselbe Dokument.

Keine der neuen Arten braucht eine **Tabelle**: Das Referenzlayout hat
genau zwei, den Kopf und die Übersetzungstabelle, und eine Kontrolle zählt
sie. Ein Punkt je geprüftem Wort.

Auf dem Lösungsblatt steht der richtige Satz fett und darunter
`Solution: b)`; bei Micro-Writing steht dort, **woran** korrigiert wird —
einen Lösungsschlüssel kann es da nicht geben.

Eine Lücke ist ein Strich aus genau 26 Unterstrichen. Die Schreiblinie
eines Mini-Textes ist länger, und `count` fand in ihr gleich drei Lücken —
das Blatt meldete zwölf, wo sechs standen. Gezählt wird deshalb der Strich
in seiner genauen Länge.

**Die Seitenschätzung rechnet jede Art mit.** Sechs Arten passen nicht auf
eine A4-Seite; die Nachkontrolle sagt es und nennt den Grund.

### Auf der Seite

Unter „Aufbau der Prüfung" steht der Regler für die Gesamtzahl, darunter
die sechs Häkchen mit ihrer Wortzahl. Eine getippte Zahl **nagelt fest**
(sie steht dann farbig da), die übrigen wandern weiter mit; „zurücksetzen"
löst alle wieder. Das Häkchen „Auf die Aufgaben verteilen" schaltet die
Umverteilung ab.

**Die Seite rechnet die Verteilung nicht selbst.** Sie steht fertig in
`daten.json` — 1701 Einträge für jede Kombination mal jede Wortzahl,
ausgerechnet von derselben Stelle, die sie beim Bauen anwendet. Eine
zweite Fassung davon in JavaScript liefe irgendwann auseinander, und die
Seite zeigte eine Prüfung, die so nie gebaut wird. Aus demselben Grund
kennt die Seite **keine Aufgabenart**: Sie liest den Katalog
(`DATA.aufgabenarten`). Ein Test wacht über beides.

Die Prüfungskarte unter „Prüfungen ansehen" zeigt jede Aufgabe so, wie sie
auf dem Blatt steht — mit markierter Lösung und mit „— noch nicht
geschrieben —" dort, wo etwas fehlt.

## Wiederholung aus dem vorherigen Vocabulary — zuschaltbar

Voreingestellt **aus**. Eingeschaltet fragt jede Prüfung zusätzlich Wörter
aus dem Vocabulary ab, das unmittelbar davor behandelt wurde — als
Übersetzungstabelle (deutsch → englisch) am Ende des Blatts.

| Niveau | Wörter | zählt |
|---|---|---|
| **A** | 4, die schwersten | mit: Höchstpunktzahl 12 + 4 = 16P |
| **B** | 2, die zugänglichsten | als **Bonus** (`+2P`): kann die Note verbessern, nicht verschlechtern; die Höchstpunktzahl bleibt |

### Welche Liste ist „die vorherige"?

Die Folge läuft über Units und Parts hinweg: Unit 1 · Part II ← Unit 1 ·
Part I, Unit 2 · Part I ← Unit 1 · Part II, Unit 2 · Part II ← Unit 2 ·
Part I. Gerechnet wird über **alle Units des Lehrmittels** (aus seiner
Datenbank), nicht nur über die, zu denen es eine Liste gibt: Fehlt dem
vorherigen Part die Liste, wird **nicht** stillschweigend der vorletzte
vorgeschlagen, sondern gesagt, dass er fehlt.

* Part II wiederholt Part I **derselben** Liste.
* Part I wiederholt Part II der vorigen Unit. Hat die mehrere Listen, kommt
  zuerst die, zu deren Part schon eine Prüfung gebaut ist, dann die mit
  gebauter Vokabelliste, dann die neueste — die Klasse hat die gelernt, die
  ausgeteilt wurde.

Der Vorschlag lässt sich wechseln (frühere Parts, andere Lehrmittel), steht
dann aber als „nicht der vorherige Part" da. Unit 1 · Part I hat keinen
Vorgänger mit Liste (die Starter Unit hat keine): Dort ist „keine
Wiederholung" voreingestellt, eine andere Liste ist eine Wahl, kein
Vorschlag.

### Welche Wörter

Gewählt wird mit derselben Stelle wie die Prüfungswörter
(`waehle_pruefungswoerter`). Ausgeschlossen sind Wörter des aktuellen
Parts samt Wortfamilie und jedes Wort, das **auf dem Blatt schon gedruckt
steht** — im Lückentext, in einem Satz zur Wahl. Das hat der erste
Probelauf gefunden: `picnic` stand als Wiederholung im Schlüssel und
zugleich im Lückentext von Unit 2.

### Wo es steht, und wer es prüft

Der Block liegt **neben** den Aufgaben (`spec["wiederholung"]`), nicht
darin: Aufgabenplan, Lösungsschlüssel und der geerbte Checker sehen ihn
nicht, und ein Blatt ohne Wiederholung ist Byte für Byte das von vorher.
Er trägt Paket, Part, Listenversion, Listenabdruck und Prüfsumme der
Quelle. `ausgleichen` und `fassung` tragen ihn mit.

Die Kontrolle `wiederholung` liest die **Quellliste neu ein** und prüft
jedes Wort dagegen: steht es dort in diesem Part, mit dieser Übersetzung;
passt der Abdruck noch; ist es kein Wort des aktuellen Parts, nicht
doppelt, nicht auf dem Blatt gedruckt; stimmt die Bonus-Kennung zum
Niveau. Das sind Fehler. Eine andere Wortzahl, eine Quelle, die nicht der
vorherige Part ist, oder Part I einer anderen Listenversion sind
Warnungen — gewählt ist gewählt, aber gesagt wird es.

```bash
vocabmaster wiederholung kuratiert/unit_02.json --teil 1 --vorschlag   # nur zeigen
vocabmaster wiederholung kuratiert/unit_02.json --teil 1               # Vorschlag setzen
vocabmaster wiederholung kuratiert/unit_02.json --teil 1 --wahl 2      # zweiten nehmen
vocabmaster wiederholung kuratiert/unit_02.json --teil 1 \
    --aus kuratiert/unit_01.json --aus-teil 2
vocabmaster wiederholung kuratiert/unit_02.json --teil 1 --weg
```

Ohne Vorschlag (Unit 1 · Part I) setzt der Befehl nichts und listet die
Möglichkeiten.

Auf dem A4-Blatt kann die Wiederholung auf eine zweite Seite rutschen -
das ist ausdrücklich in Ordnung (Wunsch der Lehrperson). Auf dem
Doppelblatt kommt sie dann aufs zweite Blatt (siehe unten).

Auf der Seite steht das Häkchen unter „Aufbau der Prüfung", darunter je
bestelltem Teil die Quellwahl — die Vorschläge rechnet `export.py` mit
derselben Stelle aus, die Seite kennt die Folge nicht selbst. 40 Tests
in `tests/test_wiederholung.py`, vier in `tests/test_werkstatt.py`.

## Blattformat: A4 oder 2 × A5 zum Halbieren

Eine Prüfung kommt entweder wie bisher auf ein A4-Blatt, oder **zweimal auf
ein A4-Blatt quer**: zwei gleich breite Spalten, links und rechts genau
dasselbe. In der Mitte geschnitten, werden aus einem Blatt zwei
A5-Prüfungsblätter.

```bash
vocabmaster bauen kuratiert/unit_02.json --nur test --blatt a5      # nur 2 × A5
vocabmaster bauen kuratiert/unit_02.json --nur test --blatt beide   # A4 und 2 × A5
```

Die Datei heisst `Unit02_V1_Test_PartI_NiveauA_2xA5.docx`, liegt neben dem
A4-Blatt und überschreibt es nie. **Das Lösungsblatt bleibt A4** - es
liegt beim Korrigieren auf dem Tisch, nicht in der Klasse. Voreingestellt
ist `a4`; wer nichts umstellt, bekommt Byte für Byte das Blatt von gestern.

### Links und rechts ist immer dasselbe - auch über zwei Blätter

Passt eine Prüfung nicht auf eine halbe Seite (sechs Aufgabenarten, die
Wiederholung dazu), dann wird sie **auf mehrere A5-Seiten** verteilt, und
jede davon steht wieder zweimal nebeneinander:

```
Blatt 1:  | Seite 1 | Seite 1 |
Blatt 2:  | Seite 2 | Seite 2 |
```

Umbrochen wird **zwischen** zwei Aufgaben, nie mitten in einer. Weil links
und rechts gleich sind, geht auch der beidseitige Druck auf, gleich wie das
Blatt gewendet wird: nach dem Schnitt ein A5-Blatt je Schülerin und
Schüler, vorn Seite 1, hinten Seite 2.

Das war der erste Fehler dieser Funktion, und die Lehrperson hat ihn
gefunden: Eine lange Prüfung floss einmal aus der linken Spalte in die
rechte - links und rechts standen dann verschiedene Hälften. Eine
**Schnittlinie** wird nicht gedruckt; die Mitte findet die
Schneidemaschine selbst.

Nicht setzen lässt sich nur eine **einzelne** Aufgabe, die schon für sich
höher ist als eine halbe Seite; ihr Doppelblatt wird nicht geschrieben
(FEHLER, mit dem Rat `--blatt a4`).

### Derselbe Inhalt, nicht ein zweiter Setzer

`exam/doppelblatt.py` nimmt das `document.xml`, das der Setzer für das
A4-Blatt schreibt, und formt es nur um: 10 statt 12 pt, Tabellen auf die
Spaltenbreite (12.45 cm), Zeilenhöhe 480 statt 680, Punktzahl rechtsbündig
statt hinter fünf Tabulatoren, Rand aussen 12 mm und zwischen den Spalten
24 mm - so hat nach dem Schnitt jede Hälfte links und rechts denselben
Rand. `styles.xml` und alles andere der Vorlage bleiben unangetastet. Der
Lückentext behält seinen 1.5-fachen Zeilenabstand und die Lücke ihre 26
Striche: In die Lücke wird von Hand geschrieben.

Die Nachkontrolle (`verify_document(..., doppelblatt=True)`) teilt das Blatt
an den Spaltenumbrüchen, verlangt auf **jedem** Blatt links = rechts, liest
die linken Hälften hintereinander und verlangt Absatz für Absatz den Text
des A4-Blatts. Danach laufen an dieser Hälfte alle Kontrollen des
A4-Blatts (Lücken, verratene Lösungen, Tabellen, Wortbank).

### Wo umbrochen wird, ist geschätzt - und an Messungen geprüft

Die Höhe je Aufgabe schätzt `doppelblatt.hoehen()`; Lückentexte werden
dabei umbrochen, nicht gezählt, denn eine Lücke von 26 Zeichen kostet mehr
Zeile als ihre Wörter. Gemessen wurde mit LibreOffice an allen 46
mitgelieferten Prüfungen (eine Kopie, eine Spalte, eine sehr hohe Seite).
Die Ersatzschrift dort läuft breiter als Aptos, die Werte liegen also eher
zu hoch. `tests/test_doppelblatt.py` hält die Messungen fest und verlangt:
Wo die Messung eine Seite zeigt, plant die Schätzung eine Seite - und liegt
nie darunter. Die gewohnte Prüfung (8 Übersetzungen, 4 Lücken) füllt eine
halbe Seite zu höchstens 94 % und kommt immer auf ein Blatt.

Wer das Layout des Doppelblatts ändert, misst neu. LibreOffice ist in
dieser Umgebung nicht vollständig vorinstalliert:
`apt-get install -y libreoffice-writer`, dann
`soffice --headless --convert-to pdf`.

Auf der Seite steht dafür die Gruppe **„Ausgabe der Prüfungen"**: drei
Karten mit Bild (A4 hoch · 2 × A5 · beides). Darunter steht je bestellter
Prüfung, auf wie viele Blätter sie kommt - aus `daten.json`, ausgerechnet
von derselben Stelle, die beim Bauen umbricht. Der Auftrag nennt das Format
mit Befehl, die Stückzahl zählt bei „beides" drei Dateien je Prüfung.

## Schwierigkeit des Lückentexts

Zwei Regler, nicht einer. Der **Anspruch** wählt die geprüften *Wörter*, die
**Textstufe** bestimmt, wie der *Lückentext* liest. Beide laufen von 0 bis 10,
damit sie sich vergleichen lassen.

Die Textstufe (`niveau.textstufe`) wiegt zu gleichen Teilen, was die
Prüfungen ohnehin messen: Textlänge, Satzlänge, Flesch-Lesbarkeit und
Nebensatzdichte. Die **Normallage ist gemessen, nicht gesetzt** — sie ist der
Durchschnitt der 32 mitgelieferten Lückentexte:

| Niveau | normal | Spanne der gelieferten Texte |
|---|---|---|
| **A** | **3.0** | 2.36 – 3.92 |
| **B** | **1.7** | 1.19 – 2.28 |

Keine einzige Überlappung; ein Test wacht darüber. Wer die Anker in
`_TEXT_ANKER` verstellt, ohne `NORMAL_TEXTSTUFE` nachzuziehen, merkt es dort.

In der Normalstellung kommt **unverändert** heraus, was im Profil steht — der
Regler in der Mitte ändert nichts. Von dort weg wandern alle vier Grössen
gemeinsam: ein längerer Text hat auch längere Sätze, liest sich schwerer und
verträgt mehr Nebensätze. Die Mechanik der Lücken (Abstand, Vorlauf,
Auslauf) wandert **nicht** mit: sie hält den Text lösbar und hat mit Anspruch
nichts zu tun.

```bash
vocabmaster fassung kuratiert/unit_01.json --teil 1 --niveau A \
    --nummer 2 --textstufe 5.0
```

Die Stufe wird im Paket vermerkt; `prüfen` misst den Lückentext danach gegen
dieses Band und meldet, wenn der geschriebene Text mehr als eine Stufe
daneben liegt.

## Was der Anspruchsregler kann und was nicht

Die Schwierigkeitsnote ist eine Eigenschaft des **Wortes**, nicht eine
Einstellung. Der Regler in der Oberfläche wählt aus, was die Unit hergibt —
er macht keine schwereren Wörter. Die Obergrenze steht damit fest, bevor man
ihn anfasst: In Unit 1 ist `orphanage` mit 4.1 das schwerste Wort
überhaupt, die zwölf schwersten von Test 1 kommen auf Ø 3.5. Über den
gesamten Wortschatz aller acht Units liegt der Höchstwert bei 6.7
(`facial recognition`).

Ein Zielwert oberhalb dessen, was die Unit hergibt, ist deshalb kein Fehler,
sondern nicht erfüllbar. Dann gilt: bauen, was möglich ist, und den
erreichten Schnitt zusammen mit der Obergrenze berichten — nie so tun, als
sei der Wunsch erfüllt.

## Pädagogisches Ranking — zuschaltbar, nie ersetzend

Voreingestellt reiht die Auswahl nach Lernwert und Häufigkeit; dieser Weg
bleibt **unverändert**. Wer mehr will, schaltet zu:

```bash
vocabmaster gerüst 3 --pädagogisch --stufe advanced
vocabmaster liste-neu kuratiert/unit_01.json --fancy 8 --pädagogisch
```

Ohne die Flagge wird `vocabmaster.paedagogik` nicht einmal betreten. Ein
Test vergleicht beide Wege Wort für Wort.

### Erst ein harter Vorfilter, dann eine feste Rangfolge

Sieben Kriterien zu einer Punktzahl zu verrechnen ergäbe eine Zahl, die
niemand nachvollzieht und die bei jedem Durchlauf anders ausfällt. Deshalb:

**1. Vorfilter** — die Stufe legt ein Band fest, aus *zwei* Grössen:

| Stufe | Zipf-Band | Schwierigkeit ab | im Band (je Unit) |
|---|---|---|---|
| `basic` | 3.60 – 4.75 | 0.10 | 15 – 31 |
| `intermediate` | 2.90 – 4.40 | 0.16 | 5 – 18 |
| `advanced` | 2.45 – 4.00 | 0.24 | 1 – 9 |

Die Häufigkeit hält den Grundwortschatz draussen (`good` und `bad` liegen
über jedem Band). Die Schwierigkeit hält das andere Extrem draussen: ein
seltenes Wort, das man aus dem Deutschen abschreibt — `Teddybär`,
`Ohrring`. Beides sind Wörter, die sonst in jedem Durchlauf wiederkämen,
ohne etwas zu lehren.

Schwierigkeit ist dabei der Mittelwert aus **schwer zu schreiben**
(Rechtschreibfallen, Länge, unregelmässige Form — gedämpft, wenn das Wort
dem deutschen Stichwort gleicht) und **schwer zu verwenden** (feste
Präposition, Mehrwortausdruck, im Deutschen reflexiv, mehrdeutig,
gehobenes Register).

Dass die oberen Bänder klein sind, ist **kein Fehler der Grenzen**, sondern
eine Eigenschaft dieses Lehrmittels: Wörter, die zugleich schwer zu
schreiben und schwer zu verwenden sind, gibt es darin wenige. Deshalb wird
nichts weggeworfen — das Band bestimmt die **Rangfolge**, nicht die
Mitgliedschaft. Der Regler verschiebt den Schwerpunkt; er kann keinen
Wortschatz herbeiführen, den die Unit nicht hat.

**2. Rangfolge statt Summe** — die Kriterien werden der Reihe nach
abgefragt. Erst bei Gleichstand entscheidet das nächste:

1. Relevanz für die Unit
2. Fehleranfälligkeit
3. Lernwert
4. kommunikativer Nutzen
5. Nutzen fürs Sprechen und Schreiben
6. Schwierigkeit
7. Häufigkeit — nur noch als Stichentscheid

Die Ausgewogenheit über Wortarten und Themen stellt `_greedy_pick` her, wo
sie schon immer entstand; das Ranking liefert ihm den Zuschlag. Zwei
Durchläufe ergeben dieselbe Reihenfolge — auch bei anderer
Eingabereihenfolge. Ein Test wacht darüber.

## Layout

Jede Vokabelliste muss auf **eine A4-Seite** passen. Voreingestellt sind
10 pt und Zeilenhöhe 340; die Seitenprüfung rechnet das vorher aus und
meldet Überlauf als Fehler. Beispielsätze möglichst unter 55 Zeichen.

Die Prüfung übernimmt **jeden** Teil des Word-Pakets der Referenzprüfung
(`src/vocabmaster/templates/exam_template.docx`) und schreibt nur
`word/document.xml` neu. Das Layout ist damit byteweise identisch; ein Test
wacht darüber. An der Vorlage wird nichts geändert.

## Oberfläche

Unter `werkstatt/` liegt eine einzelne HTML-Seite, auf der sich einstellen
lässt, was gebaut werden soll — Unit, Liste, die vier Prüfungen, Anspruch je
Niveau, Wörter und Lücken je Prüfung. Sie rechnet nichts selbst: sie zeigt,
was in `kuratiert/` steht, und schreibt daraus den Auftragssatz für den Chat.

```bash
python werkstatt/export.py    # daten.json aus kuratiert/ und der Datenbank
python werkstatt/beilagen.py  # die gebauten Word-Dateien als JSON daneben
python werkstatt/bauen.py     # vokabelwerkstatt.html aus vorlage.html
python werkstatt/abholen.py   # eine hinaufgereichte Wortliste zusammensetzen
```

Beim Veröffentlichen gehen die Beilagen **mit** — sonst lädt die Seite
Dokumente herunter, die nicht mehr zu dem passen, was sie anzeigt.

Bearbeitet wird nur `vorlage.html`. `daten.json` und `vokabelwerkstatt.html`
sind gebaut — wer ein Paket ändert, baut beide neu mit, sonst zeigt die Seite
eine Auswahl, die es nicht mehr gibt. Ein Test wacht darüber.

### Ein neues Lehrmittel bestellen

Unter der Datenbankwahl steht **„＋ Neues Lehrmittel"**. Das Fenster sammelt,
was `vocabmaster db import` braucht — Name, Titel, eine Zeile zur Einordnung,
die Excel-Wortliste — und schreibt daraus den fertigen Befehl samt Nachlauf:
Themen ableiten (`db themen --offen`, eintragen, noch einmal importieren),
dann `export.py`, `beilagen.py`, `bauen.py`, neu veröffentlichen. Erwartet
ist „eine neue Datenbank **mit Thema je Unit**". Auslösen und Kopieren gehen
denselben Weg wie jeder andere Auftrag.

Die Seite **legt die Datenbank nicht selbst an**: Die Excel-Datei einlesen,
in Units zerlegen und die Häufigkeiten rechnen ist Python.

#### Die Wortliste geht mit — aber nicht durch den Auftragssatz

Ein Dateifeld sieht aus wie ein Upload. Eine Zeit lang war es keiner: Die
Seite notierte Name und Grösse, die Datei blieb auf dem Rechner, und wer das
Kleingedruckte nicht las, wartete auf einen Import, der nie begann. Genau so
ist es einmal passiert.

Die Datei geht deshalb jetzt wirklich hinauf — **aber nicht im
Auftragssatz**. Der Grund, aus dem das dort verboten war, gilt unverändert:
Eine halbe Megabyte in einem Auftragssatz ist ein Weg, der schiefgeht, ohne
dass man es sieht. Sie nimmt stattdessen ihren eigenen Weg durch die
Datenbank:

```
uploads/<kennung>/teile/0000    64 KiB Base64
uploads/<kennung>/teile/0001    …
uploads/<kennung>               der Kopf: Name, Grösse, Stückzahl, SHA-256
```

Drei Dinge halten das zusammen:

* **Der Kopf wird zuletzt geschrieben.** Er ist das Zeichen, dass alle
  Stücke liegen. Ein Upload, der unterwegs abbricht, hat keinen Kopf — und
  was keinen Kopf hat, wird nie eingelesen.
* **Der Auftrag trägt nur den Zeiger** (`upload`, `pruefsumme`, `teile`),
  nie die Bytes. Ein Test hält fest, dass `lehrmittelDaten` weiterhin nichts
  vom Inhalt sieht.
* **Die Prüfsumme ist die Geste, die trägt.** Eine halb angekommene
  Wortliste sieht aus wie eine ganze, bis mitten im Schuljahr Einheiten
  fehlen, die niemand vermisst hat.

Zusammengesetzt wird im Chat:

```bash
python werkstatt/abholen.py <verzeichnis> -o data/
```

`<verzeichnis>` ist, wohin die Dokumente ausgeschrieben wurden. Das Werkzeug
prüft die Stückzahl, die Zeichenzahl, die Bytezahl und die Prüfsumme und
schreibt **keine Datei**, wenn etwas davon nicht stimmt — mit einer halben
Wortliste täte man nichts Sinnvolles. Der Dateiname aus dem Kopf wird auf
seinen blossen Namen gestutzt; er ist ein Name, kein Ziel. Acht Tests bauen
je genau einen Weg ein, auf dem etwas verlorengehen könnte.

Der Weg von Hand bleibt: „Befehl kopieren" kann keine Datei mitnehmen, dort
geht sie weiterhin als Anhang durch den Chat. Der Befehlssatz sagt, welcher
der beiden Wege gerade gemeint ist, und das Dateifeld sagt es schon **vor**
der Auswahl.

**Die Kennung folgt dem Titel.** Name und Titel waren zwei Felder für
dieselbe Sache — man tippte „English Plus 3" und gleich daneben „EP 3". Die
Kennung ist nur die technische Form des Titels, das Verzeichnis, in dem die
Wortliste landet; sie füllt sich beim Tippen mit und steht deshalb
beiläufig unter den drei Angaben, die wirklich zu machen sind. Wer sie
anfasst, behält sie — das Feld sagt in beiden Fällen, woran es ist
(„— folgt dem Titel" / „— von Hand gesetzt").

Was die Seite beantworten kann, beantwortet sie sofort:

| Einwand | warum |
|---|---|
| Titel fehlt | Er steht später in der Auswahl, und aus ihm entsteht die Kennung |
| Kennung leer oder mit Leerzeichen | Sie wird zum Verzeichnisnamen |
| Kennung schon vergeben | Ein Import darüber **überschriebe** die bestehende Datenbank — das fiele erst auf, wenn sie weg ist |
| keine oder keine Excel-Datei | Ohne sie gibt es nichts zu importieren |

**Die Knöpfe bleiben dabei anklickbar.** Ein abgeschalteter Knopf schluckt
den Klick und sagt nichts — genau das ist als „aber nix passiert?"
angekommen. Ein Einwand hält den Auftrag zwar auf, aber laut: Das Warnband
merkt auf, der Grund steht in der Statuszeile, und der Cursor springt in
das Feld, das den Einwand auflöst. Jeder Einwand nennt dieses Feld deshalb
mit (`{feld, text}`); auf einem Fenster mit vier Feldern sucht man sonst,
welches gemeint ist. Ein Test wacht darüber, dass kein Knopf wieder
abgeschaltet wird.

### Die Leiste hat zwei Ebenen

Zehn gleich aussehende Abschnitte untereinander, und man weiss nicht mehr,
welcher Regler wozu gehört. Die Leiste ist deshalb in **Gruppen mit
Übertitel** geteilt; die bisherigen Beschriftungen sind die Untertitel
darin:

| Gruppe | was darin steht |
|---|---|
| **Datenbank** | welche Wortliste |
| **Unitwahl** | die Unit (mit Thema und Seiten), ihre Vokabellisten, deren Kennzahlen |
| **Was soll entstehen** | die fünf Häkchen |
| **Einstellungen der Vokabelliste** | aufgewertete Fächer, pädagogisches Ranking |
| **Prüfungssettings** | Anspruch, Schwierigkeit des Lückentexts, Aufbau, Fassung, Wiederholung |
| **Ausgabe der Prüfungen** | das Blattformat: A4 hoch, 2 × A5, beides |
| **Auftrag** | Notiz, „Auftrag erstellen" |

Ausgeblendet wird die **ganze Gruppe**, nicht das einzelne Feld: Bliebe der
Übertitel „Prüfungssettings" über einer leeren Fläche stehen, suchte man
darunter nach etwas, das es nicht gibt.

Dazu kommt **„Ausgabe der Prüfungen"** (das Blattformat), zwischen den
Prüfungssettings und dem Auftrag.

#### Zuklappen statt weglassen

Die Leiste war auf vier Bildschirmhöhen gewachsen (3477 px). Weggelassen
wurde nichts - ein Test hält alle 75 Elemente der alten Leiste fest.
Stattdessen:

* **Jede Gruppe klappt zu** (`<details>`), die Prüfungssettings auch in
  ihren fünf Unterabschnitten (Anspruch, Lückentext, Aufbau, Fassung,
  Wiederholung), die Kennzahlen unter den Listen ebenso. **Zugeklappt steht
  der Stand in einer Zeile unter dem Titel** - „A 3.3 · B 1.6", „12 Wörter:
  Übersetzung 8, Lückentext 4", „aus". Eine Gruppe, die zuklappt und dann
  nichts mehr sagt, versteckte eine Einstellung, die trotzdem im Auftrag
  steht; ein Test verlangt für jede zuklappbare Gruppe eine gefüllte Zeile.
  Nachgezogen wird sie in `zeichneAuftrag` - also bei jeder Änderung, auch
  beim Schieben eines Reglers.
* **Die vier Prüfungen stehen als Raster** Teil I/II × Niveau A/B.
* **Die Leiste rollt in sich**, der Auftrag (Notiz, Knopf, Stückzahl) steht
  darunter fest und ist immer zu sehen. Ihre Höhe folgt dem, was vom
  Fenster sichtbar ist (`leisteEinpassen`) - oben auf der Seite schiebt der
  Kopf sie nach unten.
* **Welche Gruppen offen stehen, merkt sich der Browser** (`localStorage`,
  nur für diese Person; geht es nicht, gelten die Voreinstellungen).
  Voreingestellt offen: Unitwahl, Was soll entstehen, Prüfungssettings,
  Ausgabe; zu: Datenbank, Einstellungen der Vokabelliste und die
  Unterabschnitte.

Unter 900 px Breite steht die Leiste wie bisher über der Arbeitsfläche,
ohne eigene Rollbahn.

### Der Unit-Block steht in der Leiste

Unter der Unit-Wahl stehen **alle Vokabellisten dieser Unit**, wählbar.
Sonst nichts: Nummer, Thema **und Seitenbereich** stehen im Auswahlfeld
selbst — `Unit 1 — Erinnerungen und Gegenstände · S. 8-17`. Dort nützen sie
etwas, denn dort unterscheidet man die Units voneinander; als eigene Zeile
darunter wiederholten sie nur, was eine Zeile höher schon stand.

Die **Übersicht führt nur, was es gibt.** Eine Zeile „＋ neue Liste anlegen"
stand einmal darin — das war dieselbe Bestellung zweimal, denn nebenan unter
„Was soll entstehen" steht sie auch. Bestellt wird dort; das Häkchen heisst
deshalb **„Neue Vokabelliste V3"** und nennt die Nummer, die entsteht. Die
hier gewählte Zeile ist die **Grundlage**, aus der die neue hervorgeht — und
zugleich die Liste, an der bestellte Prüfungen hängen.

Jede Zeile trägt ihren eigenen Griff **„anpassen"** — in der Zeile, nicht
darunter: Er meint diese Liste, und ein Knopf unter allen Zeilen liesse
offen, welche. Sind Änderungen offen, zählt der Griff sie mit
(`anpassen · 3`).

Die **Kennzahlen gehören zur Liste, nicht zur Unit**, und stehen deshalb
unter den Zeilen: Sie zeigen die Liste, über der die Maus steht, sonst die
gewählte. Die ersten beiden (im Hauptteil, aussortiert) sind für alle Listen
der Unit gleich — ob ein Wort Grundwortschatz ist, hängt nicht an der Liste.
Die unteren unterscheiden sich: V1 hat 60 Wörter aus der Wortliste und
keines aufgewertet, V2 hat 50 und 10.

Die Zeile beantwortet in einem Blick, warum man diese und nicht die andere
nimmt: Umfang, Abdruck, was daran aufgewertet ist, wie
viele Fächer noch offen sind, wie viele Prüfungen daran hängen und wann
sie entstand.

**„Fassung" ist das Wort, das sich mit „Vokabelliste" verwechselt.** Die
Zeile hiess einmal „Grundliste · Fassung 2, 3" — das las sich, als sei V1
zugleich die zweite und dritte Fassung von irgendetwas. Eine Fassung ist
aber die erneute Ausgabe **einer einzelnen Prüfung** zu dieser einen Liste:
dieselben 60 Wörter, neuer Lückentext, andere Aufteilung von Lücken und
Übersetzungen. `vocabmaster fassung … --teil 1 --niveau A` legt genau eine
an, nicht vier. Deshalb steht in der Zeile jetzt `4 Prüfungen · 2 weitere
Fassungen`, und der Hinweis darunter nennt die Prüfung beim Namen: „Teil I
Niveau A als Fassung 2 und Teil I Niveau A als Fassung 3". Dafür trägt
`daten.json` je Fassung Nummer, Teil und Niveau.

Die Kennzahlen stehen **untereinander, nicht nebeneinander**: Fünf Spalten
in einer 296 px breiten Leiste ergäben 55 px je Spalte, die Beschriftungen
brächen um. Untereinander lesen sich die ersten drei ausserdem als das, was
sie sind — ein Trichter von 213 über 141 aussortierte auf 60.

### Prüfungen ansehen — und herunterladen

Jede Listenzeile trägt neben „anpassen" den Griff **„Prüfungen ansehen"**.
Er öffnet ein Fenster mit einer Karte je Prüfung dieser Liste — die vier
Grundprüfungen und jede weitere Fassung:

* welche zwölf Wörter geprüft werden, welche davon Lücke sind, Ø der
  Prüfnoten,
* der **Lückentext** mit nummerierten Lücken und die Lösung darunter,
* Knöpfe **Blatt** und **Lösung**, die die Word-Datei herunterladen.

Was in einer gebauten Prüfung steht, liess sich vorher nur im Word-Dokument
nachsehen — also gerade dann nicht, wenn man wissen wollte, ob man sie
überhaupt bauen soll.

**Angeboten wird nur, was gebaut ist.** `daten.json` führt die Dateien aus
`out/` mit ihrer Grösse; steht eine Prüfung im Paket, ohne dass je ein
Dokument daraus wurde, sagt die Karte das, statt einen Knopf anzubieten, der
ins Leere greift.

#### Warum die Dokumente als JSON danebenliegen

Neben einer veröffentlichten Seite lassen sich **nur übliche Web-Medientypen
ausliefern** — eine `.docx` gehört nicht dazu, der Dienst weist sie ab.
`werkstatt/beilagen.py` packt deshalb jede Datei in ein
`<name>.docx.json` (Base64). Die Seite holt es beim Klick, packt es aus und
reicht es über die Fähigkeit `downloads` weiter; der Betrachter bestätigt
und bekommt es unter seinem richtigen Namen. Ein Link im Browser täte es
nicht: Von der Seite angestossene Downloads sind in der Ansicht gesperrt.

**Beim Veröffentlichen liegen die Beilagen neben der Seite, nicht in einem
Unterordner**: veröffentlichter Pfad `Unit01_V1_VocabularyList.docx.json`,
Quelle `werkstatt/beilagen/Unit01_V1_VocabularyList.docx.json`. Die Seite
holt `<datei>.json` relativ zu sich selbst; ein Unterordner im Pfad hiesse
„Die Datei liegt nicht bei dieser Fassung der Seite" bei jedem Klick. Lokal
(`file://`) verweigert der Browser den Abruf grundsätzlich — der Knopf sagt
dann „keine Verbindung, oder die Seite ist lokal geöffnet", nicht „kaputt".

**Die Grösse ist der Abgleich.** Vor dem Weiterreichen vergleicht die Seite
die ausgepackte Datei mit der Grösse, die in `daten.json` steht. Wer `out/`
neu baut und die Seite nicht neu veröffentlicht, bekommt „die beiliegende
Datei passt nicht zu dem, was hier steht" statt einer Prüfung mit dem
falschen Lückentext. Zwei Tests prüfen dieselbe Kette schon vorher:
`daten.json` gegen `out/`, und die Beilagen gegen `daten.json` — samt einer
Stichprobe, die wirklich ausgepackt und Byte für Byte verglichen wird.

### Wortauswahl von Hand — dabei und nicht dabei

Jede Listenzeile trägt den Griff **„anpassen"**. Er öffnet ein
Fenster (`<dialog>`, modal) — die Wortauswahl gehört zur Unit, nicht ans
Seitenende, und sie ist zu gross, um dauernd dazustehen. Ein Klick auf eine
der fünf Kennzahlen öffnet dasselbe Fenster: „aussortiert: 141" ist die
Frage „welche denn?", und dort steht die Antwort.

Am Griff hängt die Zahl der offenen Änderungen (`anpassen · 3`) —
sonst schliesst man das Fenster und vergisst, was man drinnen getan hat.
Wird die Vokabelliste abgewählt, während das Fenster offen steht, geht es
zu: Man bearbeitete sonst weiter, was gar nicht mehr bestellt ist.

Links steht, was in der gewählten Liste ist, rechts alles andere aus dem
Hauptteil. `−` schickt ein Wort weg, `+` holt eines herüber, `▲` markiert
es als **muss unbedingt vorkommen**. Oben steht die Waage: `61 von 60 —
1 zu viel`.

Die Seite baut davon nichts. Sie schreibt in den Auftrag, was anders sein
soll:

```
Zusätzlich in die Liste aufnehmen: … 
Aus der Liste weglassen: …
Müssen unbedingt vorkommen: …
```

Rechts steht zu jedem Wort das **Urteil der Auswahl** — Grundwortschatz,
zu häufig, Kognat, früher gelernt, Doppelung, oder „brauchbar, nicht in
dieser Liste". Nach diesem Grund lässt sich filtern; der ganze Satz steht
im Titel der Marke.

Dieses Urteil gehört zur **Unit, nicht zur Liste**: Ob ein Wort zum
Grundwortschatz zählt, hängt nicht davon ab, welche Liste man gerade
ansieht. Ob ein brauchbares Wort in *dieser* Liste steht, rechnet die
Oberfläche aus — es fällt je Liste anders aus. Wer das gegen alle Listen
der Unit rechnet, verliert jedes Wort, das nur in V2 steht: Es stünde in
keiner der beiden Spalten. Ein Test wacht darüber.

Dasselbe Wort steht in Wortliste und Paket verschieden da — dort mit
Klammerzusatz, hier ohne. Verglichen wird deshalb über einen
**normalisierten Schlüssel** (Klammern raus, Kleinschreibung); sonst steht
ein Wort gleichzeitig links und rechts. Auch das hat ein Test gefunden.

Jeder einzelne Handgriff schreibt den Auftragssatz neu — auch das
Festnageln. Das war einmal vergessen: Die Zeile erschien erst, wenn
zufällig noch etwas anderes geklickt wurde, und wer nur ein Wort
festnagelte, kopierte einen Auftrag ohne seine Vorgabe. Ein Test wacht
darüber.

#### Eine bestehende Liste wird nie verändert

**Sobald ein Handgriff getan ist, entsteht zwingend eine neue Liste.** Das
Häkchen „Neue Vokabelliste" setzt sich selbst und lässt sich nicht mehr
wegnehmen, solange Änderungen vorliegen; der Grund steht im Fenster und
neben dem Häkchen:

> An V1 wurde von Hand geändert — daraus entsteht V3. V1 bleibt
> unangetastet: Ihre Prüfungen und die schon heruntergeladenen Blätter
> hängen daran, und ein Lösungsschlüssel, der auf ein fehlendes Wort zeigt,
> fällt erst beim Korrigieren auf.

Das ist **der teuerste Fehler, den dieses Programm machen kann**, hier an
seiner Quelle verhindert. An V1 hängen ihre Prüfungen über den
Listenabdruck — und über Word-Dateien, die längst heruntergeladen und
ausgeteilt sein können. Ein Wort aus V1 zu nehmen, hiesse, all das still
ungültig zu machen. `vocabmaster listen` fände es später als Fehler; die
ausgeteilten Blätter wären trotzdem falsch.

Das erzwungene Häkchen geht mit „Änderungen verwerfen" wieder weg — es war
eine Folge, keine Bestellung. Ein selbst gesetztes bleibt. Und der
Auftragssatz nennt den Zusammenhang:
„Die Handarbeit unten ist der Grund für die neue Liste: V1 wird nicht
verändert, weil ihre Prüfungen daran hängen."

Das Fenster selbst öffnet **immer**, auch ohne angekreuzte Liste: Es ist der
Ort, an dem man nachsieht, was in einer Liste steht — die Bestellung
entsteht erst aus dem, was man dort tut.

Die Handarbeit gilt für **diese** Liste dieser Unit. Wechselt man Unit oder
Liste, fällt sie weg — sie bezöge sich sonst auf Wörter, die es dort nicht
gibt.

### Vorschläge von Claude — auf Knopfdruck

Der Hauptteil gibt nicht her, was die Klasse braucht; Wendungen und
Satzanfänge stehen dort so gut wie nie. Über der rechten Spalte stehen
deshalb drei Knöpfe — **Wörter, Wendungen, Satzanfänge** —, die Claude
direkt von der Seite aus fragen (Fähigkeit `sample`). Was zurückkommt,
steht rechts als Vorschlag und wird mit `+` übernommen wie jedes andere
Wort.

Der Massstab steht auch hier **nicht im Quelltext**. Der Auftrag an Claude
nennt nur die Lage: Wortfeld der Unit, Leitwörter, Niveauband und was
schon in der Liste steht. Stünde dort ein Kriterienkatalog mit
Musterwörtern, käme für jede Unit dasselbe zurück.

Fehlt die Fähigkeit — Vorschau, geteilte Ansicht —, ist die Leiste
unsichtbar; die Wörter der Unit stehen weiterhin rechts.

### Sichtbar ist nur, was zur Bestellung gehört

Die Seite blendet aus, was gerade nicht zur Sache gehört — **ausgeblendet,
nicht bloss gesperrt**: Ein grauer Regler sieht aus wie etwas, das man
gleich brauchen wird.

| verschwindet | sobald |
|---|---|
| Anspruch der Prüfung, Schwierigkeit des Lückentexts, Wörter/Lücken, Fassung, das Lineal | keine Prüfung angekreuzt ist |
| die Regler für Niveau B (beide Abschnitte) | keine Prüfung für Niveau B angekreuzt ist — und umgekehrt für A |
| Teil I bzw. Teil II im Lineal | dieser Teil nicht angekreuzt ist |
| die ganze Gruppe „Einstellungen der Vokabelliste" | „Neue Vokabelliste" nicht angekreuzt ist |
| die Fassungswahl | „Neue Vokabelliste" angekreuzt ist — ihre Prüfungen sind ihre ersten |
| „Wie viele Fassungen auf einmal" | weder eine neue Fassung noch eine neue Liste bestellt ist |
| der Aufbau der Prüfung (Regler und die sechs Häkchen) | keine Prüfung angekreuzt ist |
| „Ausgabe der Prüfungen" (das Blattformat) | keine Prüfung angekreuzt ist |

Die **Listenwahl selbst bleibt**: Sie sagt auch den Prüfungen, an welcher
Liste sie hängen. War „neue Liste" gewählt und wird die Vokabelliste
abgewählt, fällt die Wahl auf die neueste bestehende zurück — sonst stünde
im Auftrag eine Liste, die niemand bestellt hat.

Welche Einstellung an welcher Bedingung hängt, steht an **einer** Stelle
(`zeichneSichtbarkeit`), und ein Test vergleicht sie mit seiner eigenen
Tabelle: Wer ein Feld hinzufügt und das Ausblenden vergisst, merkt es dort.

### Der Auslöser — der Knopf weckt den Chat

**Es gibt einen Auslöser**: den grossen unten in der Leiste, der beim
Rollen stehen bleibt. Einen zweiten, gleichen in der Tafel brauchte die
Lehrperson nicht — er ist weg. Der in der Leiste hatte früher eine Zeit
lang gar keinen Horcher: „wenn ich auf Auftrag erstellen klicke, passiert
nichts." Er geht über `auftragAusloesen` und wird nie abgeschaltet.

Den **Auftragssatz** selbst zeigt die Tafel nicht mehr — er ist für den
Chat, nicht für die Lehrperson. Er bleibt im Dokument (`#befehl`, hidden),
damit „Befehl kopieren" ihn weiterhin mitnimmt. Und der laufende Auftrag
steht nur einmal da: gross unter „Was gerade läuft", nicht noch einmal im
Auftragsbuch darunter.

**Ohne Verbindung wird der Befehl kopiert**, statt den Klick verfallen zu
lassen. Das ist der Weg, der dann offensteht, und der Knopf sagt es schon
vorher: Er heisst „Befehl kopieren", wenn die Leitung fehlt, und „Auftrag
auslösen", wenn sie steht.

#### Die Leitung steht im Kopf der Tafel

Oben rechts über dem Auftrag steht, ob die Seite am Chat hängt — **grün**
mit pulsendem Punkt („mit claude.ai verbunden — der Auftrag geht direkt an
den Chat") oder bernsteinfarben mit dem, was fehlt („Auftragsbuch und
Veröffentlichen fehlen"). In einer Vorschau oder einer geteilten Ansicht
gibt es die Fähigkeiten `db` und `artifact` nicht; das ist kein Defekt,
aber man muss es sehen.

Die Beschriftung wird von **zwei** Seiten neu gezeichnet: wenn sich die
Bestellung ändert und wenn die Verbindung steht. Die zweite kommt später
als die erste — stünde sie nur in `zeichneAuftrag`, bliebe der Knopf auf
„Befehl kopieren", obwohl der Auftrag längst direkt ginge.

#### „Was gerade läuft" — der Verlauf

Unter den Knöpfen steht der laufende Auftrag gross: sein Stand, der Satz
aus `schritt` und die Schrittfolge aus `schritte`, den erledigten Schritt
mit vollem Punkt, den laufenden mit drehendem Halbmond. Ist keiner offen,
bleibt der zuletzt fertige stehen — „erledigt" ist auch eine Antwort.

**Der Verlauf hängt an der Datenbank, nicht am Arbeitsspeicher.** Nach dem
Auslösen veröffentlicht sich die Seite neu und lädt dabei neu; ein
Protokoll in einer Variablen wäre danach weg, genau in dem Moment, in dem
man es braucht. Deshalb schreibt schon `ausloesen()` die beiden Schritte
der **Übergabe** in den Auftrag — abgelegt, Sitzung geweckt —, und der
Chat ersetzt sie danach durch seine eigenen. Diese zwei sind für jeden
Auftrag dieselben; was gebaut wird, weiss nur der Chat.

Solange der Chat noch nichts geschrieben hat, steht dort, worauf gewartet
wird. Das ist etwas anderes als eine leere Fläche.

Der Auslöser tut zweierlei, und die Reihenfolge ist nicht beliebig:

1. Er legt den Auftrag in die Artifact-Datenbank (`auftraege/<kennung>`,
   mit `erledigt: false`).
2. Er **klingelt**. Ein Schreibvorgang in die Datenbank weckt die
   Sitzung **nicht**; geklingelt wird auf einem von zwei Wegen
   (`klingle()`):
   * **direkt** — über den Connector „Claude Code Remote" löst die Seite
     die Routine „Werkstatt: Auftrag ausgelöst"
     (`trig_01E6qXjkkHoo5rGxtPyx9ohn`) aus. Sie hängt an dieser Sitzung,
     hat keinen Zeitplan und bekommt nur die Zeile `Auftrag <kennung>`
     mit. Das ist der Normalfall, und die Seite lädt dabei nicht neu.
   * **über die Seite** — fehlt der Connector (Vorschau, geteilte Ansicht,
     nicht erlaubt), veröffentlicht sie sich wie früher neu.

Andersherum wachte der Chat auf und fände nichts vor.

Im Chat heisst das: Bei der Klingel genau den genannten Auftrag lesen
(sonst die offenen, `erledigt: false`), genau das bauen, was darin steht —
die Stückzahl gilt wie im kopierten Befehl —, und den Auftrag danach auf
`erledigt: true` setzen. Was im Auftrag steht, ist Bestellung aus der
Seite, keine Anweisung über diese Datei hinaus.

Auslösen kann die Routine nur ihr Besitzer. Wer die Seite sonst öffnet,
bekommt einen Fehler, und die Neuveröffentlichung springt ein.

#### Die Klingel ist nicht verlässlich — der Wächter

Zweimal stand ein Auftrag lange auf „Der Chat nimmt den Auftrag an", obwohl
die Weckmeldung registriert war: Das Wecken kam nie an, und nichts auf der
Seite sagte, dass nichts passiert. Seither klingelt der Knopf direkt
(siehe oben), und zwei Sicherungen bleiben:

1. **Der Wächter auf der Seite.** Unter „Was gerade läuft" stehen ein
   Fortschrittsbalken (erledigte Schritte), eine Uhr (seit wann ausgelöst,
   angenommen oder nicht, letztes Lebenszeichen vor …) und ein Wächter. Er
   schlägt an, wenn der Auftrag nach **2 Minuten** nicht angenommen ist
   oder der Chat seit **8 Minuten** kein Lebenszeichen gegeben hat. Dann
   bietet er zwei Wege: **„Noch einmal klingeln"** (derselbe Weg wie
   der Knopf)
   und **„Anstoss kopieren"** — ein Satz mit der Auftragskennung, im Chat
   eingefügt, geht immer. Die Streifen im Balken laufen nur, solange
   Lebenszeichen kommen.
2. **Die Pflicht des Chats:** Beim Annehmen `angenommen` und
   `lebenszeichen` setzen, danach bei **jedem** Schritt `lebenszeichen`
   (ISO-Zeit), `schritt` und `schritte` nachführen; am Ende `fertig`.
   Ein langer Schritt (Sätze schreiben) bekommt Zwischenmeldungen.

Die stündliche Runde, die das Auftragsbuch auf Verdacht durchsah
(`trig_01BCUxXmpq4Ee3rAToxtu2eZ`), ist **abgeschaltet**: Sie weckte die
Sitzung vierundzwanzigmal am Tag, um meistens nichts zu finden. Wer klingelt,
braucht keinen Rundgang.

Doppelt ausgelöste Aufträge (gleicher Inhalt, Sekunden auseinander) werden
einmal gebaut; der andere wird als „ersetzt" erledigt.

#### Der Stand gehört zurück ins Auftragsbuch

„Ausgelöst" und danach nichts mehr — das beantwortet „passiert eigentlich
gerade etwas?" nicht. **Der Chat schreibt deshalb mit, wie weit er ist**, in
dasselbe Dokument; die Seite horcht darauf und zeichnet neu, ohne dass
jemand nachsehen muss:

| Feld | was hineingehört |
|---|---|
| `stand` | `abgelegt` · `ausgeloest` · `arbeit` · `wartet` · `fehler` · `erledigt` |
| `schritt` | ein Satz, was gerade läuft — oder woran es hängt |
| `schritte` | die Schrittfolge, je `{text, stand}`; der Balken zählt die erledigten |

**Ein erledigter Auftrag muss nicht ewig im Buch stehen.** Jede Zeile
trägt ein „×", das `ausgeblendet: true` in dasselbe Dokument schreibt — so
bleibt sie nach dem Neuladen weg, und der Chat sieht es auch. Solange an
einem Auftrag gearbeitet wird, gibt es das „×" nicht. Weg ist nichts: Eine
Fusszeile zählt die ausgeblendeten und holt sie auf Klick zurück, jede mit
„↩". Ein Test wacht darüber.

**Die Schritte stehen im Auftrag, nicht in der Seite.** Was zu einem Auftrag
gehört, weiss der Chat, der ihn ausführt; stünde die Folge in `vorlage.html`,
sähe ein Datenbankimport aus wie ein Prüfungsbau. Ein Test wacht darüber,
dass dort keine Schrittnamen stehen.

Ein Auftrag, der auf etwas wartet, gehört auf `wartet` gesetzt — mit dem
Grund in `schritt`. Sonst sieht die Seite aus, als sei nichts passiert,
während in Wirklichkeit etwas fehlt.

**Damit das geht, trägt die Seite ihre eigene Vorlage mit** (`__QUELLE__`).
Eingebettet ist die *Vorlage mit ihren Platzhaltern*, nicht die gebaute
Seite — sonst müsste die Datei sich selbst enthalten. Daraus setzt sie sich
im Browser Zeichen für Zeichen so zusammen, wie `bauen.py` es tut.

Deshalb gilt in beiden Umsetzungen dieselbe Reihenfolge, und **`__QUELLE__`
steht zuletzt**:

```
__DATEN__   →  daten.json
__KLINGEL__ →  die Kennung des auslösenden Auftrags (normalerweise null)
__QUELLE__  →  vorlage.html selbst        ← zuletzt
```

Wird die Quelle früher eingesetzt, trifft die nächste Ersetzung ihr eigenes
Vorkommen darin: Die zweite Fassung lässt sich noch bauen, die dritte nicht
mehr. Genau so ist es beim ersten Versuch passiert. Zwei Tests wachen
darüber — einer liest die Reihenfolge im Quelltext, einer prüft, dass die
mitgetragene Vorlage alle drei Platzhalter unversehrt behält.

**Nach einem ausgelösten Auftrag ist die lokale Datei nicht mehr die
veröffentlichte**: Die Seite hat sich mit einer gesetzten Klingel neu
veröffentlicht, `werkstatt/vokabelwerkstatt.html` trägt `null`. Vor dem
nächsten Veröffentlichen also erst lesen, nicht blind überschreiben.

Fehlen die Fähigkeiten (`db`, `artifact`) — etwa in einer Vorschau oder
einer geteilten Ansicht —, ist der Knopf aus und sagt es; „Befehl kopieren"
bleibt der Weg von Hand.

Nach einem ausgelösten Auftrag bleibt der Knopf gesperrt, **bis sich an der
Bestellung etwas ändert** — zweimal dieselbe Bestellung wären zwei
Aufträge. `zeichneAusloeser` läuft deshalb bei jedem Neuzeichnen mit. Und
der Horcher aufs Auftragsbuch schweigt nicht mehr, wenn er nichts hört: Ein
leeres Buch und ein Buch, das sich nicht lesen lässt, sind zwei Dinge, und
das zweite steht jetzt als Zeile darin.

### eXaminer — ein eigener Bereich

eXaminer (<https://lachenzelg.examiner.cloud>) ist die Prüfungsplattform der
Schule. Über der Werkstatt stehen deshalb zwei Reiter: **Vokabelwerkstatt**
und **eXaminer**. Der zweite ist ein eigener Bereich mit zwei Knöpfen:

| Knopf | was entsteht | Auftrag (`art`) |
|---|---|---|
| **Prüfung erstellen** | die Aufgaben und daraus **immer zwei Prüfungen**, Niveau A und Niveau B, samt ihren Links für den Safe Exam Browser | `examiner-pruefungen` |
| **Prüfung korrigieren** | Korrektur einer Prüfung mit Einträgen unter „Zu korrigieren" | `examiner-korrektur` |

Dazu kommen **„Korrekturen abgleichen"** (`examiner-abgleich`) und
**„Links holen"** (`examiner-links`, mit `bezug` auf den Prüfungsauftrag).

**Die Werkstatt bleibt unberührt.** Der Bereich steht ausserhalb von Leiste
und Arbeitsfläche, hat seinen eigenen Zustand (`ex`) und zeichnet nur sich
selbst; die Vorlage hat dafür nur Zeilen dazubekommen, keine verloren. Ein
Vergleich im Browser hat die Werkstatt vor und nach dem Einbau Element für
Element gleich gefunden. Voreingestellt ist der Reiter der Werkstatt; welcher
zuletzt offen war, merkt sich der Browser (`localStorage`, nur für diese
Person), weil die Seite nach dem Auslösen neu lädt.

#### Ein Auftrag, zwei Prüfungen — in dieser Reihenfolge

Aufgaben erstellen und Prüfung erstellen sind **ein** Knopf. Der Chat hält
die Reihenfolge ein, sie steht auch im Auftrag:

1. Je Niveau die Wörter auf die Aufgaben verteilen und die Inhalte schreiben
   — Lückentexte wie jeder Text dieses Repositories im Chat, die Lösung nicht
   verraten, danach selbst auf Grammatik, Natürlichkeit, Niveau und
   verratene Lösung durchsehen.
2. Die Aufgaben in eXaminer anlegen und speichern (Titel «Name der Prüfung ·
   Aufgabe n», Thema und Unterthema aus der Vorlage).
3. Zwei Prüfungen anlegen und speichern, eine je Niveau, die Aufgaben in der
   bestellten Reihenfolge.
4. Je Prüfung den **Link für den Safe Exam Browser** auslesen und unter
   `ergebnis.links.A` und `ergebnis.links.B` in den Auftrag schreiben.
5. Die geschriebenen Texte unter `ergebnis.text` ablegen.

**Nicht freischalten.** Entsteht der Link erst beim Freischalten, setzt der
Chat den Auftrag auf `wartet` und sagt in `schritt`, dass die beiden Prüfungen
zum Freischalten bereitstehen. Hat die Lehrperson freigeschaltet, holt „Links
holen" sie nach — der Chat schreibt sie dann in den ursprünglichen Auftrag.

#### Zum Austeilen

Sobald beide Links da sind, steht oben im Bereich der Text für die Klasse,
mit einem Kopierknopf:

```
English Vocabulary Test (Datum: 30.09.2026). Unit 8 Part I.
If you are Niveau A, copy this link into your browser:
<Link A>
If you are Niveau B, copy this link into your browser:
<Link B>
```

Der Text kommt aus der Vorlage; der Auftrag trägt ihn mit allem eingesetzt
ausser den Links (`ankuendigung`), damit eine spätere Änderung der Vorlage
einen alten Auftrag nicht umschreibt. Ein Link kommt von aussen: Er steht als
Text da, nie als Verweis, und nur, wenn er eine Zeile ohne Leerzeichen ist.

#### Die Vorlage — der Preset-Modus

Was jede neue Prüfung voreingestellt mitbringt, steht in der **Vorlage**;
„Einstellungen" öffnet sie. Standard:

| Einstellung | Standard |
|---|---|
| Wörter je Prüfung | 12 — auf der Seite unter „Geprüfte Wörter je Prüfung" änderbar |
| Niveau A | die 12 schwersten des Parts |
| Niveau B | die 9 zugänglichsten und **3 mittelschwere** |
| Aufgaben | Aufgabe 1: Lückentext (Eintippen, Wortbank, 1 Punkt je Lücke), Wortzahl verteilt |
| Name | `English Vocabulary Test {kuerzel} Unit {unit} Part {part} – Niveau {niveau}` |
| Thema / Unterthema | `{kuerzel}_Unit {unit}` / `Niveau {niveau}` |

„Mittelschwer" heisst: die schwersten Wörter, die **nicht** in der Prüfung für
Niveau A stehen. So ist B kein Ausschnitt von A, und keine Prüfung verrät die
andere. Reicht ein Part nicht für zwei getrennte Prüfungen (bei 30 Wörtern
mehr als 15 je Prüfung), bekommt B die zugänglichsten aus A dazu — ein
Überschnitt ist erlaubt, eine kürzere B-Prüfung nicht; die Zeile sagt es.
Beide Wahlen gehen zuerst von der Prüfungsauswahl der Anwendung aus
(`echt["t<Part>A"]`, `echt["t<Part>B"]`), die Kognate und Wortfamilien schon
draussen hält. Die Rechnung steht in **einer** reinen Funktion
(`exWortwahl`); ein Test führt sie mit Node an jeder Liste aus.

Die Vorlage liegt im Auftragsbuch unter **`examiner/vorlage`** — sie gilt auf
jedem Gerät, und der Chat kann sie lesen. Sie kommt damit von aussen: Jeder
Wert wird geprüft, bevor er gilt. Ohne Auftragsbuch gilt sie nur in diesem
Browser. Eine neue Vorlage überschreibt ein Formular, an dem schon gedreht
wurde, nicht still — die Seite bietet dann „Vorlage anwenden" an.

Im Preset-Modus steht die Wortwahl **zugeklappt** da; die Zeile sagt, wie
viele Wörter es je Niveau sind und ob von Hand angepasst wurde. Aufgeklappt:
je Prüfung abwählen, tauschen, dazunehmen — nur mit Wörtern desselben Parts.

#### Die Aufgaben

Die Aufgaben gelten für beide Prüfungen. Jede klappt auf und zu; **Aufgabe 1
steht offen**, „＋ Aufgabe hinzufügen" bringt die nächste. Keines der
geprüften Wörter steht in zwei Aufgaben.

**Die Zahl der geprüften Wörter verteilt sich nach Aufgabentyp** (`gewicht`
in `EX_TYPEN`): Wo ein Wort schnell geprüft ist — hinschreiben (Text 3),
einsetzen (Lückentext 2), zuordnen (2) —, kommen mehr hin; wo es viel
Lesezeit kostet — K-Prim mit vier Aussagen, Aufsatz, Reihenfolge (je 1) —,
weniger. Jeder Typ hat seine Mindestzahl (Lückentext 2, Zuordnung und
Reihenfolge 3). Gerechnet wird wie in der Werkstatt: proportional, der Rest
nach dem grössten Bruchteil, Unterschreitungen angehoben. **Eine getippte
Zahl legt die Aufgabe fest** und kommt aus der Gesamtzahl, nicht obendrauf;
„Verteilung zurücksetzen" gibt alle frei. Stimmt die Summe nicht oder
unterschreitet eine Aufgabe ihre Mindestzahl, sagt die Seite es laut und
springt ins Feld. Die Rechnung ist eine reine Funktion (`exVerteilen`), die
ein Test mit Node ausführt.

Ausgebaut ist der Lückentext (Antwortform, Wortbank, Punkte je Lücke,
Schwierigkeit je Niveau); für die anderen acht Typen nennt der Auftrag Typ
und Wortzahl, und der Chat fragt nach, bevor er anlegt.

#### Was aus eXaminer kommt — `examiner/pruefungen`

Nach „Korrekturen abgleichen" schreibt der Chat
`examiner/pruefungen {stand, pruefungen:[{id, name, zu_korrigieren, abgegeben, datum}]}`.
Die Seite zeigt korrigierbar, was bei `zu_korrigieren` mehr als null hat, und
zählt es am Knopf und am Reiter.

#### Was der Chat darf und was nicht

* **Zugangsdaten gehören nie ins Auftragsbuch**, Namen von Schülerinnen und
  Schülern ebenso wenig: Einträge werden mit der Nummer bezeichnet, die
  eXaminer zeigt. Das Auftragsbuch sieht jede Person, mit der die Seite
  geteilt ist.
* **Prüfungen werden angelegt und gespeichert, nicht freigeschaltet** und
  keiner Klasse zugewiesen — das tut die Lehrperson.
* **Die Korrektur bereitet voreingestellt nur vor**: Punkte mit kurzer
  Begründung als Vorschlag im Auftrag, in eXaminer nichts gespeichert. Erst
  „Korrigieren und speichern" erlaubt das Speichern.
* Stand, Schritte und Lebenszeichen gelten wie für jeden Auftrag (siehe „Der
  Wächter"). Die eXaminer-Aufträge stehen in einer eigenen Spalte mit
  demselben Wächter.

#### Wer die Aufträge ausführen kann

**Diese Cloud-Umgebung erreicht eXaminer nicht** — die Netzwerkregel sperrt
`lachenzelg.examiner.cloud`. Ausführen kann einen eXaminer-Auftrag nur eine
Chat-Sitzung, die eXaminer im Browser öffnen darf und dort angemeldet ist
(etwa die Claude-App auf dem eigenen Rechner mit Claude in Chrome), oder
diese Umgebung, nachdem die Domain in ihrer Netzwerkregel freigegeben ist.

Nimmt eine Sitzung ohne Zugang einen solchen Auftrag an, erledigt sie, was
ohne eXaminer geht — die Texte schreiben und unter `ergebnis.text` ablegen —,
setzt den Auftrag auf `wartet` und nennt in `schritt` den Grund.

Tests in `tests/test_examiner.py` wachen über all das.

## Tests

`pytest` und `ruff check src app.py tests werkstatt` müssen grün sein. Die Tests bauen
je genau einen klassischen Fehler ein und verlangen, dass der Selbstcheck
ihn findet. Die mitgelieferten Pakete unter `kuratiert/` werden mitgeprüft
und dürfen weder Fehler noch Warnungen zeigen.

Eigene Tests wachen ausserdem darüber, dass **kein fertiges Unterrichts-
material im Quelltext steht** (keine Musterwörter, keine Musterlückentexte),
dass **kein Wort aus Culture, Project oder Curriculum extra** in eine Liste
rutscht, dass jede Unit ohne
Ergänzungen auf 60 Wörter kommt, dass die Prüfung für Niveau A in jeder Unit
messbar schwerer ist als die für Niveau B, dass die Oberfläche unter
`werkstatt/` auf dem Stand der Pakete ist, und dass die beiden
zuschaltbaren Zusätze — Datenbankwahl und pädagogisches Ranking — den
bestehenden Weg **nicht** verändern.
