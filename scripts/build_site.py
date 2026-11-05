"""Export each notebook into its own directory (including its own wheels)."""
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
site = root / "_site"
if site.exists():
    shutil.rmtree(site)
site.mkdir()
for notebook in sorted((root / "notebooks").glob("*.py")):
    subprocess.run([
        sys.executable, "-m", "marimo", "export", "html-wasm",
        str(notebook), "-o", str(site / notebook.stem), "--mode",
        "run" if notebook.stem.startswith("01_") else "edit",
    ], cwd=root, check=True)
(site / "index.html").write_text("""<!doctype html><html lang="de"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>BVS1 · Interaktive Grundlagen</title>
<style>body{font:17px/1.6 system-ui;background:#f5f8fc;color:#172c45;max-width:850px;margin:70px auto;padding:24px}h1{font-size:40px;line-height:1.1}a{display:block;background:white;border:1px solid #dce5ef;padding:20px;margin:16px 0;border-radius:12px;color:#126a71;text-decoration:none}small{color:#596b80}</style>
<small>BVS1 / INTERAKTIVE GRUNDLAGEN</small><h1>Abläufe verstehen.<br>Schritt für Schritt.</h1>
<p>Schematische Visualisierungen für die Lehre. Code, Register und Stack zeigen denselben ausgewählten Zustand.</p>
<a href="01_funktionsaufruf/">01 · Wie verändert ein Funktionsaufruf den Stack?</a>
<a href="02_funktionsaufruf_uebung/">02 · Übung mit anderem Startwert</a>
<a href="00_techniktest/">00 · Techniktest</a>
<p><small>Die Notebooks laufen im Browser. Änderungen im Editor werden nicht automatisch nach GitHub gespeichert.</small></p></html>""", encoding="utf-8")
