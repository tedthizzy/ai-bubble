const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const THREE = require('../../viz/vendor/three-0.150.1.min.js');
const root=path.resolve(__dirname,'../..');
const source=fs.readFileSync(path.join(root,'viz/explorer.js'),'utf8').replace(/\nstart\(\);\s*$/,'');
const data=JSON.parse(fs.readFileSync(path.join(root,'viz/graph_data.json'),'utf8'));

function load(input=data,reduced=false) {
  const elements=new Map(), callbacks=new Map();
  let time=0, timerId=0;
  class Element {
    constructor() { this.style={}; this.dataset={}; this.attrs={}; this.events={}; this.innerHTML=''; this.value=''; this.hidden=false; this.isConnected=true; }
    setAttribute(k,v) { this.attrs[k]=v; }
    removeAttribute(k) { delete this.attrs[k]; }
    addEventListener(k,f) { this.events[k]=f; }
    insertAdjacentHTML(_,value) { this.innerHTML+=value; }
    getBoundingClientRect() { return {left:0,top:0,width:1200,height:800}; }
  }
  const document={body:new Element(),hidden:false,
    getElementById(id) { if(!elements.has(id)) elements.set(id,new Element()); return elements.get(id); },
    addEventListener() {}};
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
      if(name==='resumeAnimation') state.resumes=(state.resumes||0)+1;
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
  return {context,state,elements,callbacks,timers,eval:s=>vm.runInContext(s,context),
    settle() { for(let i=0;i<5;i++) { time+=2000; const batch=[...timers.values()];timers.clear();batch.forEach(f=>f()); } }};
}

test('all saved entities and links remain accessible while only core enters the force graph',() => {
  const app=load();
  assert.equal(app.state.graphData.nodes.length,data.nodes.length);
  assert.equal(app.state.graphData.links.length,data.edges.length);
  assert.equal(app.eval('nodes.length'),7715);
  assert.equal(app.eval('fieldNodes.length'),7687);
  assert.equal(app.eval('links.length'),data.edges.length+data.field.links.length);
  const field=app.state.scene.children[0];
  assert.equal(field.children.filter(x=>x.isPoints).length,1);
  assert.equal(field.children.filter(x=>x.isLineSegments).length,1);
  assert.equal(field.children[0].geometry.attributes.position.count,7687);
  app.settle();
  assert.ok(app.state.pauses>0,'idle rendering pauses');
  app.eval('wake()');
  assert.ok(app.state.resumes>0,'interaction wakes rendering');
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
