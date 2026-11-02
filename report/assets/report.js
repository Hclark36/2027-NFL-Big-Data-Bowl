(() => {
  'use strict';
  const D = JSON.parse(document.getElementById('report-data').textContent);
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = (value, digits=3) => { if(!Number.isFinite(value))return '—'; const rounded=Number(value.toFixed(digits)); return (Object.is(rounded,-0)?0:rounded).toFixed(digits); };
  const palette = ['#147d75','#d06b32','#426ab0','#9971aa','#7c8230','#a34b67'];
  const positions = ['DB','DL','OL','TE','WR'];
  const bands = ['2-to-4','4-to-6','6-to-8','8-to-10','3-to-7'];
  const state = {position:D.defaults.position, year:D.defaults.year, forty:D.defaults.forty,
    cross:false, groups:[D.defaults.position], players:new Set(D.defaults.players), attempts:new Set(),
    window:'7', reference:'recording', bands:new Set(bands.slice(0,4)), cursor:0, playing:false};
  let plotCache=[], xBounds=[0,5], animation=null, previousFrame=null, resizeTimer=null;
  const personById = new Map(D.people.map(p=>[p.id,p]));
  function option(select, label, value) { const o=document.createElement('option');o.textContent=label;o.value=value;select.append(o); }
  positions.forEach(p=>{option($('position'),p,p);option($('cross-groups'),p,p);});
  $('position').value=state.position;$('year').value=state.year;
  Array.from($('cross-groups').options).forEach(o=>o.selected=state.groups.includes(o.value));
  bands.forEach(b=>{const label=document.createElement('label');const input=document.createElement('input');input.type='checkbox';input.value=b;input.checked=state.bands.has(b);input.addEventListener('change',()=>{input.checked?state.bands.add(b):state.bands.delete(b);render();});label.append(input,document.createTextNode(b.replace('-to-',' → ')));$('band-options').append(label);});
  function groupPeople() {return D.people.filter(p=>(state.cross?state.groups:[state.position]).includes(p.position)&&(state.year==='ALL'||p.year===state.year));}
  function eligiblePeople() {return groupPeople().filter(p=>state.forty===-1||p.forty===state.forty).sort((a,b)=>a.forty-b.forty||a.name.localeCompare(b.name));}
  function stop() {state.playing=false;if(animation!==null)cancelAnimationFrame(animation);animation=null;previousFrame=null;$('play').textContent='Play cursor';$('play').setAttribute('aria-label','Play the recorded-time cursor');}
  function resetAttempts() {state.attempts=new Set([...state.players].flatMap(id=>personById.get(id)?.records||[]));}
  function refreshFilters() {
    stop();const people=groupPeople(),counts=new Map();people.forEach(p=>counts.set(p.forty,(counts.get(p.forty)||0)+1));
    if(state.forty!==-1&&!counts.has(state.forty)){const top=[...counts].sort((a,b)=>b[1]-a[1]||a[0]-b[0])[0];state.forty=top?top[0]:-1;}
    $('forty').replaceChildren();option($('forty'),'All official times',-1);
    [...counts.keys()].sort((a,b)=>a-b).forEach(t=>option($('forty'),`${(t/100).toFixed(2)} s · ${counts.get(t)} players`,t));
    $('forty').value=String(state.forty);
    const eligible=eligiblePeople(),allowed=new Set(eligible.map(p=>p.id));state.players=new Set([...state.players].filter(id=>allowed.has(id)));
    if(state.players.size===0)eligible.slice(0,2).forEach(p=>state.players.add(p.id));
    resetAttempts();renderPlayerList();renderAttempts();render();
  }
  function renderPlayerList() {
    const search=$('player-search').value.trim().toLowerCase();$('player-list').replaceChildren();
    const people=eligiblePeople().filter(p=>p.name.toLowerCase().includes(search));
    if(!people.length){const p=document.createElement('p');p.className='hint';p.textContent='No players match these filters.';$('player-list').append(p);}
    people.forEach(p=>{const label=document.createElement('label');label.className='choice';const box=document.createElement('input');box.type='checkbox';box.value=p.id;box.checked=state.players.has(p.id);box.setAttribute('aria-label',`Select ${p.name}`);
      box.addEventListener('change',()=>{if(box.checked&&state.players.size>=6){box.checked=false;$('selection-status').textContent='Select up to six players for a readable comparison.';return;}stop();box.checked?state.players.add(p.id):state.players.delete(p.id);resetAttempts();renderPlayerList();renderAttempts();render();});
      const text=document.createElement('span');text.innerHTML=`<strong>${esc(p.name)}</strong><small>${esc(p.position)} · ${esc(p.year)} · ${(p.forty/100).toFixed(2)} s · ${p.records.length} recording${p.records.length===1?'':'s'}</small>`;label.append(box,text);$('player-list').append(label);});
    $('selected-count').textContent=`${state.players.size} / 6 selected`;
  }
  function renderAttempts(){ $('attempt-list').replaceChildren();let n=0;
    eligiblePeople().filter(p=>state.players.has(p.id)).forEach(p=>p.records.forEach(key=>{const a=D.attempts[key];const label=document.createElement('label');label.className='choice';const box=document.createElement('input');box.type='checkbox';box.value=key;box.checked=state.attempts.has(key);box.setAttribute('aria-label',`${p.name}, attempt ${a.attempt}`);box.addEventListener('change',()=>{stop();box.checked?state.attempts.add(key):state.attempts.delete(key);renderAttempts();render();});const text=document.createElement('span');text.textContent=`${p.name} · attempt ${a.attempt}`;label.append(box,text);$('attempt-list').append(label);if(box.checked)n++;}));
    $('attempt-count').textContent=`(${n} selected)`;
  }
  function table(id,headers,rows){const t=$(id);t.querySelector('thead').innerHTML='<tr>'+headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')+'</tr>';t.querySelector('tbody').innerHTML=rows.map(row=>'<tr>'+row.map(c=>`<td>${typeof c==='object'?c.html:esc(c)}</td>`).join('')+'</tr>').join('');}
  const ns='http://www.w3.org/2000/svg';
  function el(tag,attrs={},text){const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,String(v)));if(text!==undefined)e.textContent=text;return e;}
  function pathFor(xs,ys,sx,sy){let path='',open=false;for(let i=0;i<xs.length;i++){if(!Number.isFinite(ys[i])){open=false;continue;}path+=(open?'L':'M')+sx(xs[i]).toFixed(2)+','+sy(ys[i]).toFixed(2);open=true;}return path;}
  function plot(id,series,kind){const svg=$(id);svg.replaceChildren();const width=Math.max(280,Math.round(svg.getBoundingClientRect().width)||420),height=290,m={l:39,r:13,t:16,b:36};svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
    if(!series.length){svg.append(el('text',{x:width/2,y:height/2,'text-anchor':'middle',class:'empty-chart'},'Select players and recordings.'));return null;}
    const allY=series.flatMap(s=>kind==='speed'?s.a.speed:s.curve.values).filter(Number.isFinite);let ymin=kind==='speed'?0:Math.min(0,Math.floor(Math.min(...allY))),ymax=Math.max(1,Math.ceil(Math.max(...allY)));if(ymax===ymin)ymax=ymin+1;
    const sx=x=>m.l+(x-xBounds[0])/(xBounds[1]-xBounds[0])*(width-m.l-m.r),sy=y=>height-m.b-(y-ymin)/(ymax-ymin)*(height-m.t-m.b);
    const defs=el('defs'),clip=el('clipPath',{id:id+'-clip'});clip.append(el('rect',{x:m.l,y:m.t,width:width-m.l-m.r,height:height-m.t-m.b}));defs.append(clip);svg.append(defs);
    for(let i=0;i<=4;i++){const y=ymin+(ymax-ymin)*i/4,x=xBounds[0]+(xBounds[1]-xBounds[0])*i/4;svg.append(el('line',{x1:m.l,x2:width-m.r,y1:sy(y),y2:sy(y),class:'plot-grid'}),el('text',{x:m.l-7,y:sy(y)+3,'text-anchor':'end',class:'axis-text'},y.toFixed(1)),el('text',{x:sx(x),y:height-15,'text-anchor':'middle',class:'axis-text'},x.toFixed(1)));}
    svg.append(el('line',{x1:m.l,x2:width-m.r,y1:height-m.b,y2:height-m.b,class:'axis-line'}));
    if(kind==='speed'){const guides=new Set();state.bands.forEach(b=>b.split('-to-').forEach(v=>guides.add(Number(v))));guides.forEach(y=>{if(y<=ymax)svg.append(el('line',{x1:m.l,x2:width-m.r,y1:sy(y),y2:sy(y),stroke:'#c0cbc4','stroke-dasharray':'2 4','stroke-width':1}));});}
    const content=el('g',{'clip-path':`url(#${id}-clip)`});svg.append(content);
    series.forEach(s=>{const values=kind==='speed'?s.a.speed:s.curve.values;const path=el('path',{d:pathFor(s.x,values,sx,sy),fill:'none',stroke:s.color,'stroke-width':1.9,'stroke-dasharray':s.dash});path.append(el('title',{},s.label));content.append(path);
      if(kind==='accel'){const px=sx(s.curve.peakTime-s.offset),py=sy(s.curve.peakValue);const marker=s.curve.boundary?el('path',{d:`M${px},${py-5}L${px-4.5},${py+4}L${px+4.5},${py+4}Z`,fill:s.color,stroke:'white','stroke-width':1}):el('circle',{cx:px,cy:py,r:4.3,fill:s.color,stroke:'white','stroke-width':1});marker.append(el('title',{},`${s.label}: observed peak ${fmt(s.curve.peakValue)} at ${fmt(s.curve.peakTime-s.offset,1)} s (${s.curve.boundary?'supported-region boundary':'interior'})`));content.append(marker);}
    });
    const cursor=el('line',{x1:sx(state.cursor),x2:sx(state.cursor),y1:m.t,y2:height-m.b,class:'cursor-line'});content.append(cursor);
    const dots=series.map(s=>{const dot=el('circle',{r:3.5,fill:s.color,class:'cursor-dot'});content.append(dot);return {dot,s,values:kind==='speed'?s.a.speed:s.curve.values};});
    return {sx,sy,cursor,dots};
  }
  function interpolate(xs,ys,at){if(at<xs[0]||at>xs[xs.length-1])return null;let i=xs.findIndex(x=>x>=at);if(i<0)return null;if(i===0||Math.abs(xs[i]-at)<1e-8)return Number.isFinite(ys[i])?ys[i]:null;if(!Number.isFinite(ys[i-1])||!Number.isFinite(ys[i]))return null;return ys[i-1]+(ys[i]-ys[i-1])*(at-xs[i-1])/(xs[i]-xs[i-1]);}
  function updateCursor(){state.cursor=Math.max(xBounds[0],Math.min(xBounds[1],state.cursor));$('time-scrub').value=state.cursor;$('time-value').textContent=state.cursor.toFixed(1)+' s';plotCache.forEach(p=>{if(!p)return;p.cursor.setAttribute('x1',p.sx(state.cursor));p.cursor.setAttribute('x2',p.sx(state.cursor));p.dots.forEach(({dot,s,values})=>{const value=interpolate(s.x,values,state.cursor);dot.setAttribute('visibility',value===null?'hidden':'visible');if(value!==null){dot.setAttribute('cx',p.sx(state.cursor));dot.setAttribute('cy',p.sy(value));}});});}
  function render(){stop();const people=eligiblePeople().filter(p=>state.players.has(p.id)),series=[],unavailable=[];
    people.forEach((p,index)=>p.records.forEach((key,attemptIndex)=>{if(!state.attempts.has(key))return;const a=D.attempts[key],curve=a.curves[state.window];if(!curve){unavailable.push(`${p.name}, attempt ${a.attempt}: no supported derivative`);return;}if(state.reference==='speed3'&&!Number.isFinite(a.reference3)){unavailable.push(`${p.name}, attempt ${a.attempt}: speed reference unavailable`);return;}const offset=state.reference==='speed3'?a.reference3:0;series.push({p,a,curve,offset,x:a.t.map(t=>t-offset),color:palette[index%palette.length],dash:['','6 4','2 3','8 3 2 3'][attemptIndex%4],label:`${p.name} · ${p.year} · attempt ${a.attempt}`});}));
    const allX=series.flatMap(s=>[s.x[0],s.x[s.x.length-1]]);xBounds=allX.length?[Math.min(...allX),Math.max(...allX)]:[0,5];if(xBounds[0]===xBounds[1])xBounds[1]+=1;state.cursor=xBounds[0];
    $('time-scrub').min=xBounds[0];$('time-scrub').max=xBounds[1];$('play').disabled=!series.length;
    const years=new Set(series.map(s=>s.p.year)),groups=new Set(series.map(s=>s.p.position));
    $('selection-status').innerHTML=`<strong>${people.length} player${people.length===1?'':'s'} · ${series.length} plotted recording${series.length===1?'':'s'}</strong>${state.forty===-1?'':` · published ${(state.forty/100).toFixed(2)} s 40`}${years.size>1?'<br>Multiple draft years: recording or processing differences may affect comparison.':''}${groups.size>1?'<br>Cross-position mode: roles and body sizes differ.':''}${unavailable.length?'<br>'+unavailable.map(esc).join('<br>'):''}`;
    plotCache=[plot('speed-chart',series,'speed'),plot('accel-chart',series,'accel')];
    $('plot-legend').innerHTML=series.map(s=>`<span class="legend-item"><i class="legend-line" style="border-color:${s.color};border-top-style:${s.dash?'dashed':'solid'}"></i>${esc(s.label)}${s.curve.boundary?' · △ boundary peak':''}</span>`).join('');
    $('reference-label').textContent=state.reference==='recording'?'X-axis: seconds since first recorded frame. This is not confirmed time from physical launch.':'X-axis: seconds relative to the observed 3-unit speed crossing. Negative times precede that reference; this is not physical launch.';
    table('peak-table',['Player','Group / year','Official 40','Attempt','Observed peak (raw/s)','Time from recording start','Time from selected reference','Peak location'],series.map(s=>[s.p.name,`${s.p.position} / ${s.p.year}`,(s.p.forty/100).toFixed(2)+' s',s.a.attempt,fmt(s.curve.peakValue),fmt(s.curve.peakTime,1)+' s',fmt(s.curve.peakTime-s.offset,1)+' s',s.curve.boundary?{html:'<span class="boundary">Boundary — review</span>'}:'Interior']));
    const selectedBands=bands.filter(b=>state.bands.has(b));
    table('interval-table',['Player','Attempt',...selectedBands.map(b=>b.replace('-to-',' → ')+' raw')],series.map(s=>[s.p.name,s.a.attempt,...selectedBands.map(b=>{const value=s.a.intervals[b];return value&&value.status==='Measured'?fmt(value.duration)+' s':{html:`<span class="unavailable" title="${esc(value?.status||'Not measured')}">Unavailable</span>`};})]));
    updateCursor();
  }
  function showView(view){const compare=view==='comparison';$('report-panel').hidden=compare;$('comparison-panel').hidden=!compare;['report','comparison'].forEach(v=>{$('tab-'+v).classList.toggle('active',v===view);$('tab-'+v).setAttribute('aria-selected',String(v===view));});if(compare)render();else stop();}
  $('tab-report').addEventListener('click',()=>showView('report'));$('tab-comparison').addEventListener('click',()=>showView('comparison'));
  $('open-comparison').addEventListener('click',()=>{showView('comparison');$('comparison-panel').scrollIntoView({block:'start'});});
  $('print-report').addEventListener('click',()=>{showView('report');window.print();});
  $('position').addEventListener('change',e=>{state.position=e.target.value;refreshFilters();});
  $('year').addEventListener('change',e=>{state.year=e.target.value;refreshFilters();});
  $('forty').addEventListener('change',e=>{state.forty=Number(e.target.value);refreshFilters();});
  $('cross-position').addEventListener('change',e=>{state.cross=e.target.checked;$('position').disabled=state.cross;$('cross-groups-wrap').hidden=!state.cross;if(state.cross){state.groups=[state.position];Array.from($('cross-groups').options).forEach(o=>o.selected=state.groups.includes(o.value));}refreshFilters();});
  $('cross-groups').addEventListener('change',e=>{state.groups=Array.from(e.target.selectedOptions,o=>o.value);refreshFilters();});
  $('player-search').addEventListener('input',renderPlayerList);
  $('window').addEventListener('change',e=>{state.window=e.target.value;render();});$('reference').addEventListener('change',e=>{state.reference=e.target.value;render();});
  $('time-scrub').addEventListener('input',e=>{stop();state.cursor=Number(e.target.value);updateCursor();});
  $('play').addEventListener('click',()=>{if(state.playing){stop();return;}if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){state.cursor=state.cursor>=xBounds[1]?xBounds[0]:Math.min(xBounds[1],state.cursor+.1);updateCursor();return;}if(state.cursor>=xBounds[1])state.cursor=xBounds[0];state.playing=true;$('play').textContent='Pause cursor';$('play').setAttribute('aria-label','Pause the recorded-time cursor');previousFrame=null;const frame=now=>{if(!state.playing)return;if(previousFrame!==null)state.cursor+=(now-previousFrame)/1000;previousFrame=now;updateCursor();if(state.cursor>=xBounds[1]){stop();return;}animation=requestAnimationFrame(frame);};animation=requestAnimationFrame(frame);});
  window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(!$('comparison-panel').hidden)render();},120);});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  refreshFilters();
})();
