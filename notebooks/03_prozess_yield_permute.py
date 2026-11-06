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
    from bvs1_interactive.scenarios.process_lab import process_lab
    from bvs1_interactive.widgets import ExecutionViewer
    return ExecutionViewer, mo, process_lab


@app.cell
def _(ExecutionViewer, mo, process_lab):
    lab = mo.ui.anywidget(ExecutionViewer(process_lab()))
    lab
    return (lab,)


@app.cell
def _(mo):
    mo.md("""
    <details><summary>Fragen zum Lab</summary>

    1. Warum ruft create noch nicht worker auf?
    2. Welche logischen Aufrufe sind beim Yield noch aktiv?
    3. Warum genügt es nicht, nur ra zu laden?
    4. Wo beginnt Resume tatsächlich: in worker oder im Yield-Pfad?
    5. Welche Daten bleiben beim Wechsel auf den OS-Stack erhalten?
    6. Was unterscheidet READY nach Yield von FINISHED nach Exit?

    </details>
    """)
    return


if __name__ == "__main__":
    app.run()
