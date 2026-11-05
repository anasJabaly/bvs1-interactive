# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo", "bvs1-interactive"]
# [tool.uv.sources]
# bvs1-interactive = { path = "../dist/bvs1_interactive-0.1.0-py3-none-any.whl" }
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from bvs1_interactive.scenarios import function_call
    from bvs1_interactive.widgets import ExecutionViewer
    return ExecutionViewer, function_call, mo


@app.cell
def _(function_call):
    scenario = function_call(7)
    return (scenario,)


@app.cell
def _(ExecutionViewer, mo, scenario):
    viewer = mo.ui.anywidget(ExecutionViewer(scenario))
    viewer
    return (viewer,)


@app.cell
def _(mo):
    mo.md("""
    ### Übung: Derselbe Baustein, ein anderes Argument

    - Welcher Rückgabewert entsteht mit dem Startargument 7?
    - Verändert bereits `jal` den Stackpointer?
    - Welcher Wert wird als Rücksprungadresse gespeichert?
    - Warum enthält der freigegebene Stack noch alte Werte?

    <details><summary>Erklärungen anzeigen</summary>

    `jal` ändert hier `ra` und den Programmzähler. Erst `addi sp, sp, -16`
    reserviert den Frame. Gesichert wird `0x1008`, die Adresse nach dem Aufruf.
    Beim Freigeben ändert sich nur `sp`; der Speicher wird nicht automatisch gelöscht.

    </details>
    """)
    return


if __name__ == "__main__":
    app.run()
