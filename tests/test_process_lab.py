from dataclasses import replace
import re
import pytest
from bvs1_interactive.scenarios.process_lab import process_lab
from bvs1_interactive.model.process import REGISTERS
from bvs1_interactive.widgets import ExecutionViewer


def find(scenario, title):
    return next(step for step in scenario.steps if step.title == title)


def test_create_prepares_start_context_without_calling_worker():
    step = find(process_lab(), "create bereitet vor")
    process = next(c for c in step.contexts if c.id == "process")
    assert step.active_owner == "os"
    assert step.process_state == "READY"
    assert step.worker_starts == 0 and step.value == ()
    assert process.ready_fields == REGISTERS
    assert dict(process.registers)["sp"] % 16 == 0
    assert process.ra_label.startswith("process_start")


def test_yield_keeps_array_and_logical_call_chain_alive():
    scenario = process_lab()
    before = find(scenario, "yield unterbricht, beendet aber nicht")
    paused = find(scenario, "OS läuft, Prozess ruht")
    assert paused.active_owner == "os" and not paused.current_process
    assert paused.process_state == "READY"
    assert paused.value == before.value == tuple("VBS1\0")
    process_stack = lambda step: next(r for r in step.regions if r.id == "process")
    assert process_stack(paused) == process_stack(before)
    assert process_stack(paused).frames == ("process_start", "worker", "permute", "process_yield")


def test_resume_restores_saved_context_before_unwinding_yield():
    scenario = process_lab()
    paused = find(scenario, "OS läuft, Prozess ruht")
    saved = next(c for c in paused.contexts if c.id == "process")
    resumed = find(scenario, "Resume beginnt im unterbrochenen Yield")
    assert resumed.registers == saved.registers
    assert resumed.ra_label.startswith("process_yield")
    assert resumed.process_state == "RUNNING" and resumed.current_process
    assert resumed.value == paused.value
    assert resumed.worker_starts == 1
    assert max(s.worker_starts for s in scenario.steps) == 1


def test_character_stores_and_null_terminator_are_exact():
    scenario = process_lab()
    writes = [s for s in scenario.steps if s.transfers and any(t.target.startswith("array:") for t in s.transfers)]
    assert ["".join(s.value[:-1]) for s in writes] == ["BVS1", "BVS1", "VVS1", "VBS1", "VB11", "VB1S"]
    assert all(s.value[-1] == "\0" for s in scenario.steps if s.value)


def test_final_state_and_uart_output_match_exercise_two():
    last = process_lab().steps[-1]
    assert last.active_owner == "os" and not last.current_process
    assert last.process_state == "FINISHED" and last.exit_status == 0
    assert last.output == (
        "process: before yield: VBS1", "os: process yielded",
        "process: result: VB1S", "os: process exited",
    )


def test_os_and_process_saved_contexts_do_not_track_live_cpu():
    scenario = process_lab()
    after_save = find(scenario, "OS: s0–s11 sichern")
    in_worker = find(scenario, "worker legt value an")
    os_context = lambda step: next(c for c in step.contexts if c.id == "os")
    assert os_context(after_save) == os_context(in_worker)
    assert dict(os_context(in_worker).registers)["s1"] != in_worker.register("s1")


def test_explanatory_switch_offsets_match_all_fourteen_registers():
    scenario = process_lab()
    source = "\n".join(next(d for d in scenario.documents if d.id == "context.S").lines)
    for mnemonic, pointer in (("sd", "a0"), ("ld", "a1")):
        fields = re.findall(rf"{mnemonic} (ra|sp|s\d+), (\d+)\({pointer}\)", source)
        assert fields == [(name, str(i * 8)) for i, name in enumerate(REGISTERS)]
    assert "nicht als originale Kursdatei verifiziert" in next(d for d in scenario.documents if d.id == "context.S").provenance


def test_serialized_contexts_keep_numeric_values_and_animation_endpoints():
    widget = ExecutionViewer(process_lab())
    payload = widget.scenario
    assert payload["kind"] == "process" and len(payload["documents"]) == 5
    context = payload["steps"][1]["contexts"][1]
    assert all(isinstance(value, str) for _, value in context["registers"])
    widget.close()


def test_missing_source_line_is_rejected():
    scenario = process_lab()
    with pytest.raises(ValueError, match="code line"):
        replace(scenario, steps=(replace(scenario.steps[0], line=99999),))
