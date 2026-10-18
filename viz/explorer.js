'use strict';

const $ = id => document.getElementById(id);
const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c =>
  ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const finite = value => Number.isFinite(+value) ? +value : 0;
const fmtB = value => {
  const x = finite(value);
  return x >= 1e12 ? (x/1e12).toFixed(1)+'T' : x >= 1e9 ? (x/1e9).toFixed(1)+'B' :
    x >= 1e6 ? (x/1e6).toFixed(0)+'M' : x.toLocaleString('en-US');
};
const lid = l => typeof l.source === 'object' ? l.source.id : l.source;
const ltd = l => typeof l.target === 'object' ? l.target.id : l.target;
const mix = (a,b,t) => 'rgb('+a.map((v,i) => Math.round(v+(b[i]-v)*t)).join(',')+')';
const frgColor = f => f < .5 ? mix([63,185,80],[210,153,34],f*2) :
  mix([210,153,34],[248,81,73],(f-.5)*2);
const sourceLinks = item => (item.sources||[]).filter(s => /^https:\/\//.test(s.source_uri||''))
  .map((s,i) => '<a href="'+esc(s.source_uri)+'" target="_blank" rel="noopener noreferrer">Source'+
    ((item.sources||[]).length>1 ? ' '+(i+1) : '')+(s.filing_date ? ' / '+esc(s.filing_date) : '')+'</a>').join(' / ');
const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
let G, meta={}, types={}, byId={}, nodes=[], links=[], fieldNodes=[], fieldLinks=[];
let live={}, sel=null, hovered=null, active=null, cascadeOn=false, cascadeTimer=null;
let revealed=new Set(), hops=[], trigger='', cascadeIds=new Set(), sceneField;
let renderDeadline=0, renderTimer=null, paused=false, dragging=false;
let selectedSearch=0, searchMatches=[], searchVersion=0;

function wake(milliseconds=200) {
  if (!G) return;
  renderDeadline=Math.max(renderDeadline, performance.now()+milliseconds);
  if (paused) { paused=false; G.resumeAnimation(); }
  if (renderTimer) return;
  const settle=() => {
    if (dragging || performance.now()<renderDeadline) { renderTimer=setTimeout(settle,80); return; }
    G.pauseAnimation(); paused=true; renderTimer=null;
  };
  renderTimer=setTimeout(settle,80);
}
function nodeColor(n) {
  if (cascadeOn) return revealed.has(n.id) ? n.color : '#263343';
  return active && !active.nodes.has(n) ? '#263343' : n.color;
}
function cascadeLink(l) { return cascadeOn && revealed.has(lid(l)) && revealed.has(ltd(l)); }
function linkColor(l) {
  if (cascadeOn) return cascadeLink(l) ? '#cba978' : '#192433';
  if (active) return active.links.has(l) ? '#cba978' : '#192433';
  return l.color;
}
function linkWidth(l) {
  if (cascadeOn) return cascadeLink(l) ? Math.max(1.8,l.width) : .25;
  return active ? (active.links.has(l) ? Math.max(1.8,l.width) : .25) : l.width;
}
function refresh() {
  if (!G) return;
  G.nodeColor(nodeColor).linkColor(linkColor).linkWidth(linkWidth)
    .linkDirectionalParticles(l => !motion.matches && cascadeTimer && cascadeLink(l) ? 3 : 0);
  if (sceneField) sceneField.highlight(active);
  wake();
}
function neighborhood(n) { return {nodes:new Set([n,...n.neighbors]),links:new Set(n.nlinks)}; }
function onHover(n) {
  if (cascadeOn || hovered===n) return;
  hovered=n;
  active=n ? neighborhood(n) : sel;
  document.body.style.cursor=n ? 'pointer' : '';
  refresh();
}
function cameraTo(point,distance=160) {
  const r=Math.hypot(point.x,point.y,point.z);
  const p=r>1 ? {x:point.x*(1+distance/r),y:point.y*(1+distance/r),z:point.z*(1+distance/r)} :
    {x:0,y:0,z:distance};
  wake(motion.matches ? 200 : 1100);
  G.cameraPosition(p,point,motion.matches ? 0 : 900);
}
function focusNode(n) {
  if (!n) return;
  showCard(n);
  cameraTo(n);
  if (!cascadeOn) { hovered=null; sel=neighborhood(n); active=sel; refresh(); }
  closeSearch();
}
function focusDeal(l) {
  if (!l) return;
  dealCard(l);
  const a=byId[lid(l)], b=byId[ltd(l)];
  if (a && b) {
    cameraTo({x:(a.x+b.x)/2,y:(a.y+b.y)/2,z:(a.z+b.z)/2});
    if (!cascadeOn) { hovered=null; sel={nodes:new Set([a,b]),links:new Set([l])}; active=sel; refresh(); }
  }
}
function otherEnd(n,l) { return byId[lid(l)===n.id ? ltd(l) : lid(l)]; }
function nodeButton(n) { return '<button class="cpc" data-id="'+esc(n.id)+'">'+esc(n.label)+'</button>'; }
function showCard(n) {
  const q=(live.quotes||{})[n.id], filing=(live.edgar||{})[n.id]||(live.edgar_last_observed||{})[n.id];
  const neighbors=[...new Set(n.neighbors)].sort((a,b) => b.usd-a.usd).slice(0,5);
  $('card').innerHTML='<div class="nm" dir="auto">'+esc(n.label)+'</div>'+
    '<div class="ty">'+esc(n.field ? 'Extracted party / raw layer' : types[n.type]||n.type||'Entity')+'</div>'+
    (n.note ? '<div class="nt" dir="auto">'+esc(n.note)+'</div>' : '')+
    (n.usd ? '<div class="usd">$'+fmtB(n.usd)+' '+esc(n.amount_label||'amount; see evidence date')+'</div>' : '')+
    (sourceLinks(n) ? '<div class="fl">'+sourceLinks(n)+'</div>' : '')+
    (n.fieldDeals ? '<div class="fl">'+n.fieldDeals.toLocaleString('en-US')+' extracted deals / $'+
      fmtB(n.fieldUsd)+' raw, unadjudicated</div>' : '')+
    (q && Number.isFinite(q.chg_pct) ? '<div class="pl">'+esc(q.sym)+' $'+finite(q.close).toFixed(2)+
      ' / '+(q.chg_pct>=0?'+':'')+q.chg_pct.toFixed(1)+'% / '+esc(q.date)+'</div>' : '')+
    (filing && filing.new_8k_7d ? '<div class="fl">'+finite(filing.new_8k_7d)+' new 8-K in 7 days'+
      (filing.observed_as_of ? ' / observed '+esc(filing.observed_as_of) : '')+'</div>' : '')+
    (neighbors.length ? '<div class="cps">'+neighbors.map(nodeButton).join('')+'</div>' : '')+
    (n.nlinks.length ? '<details id="connections"><summary>All connections ('+n.nlinks.length+
      ')</summary><div id="connection-list"></div></details>' : '<div class="fl">No saved connections.</div>');
  $('card').style.display='block';
  const disclosure=$('connections');
  if (disclosure) disclosure.addEventListener('toggle',() => {
    if (!disclosure.open || disclosure.dataset.loaded) return;
    disclosure.dataset.loaded='true';
    const list=$('connection-list'), version=disclosure;
    let offset=0;
    const append=() => {
      if (!version.isConnected) return;
      const chunk=n.nlinks.slice(offset,offset+100);
      list.insertAdjacentHTML('beforeend',chunk.map(l => {
        const other=otherEnd(n,l);
        return '<button class="connection" data-link="'+l.index+'" dir="auto">'+esc(other ? other.label : '')+
          ' / '+esc(l.field ? 'Raw extracted' : l.type.replace(/_/g,' '))+
          (l.usd ? ' / $'+fmtB(l.usd) : '')+'</button>';
      }).join(''));
      offset+=chunk.length;
      if (offset<n.nlinks.length) requestAnimationFrame(append);
    };
    append();
  });
}
function dealTags(l) {
  const tags=[];
  if (l.press) tags.push('Non-binding / press-only');
  if (l.circular) tags.push('Potential vendor round-trip');
  const a=byId[lid(l)], b=byId[ltd(l)];
  if (a && b && a.frg>.7 && b.frg>.7) tags.push('Fragile at both ends');
  else if (a && b && Math.max(a.frg,b.frg)>.8) tags.push('Fragile counterparty');
  return tags;
}
function dealCard(l) {
  const badge=l.field ? 'Raw extracted / unadjudicated' : l.tier==='filing_verified' ? 'Filing-verified role / measure' :
    l.tier==='issuer_announced' ? 'Issuer announcement' : l.tier==='historical' ? 'Historical relationship' :
    l.tier==='unconfirmed' ? 'Unconfirmed current relationship / scenario' : l.press ? 'Press-only / non-binding' : 'Source-backed';
  $('card').innerHTML='<div class="nm" dir="auto">'+esc(l.fromLabel)+' / '+esc(l.toLabel)+'</div>'+
    '<div class="ty">'+esc(l.field ? 'Collapsed deal link / obligor to risk-bearer' : l.type.replace(/_/g,' '))+'</div>'+
    '<span class="bdg">'+esc(badge)+'</span>'+dealTags(l).map(t => '<span class="bdg">'+esc(t)+'</span>').join('')+
    (l.usd ? '<div class="usd">$'+fmtB(l.usd)+(l.field ? ' raw / '+l.count+' extracted deals' : ' '+esc(l.amount_label||'amount; see source'))+'</div>' : '')+
    (l.note ? '<div class="nt" dir="auto">'+esc(l.note)+'</div>' : '')+
    (sourceLinks(l) ? '<div class="fl">'+sourceLinks(l)+'</div>' : '')+
    '<div class="cps">'+[byId[lid(l)],byId[ltd(l)]].filter(Boolean).map(nodeButton).join('')+'</div>';
  $('card').style.display='block';
}
function clearSelection() {
  $('card').style.display='none'; sel=null; active=null; hovered=null;
  if (!cascadeOn) refresh();
}
function stopCascade() {
  clearInterval(cascadeTimer); cascadeTimer=null; cascadeOn=false; revealed.clear();
  $('play').textContent='Cascade'; $('play').setAttribute('aria-pressed','false');
  $('ccline').style.opacity=0; active=sel; refresh();
}
function playCascade() {
  if (cascadeOn) { stopCascade(); return; }
  cascadeOn=true; active=null; hovered=null;
  revealed=new Set([trigger]);
  $('play').textContent='Stop cascade'; $('play').setAttribute('aria-pressed','true');
  $('ccline').style.opacity=1;
  const finish=() => {
    clearInterval(cascadeTimer); cascadeTimer=null;
    $('ccline').textContent='Scenario / CoreWeave total reported debt: $'+fmtB(meta.cascade_debt_at_risk_usd||0)+'. Loss allocation unmeasured.';
    refresh();
  };
  if (motion.matches) { cascadeIds.forEach(id => revealed.add(id)); finish(); return; }
  let step=0;
  $('ccline').textContent='Scenario / '+(byId[trigger]||{label:trigger}).label+' withdraws';
  wake(1100); G.zoomToFit(900,100,n => cascadeIds.has(n.id));
  cascadeTimer=setInterval(() => {
    if (step>=hops.length) { finish(); return; }
    const hop=hops[step++];
    (hop.nodes||[]).forEach(id => revealed.add(id));
    $('ccline').textContent='Scenario / '+(hop.label||'Hop '+hop.hop)+(hop.usd ? ' / $'+fmtB(hop.usd) : '');
    refresh();
  },1200);
  refresh();
}
motion.addEventListener('change',() => {
  if (motion.matches && cascadeOn) {
    clearInterval(cascadeTimer); cascadeTimer=null; cascadeIds.forEach(id => revealed.add(id));
    $('ccline').textContent='Scenario / CoreWeave total reported debt: $'+fmtB(meta.cascade_debt_at_risk_usd||0)+'. Loss allocation unmeasured.';
    refresh();
  }
});

function fieldLayer() {
  const group=new THREE.Group(), highlight=new THREE.Group();
  const positions=ns => new Float32Array(ns.flatMap(n => [n.x,n.y,n.z]));
  const linePositions=ls => new Float32Array(ls.flatMap(l => {
    const a=byId[lid(l)], b=byId[ltd(l)]; return [a.x,a.y,a.z,b.x,b.y,b.z];
  }));
  const geometry=values => {
    const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.BufferAttribute(values,3));
    return g;
  };
  const pointMaterial=new THREE.PointsMaterial({color:'#78889c',size:2.5,sizeAttenuation:false,
    transparent:true,opacity:.45,depthWrite:false});
  const points=new THREE.Points(geometry(positions(fieldNodes)),pointMaterial);
  points.raycast=() => {};
  const lines=new THREE.LineSegments(geometry(linePositions(fieldLinks)),
    new THREE.LineBasicMaterial({color:'#687b94',transparent:true,opacity:.03,depthWrite:false}));
  lines.raycast=() => {};
  group.add(points,lines,highlight);
  G.scene().add(group);
  const ray=new THREE.Raycaster(), pointer=new THREE.Vector2();
  return {
    pick(event) {
      if (!fieldNodes.length) return null;
      const rect=G.renderer().domElement.getBoundingClientRect();
      pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);
      const camera=G.camera(), distance=camera.position.length();
      ray.params.Points.threshold=Math.max(1,distance*Math.tan(camera.fov*Math.PI/360)*6/rect.height);
      ray.setFromCamera(pointer,camera);
      const hits=[];
      THREE.Points.prototype.raycast.call(points,ray,hits);
      hits.sort((a,b) => a.distance-b.distance);
      return hits.length ? fieldNodes[hits[0].index] : null;
    },
    highlight(selection) {
      while (highlight.children.length) {
        const object=highlight.children[0]; highlight.remove(object); object.geometry.dispose(); object.material.dispose();
      }
      pointMaterial.opacity=selection || cascadeOn ? .15 : .45;
      lines.material.opacity=selection || cascadeOn ? .012 : .03;
      if (!selection) return;
      const ns=[...selection.nodes].filter(n => n.field), ls=[...selection.links].filter(l => l.field);
      if (ns.length) highlight.add(new THREE.Points(geometry(positions(ns)),
        new THREE.PointsMaterial({color:'#adb8c8',size:4,sizeAttenuation:false})));
      if (ls.length) highlight.add(new THREE.LineSegments(geometry(linePositions(ls)),
        new THREE.LineBasicMaterial({color:'#adb8c8',transparent:true,opacity:.65})));
      highlight.children.forEach(object => { object.raycast=() => {}; });
    },
    update() {
      points.geometry.setAttribute('position',new THREE.BufferAttribute(positions(fieldNodes),3));
      lines.geometry.dispose(); lines.geometry=geometry(linePositions(fieldLinks));
      this.highlight(active);
    }
  };
}
function closeSearch() {
  $('search-results').hidden=true; $('entity-search').setAttribute('aria-expanded','false');
  $('entity-search').removeAttribute('aria-activedescendant');
}
function showSearch() {
  const value=$('entity-search').value.trim().toLocaleLowerCase(), results=$('search-results');
  const version=++searchVersion;
  if (!value) { closeSearch(); return; }
  // A bounded result list avoids adding thousands of DOM nodes on each keystroke.
  const all=nodes.filter(n => n.label.toLocaleLowerCase().includes(value) || n.id.toLocaleLowerCase().includes(value));
  searchMatches=all.slice(0,30); selectedSearch=0;
  if (version!==searchVersion) return;
  results.innerHTML='<div class="search-count" role="status">'+all.length.toLocaleString('en-US')+
    ' matches'+(all.length>30 ? '. First 30 shown; refine your search.' : '')+'</div>'+
    searchMatches.map((n,i) => '<button role="option" id="result-'+i+'" data-result="'+i+
      '" aria-selected="'+(i===0)+'" dir="auto">'+esc(n.label)+'</button>').join('');
  results.hidden=false; $('entity-search').setAttribute('aria-expanded','true');
  if (searchMatches.length) $('entity-search').setAttribute('aria-activedescendant','result-0');
}
function bindSearch() {
  $('entity-search').addEventListener('input',showSearch);
  $('entity-search').addEventListener('focus',showSearch);
  $('entity-search').addEventListener('keydown',event => {
    if (event.key==='Escape') { closeSearch(); return; }
    if (event.key==='Enter' && !$('search-results').hidden && searchMatches.length) {
      event.preventDefault(); focusNode(searchMatches[selectedSearch]); return;
    }
    if (!['ArrowDown','ArrowUp'].includes(event.key) || !searchMatches.length) return;
    event.preventDefault();
    selectedSearch=(selectedSearch+(event.key==='ArrowDown'?1:-1)+searchMatches.length)%searchMatches.length;
    [...$('search-results').querySelectorAll('[role=option]')].forEach((el,i) => el.setAttribute('aria-selected',String(i===selectedSearch)));
    $('entity-search').setAttribute('aria-activedescendant','result-'+selectedSearch);
    $('result-'+selectedSearch).scrollIntoView({block:'nearest'});
  });
  $('search-results').addEventListener('click',event => {
    const button=event.target.closest('[data-result]');
    if (button) focusNode(searchMatches[+button.dataset.result]);
  });
  document.addEventListener('pointerdown',event => { if (!event.target.closest('.search')) closeSearch(); });
}
function sourcePanel(data,fallback) {
  const origin=meta.generated_from||'Unknown report date';
  const date=meta.as_of||meta.report_as_of||(origin.match(/20\d{6}/)||[])[0];
  const label=date && /^\d{8}$/.test(date) ? date.slice(0,4)+'-'+date.slice(4,6)+'-'+date.slice(6) : date||origin;
  $('reportdate').textContent=label;
  $('m1').textContent='$'+fmtB(meta.reported_issuer_debt_usd ?? meta.committed_core_usd ?? 0);
  $('c_core').firstChild.textContent=meta.current_review ? 'Issuer debt ' : 'Core debt ';
  $('c_core').title=meta.debt_measure||'Historical adjudicated core debt.';
  const facts=[
    ['Report',label],['Core verdict',meta.core_verdict_label||meta.core_verdict||'Unavailable'],
    ['Reviewed issuers',meta.issuer_count],
    ['Debt measure',meta.debt_measure||'Historical committed-debt census'],
    ['Negative cash after capex',meta.negative_cash_after_capex==null ? null : meta.negative_cash_after_capex+' of '+meta.cashflow_observations],
    ['Historical report',meta.historical_as_of||meta.historical_report||origin],
    ['Core confidence (historical judgment)',meta.historical_core_confidence ?? meta.core_confidence],
    ['Ecosystem confidence (historical judgment)',meta.historical_ecosystem_confidence ?? meta.ecosystem_confidence],
    ['Extracted entities',(data.field||{}).entities||fieldNodes.length],
    ['Extracted deals',(data.field||{}).deals||0],
    ['Extracted field cutoff',(data.field||{}).evidence_date||'Unverified / retained field'],
    ['Layout',data.layout ? data.layout.algorithm : 'Deterministic fallback placement']
  ];
  $('panel').innerHTML='<h2>Sources and dates</h2>'+
    '<dl>'+facts.map(([key,value]) => '<dt>'+esc(key)+'</dt><dd>'+esc(value==null?'Unavailable':value)+'</dd>').join('')+'</dl>'+
    '<div id="credit-details"></div><div id="freshness-details"></div>'+
    '<h3>Evidence limits</h3><ul>'+[...(meta.honest_caveats||[]),...((data.field||{}).note ? [data.field.note] : [])]
      .map(c => '<li>'+esc(c)+'</li>').join('')+'</ul>';
  $('load-status').textContent=fallback ? 'Saved core fallback. Full extracted data could not be loaded.' :
    nodes.length ? '' : 'No entities in this dataset.';
}
function applyLive(value) {
  live=value||{};
  const quotes=Object.values(live.quotes||{}), dates=[...new Set(quotes.map(q => q.date).filter(Boolean))].sort();
  if (dates.length) {
    $('lt').textContent=dates[0]+(dates.length>1 ? ' to '+dates[dates.length-1] : '');
    $('livechip').hidden=false;
  }
  const credit=live.credit||{}, bits=[];
  ['hy_oas','ccc_oas','bb_oas','ust5y'].forEach(key => {
    const q=credit[key]; if (q && Number.isFinite(q.value)) bits.push(key.replace(/_/g,' ').toUpperCase()+': '+q.value.toFixed(2)+'% ('+q.date+')');
  });
  const signal=(live.signals||[]).find(s => s.id==='S3_bdc_discount_differential');
  if (signal && Number.isFinite(signal.differential_pp)) bits.push('AI-BDC discount differential: '+signal.differential_pp.toFixed(1)+'pp vs control');
  const issuance=live.issuance_latest;
  if (issuance && Number.isFinite(issuance.spread_vs_5y_bp)) bits.push('Latest coupon proxy: +'+issuance.spread_vs_5y_bp+'bp ('+issuance.date+')');
  $('credit-details').innerHTML='<h3>Market overlay</h3><ul>'+bits.map(b => '<li>'+esc(b)+'</li>').join('')+'</ul>'+
    '<p>Market observations and the BDC comparison are separate from adjudicated evidence. Signal definitions and amendments remain in the repository.</p>';
}
function applyFreshness(status) {
  const acquisition=status.sec_acquisition||{}, queue=acquisition.new_run_queue||{}, market=status.market||{};
  const dates=value => Array.isArray(value) ? value.join(', ') : 'Unavailable';
  const facts=[
    ['Snapshot (Pacific)',status.snapshot_at_pacific||'Unavailable'],
    ['Prices',dates(market.price_dates)],['Credit',dates(market.credit_dates)],
    ['Reported BDC NAV',dates(market.nav_periods)],
    ['SEC retained baseline',acquisition.baseline_inventory],['SEC new documents acquired',queue.acquired||0],
    ['SEC documents queued',(queue.queued||0)+(queue.inflight||0)],
    ['SEC recovered source errors',acquisition.recovered_failures||0],
    ['SEC unresolved source errors',acquisition.unresolved_source_errors ?? queue.failed ?? 0],
    ['Exhibit documents acquired',((acquisition.exhibits||{}).documents||{}).acquired||0],
    ['Exhibit completion',(acquisition.exhibits||{}).status||'Unavailable']
  ];
  $('freshness-details').innerHTML='<h3>Evidence refresh</h3><dl>'+facts.map(([label,value]) =>
    '<dt>'+esc(label)+'</dt><dd>'+esc(value==null?'Unavailable':value)+'</dd>').join('')+'</dl>'+
    '<p>'+esc(acquisition.note||'')+'</p>'+
    (status.complete ? '' : '<p>The broad acquisition is incomplete. Current financial measurements retain their stated period ends.</p>');
}
function place(n,position,index,total,field=false) {
  const angle=index*2.399963229728653, radius=field ? 200+350*Math.sqrt((index+1)/Math.max(total,1)) : 100;
  const point=Array.isArray(position) && position.length===3 && position.every(Number.isFinite) ? position :
    [Math.cos(angle)*radius,Math.sin(angle)*radius,Math.sin(index*.7)*(field ? 180 : 70)];
  [n.x,n.y,n.z]=point; if (!field) { n.fx=n.x; n.fy=n.y; n.fz=n.z; }
}
function boot(data,fallback=false) {
  if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.edges)) throw new Error('Invalid graph data');
  meta=data.meta||{}; types=(data.legend||{}).node_types||{};
  const layout=data.layout||{};
  nodes=data.nodes.map((n,i) => {
    const frg=Math.max(0,Math.min(1,finite(n.fragility)));
    const node={...n,label:String(n.label||n.id),usd:finite(n.usd),frg,color:n.fragility==null ? '#78889c' : frgColor(frg),
      val:Math.max(1.2,Math.sqrt(Math.max(0,finite(n.usd))/1e9)*1.7),neighbors:[],nlinks:[]};
    place(node,(layout.core||{})[node.id],i,data.nodes.length); return node;
  });
  byId=Object.assign(Object.create(null),Object.fromEntries(nodes.map(n => [n.id,n])));
  links=data.edges.filter(e => byId[e.from] && byId[e.to]).map(e => {
    const a=byId[e.from], b=byId[e.to], press=e.tier==='press_reported';
    const vendorFunding=['equity_investment','announced_investment','framework_commitment','cloud_services_contract','conditional_guarantee'];
    const circular=(e.from==='NVIDIA' && vendorFunding.includes(e.type)) ||
      (e.to==='NVIDIA' && e.type==='gpu_purchase' && data.edges.some(other =>
        other.from==='NVIDIA' && other.to===e.from && vendorFunding.includes(other.type)));
    const risk=Math.min(1,.25*(a.frg+b.frg)+.35*Number(press)+.15*Number(circular));
    return {...e,source:e.from,target:e.to,type:e.type||'exposure',usd:finite(e.usd),press,circular,risk,
      fromLabel:a.label,toLabel:b.label,color:['unconfirmed','historical'].includes(e.tier) ? '#687b94' : mix([72,89,112],[178,76,86],risk),
      width:press ? .6 : Math.min(3.2,Math.max(.5,Math.sqrt(finite(e.usd)/1e9)*.45))};
  });
  const field=data.field||{}, fieldIds=[];
  (field.nodes||[]).forEach((row,i) => {
    if (row[3] && byId[row[3]]) {
      fieldIds.push(row[3]); byId[row[3]].fieldUsd=finite(row[1]); byId[row[3]].fieldDeals=finite(row[2]); return;
    }
    const node={id:'f'+i,label:String(row[0]||'(unnamed party)'),type:'field_entity',field:true,
      usd:0,fieldUsd:finite(row[1]),fieldDeals:finite(row[2]),neighbors:[],nlinks:[]};
    place(node,(layout.field||[])[i],i,(field.nodes||[]).length,true);
    fieldIds.push(node.id); nodes.push(node); byId[node.id]=node;
  });
  (field.links||[]).forEach(row => {
    const a=fieldIds[row[0]], b=fieldIds[row[1]];
    if (!byId[a] || !byId[b] || a===b) return;
    links.push({source:a,target:b,usd:finite(row[2]),count:finite(row[3])||1,type:'deals',tier:'raw_extracted',
      field:true,fromLabel:byId[a].label,toLabel:byId[b].label});
  });
  links.forEach((l,index) => {
    l.index=index; const a=byId[lid(l)], b=byId[ltd(l)];
    a.neighbors.push(b); b.neighbors.push(a); a.nlinks.push(l); b.nlinks.push(l);
  });
  fieldNodes=nodes.filter(n => n.field); fieldLinks=links.filter(l => l.field);
  const cascade=data.cascade||{}; trigger=cascade.trigger||''; hops=cascade.hops||[];
  cascadeIds=new Set([trigger,...hops.flatMap(h => h.nodes||[])]);
  G=ForceGraph3D()($('g')).backgroundColor('#05070c').showNavInfo(false)
    .warmupTicks(0).cooldownTicks(0).cooldownTime(0)
    .graphData({nodes:nodes.filter(n => !n.field),links:links.filter(l => !l.field)})
    .nodeLabel(n => esc(n.label)).nodeColor(nodeColor).nodeVal(n => n.val).nodeOpacity(.95)
    .linkColor(linkColor).linkWidth(linkWidth).linkDirectionalParticleWidth(2)
    .linkLabel(l => esc(l.fromLabel)+' / '+esc(l.toLabel)+(l.usd ? ' / $'+fmtB(l.usd) : ''))
    .onNodeHover(onHover).onNodeClick(focusNode).onLinkClick(focusDeal)
    .onBackgroundClick(event => {
      const node=sceneField.pick(event); if (node) focusNode(node); else clearSelection();
    })
    .onNodeDrag(() => { dragging=true; sceneField.update(); wake(); })
    .onNodeDragEnd(() => { dragging=false; sceneField.update(); wake(); });
  G.d3Force('charge',null); G.d3Force('link',null); G.d3Force('center',null);
  G.renderer().setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  const controls=G.controls(); controls.staticMoving=true;
  controls.addEventListener('start',() => { dragging=true; wake(); });
  controls.addEventListener('end',() => { dragging=false; wake(); });
  controls.addEventListener('change',() => wake());
  sceneField=fieldLayer();
  let autoCamera=true, initialFitPending=true;
  const fitInitial=() => {
    if (!initialFitPending || !autoCamera || document.hidden) return;
    initialFitPending=false;
    wake(1100);
    requestAnimationFrame(() => {
      if (document.hidden) { initialFitPending=true; return; }
      if (autoCamera && nodes.some(n => !n.field)) G.zoomToFit(motion.matches ? 0 : 900,100);
    });
  };
  ['pointerdown','pointermove','wheel','touchstart','keydown'].forEach(name => {
    $('g').addEventListener(name,() => {
      if (name!=='pointermove') autoCamera=false;
      wake(250);
    },{capture:true,passive:true});
  });
  $('g').addEventListener('pointerdown',() => { dragging=true; },true);
  window.addEventListener('pointerup',() => { dragging=false; wake(); });
  window.addEventListener('pointercancel',() => { dragging=false; wake(); });
  window.addEventListener('resize',() => { G.width(window.innerWidth).height(window.innerHeight); wake(); });
  document.addEventListener('visibilitychange',() => {
    if (document.hidden) { G.pauseAnimation(); paused=true; }
    else { wake(); fitInitial(); }
  });
  setTimeout(fitInitial,100);
  sourcePanel(data,fallback); bindSearch();
  $('play').disabled=!trigger || !hops.length || !byId[trigger];
  $('play').onclick=playCascade;
  const toggle=(button,panel) => {
    const open=panel.style.display!=='block'; panel.style.display=open ? 'block' : 'none';
    button.setAttribute('aria-expanded',String(open));
  };
  $('info').onclick=() => toggle($('info'),$('panel'));
  const deals=links.filter(l => !l.field).sort((a,b) => b.risk-a.risk || b.usd-a.usd);
  $('dpanel').innerHTML='<h2>Deal exposures</h2><p>Ordered by fragility, evidence tier, and circularity. These are review priorities.</p>'+
    deals.map(l => '<button class="connection deal" data-link="'+l.index+'"><span class="dl">'+esc(l.fromLabel)+
      ' / '+esc(l.toLabel)+(l.usd ? ' / $'+fmtB(l.usd) : '')+'</span><span class="dwhy">'+
      esc(dealTags(l).join(' / '))+'</span></button>').join('');
  $('deals').onclick=() => toggle($('deals'),$('dpanel'));
  [$('card'),$('dpanel')].forEach(panel => panel.addEventListener('click',event => {
    const button=event.target.closest('[data-id],[data-link]'); if (!button) return;
    if (button.dataset.id) focusNode(byId[button.dataset.id]);
    else focusDeal(links[+button.dataset.link]);
  }));
  document.addEventListener('keydown',event => {
    if (event.key!=='Escape') return;
    closeSearch(); clearSelection();
    ['panel','dpanel'].forEach(id => { $(id).style.display='none'; });
    $('info').setAttribute('aria-expanded','false'); $('deals').setAttribute('aria-expanded','false');
  });
  fetch('live.json',{cache:'no-cache'}).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(applyLive).catch(() => { $('credit-details').textContent='Market overlay unavailable.'; });
  fetch('freshness.json',{cache:'no-cache'}).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(applyFreshness).catch(() => { $('freshness-details').textContent='Extended acquisition status unavailable.'; });
}
async function start() {
  let data, fallback=false;
  try {
    const response=await fetch('graph_data.json',{cache:'no-cache'});
    if (!response.ok) throw new Error('Graph HTTP '+response.status);
    data=await response.json();
  } catch (_) { data=EMBEDDED; fallback=true; }
  try { boot(data,fallback); }
  catch (error) {
    $('load-status').textContent='The visualization could not start. Reload to retry.';
    console.error('Bubble visualization failed',error);
  }
}
start();
