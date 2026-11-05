"""Reusable HTML views; independent of Marimo and scenario implementation."""
from html import escape
from bvs1_interactive.model import Scenario, Step, changed_registers

STYLE = """<style>
.bvs{--ink:#172c45;--muted:#596b80;--line:#dce5ef;--accent:#126a71;--soft:#e8f6f4;color:var(--ink);font:15px/1.55 system-ui,sans-serif;background:#f5f8fc;padding:24px;border-radius:18px}
.bvs *{box-sizing:border-box}.bvs h1{font-size:clamp(24px,3vw,36px);line-height:1.18;letter-spacing:-.025em;margin:12px 0}.bvs h2{font-size:17px;margin:0 0 16px}.bvs p{margin:8px 0}.bvs small,.bvs .muted{color:var(--muted)}
.bvs .tag{font-size:11px;font-weight:750;letter-spacing:.13em;color:var(--accent);text-transform:uppercase}.bvs .grid{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:16px;margin-top:20px}.bvs .panel{background:white;border:1px solid var(--line);border-radius:12px;padding:20px;min-width:0}.bvs .wide{grid-column:1/-1}.bvs .callout{background:var(--soft);border-left:4px solid var(--accent);padding:14px 18px;border-radius:4px;margin-top:16px}
.bvs .code{font:13px/1.7 ui-monospace,monospace;overflow-x:auto}.bvs .code-row{display:grid;grid-template-columns:60px minmax(190px,1fr);gap:10px;padding:6px 8px;border-left:3px solid transparent;border-radius:3px}.bvs .next{background:var(--soft);border-left-color:var(--accent);font-weight:650}.bvs .address{color:var(--muted)}.bvs .comment{font:11px/1.4 system-ui,sans-serif;color:var(--muted)}
.bvs table{width:100%;border-collapse:collapse;font-size:13px}.bvs th{text-align:left;color:var(--muted);font-size:11px;font-weight:600;padding:7px}.bvs td{padding:10px 7px;border-top:1px solid var(--line)}.bvs code{font-family:ui-monospace,monospace}.bvs .changed{background:#fff3d6}.bvs .badge{display:inline-block;background:#fff3d6;color:#7a4b00;padding:1px 6px;border-radius:4px;font-size:10px;margin-left:5px}.bvs .stack{border:1px solid var(--line);border-radius:8px;overflow:hidden}.bvs .slot{display:grid;grid-template-columns:72px minmax(0,1fr);gap:12px;padding:12px;border-bottom:1px solid var(--line);font-size:12px}.bvs .slot:last-child{border-bottom:0}.bvs .inactive{background:#f1f4f8;color:var(--muted)}.bvs .sp{outline:2px solid var(--accent);outline-offset:-2px}.bvs .footer{font-size:12px;margin-top:18px;color:var(--muted)}
@media(max-width:760px){.bvs{padding:14px}.bvs .grid{grid-template-columns:1fr}.bvs .panel{padding:14px}}
</style>"""


def code_view(scenario: Scenario, step: Step) -> str:
    rows = []
    for line in scenario.code:
        selected = line.address == step.pc
        rows.append(f'<div class="code-row {"next" if selected else ""}" {"aria-current=step" if selected else ""}><span class="address">{line.address:04x}</span><span>{escape(line.instruction)}<div class="comment">{escape(line.comment)}</div></span></div>')
    return '<h2>Programmcode</h2><p class="muted">Markiert: die nächste Anweisung.</p><div class="code">' + ''.join(rows) + '</div>'


def register_view(step: Step, previous: Step | None = None) -> str:
    changed = changed_registers(step, previous)
    meanings = {"sp": "Stackpointer", "ra": "Rücksprungadresse", "s0": "Framepointer (hier)", "a0": "Argument / Ergebnis"}
    rows = []
    for name, value in step.registers:
        badge = '<span class="badge">geändert</span>' if name in changed else ''
        shown = str(value) if name == 'a0' else f'0x{value:04x}'
        rows.append(f'<tr class="{"changed" if name in changed else ""}"><td><code>{escape(name)}</code>{badge}<br><small>{escape(meanings.get(name, name))}</small></td><td><code>{shown}</code></td></tr>')
    return '<h2>CPU · Registerauszug</h2><p class="muted">PC · nächste Adresse: <code>0x' + f'{step.pc:04x}' + '</code></p><table><thead><tr><th>Register</th><th>Wert</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table><p><small>Gelb: anderer Wert als im vorherigen Szenarioschritt.</small></p>'


def stack_view(scenario: Scenario, step: Step, previous: Step | None = None) -> str:
    slots = {slot.address: slot for slot in step.stack}
    old = {slot.address: slot for slot in previous.stack} if previous else {}
    sp = step.register('sp')
    rows = []
    if sp == scenario.stack_top:
        rows.append(f'<div class="slot sp"><code>0x{sp:04x}</code><span>← sp · oberes Ende; kein aktiver Funktionsframe</span></div>')
    for address in range(scenario.stack_top - 8, scenario.stack_bottom - 1, -8):
        slot = slots.get(address)
        inactive = slot is None or not slot.active
        changed = slot is not None and old.get(address) != slot
        value = 'Nicht belegt' if slot is None else ('Inhalt unbekannt' if slot.value is None else f'0x{slot.value:04x}')
        label = '' if slot is None else slot.label
        if slot is not None and not slot.active:
            label += ' · alter Inhalt, freigegeben'
        cls = ('inactive ' if inactive else '') + ('changed ' if changed else '') + ('sp' if address == sp else '')
        pointer = ' ← sp' if address == sp else ''
        rows.append(f'<div class="slot {cls}"><code>0x{address:04x}</code><span><strong>{value}{pointer}</strong><br>{escape(label)}</span></div>')
    return '<h2>Stack · 8 Byte je Zeile</h2><p class="muted">Hohe Adressen oben · Wachstum ↓</p><div class="stack">' + ''.join(rows) + '</div><p><small>Grüner Rahmen: sp. Grau: außerhalb des aktiven Frames. Angezeigt werden nur die gewählten 32 Byte.</small></p>'


def dashboard(scenario: Scenario, index: int) -> str:
    step = scenario.at(index)
    previous = scenario.at(index - 1) if index else None
    return STYLE + f"""<section class="bvs" aria-label="Visualisierung eines Funktionsaufrufs">
    <div class="tag">BVS1 / Interaktive Grundlagen</div>
    <h1>{escape(scenario.title)}</h1><p class="muted">{escape(scenario.description)}</p>
    <div class="callout" aria-live="polite"><small>Schritt {index + 1} / {len(scenario.steps)} · Zuletzt: <code>{escape(step.event)}</code></small><h2 style="margin:8px 0">{escape(step.title)}</h2><p>{escape(step.explanation)}</p></div>
    <div class="grid"><div class="panel">{code_view(scenario, step)}</div><div><div class="panel">{register_view(step, previous)}</div><div class="panel" style="margin-top:16px">{stack_view(scenario, step, previous)}</div></div></div>
    <p class="footer">{escape(scenario.notes)}</p></section>"""


from .viewer import ExecutionViewer
