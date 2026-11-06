# CP1-Szenario: Quellen und Modellgrenzen

Das Szenario zeigt die Exercise-2-Anwendung mit der in der Vorbereitung
festgehaltenen möglichen CP1-Prozessimplementierung. Es emuliert keine CPU.

## Enthaltene Code-Dateien

- `main.c`: vollständig aus dem C-Referenzblock in
  `Vorbereitung/Exercise-2.md` übernommen, inklusive UART-Helfern.
- `process.c`: vollständig aus der möglichen Referenzlösung in
  `Vorbereitung/Checkpoint-1.md`, Abschnitt 10.9, übernommen.
- `process.h`: dokumentierte öffentliche Schnittstelle aus Exercise 2.
- `context.h`: erklärende Headerfassung anhand des dokumentierten Layouts.
- `context.S`: erklärende vollständige RV64-Umsetzung des dokumentierten
  Schemas `sd` → `ld` → `ret`. Die originale bereitgestellte Datei konnte
  hier nicht eingesehen werden. Die Ansicht kennzeichnet dies ausdrücklich.

Die Dateien liegen unter `src/bvs1_interactive/scenarios/lab_sources/` und
werden mit dem Wheel ausgeliefert. Sie dienen als lesbare Quellen des
Lehrszenarios und sind keine ausführbare Lab-Umgebung.

Die fachliche Semantik wurde mit den lokalen Aufgabenblättern
`BVS1-Exercise-02-Using-Your-First-Process-WS26-27.pdf` und
`BVS1-Checkpoint-01-I-Have-a-Process-WS26-27.pdf` abgeglichen.
Kursunterlagen: Stavros Kousidis, TH Köln / ICCT, WS 2026/27;
Lizenzhinweis der Aufgabenblätter: CC BY 4.0, soweit nicht anders angegeben.

## Was das Modell behauptet

- create baut einen Anfangskontext, startet aber worker nicht.
- Der Switch sichert ra, sp und s0–s11 in getrennte Kontextobjekte.
- Beim Yield bleiben worker, permute und der Yield-Pfad logisch aktiv.
- Der zweite run lädt die gespeicherte Fortsetzung in process_yield.
- Der Prozessstack und das Array werden nicht kopiert oder neu initialisiert.
- Yield setzt READY; Exit setzt FINISHED und speichert den Exitstatus.
- Die vier UART-Zeilen entsprechen der dokumentierten Basisanwendung.

## Was schematisch bleibt

Die Adressen sowie die dargestellte Nutzung von s0 und s1 sind bewusst
gewählte Modellwerte. Die OS-Stackpositionen sind dabei unterhalb des
innerhalb von p reservierten Prozessstackbereichs gewählt; die dargestellte
Rücksprungadresse in main unterscheidet sich von der in process_run gesicherten
Switch-Fortsetzung. Die Stackblöcke sind logische C-Aufrufketten, keine
vermessenen physischen Frames aus einem -O2-Build. UART-interne Aufrufe sind
für die Übersicht ausgeblendet. tmp ist eine logische Variable; wir legen
keinen tatsächlichen Register- oder Stackplatz dafür fest.

Das lokale p in main enthält das Prozessstackarray. Die zwei nebeneinander
gezeichneten Stackbereiche behaupten deshalb weder getrennte Adressräume
noch Speicherisolation. Das OS-Kontextobjekt kann nach Rückkehr von run
noch eine alte Momentaufnahme enthalten; es wird beim nächsten run erneut
gesichert. Kontextobjekte sind keine Live-Spiegel der CPU.

## Weiteres Material ergänzen

`ProcessScenario` enthält CodeDocument-Dateien, unveränderliche ProcessStep-
Zustände und Kapitelmarken. Die gemeinsame ExecutionViewer-Steuerung und
Animationsengine stellt sowohl dieses Szenario als auch das kleine
Funktionsaufruf-Beispiel dar. Weitere Prozessbeispiele tauschen die Daten
und Erklärungen aus, ohne eine zweite Abspielsteuerung zu implementieren.
