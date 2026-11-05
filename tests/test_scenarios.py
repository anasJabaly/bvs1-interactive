from dataclasses import replace
import pytest
from bvs1_interactive.scenarios import function_call
from bvs1_interactive.widgets import dashboard


def test_call_allocates_frame_only_after_jal():
    scenario = function_call()
    assert scenario.at(1).register("ra") == 0x1008
    assert scenario.at(1).register("sp") == 0x8000
    assert scenario.at(2).register("sp") == 0x7FF0
    assert all(step.register("sp") % 16 == 0 for step in scenario.steps)


@pytest.mark.parametrize("argument", [0, 7, 41, 999])
def test_return_restores_callee_saved_state_and_preserves_result(argument):
    scenario = function_call(argument)
    first, last = scenario.steps[0], scenario.steps[-1]
    assert last.register("a0") == argument + 1
    assert last.pc == 0x1008
    for register in ("sp", "s0"):
        assert last.register(register) == first.register(register)


def test_releasing_frame_does_not_erase_stack_bytes():
    scenario = function_call()
    before, after = scenario.at(8), scenario.at(9)
    assert [(s.address, s.value) for s in before.stack] == [(s.address, s.value) for s in after.stack]
    assert all(not s.active for s in after.stack)


def test_register_only_computation_does_not_change_stack():
    scenario = function_call()
    assert scenario.at(5).stack == scenario.at(6).stack


def test_views_support_both_scenarios_and_escape_scenario_content():
    for value in (7, 41):
        scenario = function_call(value)
        for index in range(len(scenario.steps)):
            html = dashboard(scenario, index)
            assert 'aria-current=step' in html
        assert str(value + 1) in dashboard(scenario, 10)
    unsafe = replace(function_call(), title='<script>alert(1)</script>')
    assert '<script>' not in dashboard(unsafe, 0)


def test_out_of_range_steps_are_rejected():
    scenario = function_call()
    with pytest.raises(IndexError):
        scenario.at(-1)
    with pytest.raises(IndexError):
        scenario.at(len(scenario.steps))


def test_animation_metadata_matches_save_and_restore_operations():
    scenario = function_call()
    store = scenario.at(3).transfers[0]
    load = scenario.at(8).transfers[0]
    assert (store.source, store.target) == ("register:ra", "stack:32760")
    assert (load.source, load.target) == (store.target, store.source)
    assert store.value == load.value == "0x1008"


def test_invalid_animation_endpoint_is_rejected():
    from bvs1_interactive.model import Transfer
    scenario = function_call()
    broken = replace(scenario.at(1), transfers=(Transfer("register:missing", "cpu:pc", "0", "broken"),))
    with pytest.raises(ValueError, match="endpoint"):
        replace(scenario, steps=(scenario.at(0), broken))


def test_widget_preserves_large_register_values_and_rejects_invalid_selection():
    import traitlets
    from bvs1_interactive.widgets import ExecutionViewer
    value = 2**60 + 1
    widget = ExecutionViewer(function_call(value))
    assert dict(widget.scenario["steps"][0]["registers"])["a0"] == str(value)
    assert dict(widget.scenario["steps"][6]["registers"])["a0"] == str(value + 1)
    with pytest.raises(traitlets.TraitError):
        widget.selected_index = -1
    widget.close()
