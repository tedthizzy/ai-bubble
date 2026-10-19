const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const THREE = require('../../viz/vendor/three-0.150.1.min.js');
const root=path.resolve(__dirname,'../..');
const source=fs.readFileSync(path.join(root,'viz/explorer.js'),'utf8').replace(/\nstart\(\);\s*$/,'');
const data=JSON.parse(fs.readFileSync(path.join(root,'viz/graph_data.json'),'utf8'));

function load(input=data,reduced=false,hidden=false) {
  const elements=new Map(), callbacks=new Map();
  let time=0, timerId=0;
  class Element {
    constructor() { this.style={}; this.dataset={}; this.attrs={}; this.events={}; this.innerHTML=''; this.value=''; this.hidden=false; this.isConnected=true; this.firstChild={textContent:''}; }
    setAttribute(k,v) { this.attrs[k]=v; }
    removeAttribute(k) { delete this.attrs[k]; }
    addEventListener(k,f) { this.events[k]=f; }
    insertAdjacentHTML(_,value) { this.innerHTML+=value; }
    getBoundingClientRect() { return {left:0,top:0,width:1200,height:800}; }
  }
  const documentEvents=new Map();
  const document={body:new Element(),hidden,
    getElementById(id) { if(!elements.has(id)) elements.set(id,new Element()); return elements.get(id); },
    addEventListener(name,handler) {documentEvents.set(name,handler);}};
  const scene=new THREE.Scene(), camera=new THREE.PerspectiveCamera(75,1.5,.1,5000);
  camera.position.z=1000; camera.updateProjectionMatrix();camera.updateMatrixWorld();
  const state={scene,camera}, controls={addEventListener(){}};
  let graph;
  graph=new Proxy({}, {get(_,name) {
    if(name==='scene') return () => scene;
    if(name==='camera') return () => camera;
    if(name==='controls') return () => controls;
    if(name==='renderer') return () => ({setPixelRatio(){},domElement:document.getElementById('g')});
    return (...args) => {
      if(name==='graphData' && args.length) state.graphData=args[0];
      if(name==='cameraPosition') state.cameraArgs=args;
      if(name==='pauseAnimation') state.pauses=(state.pauses||0)+1;
      if(name==='zoomToFit') state.fits=(state.fits||0)+1;
      if(name==='resumeAnimation') {
        state.resumes=(state.resumes||0)+1;
        state.onResume?.();
      }
      if(name.startsWith('on')) callbacks.set(name,args[0]);
      return graph;
    };
  }});
  const timers=new Map();
  const context=vm.createContext({
    document, window:{matchMedia:() => ({matches:reduced,addEventListener(){}}),devicePixelRatio:2,addEventListener(){}},
    THREE, ForceGraph3D:() => () => graph, performance:{now:()=>time}, console,
    setTimeout(fn) { const id=++timerId;timers.set(id,fn);return id; },
    setInterval(fn) { const id=++timerId;timers.set(id,fn);return id; },
    clearInterval(id) { timers.delete(id); },
    requestAnimationFrame(fn) { fn(); },
    fetch:() => Promise.reject(new Error('offline fixture')),
    input
  });
  vm.runInContext(source,context);
  vm.runInContext('boot(input)',context);
  return {context,state,elements,callbacks,timers,documentEvents,eval:s=>vm.runInContext(s,context),
    settle() { for(let i=0;i<5;i++) { time+=2000; const batch=[...timers.values()];timers.clear();batch.forEach(f=>f()); } }};
}

test('all saved entities and links remain accessible while only core enters the force graph',() => {
  const app=load();
  assert.equal(app.state.graphData.nodes.length,data.nodes.length);
  assert.equal(app.state.graphData.links.length,data.edges.length);
  const unmapped=data.field.nodes.filter(row => !row[3] || !data.nodes.some(n=>n.id===row[3])).length;
  assert.equal(app.eval('nodes.length'),data.nodes.length+unmapped);
  assert.equal(app.eval('fieldNodes.length'),unmapped);
  assert.equal(app.eval('links.length'),data.edges.length+data.field.links.length);
  const field=app.state.scene.children[0];
  assert.equal(field.children.filter(x=>x.isPoints).length,1);
  assert.equal(field.children.filter(x=>x.isLineSegments).length,1);
  assert.equal(field.children[0].geometry.attributes.position.count,unmapped);
  app.settle();
  assert.ok(app.state.pauses>0,'idle rendering pauses');
  app.eval('wake()');
  assert.ok(app.state.resumes>0,'interaction wakes rendering');
});

test('resuming can emit a synchronous controls change without recursively resuming',() => {
  const app=load();
  app.settle();
  const before=app.state.resumes||0;
  app.state.onResume=() => app.eval('wake()');
  app.eval('wake()');
  assert.equal(app.state.resumes,before+1);
  assert.equal(app.eval('paused'),false);
});

test('loading while hidden waits for a visible frame before the first camera fit',() => {
  const app=load(data,false,true);
  app.settle();
  assert.equal(app.state.fits||0,0);
  app.eval('document.hidden=false');
  app.documentEvents.get('visibilitychange')();
  assert.equal(app.state.fits,1);
  app.settle();
  app.eval('document.hidden=true');
  app.documentEvents.get('visibilitychange')();
  app.eval('document.hidden=false');
  app.documentEvents.get('visibilitychange')();
  assert.equal(app.state.fits,1,'returning to an explored graph preserves its camera');
});

test('search reaches raw entities and every selected connection can open its evidence card',() => {
  const app=load();
  const raw=app.eval('fieldNodes.find(n=>n.nlinks.length>10)');
  app.elements.get('entity-search').value=raw.label;
  app.eval('showSearch()');
  app.context.inputId=raw.id;
  assert.ok(app.eval('searchMatches.some(n=>n.id===inputId)'));
  app.eval('focusNode(byId[inputId])');
  assert.match(app.elements.get('card').innerHTML,/All connections/);
  const details=app.elements.get('connections'); details.open=true;details.events.toggle();
  const html=app.elements.get('connection-list').innerHTML;
  assert.equal((html.match(/data-link=/g)||[]).length,raw.nlinks.length);
  app.context.connection=raw.nlinks[0].index;
  app.eval('focusDeal(links[connection])');
  assert.match(app.elements.get('card').innerHTML,/Raw extracted/);
});

test('grey dots skip automatic raycasting and remain selectable through the click path',() => {
  const app=load();
  app.state.scene.updateMatrixWorld(true);
  const points=app.state.scene.children[0].children[0], automatic=[];
  points.raycast(new THREE.Raycaster(),automatic);
  assert.equal(automatic.length,0);
  const node=app.eval('fieldNodes[0]');
  const p=new THREE.Vector3(node.x,node.y,node.z).project(app.state.camera);
  const event={clientX:(p.x+1)*600,clientY:(1-p.y)*400};
  app.context.clickEvent=event;
  const selected=app.eval('sceneField.pick(clickEvent)');
  assert.ok(selected && selected.field);
  app.callbacks.get('onBackgroundClick')(event);
  assert.match(app.elements.get('card').innerHTML,/Extracted party/);
});

test('long Unicode and HTML-shaped labels stay escaped; reduced motion finishes without timed cascade',() => {
  const fixture=structuredClone(data);
  fixture.nodes[0].label='Name '.repeat(30)+'漢字 العربية 😀 <img src=x onerror=bad()>';
  fixture.nodes[0].note='<script>bad()</script>';
  const app=load(fixture,true);
  app.eval('focusNode(nodes[0])');
  const card=app.elements.get('card').innerHTML;
  assert.ok(card.includes('漢字 العربية 😀'));
  assert.ok(card.includes('&lt;img'));
  assert.ok(!card.includes('<script>'));
  assert.equal(app.state.cameraArgs[2],0);
  app.eval('playCascade()');
  assert.equal(app.eval('cascadeTimer'),null);
  assert.equal(app.eval('revealed.size'),app.eval('cascadeIds.size'));
  for(let i=0;i<10;i++) app.eval('playCascade()');
  assert.equal(app.eval('cascadeTimer'),null);
});

test('empty data and failed market fetch keep the page usable',async() => {
  const app=load({nodes:[],edges:[],meta:{}});
  assert.equal(app.state.graphData.nodes.length,0);
  assert.match(app.elements.get('load-status').textContent,/No entities/);
  assert.equal(app.elements.get('play').disabled,true);
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(app.elements.get('credit-details').textContent,/unavailable/);
});


test('raw candidates without a measured amount do not show a zero-dollar exposure',() => {
  const fixture=structuredClone(data);
  const raw=fixture.field.nodes.find(row=>!row[3]||!fixture.nodes.some(n=>n.id===row[3]));
  raw[1]=0;raw[2]=27;
  const app=load(fixture);
  app.eval('showCard(fieldNodes[0])');
  assert.match(app.elements.get('card').innerHTML,/<dd>27<\/dd>/);
  assert.match(app.elements.get('card').innerHTML,/amount unmeasured/);
  assert.match(app.elements.get('card').innerHTML,/Raw, unadjudicated/);
  assert.ok(!app.elements.get('card').innerHTML.includes('$0 raw'));
});

test('new core counterparties can use existing dated adjacent quotes',() => {
  const app=load();
  app.eval('live={adjacent:{SpaceX:{sym:"SPCX",close:100,chg_pct:1,date:"2026-10-16"},Alphabet:{sym:"GOOGL",close:200,chg_pct:2,date:"2026-10-16"}}}');
  app.eval('showCard(byId.SpaceX)');
  assert.match(app.elements.get('card').innerHTML,/SPCX/);
  assert.match(app.elements.get('card').innerHTML,/\$100\.00/);
  app.eval('showCard(byId.Google)');
  assert.match(app.elements.get('card').innerHTML,/GOOGL/);
  assert.match(app.elements.get('card').innerHTML,/\$200\.00/);
  assert.match(app.elements.get('card').innerHTML,/2026-10-16/);
});

test('vendor funding flags cover reviewed reciprocal purchases across suppliers',() => {
  const app=load();
  for (const [vendor,customer] of [['Amazon','OpenAI'],['Amazon','Anthropic'],['Microsoft','OpenAI'],['Microsoft','Anthropic'],['NVIDIA','Anthropic'],['NVIDIA','OpenAI'],['NVIDIA','IREN']]) {
    app.context.vendor=vendor;app.context.customer=customer;
    assert.equal(app.eval('links.find(e=>e.from===vendor && e.to===customer).circular'),true);
    assert.equal(app.eval('links.find(e=>e.from===customer && e.to===vendor).circular'),true);
  }
  assert.equal(app.eval('links.find(e=>e.from==="Google" && e.to==="Anthropic").circular'),false,'historical investment does not establish a current funding loop');
  assert.equal(app.eval('links.find(e=>e.from==="OpenAI" && e.to==="JPMorgan Chase").circular'),false,'undrawn bank participation does not establish a vendor purchase');
  assert.equal(app.eval('links.find(e=>e.from==="NVIDIA" && e.to==="SB Energy").circular'),true,'the primary filing explicitly requires exclusive vendor hardware');
});

test('sources, deals and selection remain readable without overlapping panels',() => {
  const app=load();
  app.eval('focusNode(nodes[0])');
  assert.equal(app.elements.get('card').style.display,'block');
  assert.ok(!app.elements.get('card').innerHTML.includes('<a '),'citations stay outside the details card');
  const evidence=app.elements.get('selected-evidence').innerHTML;
  assert.ok(evidence.includes(data.nodes[0].sources[0].source_uri));
  assert.match(evidence,/Neither August draw is included/,'the full note remains available');
  app.elements.get('info').onclick();
  assert.equal(app.elements.get('card').style.display,'none');
  assert.equal(app.elements.get('panel').style.display,'block');
  assert.equal(app.elements.get('selected-evidence').innerHTML,evidence,'Sources retains selected evidence when it closes the card');
  app.elements.get('deals').onclick();
  assert.equal(app.elements.get('panel').style.display,'none');
  assert.equal(app.elements.get('dpanel').style.display,'block');
  app.eval('focusDeal(links[0])');
  assert.equal(app.elements.get('dpanel').style.display,'none');
  assert.equal(app.elements.get('card').style.display,'block');
});

test('facility details stay collapsed and sources retain payment schedules and assumptions',() => {
  const app=load();
  app.eval('focusNode(byId["Hut 8"])');
  const card=app.elements.get('card').innerHTML;
  assert.match(card,/Facilities \(3\)/);
  assert.match(card,/DSCR: Unmeasured/);
  assert.match(card,/15-year base term/);
  assert.match(card,/Forecast \/ 2025-12-17/);
  assert.ok(!card.includes('<a '),'source links stay out of the concise card');
  assert.ok(!card.includes('Scheduled debt payments'),'the full schedule stays in Sources');
  assert.ok(!/<details[^>]+\bopen\b/.test(card),'facility folds do not open automatically');
  const evidence=app.elements.get('selected-evidence').innerHTML;
  assert.match(evidence,/Scheduled debt payments/);
  assert.match(evidence,/61\.4% cash margin/);
  assert.match(evidence,/Cash sensitivity assumptions/);
  assert.match(evidence,/fixed baseline cash costs/i);
  assert.match(evidence,/tm2613163d1_ex4-1.htm/);
  assert.match(evidence,/no parent, tenant or lease-guarantor guarantee/);
  app.elements.get('info').onclick();
  assert.equal(app.elements.get('panel').style.display,'block');
});

test('partial interest and redacted installments never become full facility coverage',() => {
  const app=load();
  app.eval('focusNode(byId.IREN)');
  const card=app.elements.get('card').innerHTML;
  assert.match(card,/Known interest \/ year/);
  assert.match(card,/Incomplete debt payments/);
  assert.match(card,/DSCR: Unmeasured/);
  assert.ok(!card.includes('Interest requires'));
  assert.match(app.elements.get('selected-evidence').innerHTML,/redact/i);
  app.eval('focusNode(byId.CoreWeave)');
  assert.ok(!app.elements.get('card').innerHTML.includes('Interest / year'),'effective accounting rates are not cash coupons');
});

test('quarterly colocation revenue remains dated and is not assigned to the financing pool',() => {
  const app=load();
  app.eval('focusNode(byId["Core Scientific"])');
  const card=app.elements.get('card').innerHTML;
  assert.match(card,/Quarter revenue/);
  assert.match(card,/2026-Q2/);
  assert.ok(!card.includes('Contract avg. / year'));
  assert.match(app.elements.get('selected-evidence').innerHTML,/Total colocation revenue is not assigned/);
});

test('facility labels escape long Unicode input and older graphs need no facility layer',() => {
  const fixture=structuredClone(data);
  const c=fixture.facility_cashflows.cases.find(c=>c.entity==='Hut 8');
  c.project='Facility '.repeat(30)+'漢字 العربية 😀 <img src=x onerror=bad()>';
  const app=load(fixture);
  app.eval('focusNode(byId["Hut 8"])');
  const card=app.elements.get('card').innerHTML;
  assert.ok(card.includes('漢字 العربية 😀'));
  assert.ok(card.includes('&lt;img'));
  assert.ok(!card.includes('<img'));
  delete fixture.facility_cashflows;
  const old=load(fixture);
  old.eval('focusNode(byId["Hut 8"])');
  assert.ok(!old.elements.get('card').innerHTML.includes('Facilities ('));
});
