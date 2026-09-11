# Vokabelwerkstatt — die Oberfläche

Eine einzelne HTML-Seite, auf der sich einstellen lässt, was gebaut werden
soll: Unit, Vokabelliste, die vier Prüfungen, Anspruch je Niveau, Wörter und
Lücken je Prüfung, Fassung. Der Knopf **Auftrag erstellen** schreibt daraus
den Satz, mit dem der Auftrag im Chat erteilt wird.

Die Seite rechnet nichts selbst. Sie zeigt, was in `kuratiert/` schon steht,
und gibt einen Auftrag weiter — geschrieben wird nach wie vor im Chat und
gebaut mit `vocabmaster bauen`.

## Bauen

```bash
python werkstatt/export.py   # daten.json aus kuratiert/ und der Datenbank
python werkstatt/bauen.py    # vokabelwerkstatt.html aus vorlage.html
```

| Datei | |
|---|---|
| `vorlage.html` | die Seite, von Hand gepflegt; `__DATEN__` ist die Fuge |
| `export.py` | zieht Wörter, Schwierigkeit und die echten Prüfungsauswahlen |
| `daten.json` | das Ergebnis, eingerückt, damit git es lesbar zeigt |
| `bauen.py` | setzt beides zusammen |
| `vokabelwerkstatt.html` | die veröffentlichte Datei — **nie von Hand ändern** |

## Die Vokabelliste wählen

Oben in der Leiste stehen **alle** Vokabellisten dieser Unit — V1, V2, V3 —
und darunter „＋ neue Liste anlegen". Voreingestellt ist **V1**: der
Normalfall ist eine Liste, zu der über die Zeit mehrere verschiedene
Prüfungen entstehen.

Was die Seite darunter zeigt — die 60 Wörter, die Schwierigkeitslineale, die
Prüfungsauswahlen — gehört zur **gewählten** Liste. Der Auftrag nennt sie
beim Namen, damit im Chat nichts verwechselt wird.

Aufgewertete Wörter gehören zu einer **neuen** Liste; bei einer bestehenden
sind die Felder deshalb aus. Eine bestehende Liste nachträglich zu verändern
hiesse, ihre Prüfungen ungültig zu machen — das verhindert die Kontrolle
`listenbezug` ohnehin.

## Zwei Regler

**Anspruch der Prüfung** wählt die geprüften Wörter, **Schwierigkeit des
Lückentexts** bestimmt, wie der Text liest. Beide zeigen als Strich auf der
Bahn, wo die Normallage liegt — beim Anspruch der Durchschnitt dieser Unit,
beim Lückentext der Durchschnitt aller 32 gelieferten Texte (Niveau A 3.0,
Niveau B 1.7). Unter dem Textregler steht das Zielband, das sich daraus
ergibt: Wörter, Satzlänge, Lesbarkeit, Nebensätze je Satz.

Die Seite rechnet das mit denselben Ankern wie die Anwendung — sie stehen in
`daten.json`, damit keine zweite Wahrheit entsteht.

## Was die Seite voreinstellt

Der Regler „Anspruch" steht je Unit auf dem **gemessenen** Durchschnitt der
bestehenden Prüfung, nicht auf einem Richtwert. Solange er dort steht und
zwölf Wörter eingestellt sind, zeigt die Seite die **tatsächliche** Auswahl
aus `kuratiert/`. Wird er bewegt, ist die Auswahl nur noch gerechnet — die
Seite schreibt dann „Näherung — endgültige Auswahl beim Bau" daneben, weil
erst `vocabmaster bauen` sie verbindlich trifft.

## Zwei Fähigkeiten der veröffentlichten Seite

* **Auftragsbuch** (`db`) — ein Auftrag lässt sich ablegen; im Chat genügt
  dann „Nimm den nächsten Auftrag."
* **Sichern** (`downloads`) — derselbe Auftrag als JSON-Datei.

Beide sind freiwillig: fehlt die Berechtigung, bleibt der Knopf weg und der
Befehl lässt sich weiterhin kopieren.
