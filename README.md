# BVS1 Interactive

Wiederverwendbare Visualisierungen für Marimo: Code, Register und Stack.
Die Abläufe sind explizite Lehrszenarien, keine Emulation und kein aus einem
Compilerlauf gewonnenes Stacklayout.

## Lokal starten

```bash
uv sync --frozen
uv build --wheel
uv run marimo edit notebooks/01_funktionsaufruf.py
```

Bei Änderungen an der Bibliothek das Wheel vor Sandbox-Start oder Browserexport
neu bauen. Der Notebook-Verweis verwendet momentan Paketversion 0.1.0.

## Prüfen und veröffentlichen

```bash
uv run pytest
uv run marimo check notebooks/01_funktionsaufruf.py notebooks/02_funktionsaufruf_uebung.py
uv build --wheel
uv run python scripts/build_site.py
uv run python -m http.server 8000 --directory _site
```

Die letzte Adresse ist http://localhost:8000. GitHub Actions führt Tests,
Paketbau und Export aus und veröffentlicht die Startseite über GitHub Pages.
Das erste Beispiel wird als Lernoberfläche ohne Code-Editor veröffentlicht;
die Übung und der Techniktest öffnen sich im Editor. Im exportierten Editor gegebenenfalls zuerst die ausstehenden Zellen über
die gelbe Ausführen-Schaltfläche unten rechts starten.
Browseränderungen werden nicht automatisch im Repository gespeichert.

## Bausteine wiederverwenden

```python
from bvs1_interactive.scenarios import function_call
from bvs1_interactive.widgets import dashboard, stack_view, register_view, code_view

scenario = function_call(argument=7)
html = dashboard(scenario, index=3)
```

In Marimo wird HTML mit `mo.Html(html)` angezeigt. Einzelansichten liefern
HTML-Fragmente; sie verwenden das gemeinsame Stylesheet `widgets.STYLE` und
einen umschließenden Bereich mit CSS-Klasse `bvs`.

- `model/`: unveränderliche Beschreibungen von Szenarien und Zuständen.
- `scenarios/`: fachliche Lehrabläufe; keine Abhängigkeit von Marimo.
- `widgets/`: HTML-Ansichten; keine Emulations- oder Ablaufregeln.
- `integrations/`: Marimo-Steuerung für Vor, Zurück und Schrittregler.
- `notebooks/`: Lehrtext, Aufgaben und Zusammensetzung der Bausteine.

## Fachliches Modell

Jeder Zustand zeigt das Ergebnis der zuletzt beschriebenen Aktion. Der PC
markiert die nächste Anweisung. Gelbe Register unterscheiden sich vom direkt
vorherigen Szenarioschritt, auch beim Rückwärtsgehen oder Springen.

Der Beispielstack wächst abwärts. Jeder Slot umfasst 8 Byte, der gewählte
Frame 16 Byte. Freigegebene Bytes werden als alter Inhalt weiter angezeigt.
Das Speichern von ra und die Verwendung von s0 als Framepointer sind in diesem
Lehrbeispiel bewusst gewählt und für eine Blattfunktion nicht vorgeschrieben.
Die Arbeitsfläche enthält Abspielen/Pause, drei Geschwindigkeiten, einen
Schrittregler und die Wiederholung einzelner Wertübertragungen. Ein Kontextwechsel
ist noch nicht enthalten.

## Ein weiteres Szenario hinzufügen

1. `Scenario` mit `CodeLine`-Liste und `Step`-Zuständen erstellen.
2. Pro Schritt dieselben Register angeben; `pc` muss auf eine Codezeile zeigen.
3. Stackslots nach Adresse beschreiben; ein Slot entspricht hier 8 Byte.
4. Im Notebook nur Szenario und Aufgaben austauschen. Die Ansichten bleiben gleich.
5. Den neuen Ablauf fachlich testen; danach lokal den Browserexport prüfen.

Mit `02_funktionsaufruf_uebung.py` wird derselbe Satz von Ansichten ohne
Änderung am Darstellungscode mit einem anderen Startargument verwendet.


## Animierte Arbeitsfläche

```python
import marimo as mo
from bvs1_interactive.scenarios import function_call
from bvs1_interactive.widgets import ExecutionViewer

viewer = mo.ui.anywidget(ExecutionViewer(function_call(41)))
viewer
```

Die Auswahl steht im Marimo-Wrapper als `viewer.selected_index` zur Verfügung.
`ExecutionViewer` ist ein AnyWidget und funktioniert auch außerhalb von Marimo.
JS und CSS liegen mit im Python-Paket; Node oder ein Frontend-Build sind für die
Nutzung nicht nötig. C-Ansicht, Registerbank, ALU und RAM teilen denselben Ablauf.

`Step.transfers` beschreibt Wertflüsse unabhängig von den Ansichten. Ein Transfer
enthält Quelle, Ziel, Wert und Erklärung, etwa `register:ra` → `stack:32760`.
Gültige Endpunkte sind `code:<Adresse>`, `register:<Name>`, `stack:<Adresse>`,
`stack:top`, `cpu:pc` und `cpu:alu`. Diese Transfers sind didaktische Animationen,
keine behaupteten CPU-Takte. Rückwärtsgehen und Springen wählen einen Zustand;
Vorwärtsgehen und „Schritt“ animieren den Übergang aus dem vorherigen Zustand.
Pause hält auch die gerade sichtbare Bewegung an. Verminderte Bewegung wird
über `prefers-reduced-motion` berücksichtigt. RV64-Werte werden ohne Verlust
durch JavaScripts Zahlenformat an die Oberfläche übertragen.


## Lab-Anwendung: permute, Yield und Kontextwechsel

```bash
uv build --wheel
uv run marimo edit notebooks/03_prozess_yield_permute.py
```

Das neue Lab-Notebook verbindet fünf vollständig einsehbare Quelldateien
mit zwei Stackansichten, der aktiven CPU, den beiden gespeicherten Kontexten,
dem Zeichenarray und der UART-Ausgabe. Kapitel erlauben Sprünge zu Yield,
OS-Pause, Resume und Exit. „Folgen“ bindet die Codeansicht an den aktuellen
Schritt; ausgeschaltet können alle Dateien unabhängig gelesen werden.

Quellen und fachliche Grenzen: [docs/03_lab_quellen.md](docs/03_lab_quellen.md).
Insbesondere context.S ist eine gekennzeichnete erklärende Umsetzung,
keine als original verifizierte Kursdatei. Die 54 Schritte sind Lehrzustände,
keine gemessene RISC-V-Instruktionsspur.

Schnelles Ziehen am Schrittregler wird lokal sofort dargestellt; die Auswahl
wird nach 200 ms ohne weitere Änderung gebündelt an den Kernel zurückgemeldet.
