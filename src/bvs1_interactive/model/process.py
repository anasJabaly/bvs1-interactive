"""A teaching timeline of the CP1 process API, separate from instruction execution."""
from dataclasses import dataclass
from . import Transfer

REGISTERS = ("ra", "sp") + tuple(f"s{i}" for i in range(12))


@dataclass(frozen=True)
class CodeDocument:
    id: str
    title: str
    language: str
    lines: tuple[str, ...]
    provenance: str


@dataclass(frozen=True)
class SavedContext:
    id: str
    title: str
    registers: tuple[tuple[str, int], ...]
    ready_fields: tuple[str, ...]
    ra_label: str


@dataclass(frozen=True)
class StackRegion:
    id: str
    title: str
    sp: int
    frames: tuple[str, ...]
    allocated: bool = True


@dataclass(frozen=True)
class ProcessStep:
    title: str
    explanation: str
    document: str
    line: int
    location: str
    registers: tuple[tuple[str, int], ...]
    active_owner: str
    contexts: tuple[SavedContext, ...]
    regions: tuple[StackRegion, ...]
    process_state: str
    current_process: bool
    value: tuple[str, ...]
    tmp: str | None
    output: tuple[str, ...]
    event: str
    ra_label: str
    transfers: tuple[Transfer, ...] = ()
    focus_lines: tuple[int, ...] = ()
    worker_starts: int = 0
    exit_status: int | None = None

    def register(self, name: str) -> int:
        return dict(self.registers)[name]


@dataclass(frozen=True)
class ProcessScenario:
    title: str
    description: str
    documents: tuple[CodeDocument, ...]
    steps: tuple[ProcessStep, ...]
    chapters: tuple[tuple[str, int], ...]
    notes: str
    kind: str = "process"

    def __post_init__(self):
        docs = {doc.id: doc for doc in self.documents}
        if len(docs) != len(self.documents) or not self.steps:
            raise ValueError("A process scenario needs documents and steps")
        endpoints = {f"register:{name}" for name in REGISTERS}
        endpoints |= {f"context:{owner}:{field}" for owner in ("os", "process") for field in ("ra", "sp", "bank")}
        endpoints |= {"stack:os", "stack:process", "cpu:pc", "cpu:alu", "cpu:bank", "code:active", "local:tmp", "array:base"}
        endpoints |= {f"array:{i}" for i in range(5)}
        for step in self.steps:
            if step.document not in docs or not 1 <= step.line <= len(docs[step.document].lines):
                raise ValueError("Highlighted code line is missing")
            if any(not 1 <= line <= len(docs[step.document].lines) for line in step.focus_lines):
                raise ValueError("Highlighted code range is missing")
            if tuple(name for name, _ in step.registers) != REGISTERS:
                raise ValueError("All 14 cooperative context registers are required")
            if step.active_owner not in ("os", "process"):
                raise ValueError("Unknown active stack")
            if step.process_state not in ("—", "READY", "RUNNING", "FINISHED"):
                raise ValueError("Unknown lifecycle state")
            if step.register("sp") != next(r.sp for r in step.regions if r.id == step.active_owner):
                raise ValueError("Active CPU stack pointer and region disagree")
            if step.value and (len(step.value) != 5 or step.value[-1] != "\0"):
                raise ValueError("The permutation must preserve the null terminator")
            for transfer in step.transfers:
                if transfer.source not in endpoints or transfer.target not in endpoints:
                    raise ValueError("Unknown process animation endpoint")
        if any(not 0 <= i < len(self.steps) for _, i in self.chapters):
            raise ValueError("Chapter outside timeline")

    def at(self, index: int) -> ProcessStep:
        if not 0 <= index < len(self.steps):
            raise IndexError("Step index outside scenario")
        return self.steps[index]
