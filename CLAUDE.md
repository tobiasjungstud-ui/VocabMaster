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
| **Prüfungssettings** | Anspruch der Prüfung, Schwierigkeit des Lückentexts, Feinheiten |
| **Auftrag** | Notiz, „Auftrag erstellen" |

Ausgeblendet wird die **ganze Gruppe**, nicht das einzelne Feld: Bliebe der
Übertitel „Prüfungssettings" über einer leeren Fläche stehen, suchte man
darunter nach etwas, das es nicht gibt.

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

Die **Listenwahl selbst bleibt**: Sie sagt auch den Prüfungen, an welcher
Liste sie hängen. War „neue Liste" gewählt und wird die Vokabelliste
abgewählt, fällt die Wahl auf die neueste bestehende zurück — sonst stünde
im Auftrag eine Liste, die niemand bestellt hat.

Welche Einstellung an welcher Bedingung hängt, steht an **einer** Stelle
(`zeichneSichtbarkeit`), und ein Test vergleicht sie mit seiner eigenen
Tabelle: Wer ein Feld hinzufügt und das Ausblenden vergisst, merkt es dort.

### Der Auslöser — der Knopf weckt den Chat

**Es sind zwei Knöpfe, und sie tun dasselbe**: der grosse unten in der
Leiste und „Auftrag auslösen" in der Tafel. Der in der Leiste hatte eine
Zeit lang gar keinen Horcher — und weil er der auffälligere ist, wurde er
geklickt: „wenn ich auf Auftrag erstellen klicke, passiert nichts." Beide
gehen jetzt über **eine** Stelle (`auftragAusloesen`), und keiner von
beiden wird je abgeschaltet.

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
2. Er **veröffentlicht die Seite neu**. Das ist die Klingel: Eine neue
   Fassung weckt die Chat-Sitzung, ein Schreibvorgang in die Datenbank
   weckt sie **nicht**.

Andersherum wachte der Chat auf und fände nichts vor.

Im Chat heisst das: Bei einer Weckmeldung zu diesem Artifact die offenen
Aufträge lesen (`auftraege`, `erledigt: false`), genau das bauen, was
darin steht — die Stückzahl gilt wie im kopierten Befehl —, und den Auftrag
danach auf `erledigt: true` setzen.

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
