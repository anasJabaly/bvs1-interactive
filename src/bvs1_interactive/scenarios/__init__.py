"""Explicit teaching timelines; no instruction execution or emulation."""
from dataclasses import replace
from bvs1_interactive.model import CodeLine, Scenario, StackSlot, Step, Transfer


def function_call(argument: int = 41) -> Scenario:
    """A deliberately explicit RV64 teaching example, not compiler output.

    Each state is AFTER the described action. PC marks the NEXT instruction.
    The 16-byte frame is chosen for teaching; even a leaf function need not
    actually save ra or use s0 in optimized compiler output.
    """
    if not 0 <= argument < (1 << 63) - 1:
        raise ValueError("Choose a nonnegative teaching value below 2**63 - 1")
    code = (
        CodeLine(0x1004, "jal ra, increment", "Funktionsaufruf"),
        CodeLine(0x1008, "…", "Aufrufer setzt hier fort"),
        CodeLine(0x1100, "addi sp, sp, -16", "16 Byte reservieren"),
        CodeLine(0x1104, "sd ra, 8(sp)", "Rücksprungadresse sichern"),
        CodeLine(0x1108, "sd s0, 0(sp)", "Alten Framepointer sichern"),
        CodeLine(0x110C, "addi s0, sp, 16", "Framepointer setzen"),
        CodeLine(0x1110, "addi a0, a0, 1", "Ergebnis berechnen"),
        CodeLine(0x1114, "ld s0, 0(sp)", "Framepointer wiederherstellen"),
        CodeLine(0x1118, "ld ra, 8(sp)", "Rücksprungadresse laden"),
        CodeLine(0x111C, "addi sp, sp, 16", "Stackframe freigeben"),
        CodeLine(0x1120, "ret", "Zum Aufrufer zurückkehren"),
    )
    def regs(sp=0x8000, ra=0x9000, s0=0x8100, a0=argument):
        return (("sp", sp), ("ra", ra), ("s0", s0), ("a0", a0))

    reserved = (StackSlot(0x7FF8, None, "Reserviert; Inhalt nicht festgelegt"),
                StackSlot(0x7FF0, None, "Reserviert; Inhalt nicht festgelegt"))
    saved_ra = (StackSlot(0x7FF8, 0x1008, "Gesicherte ra"), reserved[1])
    saved = (saved_ra[0], StackSlot(0x7FF0, 0x8100, "Gesicherte s0"))
    released = tuple(StackSlot(s.address, s.value, s.label, False) for s in saved)
    steps = (
        Step("Bereit zum Aufruf", f"a0 enthält das Argument {argument}. Der Aufrufer verwendet sp = 0x8000. Die Funktion hat noch keinen Stackframe.", 0x1004, regs(), event="Ausgangszustand"),
        Step("Aufruf und Rücksprungadresse", "jal setzt ra auf 0x1008 und verzweigt zur Funktion. Ein Aufruf reserviert nicht automatisch einen Stackframe.", 0x1100, regs(ra=0x1008), event="jal ra, increment"),
        Step("Stackframe reserviert", "sp sinkt um 16 Byte auf 0x7ff0. Der Stack wächst zu kleineren Adressen. Die reservierten Bytes sind noch nicht initialisiert.", 0x1104, regs(sp=0x7FF0, ra=0x1008), reserved, "addi sp, sp, -16"),
        Step("Rücksprungadresse gesichert", "Der Wert von ra wird bei sp + 8 gespeichert. ra ist weiterhin auch im Register vorhanden.", 0x1108, regs(sp=0x7FF0, ra=0x1008), saved_ra, "sd ra, 8(sp)"),
        Step("Alter Framepointer gesichert", "Der bisherige Wert von s0 liegt jetzt bei sp. s0 ist ein callee-saved Register und wird vor der Rückkehr wiederhergestellt.", 0x110C, regs(sp=0x7FF0, ra=0x1008), saved, "sd s0, 0(sp)"),
        Step("Framepointer gesetzt", "s0 zeigt in diesem gewählten Layout auf das obere Ende des Frames. sp zeigt weiterhin auf dessen unteres Ende.", 0x1110, regs(sp=0x7FF0, ra=0x1008, s0=0x8000), saved, "addi s0, sp, 16"),
        Step("Ergebnis im Register", f"a0 steigt von {argument} auf {argument + 1}. Hier ist keine lokale Variable auf dem Stack nötig. a0 dient auch als Rückgaberegister.", 0x1114, regs(sp=0x7FF0, ra=0x1008, s0=0x8000, a0=argument + 1), saved, "addi a0, a0, 1"),
        Step("Framepointer wiederhergestellt", "s0 erhält den gesicherten Wert 0x8100 zurück. Das Lesen löscht den Speicherinhalt nicht.", 0x1118, regs(sp=0x7FF0, ra=0x1008, a0=argument + 1), saved, "ld s0, 0(sp)"),
        Step("Rücksprungadresse geladen", "ra wird aus dem Stack geladen. Sein Wert ändert sich hier nicht, weil diese Blattfunktion keinen weiteren Aufruf ausgeführt hat.", 0x111C, regs(sp=0x7FF0, ra=0x1008, a0=argument + 1), saved, "ld ra, 8(sp)"),
        Step("Stackframe freigegeben", "sp steigt zurück auf 0x8000. Die Bytes darunter sind nicht mehr Teil des aktiven Frames; ihre bisherigen Inhalte werden nicht automatisch gelöscht.", 0x1120, regs(ra=0x1008, a0=argument + 1), released, "addi sp, sp, 16"),
        Step("Zurück beim Aufrufer", f"ret setzt den Programmzähler auf die Adresse in ra: 0x1008. Das Ergebnis {argument + 1} liegt in a0; sp und s0 sind wiederhergestellt.", 0x1008, regs(ra=0x1008, a0=argument + 1), released, "ret"),
    )
    # Animation metadata belongs to the scenario; views need no instruction parser.
    transfers = (
        (),
        (Transfer("code:4100", "register:ra", "0x1008", "Rücksprungadresse merken", "control"),
         Transfer("code:4352", "cpu:pc", "0x1100", "Zur Funktion springen", "control")),
        (Transfer("register:sp", "cpu:alu", "−16", "Stackpointer verkleinern"),
         Transfer("cpu:alu", "register:sp", "0x7ff0", "Neuen Stackpointer setzen")),
        (Transfer("register:ra", "stack:32760", "0x1008", "ra in den Stack schreiben"),),
        (Transfer("register:s0", "stack:32752", "0x8100", "s0 in den Stack schreiben"),),
        (Transfer("register:sp", "register:s0", "0x8000", "Framepointer = sp + 16"),),
        (Transfer("register:a0", "cpu:alu", str(argument), "Argument zur ALU"),
         Transfer("cpu:alu", "register:a0", str(argument + 1), "Ergebnis zurück nach a0")),
        (Transfer("stack:32752", "register:s0", "0x8100", "Alten Framepointer laden"),),
        (Transfer("stack:32760", "register:ra", "0x1008", "Rücksprungadresse laden"),),
        (Transfer("register:sp", "cpu:alu", "+16", "Stackframe freigeben"),
         Transfer("cpu:alu", "register:sp", "0x8000", "Stackpointer zurücksetzen")),
        (Transfer("register:ra", "cpu:pc", "0x1008", "Rücksprungadresse wird PC", "control"),
         Transfer("cpu:pc", "code:4104", "0x1008", "Beim Aufrufer fortsetzen", "control")),
    )
    source_lines = (4, 1, 1, 1, 1, 1, 2, 3, 3, 3, 5)
    steps = tuple(replace(step, transfers=transfers[i], source_line=source_lines[i])
                  for i, step in enumerate(steps))
    return Scenario(
        "Wie verändert ein Funktionsaufruf den Stack?",
        f"Ein Aufruf von increment({argument}) – Schritt für Schritt.",
        code, steps, 0x8000, 0x7FE0,
        "Schematisches RV64-Beispiel mit festgelegten Zuständen. Kein Emulator und kein tatsächliches -O2-Stacklayout. Adressen und Frameaufbau sind für die Erklärung gewählt. Das Sichern von ra und ein Framepointer sind für diese einfache Blattfunktion nicht zwingend nötig. Ein Kontextwechsel ist noch nicht Teil dieses Beispiels.",
        ("int increment(int x) {", "    return x + 1;", "}",
         f"int result = increment({argument});", "// Ergebnis liegt jetzt in result"),
    )
