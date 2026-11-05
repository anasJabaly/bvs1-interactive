"""Animated, reusable teaching workspace for Marimo and other widget hosts."""
from dataclasses import asdict
from pathlib import Path
import anywidget
import traitlets
from bvs1_interactive.model import Scenario


class ExecutionViewer(anywidget.AnyWidget):
    _esm = Path(__file__).with_name("viewer.js")
    _css = Path(__file__).with_name("viewer.css")
    scenario = traitlets.Dict().tag(sync=True)
    selected_index = traitlets.Int(0).tag(sync=True)

    def __init__(self, scenario: Scenario, **kwargs):
        payload = asdict(scenario)
        # JSON numbers cannot represent every RV64 register value exactly.
        for step in payload["steps"]:
            step["registers"] = [(name, str(value)) for name, value in step["registers"]]
            for slot in step["stack"]:
                if slot["value"] is not None:
                    slot["value"] = str(slot["value"])
        super().__init__(scenario=payload, **kwargs)

    @traitlets.validate("selected_index")
    def _validate_index(self, proposal):
        value = proposal["value"]
        if self.scenario and not 0 <= value < len(self.scenario["steps"]):
            raise traitlets.TraitError("Step index outside scenario")
        return value
