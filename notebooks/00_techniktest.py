# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo", "bvs1-interactive"]
#
# [tool.uv.sources]
# bvs1-interactive = { path = "../dist/bvs1_interactive-0.1.0-py3-none-any.whl" }
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import bvs1_interactive

    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # BVS1 – Techniktest

    Dieses Notebook prüft die Browseroberfläche
    und den Import unserer eigenen Bibliothek.
    """)
    return


@app.cell
def _(mo):
    step = mo.ui.slider(
        start=0,
        stop=10,
        value=0,
        label="Ausführungsschritt",
    )
    step
    return (step,)


@app.cell
def _(mo, step):
    mo.md(f"""
    Ausgewählter Schritt: **{step.value}**
    """)
    return


if __name__ == "__main__":
    app.run()
