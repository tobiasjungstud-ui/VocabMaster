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

Die Prüfungsform ist für beide dieselbe (8× Übersetzen + 4 Lücken,
12 Punkte), wie in der Vorlage. Unterschiedlich sind Wortauswahl,
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

## Aufgewertete Wörter („fancy")

Eine neue Liste entsteht nicht aus dem Nichts, sondern durch **Aufwertung**:

```bash
vocabmaster liste-neu kuratiert/unit_01.json --fancy 3 \
    --wort "englisch=deutsch"
```

Das schreibt `kuratiert/unit_01_v2.json`. Die Liste bleibt bei **60 Wörtern**
— sie muss auf eine A4-Seite passen —, also tritt jedes aufgewertete Wort an
die Stelle eines zu einfachen. Es weichen die **zugänglichsten** zuerst, und
welche das sind, hängt an der Unit: in Unit 3 `exotic` und `realistic`, in
Unit 7 `sports stadium` und `skeleton`.

### Der Massstab steht nicht im Programm

`--fancy N` öffnet N Fächer, die **im Chat** gefüllt werden. Das Fach liefert
die **Lage**, nicht das Ergebnis:

* das Wortfeld der Unit und ihre Leitwörter,
* das Niveauband der Liste,
* welches Wort gewichen ist und mit welcher Prüfnote.

Wonach ausgewählt wird, gehört ausdrücklich **nicht** in den Quelltext.
Steht dort erst einmal ein Kriterienkatalog mit Musterwörtern, bekommt jede
Unit dieselbe Antwort zurück — dieselben fünf Adjektive für Werbung wie für
Bauwerke. Was ein Wort hier verdient, entscheidet sich am Wortfeld dieser
Unit, an dem, was schon in der Liste steht, und daran, was der Klasse an
Ausdruck wirklich fehlt. Das ist eine Überlegung, keine Tabelle.

Ein Test wacht darüber (`tests/test_keine_schablonen.py`): Sobald fertige
Beispielvokabeln in `src/` oder in der Oberfläche auftauchen, schlägt er an.
Er hat schon einmal angeschlagen.

Die Begründung je Wort gehört ins Feld `begruendung` — die Themenkontrolle
liest sie, und sie bleibt im Paket nachlesbar. Im Chat gehört sie ohnehin in
die Antwort (siehe „Pflicht: Herkunft immer im Chat berichten").

`--wort` nimmt die Angabe in beiden Richtungen (`englisch=deutsch` wie
`deutsch=englisch`); erkannt wird sie an der Schreibung — Umlaute und
typische Endungen sprechen für Deutsch, `th` oder `-ness` für Englisch. Wo
das nicht reicht (`rot=red`), wird **nicht geraten**, sondern zurückgefragt;
eindeutig ist `en:<wort>=<Wort>`.

Die vier Prüfungen werden gegen die neue Liste neu aufgesetzt; die
handgeschriebenen Lückentexte bleiben erhalten. Fällt eines ihrer
Lückenwörter der Aufwertung zum Opfer, meldet das `loesungsschluessel` —
lieber ein klarer Fehler als stillschweigend weggeworfene Arbeit.

### Ein übernommener Lückentext ist nicht automatisch gültig

Ein Lückentext ist für **bestimmte** Lücken geschrieben. Werden die
Prüfungswörter neu gesetzt — durch `liste-neu` oder durch `ausgleichen` —,
passt er nicht mehr: Der Satz, der `checkout` erschliessbar machte, steht
dann über der Lösung `downside`.

Genau das lief lange still durch, und der Selbstcheck hat es nicht bemerkt:
`loesungsschluessel` prüft nur, dass die Lückenwörter *in der Liste stehen*,
nicht, dass der Text sie *meint*. Deshalb merkt sich `task2.text_ueberholt`
jetzt, für welche Lücken ein übernommener Text einmal geschrieben wurde.
Stimmen sie nicht mehr mit den heutigen überein, ist das ein **Fehler** —
auszuräumen nur durch Neuschreiben, danach das Feld löschen.

Der Text wird trotzdem übernommen und nicht verworfen: Er ist Handarbeit
und die bessere Grundlage für die neue Fassung als ein leeres Feld.

## Zweite Fassung einer Prüfung

Für eine Nachprüfung, oder wenn ein Blatt bekannt geworden ist:

```bash
vocabmaster fassung kuratiert/unit_01.json --teil 1 --niveau A \
     --nummer 2 --woerter 12 --luecken 6
```

Das schreibt `kuratiert/unit_01_fassung2.json` — **dieselbe Vokabelliste**,
Wort für Wort, aber nur die eine neu gesetzte Prüfung. Die Dokumente heissen
`Unit01_Test_PartI_NiveauA_Fassung2.docx`; die erste Fassung bleibt
unangetastet. Danach wie immer: Lückentext im Chat schreiben, `prüfen`,
`bauen`.

`--gemeinsam` ist die Obergrenze für Wörter, die schon in Fassung 1 geprüft
wurden; voreingestellt sind **40 %** der Prüfung (`VM_MAX_OVERLAP`), bei
12 Wörtern also 4. Ein Überschnitt ist ausdrücklich erlaubt — beide
Fassungen prüfen dieselbe Liste —, aber darüber ist es keine zweite Fassung
mehr, sondern dieselbe mit anderer Reihenfolge. Ganz ohne Überschnitt geht es selten: Beide Fassungen schöpfen aus
denselben dreissig Wörtern und beide wollen dasselbe Ende davon — das
schwere für Niveau A, das zugängliche für Niveau B. **Je weniger gemeinsam,
desto weiter muss die Auswahl von diesem Ende weg, desto mehr weicht der
Anspruch von der ersten Fassung ab.** Der Befehl schreibt beide Zahlen hin.

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
python werkstatt/export.py   # daten.json aus kuratiert/ und der Datenbank
python werkstatt/bauen.py    # vokabelwerkstatt.html aus vorlage.html
```

Bearbeitet wird nur `vorlage.html`. `daten.json` und `vokabelwerkstatt.html`
sind gebaut — wer ein Paket ändert, baut beide neu mit, sonst zeigt die Seite
eine Auswahl, die es nicht mehr gibt. Ein Test wacht darüber.

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
messbar schwerer ist als die für Niveau B, und dass die Oberfläche unter
`werkstatt/` auf dem Stand der Pakete ist.
