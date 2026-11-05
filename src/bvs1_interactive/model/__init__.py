"""Immutable, UI-independent descriptions of teaching scenarios."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CodeLine:
    address: int
    instruction: str
    comment: str = ""


@dataclass(frozen=True)
class StackSlot:
    address: int
    value: int | None
    label: str
    active: bool = True


@dataclass(frozen=True)
class Transfer:
    """A teaching animation between named view endpoints, not a hardware bus trace."""
    source: str
    target: str
    value: str
    label: str
    kind: str = "data"


@dataclass(frozen=True)
class Step:
    title: str
    explanation: str
    pc: int
    registers: tuple[tuple[str, int], ...]
    stack: tuple[StackSlot, ...] = ()
    event: str = ""
    transfers: tuple[Transfer, ...] = ()
    source_line: int | None = None

    def register(self, name: str) -> int:
        return dict(self.registers)[name]


@dataclass(frozen=True)
class Scenario:
    title: str
    description: str
    code: tuple[CodeLine, ...]
    steps: tuple[Step, ...]
    stack_top: int
    stack_bottom: int
    notes: str
    source_code: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.steps:
            raise ValueError("A scenario needs at least one step")
        addresses = {line.address for line in self.code}
        if len(addresses) != len(self.code):
            raise ValueError("Code addresses must be unique")
        names = tuple(name for name, _ in self.steps[0].registers)
        if len(set(names)) != len(names):
            raise ValueError("Register names must be unique")
        endpoints = {f"code:{address}" for address in addresses}
        endpoints |= {f"register:{name}" for name in names}
        endpoints |= {f"stack:{address}" for address in range(self.stack_bottom, self.stack_top, 8)}
        endpoints |= {"cpu:pc", "cpu:alu", "stack:top"}
        for step in self.steps:
            if step.source_line is not None and not 1 <= step.source_line <= len(self.source_code):
                raise ValueError("Source highlight must reference a displayed source line")
            for transfer in step.transfers:
                if transfer.source not in endpoints or transfer.target not in endpoints:
                    raise ValueError("Transfer endpoint is not present in the scenario")
                if transfer.kind not in {"data", "control"}:
                    raise ValueError("Transfer kind must be data or control")
            if step.pc not in addresses:
                raise ValueError("Each PC must reference a displayed code line")
            if tuple(name for name, _ in step.registers) != names:
                raise ValueError("Steps must use the same ordered register set")
            if not self.stack_bottom <= step.register("sp") <= self.stack_top:
                raise ValueError("Stack pointer is outside the displayed stack")
            slots = [slot.address for slot in step.stack]
            if len(set(slots)) != len(slots):
                raise ValueError("Stack slot addresses must be unique")
            if any(not self.stack_bottom <= a <= self.stack_top - 8 for a in slots):
                raise ValueError("Stack slot is outside the displayed stack")

    def at(self, index: int) -> Step:
        if not 0 <= index < len(self.steps):
            raise IndexError("Step index outside scenario")
        return self.steps[index]


def changed_registers(current: Step, previous: Step | None) -> frozenset[str]:
    if previous is None:
        return frozenset()
    old = dict(previous.registers)
    return frozenset(name for name, value in current.registers if old[name] != value)
