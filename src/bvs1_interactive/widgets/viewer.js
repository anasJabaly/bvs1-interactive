// A scenario player: all states and data transfers come from Python metadata.
// It visualizes teaching steps; it does not decode or execute instructions.
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const hex = value => '0x' + BigInt(value).toString(16).padStart(4, '0');
const svgNS = 'http://www.w3.org/2000/svg';
let nextId = 0;

function render({model, el}) {
  const scenario = model.get('scenario');
  const steps = scenario.steps;
  const processMode = scenario.kind === 'process';
  let selectedDocument = processMode ? steps[0].document : null, followCode = true, displayOwner = 'os';
  const openDetails = new Set();
  const uid = `bv-${++nextId}`;
  let index = Math.max(0, Math.min(steps.length - 1, model.get('selected_index') || 0));
  let codeMode = 'asm', playing = false, frozen = false, animating = false;
  let epoch = 0, frameId = 0, timer = 0, syncTimer = 0, disposed = false, resolveMotion = null;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const root = document.createElement('section');
  root.className = 'bv-workbench';
  root.setAttribute('aria-label', 'Interaktive Visualisierung: Code, CPU und Stack');
  root.tabIndex = 0;
  root.innerHTML = `
    <header class="bv-top"><div><div class="bv-eyebrow">BVS1 · Ablaufwerkstatt</div><h1>${esc(scenario.title)}</h1></div><span class="bv-model-tag">Schematisches RV64-Modell</span></header>
    <nav class="bv-toolbar" aria-label="Ablaufsteuerung">
      <button class="bv-btn" data-action="reset" aria-label="Zum Anfang">↺ Anfang</button>
      <button class="bv-btn" data-action="back" aria-label="Schritt zurück">← Zurück</button>
      <button class="bv-btn bv-primary" data-action="play" aria-label="Abspielen">▶ Abspielen</button>
      <button class="bv-btn" data-action="next" aria-label="Schritt weiter">Weiter →</button>
      <button class="bv-btn" data-action="replay" aria-label="Schritt erneut animieren">↻ Schritt</button>
      <label class="bv-speed">Tempo <select aria-label="Geschwindigkeit"><option value="0.5">0,5×</option><option value="1" selected>1×</option><option value="2">2×</option></select></label>
      <label class="bv-timeline"><input type="range" aria-label="Ausführungsschritt" min="0" max="${steps.length - 1}" value="${index}" step="1"><span class="bv-count"></span></label>
    </nav>
    <div class="bv-stage"><div class="bv-columns">
      <section class="bv-panel bv-code-panel" aria-label="Programmcode">
        <div class="bv-panel-head"><h2><span class="bv-panel-index">01</span> Programm</h2><div class="bv-tabs" role="tablist" aria-label="Codeansicht"><button class="bv-tab" role="tab" data-mode="asm" aria-selected="true">RISC-V</button><button class="bv-tab" role="tab" data-mode="source" aria-selected="false">C</button></div></div>
        <div class="bv-code-body"></div>
        <div class="bv-code-legend"><span><i class="bv-dot"></i>ausgeführter Befehl</span><span><i class="bv-dot bv-blue"></i>PC · als Nächstes</span></div>
        <div class="bv-source" aria-label="C-Quelltext"></div>
      </section>
      <section class="bv-panel bv-cpu-panel" aria-label="CPU und Register">
        <div class="bv-panel-head"><h2><span class="bv-panel-index">02</span> CPU</h2><span class="bv-eyebrow" style="font-size:9px">Aktiver Zustand</span></div>
        <div class="bv-chip"><div class="bv-chip-title">RV64 · REGISTER & RECHENWERK</div>
          <div class="bv-pc" data-endpoint="cpu:pc"><span>PC <small>nächste Adresse</small></span><code></code></div>
          <div class="bv-registers"></div><div class="bv-mini-bus" aria-hidden="true">↓ ↓</div>
          <div class="bv-alu" data-endpoint="cpu:alu"><strong>ALU</strong><div class="bv-alu-value">Rechnen & Adressen bilden</div></div>
        </div><div class="bv-cpu-note">Register liegen in der CPU. Der Stack liegt im Speicher. Pfeile zeigen, woher ein Wert kommt und wohin er geht.</div>
      </section>
      <section class="bv-panel bv-stack-panel" aria-label="Stack im Arbeitsspeicher">
        <div class="bv-panel-head"><h2><span class="bv-panel-index">03</span> Arbeitsspeicher · Stack</h2><span class="bv-eyebrow" style="font-size:9px">RAM</span></div>
        <div class="bv-memory-body"><div class="bv-memory-direction"><span>Hohe Adressen</span><span>Wachstum ↓</span></div><div class="bv-memory-grid"></div><div class="bv-memory-state"></div><div class="bv-memory-direction" style="margin-top:10px"><span>Niedrige Adressen</span><span>8 Byte je Zelle</span></div></div>
      </section>
    </div><svg class="bv-wires" aria-label="Verbindungen zwischen CPU und Speicher"></svg></div>
    <section class="bv-caption" aria-live="polite"><div><div class="bv-caption-step"></div><h3></h3><div class="bv-transfer-label"></div></div><p class="bv-caption-text"></p></section>
    <footer class="bv-bottom"><details><summary>Was zeigt dieses Modell?</summary><p>${esc(scenario.notes)} Die Animation zeigt logische Wertübertragungen, keine tatsächlichen Takte oder Mikroarchitektur.</p></details><span class="bv-flow-legend"><i class="bv-dot"></i>Wert / Zeiger &nbsp; <i class="bv-dot bv-blue"></i>Kontrollfluss</span></footer>`;
  el.appendChild(root);
  const $ = selector => root.querySelector(selector);
  const stage = $('.bv-stage'), wires = $('.bv-wires'), range = $('input[type=range]'), speed = $('.bv-speed select');
  const button = action => $(`[data-action="${action}"]`);
  const valueText = (name, value) => name === 'a0' ? String(value) : hex(value);
  const meanings = {sp:'Stackpointer',ra:'Rücksprung',s0:'Framepointer',a0:'Argument / Ergebnis'};

  if (processMode) installProcessUI();

  // The process lesson uses the same player, transport animation and controls.
  // Its additional panes are data-driven views of contexts and logical stacks.
  function installProcessUI() {
    root.classList.add('bv-process-workbench');
    $('.bv-model-tag').textContent='Exercise 2 / CP1';
    $('.bv-code-panel').innerHTML=`<div class="bv-panel-head"><h2><span class="bv-panel-index">01</span> Lab-Code</h2><label class="bv-follow"><input type="checkbox" checked aria-label="Codeposition automatisch folgen"> Folgen</label></div><div class="bv-filebar"><select aria-label="Quelldatei">${scenario.documents.map(doc=>`<option value="${esc(doc.id)}">${esc(doc.title)}</option>`).join('')}</select><span class="bv-file-kind"></span></div><div class="bv-code-body bv-lab-code"></div><div class="bv-code-provenance"></div>`;
    $('.bv-cpu-panel').innerHTML=`<div class="bv-panel-head"><h2><span class="bv-panel-index">02</span> CPU & Kontextwechsel</h2><span class="bv-owner"></span></div><div class="bv-chip"><div class="bv-chip-title">AKTIVE CPU-REGISTER</div><div class="bv-pc" data-endpoint="cpu:pc"><span>Codeposition</span><code data-value></code></div><div class="bv-registers"></div><div class="bv-saved-bank" data-endpoint="cpu:bank"></div></div><div class="bv-context-heading">RAM · gespeicherte Registerkopien</div><div class="bv-context-dock"></div><div class="bv-cpu-note">Ein Kontext ist eine gespeicherte Kopie. Der Switch kopiert Registerwerte, kein Stackarray.</div>`;
    $('.bv-stack-panel').innerHTML=`<div class="bv-panel-head"><h2><span class="bv-panel-index">03</span> Stacks & lokale Daten</h2><span class="bv-state-badge"></span></div><div class="bv-process-memory"><div class="bv-process-object"></div><div class="bv-process-stacks"></div><div class="bv-storage-note">p lebt in main; p.stack[4096] ist der reservierte Prozessstack.</div><div class="bv-array-section"></div><div class="bv-tmp"></div><div class="bv-terminal"><div class="bv-terminal-label">UART · bisherige Ausgabe</div><pre></pre></div></div>`;
    const chapters=document.createElement('nav');chapters.className='bv-chapters';chapters.setAttribute('aria-label','Abschnitte im Lab-Ablauf');
    chapters.innerHTML=scenario.chapters.map(([title,i])=>`<button data-step="${i}">${esc(title)}</button>`).join('');
    $('.bv-toolbar').after(chapters);
    const follow=$('.bv-follow input'),select=$('.bv-filebar select');
    select.addEventListener('change',()=>{followCode=false;follow.checked=false;selectedDocument=select.value;drawProcessCode(steps[index]);drawWires();});
    follow.addEventListener('change',()=>{followCode=follow.checked;drawProcessCode(steps[index]);drawWires();});
    $('.bv-flow-legend').textContent='Stacks schematisch · Adressen sind Modellwerte';
  }

  function registerDetails(registers, fields=null) {
    const values=Object.fromEntries(registers);
    return Array.from({length:12},(_,i)=>`<span data-sreg="s${i}"><small>s${i}</small><code>${fields&&!fields.includes(`s${i}`)?'—':hex(values[`s${i}`])}</code></span>`).join('');
  }
  function drawProcessCode(step) {
    if(followCode)selectedDocument=step.document;
    const doc=scenario.documents.find(doc=>doc.id===selectedDocument)||scenario.documents[0];
    $('.bv-filebar select').value=doc.id;
    $('.bv-file-kind').textContent=doc.id==='process.c'?'CP1-Referenz':doc.id==='context.S'||doc.id==='context.h'?'Erklärende Fassung':'Anwendung / API';
    const focused=doc.id===step.document?new Set(step.focus_lines?.length?step.focus_lines:[step.line]):new Set();
    $('.bv-code-body').innerHTML=doc.lines.map((line,i)=>`<div class="bv-code-row ${focused.has(i+1)?'bv-executed':''}" ${doc.id===step.document&&step.line===i+1?'data-endpoint="code:active" aria-current="step"':''}><span class="bv-code-address">${i+1}</span><code>${esc(line)||' '}</code></div>`).join('');
    $('.bv-code-provenance').textContent=doc.provenance;
    if(followCode){const body=$('.bv-code-body'),node=body.querySelector('[aria-current]');if(node)body.scrollTop=node.offsetTop-body.offsetTop-body.clientHeight/2+node.clientHeight/2;}
  }
  function drawProcessContexts(step) {
    $('.bv-context-dock').innerHTML=step.contexts.map(context=>{
      const values=Object.fromEntries(context.registers),ready=new Set(context.ready_fields),key=`context-${context.id}`;
      return `<section class="bv-context-card"><header><strong>${esc(context.title)}</strong><small>${ready.size}/14 gesichert</small></header>${['ra','sp'].map(name=>`<div class="bv-context-field" data-endpoint="context:${context.id}:${name}"><span>${name}</span><code data-value>${ready.has(name)?hex(values[name]):'—'}</code></div>`).join('')}<div class="bv-context-ra-label">${ready.has('ra')?esc(context.ra_label):'Noch kein Fortsetzungsziel'}</div><details class="bv-bank-details" data-detail="${key}" data-endpoint="context:${context.id}:bank" ${openDetails.has(key)?'open':''}><summary><span data-value>${Array.from(ready).filter(n=>n.startsWith('s')&&n!=='sp').length}/12 s-Register</span></summary><div class="bv-register-details">${registerDetails(context.registers,context.ready_fields)}</div></details></section>`;
    }).join('');
  }
  function drawProcessStacks(step) {
    $('.bv-process-stacks').innerHTML=step.regions.map(region=>`<section class="bv-stack-region ${region.id===step.active_owner?'bv-live-stack':'bv-resting-stack'}"><header><strong>${esc(region.title)}</strong><small>${region.id===step.active_owner?'CPU aktiv':region.id==='process'&&step.process_state==='FINISHED'?'beendet · nicht fortsetzen':region.allocated?'erhalten':'nicht vorbereitet'}</small></header><div class="bv-call-frames">${region.frames.length?region.frames.map((name,i)=>`<div class="bv-call-frame"><span>${i?'↳':'●'}</span><code>${esc(name)}</code></div>`).join(''):`<div class="bv-no-frame">${region.allocated?'Vorbereitet; noch keine aktive Aufrufkette':'Noch nicht vorbereitet'}</div>`}</div><div class="bv-region-sp" data-endpoint="stack:${region.id}"><small>sp ${region.id===step.active_owner?'← CPU':'gespeichert / ruhend'}</small><code>${hex(region.sp)}</code></div></section>`).join('');
    $('.bv-array-section').innerHTML=`<div class="bv-array-heading"><strong>value[]</strong><span>lokales Array von worker</span></div><div class="bv-array" data-endpoint="array:base">${Array.from({length:5},(_,i)=>`<div class="bv-byte ${i===4?'bv-null-byte':''}" data-endpoint="array:${i}"><small>[${i}]</small><strong data-value>${step.value.length?esc(step.value[i]==='\0'?'\\0':step.value[i]):'—'}</strong></div>`).join('')}</div><div class="bv-array-note">${step.process_state==='FINISHED'?'Ausführung beendet; die alten Bytes bleiben sichtbar.':step.value.length?'permute erhält einen Zeiger auf dieses Array, keine Kopie.':'Das Array entsteht erst beim ersten Eintritt in worker.'}</div>`;
    $('.bv-tmp').innerHTML=`<span>tmp <small>· logischer C-Wert</small></span><strong data-endpoint="local:tmp"><span data-value>${step.tmp===null?'—':esc(step.tmp)}</span></strong>`;
    $('.bv-process-object').innerHTML=`<span>current_process <strong>${step.current_process?'&p':'0'}</strong></span><span>entry <strong>${step.contexts.find(c=>c.id==='process').ready_fields.length?'worker':'—'}</strong></span><span>exit <strong>${step.exit_status===null?'—':step.exit_status}</strong></span>`;
    $('.bv-terminal pre').textContent=step.output.length?step.output.join('\n'):'Noch keine Ausgabe';
  }
  function drawProcessState() {
    const step=steps[index],previous=index?steps[index-1]:null;
    const values=Object.fromEntries(step.registers),old=Object.fromEntries(previous?.registers||[]);
    displayOwner=step.active_owner;
    drawProcessCode(step);
    $('.bv-owner').textContent=step.active_owner==='os'?'OS-Stack aktiv':'Prozessstack aktiv';
    $('.bv-pc code').textContent=step.location;
    $('.bv-registers').innerHTML=['sp','ra','s0','s1'].map(name=>`<div class="bv-register ${previous&&old[name]!==values[name]?'bv-changed':''}" data-endpoint="register:${name}"><div class="bv-register-name"><span>${name}</span><small>${name==='sp'?'Stackpointer':name==='ra'?'Fortsetzung':'callee-saved'}</small></div><span class="bv-register-value" data-value>${hex(values[name])}</span>${name==='ra'?`<small class="bv-ra-label">${esc(step.ra_label)}</small>`:''}</div>`).join('');
    $('.bv-saved-bank').innerHTML=`<details class="bv-bank-details" data-detail="cpu-registers" ${openDetails.has('cpu-registers')?'open':''}><summary><span data-value>s0–s11 · alle 12 anzeigen</span></summary><div class="bv-register-details">${registerDetails(step.registers)}</div></details>`;
    drawProcessContexts(step);drawProcessStacks(step);
    $('.bv-state-badge').textContent=step.process_state==='—'?'nicht angelegt':step.process_state;
    $('.bv-state-badge').dataset.state=step.process_state;
    $('.bv-caption-step').textContent=`SCHRITT ${String(index+1).padStart(2,'0')} / ${steps.length} · ${step.document}`;
    $('h3').textContent=step.title;$('.bv-caption-text').textContent=step.explanation;
    $('.bv-transfer-label').textContent=step.transfers.length?'↗ „Schritt“ animiert diesen Übergang.':'';
    $('.bv-count').textContent=`${index+1} / ${steps.length}`;range.value=index;
    let currentChapter=0;scenario.chapters.forEach(([_,i])=>{if(i<=index)currentChapter=i;});
    root.querySelectorAll('[data-step]').forEach(node=>node.setAttribute('aria-current',Number(node.dataset.step)===currentChapter?'step':'false'));
    updateButtons();requestAnimationFrame(drawWires);
  }
  function drawProcessWires() {
    const rect=stage.getBoundingClientRect();wires.setAttribute('viewBox',`0 0 ${rect.width} ${rect.height}`);
    let fixed=wires.querySelector('.bv-fixed');if(!fixed){fixed=svgElement('g',{class:'bv-fixed'});wires.prepend(fixed);}
    fixed.innerHTML=`<defs><marker id="${uid}-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 8 4 L 0 8 z" fill="#098489"/></marker></defs>`;
    const path=route('register:sp',`stack:${displayOwner}`);
    if(path)fixed.append(svgElement('path',{d:path,class:'bv-sp-wire','marker-end':`url(#${uid}-arrow)`}));
  }
  function setProcessDestination(transfer,prior) {
    const node=endpoint(transfer.target);if(!node)return;
    const snapshot=prior&&index?steps[index-1]:steps[index];
    const values=Object.fromEntries(snapshot.registers);
    let value=transfer.value;
    if(transfer.target.startsWith('register:')) {
      const name=transfer.target.split(':')[1];value=hex(values[name]);
      if(name==='sp'){displayOwner=snapshot.active_owner;drawProcessStacks(snapshot);$('.bv-owner').textContent=displayOwner==='os'?'OS-Stack aktiv':'Prozessstack aktiv';drawWires();}
    } else if(transfer.target.startsWith('context:')) {
      const [,owner,field]=transfer.target.split(':'),context=snapshot.contexts.find(c=>c.id===owner);
      if(field!=='bank')value=context.ready_fields.includes(field)?hex(Object.fromEntries(context.registers)[field]):'—';
      else {
        value=`${context.ready_fields.filter(n=>n.startsWith('s')&&n!=='sp').length}/12 s-Register`;
        node.querySelector('.bv-register-details').innerHTML=registerDetails(context.registers,context.ready_fields);
      }
    } else if(transfer.target==='cpu:bank') {
      value='s0–s11 · alle 12 anzeigen';
      node.querySelector('.bv-register-details').innerHTML=registerDetails(snapshot.registers);
      for(const name of ['s0','s1'])endpoint(`register:${name}`).querySelector('[data-value]').textContent=hex(values[name]);
    } else if(transfer.target==='local:tmp')value=snapshot.tmp===null?'—':snapshot.tmp;
    else if(transfer.target.startsWith('array:')) {
      if(transfer.target==='array:base'){
        for(let i=0;i<5;i++)endpoint(`array:${i}`).querySelector('[data-value]').textContent=snapshot.value.length?(snapshot.value[i]==='\0'?'\\0':snapshot.value[i]):'—';
        return;
      }
      const character=snapshot.value[Number(transfer.target.split(':')[1])];value=character==='\0'?'\\0':character??'—';
    } else if(transfer.target==='cpu:pc')value=snapshot.location;
    const label=node.querySelector('[data-value]');if(label)label.textContent=value;
    if(!prior){node.classList.add('bv-flash');setTimeout(()=>node.classList.remove('bv-flash'),500);}
  }

  function codeRows(step) {
    const previous = index > 0 ? steps[index - 1] : null;
    if (codeMode === 'source') {
      $('.bv-code-body').innerHTML = (scenario.source_code || []).map((line,i) => `<div class="bv-code-row ${i+1===step.source_line?'bv-executed':''}"><span class="bv-code-address">${i+1}</span><code>${esc(line)}</code><span class="bv-code-marker">${i+1===step.source_line?'◀':''}</span></div>`).join('');
    } else {
      $('.bv-code-body').innerHTML = scenario.code.map(line => {
        const executed = previous && line.address === previous.pc;
        const next = line.address === step.pc;
        return `<div class="bv-code-row ${executed?'bv-executed':''} ${next?'bv-next':''}" data-endpoint="code:${line.address}" ${next?'aria-current="step"':''} title="${esc(line.comment)}"><span class="bv-code-address">${line.address.toString(16)}</span><code>${esc(line.instruction)}</code><span class="bv-code-marker">${next?'◀':executed?'✓':''}</span></div>`;
      }).join('');
    }
    $('.bv-source').innerHTML = codeMode==='asm' ? (scenario.source_code || []).map((line,i) => `<div class="bv-source-line ${i+1===step.source_line?'bv-source-active':''}">${esc(line)}</div>`).join('') : '<span>Der C-Code zeigt die Absicht. Die Register- und Stackänderungen gehören zum gewählten RISC-V-Ablauf.</span>';
    root.querySelectorAll('[data-mode]').forEach(tab => tab.setAttribute('aria-selected', String(tab.dataset.mode === codeMode)));
  }

  function drawState() {
    if (processMode) { drawProcessState(); return; }
    const step = steps[index], previous = index ? steps[index-1] : null;
    const registers = Object.fromEntries(step.registers);
    const old = Object.fromEntries(previous?.registers || []);
    codeRows(step);
    $('.bv-pc code').textContent = hex(step.pc);
    $('.bv-registers').innerHTML = step.registers.map(([name,value]) => `<div class="bv-register ${previous&&old[name]!==value?'bv-changed':''}" data-endpoint="register:${esc(name)}"><div class="bv-register-name"><span>${esc(name)}</span><small>${esc(meanings[name]||'Register')}</small></div><span class="bv-register-value">${esc(valueText(name,value))}</span></div>`).join('');
    $('.bv-alu-value').textContent = /addi/.test(step.event) ? step.event.replace('addi ', '').replaceAll(', ', ' · ') : 'Rechnen & Adressen bilden';
    drawMemory(step);
    $('.bv-caption-step').textContent=`SCHRITT ${String(index+1).padStart(2,'0')} / ${steps.length} · ${step.event}`;
    $('h3').textContent=step.title;
    $('.bv-caption-text').textContent=step.explanation;
    $('.bv-transfer-label').textContent=index?'↗ Schritt erneut abspielen, um den Wertfluss zu verfolgen.':'Bereit für den Funktionsaufruf.';
    $('.bv-count').textContent=`${index+1} / ${steps.length}`;
    range.value=index;
    updateButtons();
    requestAnimationFrame(drawWires);
  }

  function drawMemory(step) {
    const registers = Object.fromEntries(step.registers.map(([name,value]) => [name, name==='sp'?Number(value):value]));
    const slots = new Map(step.stack.map(slot => [slot.address,slot]));
    let memory = `<div class="bv-memory-top ${registers.sp===scenario.stack_top?'bv-at-sp':''}" data-endpoint="stack:top"><span>${hex(scenario.stack_top)}</span><span>${registers.sp===scenario.stack_top?'← sp · Stackoberkante':'Stackoberkante'}</span></div>`;
    for (let address=scenario.stack_top-8;address>=scenario.stack_bottom;address-=8) {
      const slot=slots.get(address), active=slot?.active;
      const text=slot ? (slot.value===null?'? ? ? ?':hex(slot.value)) : '· · · ·';
      const label=slot ? (slot.active ? (slot.value===null?'Reserviert · noch nicht beschrieben':slot.label) : 'Freigegeben · alter Inhalt') : 'Freier Stackbereich';
      memory += `<div class="bv-memory-row ${active?'bv-allocated':slot?'bv-old':'bv-free'} ${registers.sp===address?'bv-at-sp':''}" data-endpoint="stack:${address}"><span class="bv-memory-address">${hex(address)}</span><div><div class="bv-memory-value">${esc(text)}</div><div class="bv-memory-label">${esc(label)}${registers.sp===address?' · ← sp':''}</div></div></div>`;
    }
    $('.bv-memory-grid').innerHTML = memory;
    const bytes=scenario.stack_top-registers.sp;
    $('.bv-memory-state').innerHTML=`<span>Aktiver Funktionsframe</span><strong>${bytes} Byte ${bytes?'reserviert':'· freigegeben'}</strong>`;
  }

  function updateButtons() {
    button('back').disabled=index===0;
    button('next').disabled=index===steps.length-1;
    button('reset').disabled=index===0&&!playing&&!animating;
    button('replay').disabled=index===0;
    button('play').textContent=playing?'Ⅱ Pause':frozen?'▶ Fortsetzen':'▶ Abspielen';
    button('play').setAttribute('aria-label',playing?'Pause':frozen?'Fortsetzen':'Abspielen');
  }

  function endpoint(name) {
    return root.querySelector(`[data-endpoint="${CSS.escape(name)}"]`) || (name.startsWith('code:')?$('.bv-code-panel'):null);
  }
  function point(name, side='center') {
    const node=endpoint(name); if(!node) return null;
    const r=node.getBoundingClientRect(), base=stage.getBoundingClientRect();
    return {x:(side==='left'?r.left:side==='right'?r.right:r.left+r.width/2)-base.left,y:r.top+r.height/2-base.top};
  }
  function curve(from,to) {
    const span=Math.max(25,Math.abs(to.x-from.x)*.4);
    const direction=to.x>=from.x?1:-1;
    return `M ${from.x} ${from.y} C ${from.x+span*direction} ${from.y}, ${to.x-span*direction} ${to.y}, ${to.x} ${to.y}`;
  }
  function route(source, target) {
    // Leave register banks through the gaps between rows, not through other registers.
    const a=point(source),b=point(target);if(!a||!b)return '';
    if(/^array:\d+$/.test(source)&&/^array:\d+$/.test(target)) {
      const base=stage.getBoundingClientRect();
      const from=endpoint(source).getBoundingClientRect(),to=endpoint(target).getBoundingClientRect();
      const ax=from.left+from.width/2-base.left,ay=from.top-base.top;
      const bx=to.left+to.width/2-base.left,by=to.top-base.top;
      return `M ${ax} ${ay} C ${ax} ${ay-40}, ${bx} ${by-40}, ${bx} ${by}`;
    }
    const base=stage.getBoundingClientRect(),cpu=$('.bv-cpu-panel').getBoundingClientRect();
    const lane=cpu.right-base.left+12;
    let path='',end;
    if(source.startsWith('register:')) {
      const box=endpoint(source).getBoundingClientRect();
      a.y=box.bottom-base.top;
      path=`M ${a.x} ${a.y} V ${a.y+6} H ${lane}`;
      end={x:lane,y:a.y+6};
    } else {
      const right=b.x>=a.x;
      const start=point(source,right?'right':'left');
      path=`M ${start.x} ${start.y}`;end=start;
    }
    if(target.startsWith('register:')) {
      const box=endpoint(target).getBoundingClientRect();
      const y=box.top-base.top-6;
      path+=` L ${lane} ${y} H ${b.x} V ${box.top-base.top}`;
    } else {
      const dest=point(target,b.x>=end.x?'left':'right');
      const span=Math.max(16,Math.abs(dest.x-end.x)*.45);
      const direction=dest.x>=end.x?1:-1;
      path+=` C ${end.x+span*direction} ${end.y}, ${dest.x-span*direction} ${dest.y}, ${dest.x} ${dest.y}`;
    }
    return path;
  }

  function svgElement(tag, attrs={}) {
    const element=document.createElementNS(svgNS,tag);
    for(const [key,value] of Object.entries(attrs)) element.setAttribute(key,String(value));
    return element;
  }
  function drawWires() {
    if(disposed) return;
    if(processMode){drawProcessWires();return;}
    const rect=stage.getBoundingClientRect();
    wires.setAttribute('viewBox',`0 0 ${rect.width} ${rect.height}`);
    let fixed=wires.querySelector('.bv-fixed');
    if(!fixed){fixed=svgElement('g',{class:'bv-fixed'});wires.prepend(fixed);}
    const sp=Number(endpoint('register:sp')?.querySelector('.bv-register-value')?.textContent || Object.fromEntries(steps[index].registers).sp);
    const a=point('register:sp','right'),b=point(sp===scenario.stack_top?'stack:top':`stack:${sp}`,'left');
    fixed.innerHTML=`<defs><marker id="${uid}-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 8 4 L 0 8 z" fill="#098489"/></marker></defs>`;
    if(a&&b){fixed.appendChild(svgElement('path',{d:route('register:sp',sp===scenario.stack_top?'stack:top':`stack:${sp}`),class:'bv-sp-wire','marker-end':`url(#${uid}-arrow)`}));
      const label=svgElement('text',{x:(a.x+b.x)/2,y:(a.y+b.y)/2-9,fill:'#087f83','font-size':'10','font-family':'ui-monospace','text-anchor':'middle'});label.textContent='sp';fixed.appendChild(label);}
  }
  function cancelMotion() {
    epoch++;clearTimeout(timer);cancelAnimationFrame(frameId);if(resolveMotion){resolveMotion();resolveMotion=null;}animating=false;frozen=false;
    wires.querySelectorAll('.bv-motion').forEach(node=>node.remove());
    root.querySelectorAll('.bv-active-node').forEach(node=>node.classList.remove('bv-active-node'));
  }
  function stop() {playing=false;cancelMotion();drawState();}
  function syncIndex() {
    // Keep dragging/animation local; publish only the last settled selection.
    // The complete immutable lesson is already available in this browser.
    clearTimeout(syncTimer);
    if(model.get('selected_index')!==index) syncTimer=setTimeout(()=>{
      syncTimer=0;
      if(disposed)return;
      model.set('selected_index',index);model.save_changes();
    },200);
  }

  function setDestination(transfer, prior=false) {
    if(processMode){setProcessDestination(transfer,prior);return;}
    const node=endpoint(transfer.target);if(!node)return;
    const previous=steps[index-1];
    let value=transfer.value;
    if(prior&&previous){
      if(transfer.target.startsWith('register:')){const name=transfer.target.split(':')[1];value=valueText(name,Object.fromEntries(previous.registers)[name]);}
      else if(transfer.target.startsWith('stack:')){const slot=previous.stack.find(s=>String(s.address)===transfer.target.split(':')[1]);value=slot&&slot.value!==null?hex(slot.value):'? ? ? ?';}
      else if(transfer.target==='cpu:pc') value=hex(previous.pc);
    }
    const text=node.querySelector('.bv-register-value,.bv-memory-value,code,.bv-alu-value');
    if(text) text.textContent=value;
    if(transfer.target==='register:sp'){drawMemory(prior&&previous?previous:steps[index]);drawWires();}
    if(!prior){node.classList.add('bv-flash');setTimeout(()=>node.classList.remove('bv-flash'),500);}
  }

  async function animateTransfers(token) {
    const transfers=steps[index].transfers||[];
    animating=true;
    transfers.forEach(transfer=>{if(!transfer.target.startsWith('code:'))setDestination(transfer,true);});
    for(const transfer of transfers) {
      if(token!==epoch||disposed)return;
      const source=endpoint(transfer.source),target=endpoint(transfer.target);
      const right=(point(transfer.target)?.x||0)>=(point(transfer.source)?.x||0);
      const from=point(transfer.source,right?'right':'left'),to=point(transfer.target,right?'left':'right');
      if(!from||!to)continue;
      source?.classList.add('bv-active-node');target?.classList.add('bv-active-node');
      $('.bv-transfer-label').textContent='● '+transfer.label;
      const group=svgElement('g',{class:'bv-motion'});
      const path=svgElement('path',{d:route(transfer.source,transfer.target),class:'bv-transfer-path '+(transfer.kind==='control'?'bv-control':'')});
      const packet=svgElement('g',{class:'bv-packet'});
      const width=Math.max(46,transfer.value.length*8+20);
      packet.append(svgElement('circle',{r:6}),svgElement('rect',{x:-width/2,y:-28,width,height:22}));
      const label=svgElement('text',{x:0,y:-16});label.textContent=transfer.value;packet.append(label);
      group.append(path,packet);wires.append(group);
      const length=path.getTotalLength();let progress=0,last=performance.now();
      await new Promise(resolve=>{
        resolveMotion=resolve;
        const tick=now=>{
          if(token!==epoch||disposed){resolve();return;}
          if(!frozen)progress+=Math.max(0,now-last)/(reduced?1:Math.max(350,2100/transfers.length/Number(speed.value)));
          last=now;
          const t=Math.min(progress,1),eased=t*t*(3-2*t),p=path.getPointAtLength(length*eased);
          packet.setAttribute('transform',`translate(${p.x},${p.y})`);
          if(t<1)frameId=requestAnimationFrame(tick);else{resolveMotion=null;resolve();}
        };
        frameId=requestAnimationFrame(tick);
      });
      group.remove();source?.classList.remove('bv-active-node');target?.classList.remove('bv-active-node');
      if(token!==epoch||disposed)return;
      if(!transfer.target.startsWith('code:'))setDestination(transfer);
    }
    if(token!==epoch||disposed)return;
    animating=false;frozen=false;drawState();
    $('.bv-transfer-label').textContent=transfers.length?'✓ '+transfers[transfers.length-1].label:'Schritt abgeschlossen.';
    if(playing&&index<steps.length-1)timer=setTimeout(()=>go(index+1,true),450/Number(speed.value));
    else if(index===steps.length-1){playing=false;updateButtons();}
  }
  function go(next,animate=false) {
    cancelMotion();index=Math.max(0,Math.min(steps.length-1,next));drawState();syncIndex();
    if(animate&&index>0)animateTransfers(epoch);
    else if(playing&&index<steps.length-1)timer=setTimeout(()=>go(index+1,true),300);
  }
  function playPause() {
    if(playing){playing=false;frozen=animating;clearTimeout(timer);updateButtons();return;}
    playing=true;
    if(frozen){frozen=false;updateButtons();return;}
    if(index===steps.length-1)go(0,false);else go(index+1,true);
    updateButtons();
  }
  const actions={reset:()=>{playing=false;go(0);},back:()=>{playing=false;go(index-1);},next:()=>{playing=false;go(index+1,true);},play:playPause,replay:()=>{playing=false;go(index,true);}};
  const click=event=>{const target=event.target.closest('[data-action],[data-mode],[data-step]');if(!target)return;if(target.dataset.step!==undefined){playing=false;go(Number(target.dataset.step));return;}if(target.dataset.action)actions[target.dataset.action]?.();else{codeMode=target.dataset.mode;stop();}};
  const scrub=()=>{playing=false;go(Number(range.value));};
  const external=()=>{if(syncTimer)return;const next=model.get('selected_index');if(next!==index){playing=false;go(next);}};
  const trackDetails=event=>{const key=event.target.dataset?.detail;if(key){if(event.target.open)openDetails.add(key);else openDetails.delete(key);}};
  root.addEventListener('toggle',trackDetails,true);
  root.addEventListener('click',click);range.addEventListener('input',scrub);
  model.on('change:selected_index',external);
  const resize=new ResizeObserver(drawWires);resize.observe(stage);
  drawState();
  return ()=>{disposed=true;clearTimeout(syncTimer);cancelMotion();resize.disconnect();root.removeEventListener('toggle',trackDetails,true);root.removeEventListener('click',click);range.removeEventListener('input',scrub);model.off('change:selected_index',external);root.remove();};
}
export default {render};
