"""Marimo adapters. Import only when displaying a scenario."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlPanel:
    """Keep UI elements alive while their layout is displayed."""
    view: object
    widgets: tuple[object, ...]


def controls(scenario, index, set_index):
    """Create synchronized controls; call in a cell depending on get_index()."""
    import marimo as mo

    last = len(scenario.steps) - 1
    back = mo.ui.button(label="← Zurück", disabled=index == 0,
                        on_change=lambda _: set_index(max(0, index - 1)))
    forward = mo.ui.button(label="Weiter →", disabled=index == last,
                           on_change=lambda _: set_index(min(last, index + 1)))
    reset = mo.ui.button(label="Zum Anfang", disabled=index == 0,
                         on_change=lambda _: set_index(0))
    slider = mo.ui.slider(start=0, stop=last, value=index, show_value=True,
                          label="Szenarioschritt (ab 0)", full_width=True,
                          on_change=set_index)
    view = mo.vstack([mo.hstack([back, forward, reset], justify="start"), slider])
    return ControlPanel(view, (back, forward, reset, slider))
