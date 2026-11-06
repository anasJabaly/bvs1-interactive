"""Explicit CP1 teaching states based on the documented application and reference."""
from pathlib import Path
from bvs1_interactive.model import Transfer
from bvs1_interactive.model.process import (
    CodeDocument, ProcessScenario, ProcessStep, REGISTERS, SavedContext, StackRegion,
)


def process_lab() -> ProcessScenario:
    folder = Path(__file__).with_name("lab_sources")
    provenance = {
        "main.c": "Vollständige Anwendungsreferenz aus Vorbereitung/Exercise-2.md; UART-Helfer enthalten.",
        "process.c": "Mögliche CP1-Referenzlösung aus Vorbereitung/Checkpoint-1.md, Abschnitt 10.9.",
        "process.h": "Öffentliche Schnittstelle aus Vorbereitung/Exercise-2.md.",
        "context.h": "Erklärende vollständige Headerfassung zum dokumentierten Registerlayout.",
        "context.S": "Erklärende vollständige Umsetzung des dokumentierten sd/ld/ret-Schemas; nicht als originale Kursdatei verifiziert.",
    }
    documents = tuple(CodeDocument(name, name, "asm" if name.endswith(".S") else "c",
                         tuple((folder/name).read_text().splitlines()), provenance[name])
                      for name in ("main.c", "process.c", "context.S", "process.h", "context.h"))
    docs = {doc.id: doc for doc in documents}

    def line(document, needle, occurrence=0):
        return [i+1 for i, text in enumerate(docs[document].lines) if needle in text][occurrence]

    live = dict(zip(REGISTERS, (0x1000, 0x5000) + tuple(0x8100+i*0x10 for i in range(12))))
    saved = {owner: dict.fromkeys(REGISTERS, 0) for owner in ("os", "process")}
    ready = {owner: set() for owner in saved}
    labels = {"os": "Noch nicht gesichert", "process": "Noch nicht vorbereitet"}
    frames = {"os": ["main"], "process": []}
    pointers = {"os": 0x5000, "process": 0x7000}
    active = "os"; state = "—"; current = False; allocated = False
    value = []; tmp = None; output = []; starts = 0; exit_status = None
    ra_label = "Aufrufer von main"
    steps = []; chapters = []
    OS_RETURN, YIELD_RETURN, EXIT_RETURN, START = 0x1010, 0x2020, 0x2030, 0x3000
    AFTER_ENTRY, AFTER_PERMUTE, AFTER_YIELD = 0x3010, 0x3020, 0x3030

    def emit(title, explanation, document, needle, location, transfers=(), occurrence=0, focus=()):
        steps.append(ProcessStep(
            title, explanation, document, line(document, needle, occurrence), location,
            tuple((name, live[name]) for name in REGISTERS), active,
            tuple(SavedContext(owner, "os_context" if owner == "os" else "p.context",
                  tuple((name, saved[owner][name]) for name in REGISTERS),
                  tuple(name for name in REGISTERS if name in ready[owner]), labels[owner])
                  for owner in ("os", "process")),
            tuple(StackRegion(owner, "OS-Stack" if owner == "os" else "Prozessstack",
                  pointers[owner], tuple(frames[owner]), owner == "os" or allocated)
                  for owner in ("os", "process")),
            state, current, tuple(value), tmp, tuple(output), needle.strip(), ra_label,
            tuple(transfers), tuple(focus), starts, exit_status,
        ))

    def chapter(title):
        chapters.append((title, len(steps)))

    def switch(target):
        nonlocal active, ra_label
        source = active
        source_title = "OS" if source == "os" else "Prozess"
        target_title = "OS" if target == "os" else "Prozess"
        for field, fields, needle in (
            ("ra", ("ra",), "sd ra,"),
            ("sp", ("sp",), "sd sp,"),
            ("bank", tuple(f"s{i}" for i in range(12)), "sd s0,"),
        ):
            for name in fields:
                saved[source][name] = live[name]; ready[source].add(name)
            if field == "ra": labels[source] = ra_label
            transfer_value = "s0–s11" if field == "bank" else f"0x{live[field]:04x}"
            emit(f"{source_title}: {('s0–s11' if field == 'bank' else field)} sichern",
                 f"context_switch schreibt {('die zwölf callee-saved Register' if field == 'bank' else field)} aus der CPU nach {('os_context' if source == 'os' else 'p.context')}. Der Stack selbst wird nicht kopiert.",
                 "context.S", needle, "context_switch · sichern",
                 (Transfer("cpu:bank" if field == "bank" else f"register:{field}", f"context:{source}:{field}", transfer_value, f"{source_title}-Kontext sichern"),),
                 focus=tuple(line("context.S", f"sd s{i},") for i in range(12)) if field == "bank" else ())
        for field, fields, needle in (
            ("ra", ("ra",), "ld ra,"),
            ("sp", ("sp",), "ld sp,"),
            ("bank", tuple(f"s{i}" for i in range(12)), "ld s0,"),
        ):
            for name in fields: live[name] = saved[target][name]
            if field == "ra": ra_label = labels[target]
            if field == "sp": active = target; pointers[target] = live["sp"]
            transfer_value = "s0–s11" if field == "bank" else f"0x{live[field]:04x}"
            emit(f"{target_title}: {('s0–s11' if field == 'bank' else field)} laden",
                 (f"Das geladene sp aktiviert den {target_title}-Stack. Seine vorhandenen Daten bleiben an ihrem Ort." if field == "sp" else f"Die CPU lädt {('die zwölf s-Register' if field == 'bank' else 'die Rücksprungadresse')} aus dem gespeicherten {target_title}-Kontext. Geladener Kontext und laufende CPU sind getrennte Dinge."),
                 "context.S", needle, "context_switch · laden",
                 (Transfer(f"context:{target}:{field}", "cpu:bank" if field == "bank" else f"register:{field}", transfer_value, f"{target_title}-Kontext laden"),),
                 focus=tuple(line("context.S", f"ld s{i},") for i in range(12)) if field == "bank" else ())
        emit(f"ret: {target_title} fortsetzen", f"ret verwendet die geladene ra ({ra_label}). Erst jetzt verlässt die Ausführung den Switch. Der Kontext enthält hier kein separates PC-Feld.",
             "context.S", "    ret", ra_label,
             (Transfer("register:ra", "cpu:pc", f"0x{live['ra']:04x}", "Geladene ra bestimmt die Fortsetzung", "control"),))

    chapter("Vorbereiten")
    emit("Noch kein Prozess gestartet", "main besitzt das lokale Prozessobjekt p. Sein Stackarray ist reservierter Speicher innerhalb dieses weiterhin lebenden Objekts; worker läuft noch nicht.",
         "main.c", "struct process p;", "main")
    allocated = True; frames["os"] = ["main", "process_create"]
    for name in REGISTERS: saved["process"][name] = 0
    saved["process"]["sp"] = 0x7000; saved["process"]["ra"] = START
    ready["process"].update(REGISTERS); labels["process"] = "process_start · erster Einstieg"
    state = "READY"
    emit("create bereitet vor", "entry wird worker. Ein ausgerichteter Anfangs-sp, ra = process_start und zwölf initiale s-Register bilden den Startkontext. create ruft worker nicht auf.",
         "process.c", "process->context.ra =", "process_create",
         (Transfer("code:active", "context:process:ra", "process_start", "Ersten Einstieg vorbereiten", "control"),
          Transfer("stack:process", "context:process:sp", "0x7000", "Anfangs-sp des eigenen Stacks merken")))
    frames["os"] = ["main"]
    emit("READY, noch ohne Ausführung", "p ist bereit. Das Prozessstackarray existiert, aber worker, permute und das lokale Array value sind noch nicht aktiv.",
         "main.c", "process_create(&p, worker);", "main")

    chapter("Erster Start")
    state = "RUNNING"; current = True; frames["os"] = ["main", "process_run"]
    live["sp"] = pointers["os"] = 0x4FC0; live["ra"] = OS_RETURN; ra_label = "process_run · nach context_switch"
    emit("run gibt dem Prozess die CPU", "process_run setzt current_process = &p und RUNNING. Beim Aufruf von context_switch zeigt ra auf die Fortsetzung in process_run.",
         "process.c", "context_switch(&os_context", "process_run → context_switch")
    switch("process")
    frames["process"] = ["process_start"]
    emit("Erster Einstieg über process_start", "Der künstlich vorbereitete Startkontext führt in process_start. Diese interne Funktion ruft die gespeicherte Entry-Funktion worker auf.",
         "process.c", "current_process->entry();", "process_start",
         (Transfer("code:active", "cpu:pc", "worker", "Entry-Funktion erstmals aufrufen", "control"),))
    starts += 1; frames["process"] = ["process_start", "worker"]
    live["sp"] = pointers["process"] = 0x6FE0; live["ra"] = AFTER_ENTRY; ra_label = "process_start · nach entry"
    live["s0"] = 0x7000; live["s1"] = 0x6FE0
    value[:] = list("BVS1") + ["\0"]
    emit("worker legt value an", "Das veränderbare Array value gehört zu worker. Es enthält B, V, S, 1 und das Nullzeichen. Genau dieses Array bleibt beim Yield erhalten.",
         "main.c", 'char value[] = "BVS1";', "worker",
         (Transfer("code:active", "array:base", "BVS1", "Lokales Array initialisieren"),))
    frames["process"].append("permute");live["sp"] = pointers["process"] = 0x6FC0
    live["ra"] = AFTER_PERMUTE;ra_label = "worker · nach permute"
    emit("permute arbeitet am selben Array", "Der Parameter char value[] ist ein Zeiger auf das vorhandene Array. Es entsteht keine zweite Arraykopie. worker und permute sind logisch gleichzeitig aktiv.",
         "main.c", "permute(value);", "worker → permute",
         (Transfer("code:active", "array:base", "value*", "Zeiger auf dasselbe Array übergeben"),))
    chapter("Tausch 1")
    tmp = value[0]
    emit("Erstes Zeichen zwischenspeichern", "tmp merkt sich B, bevor value[0] überschrieben wird. Die Ablage von tmp ist hier eine logische C-Variable; wir behaupten keinen festen Register- oder Stackplatz.",
         "main.c", "tmp = value[0];", "permute",
         (Transfer("array:0", "local:tmp", tmp, "B nach tmp übernehmen"),))
    value[0] = value[1]
    emit("V an Position 0 schreiben", "value[0] übernimmt V. Der Zwischenstand VVS1 ist korrekt, weil B noch in tmp erhalten ist.",
         "main.c", "value[0] = value[1];", "permute",
         (Transfer("array:1", "array:0", value[0], "V von Index 1 nach Index 0 kopieren"),))
    value[1] = tmp
    emit("B aus tmp zurückschreiben", "Der erste Tausch ist abgeschlossen: value enthält VBS1. Das abschließende Nullzeichen bleibt unverändert.",
         "main.c", "value[1] = tmp;", "permute",
         (Transfer("local:tmp", "array:1", tmp, "B an Index 1 schreiben"),))
    output.append("process: before yield: VBS1")
    prefix = line("main.c", 'uart_puts("process: before yield:')
    emit("Ausgabe vor Yield", "Die drei UART-Aufrufe geben die erste Prozesszeile aus. Für die Übersicht sind UART-interne Aufrufe in der Stackzeichnung ausgeblendet.",
         "main.c", 'uart_puts("process: before yield:', "permute · UART", focus=range(prefix,prefix+3))

    chapter("Yield")
    frames["process"].append("process_yield");live["sp"] = pointers["process"] = 0x6FA0
    live["ra"] = AFTER_YIELD;ra_label = "permute · nach process_yield"
    state = "READY"
    emit("yield unterbricht, beendet aber nicht", "process_yield setzt READY. worker und permute sind nicht zurückgekehrt. Das Array bleibt VBS1; das OS soll seine eigene unterbrochene Ausführung fortsetzen.",
         "process.c", "process->state = READY;", "process_yield", occurrence=1)
    live["ra"] = YIELD_RETURN;ra_label = "process_yield · nach context_switch"
    emit("Prozess → OS: Richtung wählen", "Die Argumente sind &process->context und &os_context: zuerst den laufenden Prozess sichern, danach den OS-Kontext laden.",
         "process.c", "context_switch(&process->context", "process_yield → context_switch")
    switch("os")
    current = False
    emit("Der erste run kehrt vom Switch zurück", "Die geladene OS-ra führt hinter den Switch in process_run. current_process wird auf 0 gesetzt. Der Prozess bleibt READY und seine Aufrufkette bleibt erhalten.",
         "process.c", "current_process = 0;", "process_run · Fortsetzung")
    chapter("OS nach Yield")
    frames["os"] = ["main"];live["sp"] = pointers["os"] = 0x5000
    live["ra"] = 0x1040; ra_label = "main · nach erstem process_run"
    output.append("os: process yielded")
    emit("OS läuft, Prozess ruht", "main beobachtet READY und druckt die OS-Meldung. Der Prozessstack liegt unverändert daneben: worker → permute → process_yield. Kein Stackarray wurde kopiert oder neu aufgebaut.",
         "main.c", 'uart_puts("os: process yielded', "main · nach erstem run")

    chapter("Resume")
    current = True;state = "RUNNING";frames["os"] = ["main", "process_run"]
    live["sp"] = pointers["os"] = 0x4FC0;live["ra"] = OS_RETURN;ra_label = "process_run · nach context_switch"
    emit("Zweiter run lädt die Fortsetzung", "main ruft process_run erneut auf. RUNNING wird gesetzt; der Anfangskontext wird nicht neu erzeugt. p.context enthält die beim Yield gespeicherte Fortsetzung.",
         "main.c", "process_run(&p);", "main · zweiter run", occurrence=1)
    switch("process")
    emit("Resume beginnt im unterbrochenen Yield", "Die geladene ra führt zuerst hinter context_switch in process_yield. Sie zeigt weder auf worker noch direkt auf den zweiten Zeichentausch.",
         "process.c", "context_switch(&process->context", "process_yield · Fortsetzung")
    frames["process"] = ["process_start", "worker", "permute"]
    live["sp"] = pointers["process"] = 0x6FC0;live["ra"] = AFTER_YIELD;ra_label = "permute · nach process_yield"
    emit("yield kehrt zu permute zurück", "Dieselbe permute-Ausführung läuft weiter. value ist weiterhin VBS1. worker wurde genau einmal gestartet; seine lokale Initialisierung wird nicht wiederholt.",
         "main.c", "process_yield();", "permute · hinter yield")

    chapter("Tausch 2")
    tmp = value[2]
    emit("S zwischenspeichern", "Der zweite Tausch beginnt erst nach Resume. tmp übernimmt S aus Index 2.",
         "main.c", "tmp = value[2];", "permute",
         (Transfer("array:2", "local:tmp", tmp, "S nach tmp übernehmen"),))
    value[2] = value[3]
    emit("1 an Position 2 schreiben", "Der Zwischenstand lautet VB11. S ist weiterhin in tmp erhalten.",
         "main.c", "value[2] = value[3];", "permute",
         (Transfer("array:3", "array:2", value[2], "1 an Index 2 schreiben"),))
    value[3] = tmp
    emit("Ergebnis: VB1S", "tmp liefert S für Index 3. Beide Tausche sind abgeschlossen; das Nullzeichen an Index 4 bleibt an seinem Platz.",
         "main.c", "value[3] = tmp;", "permute",
         (Transfer("local:tmp", "array:3", tmp, "S an Index 3 schreiben"),))
    frames["process"] = ["process_start", "worker"]
    live["sp"] = pointers["process"] = 0x6FE0;live["ra"] = AFTER_PERMUTE;ra_label = "worker · nach permute";tmp = None
    output.append("process: result: VB1S")
    prefix = line("main.c", 'uart_puts("process: result:')
    emit("permute kehrt zu worker zurück", "worker gibt das Ergebnis VB1S aus. Die zweite run-Ausführung ist noch aktiv; erst exit gibt die Kontrolle endgültig zurück.",
         "main.c", 'uart_puts("process: result:', "worker · UART", focus=range(prefix,prefix+3))

    chapter("Exit")
    frames["process"].append("process_exit");live["sp"] = pointers["process"] = 0x6FC0
    state = "FINISHED";exit_status = 0
    live["ra"] = EXIT_RETURN;ra_label = "process_exit · nach context_switch (nicht fortsetzen)"
    emit("exit setzt FINISHED", "process_exit speichert Status 0 und setzt FINISHED. Anders als Yield erlaubt dieser Zustand keinen weiteren run. Die Stackdaten müssen dazu nicht gelöscht werden.",
         "process.c", "process->state = FINISHED;", "process_exit")
    emit("Prozess → OS nach Exit", "Auch exit nutzt den gleichen Kontextwechsel. Der Lebenszykluszustand verhindert später, dass dieser beendete Kontext wieder geladen wird.",
         "process.c", "context_switch(&process->context", "process_exit → context_switch", occurrence=1)
    switch("os")
    current = False
    emit("Zweiter run kommt zurück", "Das OS setzt process_run hinter context_switch fort und löscht current_process. Der Prozess ist FINISHED; ein weiterer run würde vor dem Switch zurückkehren.",
         "process.c", "current_process = 0;", "process_run · nach Exit")
    frames["os"] = ["main"];live["sp"] = pointers["os"] = 0x5000
    live["ra"] = 0x1050; ra_label = "main · nach zweitem process_run"
    output.append("os: process exited")
    chapter("Ergebnis")
    emit("OS sieht den beendeten Prozess", "main prüft FINISHED und druckt die letzte Zeile. value bleibt im dargestellten Stackbereich als alter Inhalt sichtbar. Die Prozessausführung darf nicht fortgesetzt werden.",
         "main.c", 'uart_puts("os: process exited', "main · abgeschlossen")
    return ProcessScenario(
        "CP1: permute, Yield und Kontextwechsel",
        "Die dokumentierte Exercise-2-Anwendung mit der CP1-Referenzimplementierung.",
        documents, tuple(steps), tuple(chapters),
        "Anwendung und process.c stammen aus euren lokalen Leitfäden. context.h/context.S sind als erklärende Fassungen gekennzeichnet. Logische C-Aufrufketten und frei gewählte Modelladressen; kein gemessenes -O2-Stacklayout. Kontextwechsel sichern ra, sp und s0–s11, nicht den gesamten Stack. UART-interne Frames sind ausgeblendet. Der reservierte Prozessstack liegt in p innerhalb des weiterhin lebenden main-Aufrufs; getrennte Darstellung bedeutet keine Speicherisolation.",
    )
