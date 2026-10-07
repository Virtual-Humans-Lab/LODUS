import * as maplibregl from 'maplibre-gl';
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import {MapLibreOverlay} from '@deck.gl/maplibre';
import {GeoJsonLayer,PathLayer,ScatterplotLayer,TextLayer} from '@deck.gl/layers';
import {HeatmapLayer} from '@deck.gl/aggregation-layers';
import type {Layer,PickingInfo} from '@deck.gl/core';
import type {FeatureCollection} from 'geojson';
import {StreetParticleLayer} from './particle-layer';
import {hydrateRoutes,validateRun,visibleCount,populationWeight,tripWeight,fraction,prepareParticles,routePosition,originColor} from './data';
import {RenderBenchmark,downloadResult,measureIdleCadence,type BenchmarkResult} from './benchmark';
import type {Run,Atlas,ParticleBuffers,Filters,XY,Population} from './types';
import './style.css';
maplibregl.setWorkerUrl(mapWorkerUrl);

const el=<T extends HTMLElement=HTMLElement>(id:string)=>document.getElementById(id) as T;
const text=(id:string,value:string)=>{el(id).textContent=value;};
const format=(n:number)=>new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(n);
const cyan:[number,number,number]=[92,225,191], orange:[number,number,number]=[248,139,101];
const zero:Population={Total:0,Locals:0,Outsiders:0,dTotals:0,dLocals:0,dOutsiders:0};
const benchmark=new RenderBenchmark();
let run:Run,atlas:Atlas,prepared:ParticleBuffers[],map:maplibregl.Map,overlay:MapLibreOverlay;
let clock=18,playing=false,speed=.1,previous=0,lastUi=0,currentHour=-1;
let filters:Filters={age:15,occupation:7,status:3};
let staticLayers:Layer[]=[],particleLayer:StreetParticleLayer|undefined,frameBuffers:ParticleBuffers;
let neighborhoodData:FeatureCollection,selectedVenue=0,stressBuffers:ParticleBuffers|undefined;
let benchmarkResult:BenchmarkResult|undefined,renderCount=0,fpsStart=0,lastRender=0;
const layerOptions={particles:true,boundaries:true,heat:false,sir:false};
let graphicsError=false;
let colorByOrigin=false,concentrationLayers:Layer[]=[],lastConcentration=0;
const concentrationOptions={centers:false,pois:false};

function hour(){return Math.min(23,Math.floor(clock));}
function alpha(){return clock-hour();}
function mask(id:string){return [...el(id).querySelectorAll<HTMLInputElement>('input:checked')].reduce((m,n)=>m|(1<<Number(n.value)),0);}
function resetFilters() {
  for(const id of ['ages','occupations','residency'])el(id).querySelectorAll<HTMLInputElement>('input').forEach(i=>i.checked=true);
  filters={age:15,occupation:7,status:3};
}
function regionState(frame:number,name:string):Population {
  if(run.meta.level==='regions')return run.frames[frame].zones[name]??zero;
  const aggregate={...zero};
  for(const [node,p] of Object.entries(run.frames[frame].zones))if(node.split('//')[0]===name)for(const key of Object.keys(aggregate) as (keyof Population)[])aggregate[key]+=p[key];
  return aggregate;
}
function zoneFlux(name:string) {
  const h=hour();return h===23?0:populationWeight(regionState(h+1,name),run,filters)-populationWeight(regionState(h,name),run,filters);
}
function zonePopulation(name:string) {
  const h=hour(),a=alpha();return (1-a)*populationWeight(regionState(h,name),run,filters)+a*populationWeight(regionState(Math.min(23,h+1),name),run,filters);
}
function tooltip(info:PickingInfo) {
  const tip=el('tooltip');
  const name=info.object?.properties?.name;
  if(!name){tip.hidden=true;return;}
  tip.textContent=`${name}\n${format(zonePopulation(name))} estimated people\n${zoneFlux(name)>=0?'+':''}${format(zoneFlux(name))} net change into ${Math.min(23,hour()+1)}:00`;
  tip.hidden=false;tip.style.left=`${Math.min(innerWidth-245,info.x+320)}px`;tip.style.top=`${Math.min(innerHeight-180,info.y+12)}px`;
}
function pointTooltip(info:PickingInfo,textValue?:string) {
  const tip=el('tooltip');
  if(!textValue){tip.hidden=true;return;}
  tip.textContent=textValue;tip.hidden=false;
  const rect=map.getContainer().getBoundingClientRect();
  tip.style.left=`${Math.min(innerWidth-255,rect.left+info.x+12)}px`;
  tip.style.top=`${Math.min(innerHeight-200,info.y+12)}px`;
}
function updateConcentrations() {
  const h=hour(),a=alpha(),demographic=fraction(run.meta.demographics.age,filters.age)*fraction(run.meta.demographics.occupation,filters.occupation);
  const centers=Object.entries(run.zonePoints).map(([name,position])=>({name,position,weight:zonePopulation(name)}));
  const pois=(run.pois??[]).map(p=>{
    const at=(i:number)=>demographic*(((filters.status&1)?p.locals[i]:0)+((filters.status&2)?p.hours[i]-p.locals[i]:0));
    return {...p,weight:at(h)*(1-a)+at(Math.min(23,h+1))*a};
  }).filter(p=>p.weight>0);
  concentrationLayers=[
    new HeatmapLayer({id:'neighborhood-concentration',data:centers,visible:concentrationOptions.centers,getPosition:d=>d.position,getWeight:d=>d.weight,radiusPixels:60,intensity:1,colorDomain:[25,2500],weightsTextureSize:512,opacity:.5,
      colorRange:[[33,25,66],[64,48,108],[99,78,158],[143,115,196],[190,164,227],[231,216,252]]}),
    new HeatmapLayer({id:'poi-concentration',data:pois,visible:concentrationOptions.pois,getPosition:d=>d.position,getWeight:d=>d.weight,radiusPixels:40,intensity:.85,colorDomain:[1,150],weightsTextureSize:512,opacity:.85,
      colorRange:[[255,224,32],[255,150,16],[255,64,16],[235,24,24],[255,140,140],[255,255,255]]}),
    new ScatterplotLayer({id:'concentration-centers',data:centers,visible:concentrationOptions.centers,getPosition:d=>d.position,getRadius:2,radiusUnits:'pixels',getFillColor:[221,201,252,220],pickable:true,
      onHover:info=>pointTooltip(info,info.object?`${info.object.name}\n${format(info.object.weight)} estimated people · neighborhood center`:undefined)}),
    // Transparent hit targets preserve tooltips without painting every POI as a hot spot.
    new ScatterplotLayer({id:'concentration-pois',data:pois,visible:concentrationOptions.pois,getPosition:d=>d.position,getRadius:5,radiusUnits:'pixels',getFillColor:[0,0,0,0],pickable:true,
      onHover:info=>pointTooltip(info,info.object?`${info.object.name}\n${format(info.object.weight)} estimated people · point of interest`:undefined)})
  ];
}
function buildLayers() {
  const h=hour(),trips=run.frames[h].trips;
  const flows=trips.map(t=>({trip:t,route:run.routes[t.route],weight:tripWeight(t,run,filters)})).filter(t=>t.weight>.001);
  const vectors=run.boundaryVectors.map(v=>{const flux=zoneFlux(v.region);return {...v,flux,path:flux>0?[v.outer,v.inner]:[v.inner,v.outer]};}).filter(v=>Math.abs(v.flux)>.01);
  const heat=flows.flatMap(f=>[.125,.375,.625,.875].map(p=>({position:routePosition(f.route,p),weight:f.weight/4})));
  staticLayers=[
    new GeoJsonLayer({id:'zones',data:neighborhoodData,filled:true,stroked:true,pickable:true,
      getFillColor:f=>{const flux=zoneFlux(f.properties!.name),c=flux>=0?cyan:orange;return [...c,Math.min(45,5+Math.sqrt(Math.abs(flux))*.15)];},
      getLineColor:[90,142,153,55],getLineWidth:1,lineWidthUnits:'pixels',onHover:tooltip,
      updateTriggers:{getFillColor:[h,filters.age,filters.occupation,filters.status]},parameters:{depthWriteEnabled:false}}),
    new HeatmapLayer({id:'crowd-density',data:heat,visible:layerOptions.heat,getPosition:d=>d.position,getWeight:d=>d.weight,
      radiusPixels:38,intensity:.7,threshold:.08,weightsTextureSize:512,colorRange:[[44,40,80],[65,57,112],[109,84,150],[145,111,182],[195,164,217],[242,210,231]],opacity:.6}),
    new PathLayer({id:'flow-corridors',data:flows,getPath:d=>d.route.path,getColor:[79,177,160,45],getWidth:d=>Math.min(6,.4+Math.sqrt(d.weight)/45),widthUnits:'pixels',widthMinPixels:.5,visible:layerOptions.particles,parameters:{depthWriteEnabled:false}}),
    new PathLayer({id:'boundary-flux',data:vectors,getPath:d=>d.path,getColor:d=>[...(d.flux>0?cyan:orange),Math.min(210,65+Math.sqrt(Math.abs(d.flux)))],getWidth:d=>Math.min(5,1+Math.sqrt(Math.abs(d.flux))/100),widthUnits:'pixels',visible:layerOptions.boundaries}),
    new TextLayer({id:'flux-arrowheads',data:vectors,getPosition:d=>d.path[1],getText:()=> '▶',getSize:d=>Math.min(15,7+Math.sqrt(Math.abs(d.flux))/60),getColor:d=>d.flux>0?cyan:orange,
      getAngle:d=>Math.atan2((d.path[1][1]-d.path[0][1]),(d.path[1][0]-d.path[0][0])*Math.cos(-30*Math.PI/180))*180/Math.PI,
      characterSet:['▶'],getTextAnchor:'middle',getAlignmentBaseline:'center',billboard:false,visible:layerOptions.boundaries}),
    new TextLayer({id:'neighborhood-labels',data:Object.entries(run.zonePoints),getPosition:d=>d[1],getText:d=>d[0].toUpperCase(),getSize:9,getColor:[146,175,182,155],fontFamily:'Arial',fontWeight:500,characterSet:'auto',getPixelOffset:[0,-11],pickable:false}),
    new ScatterplotLayer({id:'venues',data:run.venues,getPosition:d=>d.position,getRadius:115,radiusMinPixels:8,radiusMaxPixels:15,getFillColor:[244,157,110,70],stroked:true,getLineColor:orange,getLineWidth:2,lineWidthUnits:'pixels',pickable:true,onClick:info=>{if(info.index>=0){selectedVenue=info.index;el<HTMLSelectElement>('venue-select').value=String(selectedVenue);updateVenue();}}}),
    new TextLayer({id:'venue-labels',data:run.venues,getPosition:d=>d.position,getText:d=>d.name,getPixelOffset:[0,23],getSize:12,getColor:[251,194,157],fontFamily:'Arial',characterSet:'auto'}),
    new ScatterplotLayer({id:'sir',visible:layerOptions.sir,data:run.extensions.nodes_sir.filter(r=>Number(r.Frame)%24===h),getPosition:r=>[Number(r.InnerLong),Number(r.InnerLat)],getRadius:r=>Math.sqrt(Number(r.Infected))*3,radiusMinPixels:0,radiusMaxPixels:35,getFillColor:[245,85,118,145],pickable:false})
  ];
  frameBuffers=stressBuffers??prepared[h];
  particleLayer=new StreetParticleLayer({id:'street-particles',data:{length:frameBuffers.length,attributes:{getRoute:{value:frameBuffers.route,size:4},getDemographic:{value:frameBuffers.demographic,size:3},...(colorByOrigin?{getFillColor:{value:frameBuffers.colors,size:4}}:{})}},
    atlas,clock:alpha(),filters,getPosition:[0,0,0],getRadius:1.65,radiusUnits:'pixels',getFillColor:[255,222,141,245],stroked:false,billboard:true,pickable:!stressBuffers,visible:layerOptions.particles,parameters:{depthWriteEnabled:false},
    onHover:info=>{const ri=offsetToRoute.get(frameBuffers.route[info.index*4]);const r=ri===undefined?undefined:run.routes[ri];pointTooltip(info,r?`Origin: ${r.origin.split('//')[0]}\nDestination: ${r.destination.split('//')[0]}\nEstimated stream sample`:undefined);}});
  updateConcentrations();
  currentHour=h;
}

function updateVenue() {
  const venue=run.venues[selectedVenue];
  if(!venue){text('venue-population','No venue data');el('venue-chart').replaceChildren();return;}
  const demographic=fraction(run.meta.demographics.age,filters.age)*fraction(run.meta.demographics.occupation,filters.occupation);
  const values=venue.hours.map((n,i)=>demographic*(((filters.status&1)?venue.locals[i]:0)+((filters.status&2)?n-venue.locals[i]:0)));
  const h=hour(),n=values[h]*(1-alpha())+values[Math.min(h+1,23)]*alpha();
  text('venue-population',format(n));
  const capacity=Number(el<HTMLInputElement>('capacity').value),cap=capacity>0?capacity:0,max=Math.max(...values,cap,1);
  const xy=values.map((n,i)=>[i/23*280,80-n/max*72]);
  const path=xy.map((p,i)=>`${i?'L':'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' ');
  const svg=el<HTMLElement>('venue-chart');
  // All interpolation values below are numeric; labels use textContent elsewhere.
  svg.innerHTML=`<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#efad81" stop-opacity=".3"/><stop offset="1" stop-color="#efad81" stop-opacity="0"/></linearGradient></defs><path d="${path} L280,85 L0,85Z" fill="url(#fill)"/><path d="${path}" fill="none" stroke="#f7b48a" stroke-width="1.5"/>${cap?`<path d="M0,${80-cap/max*72}H280" stroke="#82999f" stroke-dasharray="3,4"/>`:''}<path d="M${clock/23*280},0V85" stroke="#73e6c6" stroke-opacity=".6"/><circle cx="${clock/23*280}" cy="${80-n/max*72}" r="3" fill="#73e6c6"/>`;
  text('saturation',cap?`${(n/cap*100).toFixed(1)}% of scenario capacity`:`${(n/Math.max(1,...values)*100).toFixed(1)}% of filtered run peak · capacity unknown`);
  const gain=venue.hours.findIndex((v,i)=>i>0&&v>venue.hours[i-1]);
  const release=venue.hours.findIndex((v,i)=>i>Math.max(0,gain)&&v<venue.hours[i-1]);
  text('venue-event',`Recorded accumulation ${gain>=0?String(gain).padStart(2,'0')+':00':'unavailable'} · release ${release>=0?String(release).padStart(2,'0')+':00':'unavailable'}`);
}

function updateUi() {
  const h=hour(),next=Math.min(h+1,23),a=alpha();
  let total=0;
  for(const [name,p] of Object.entries(run.frames[h].zones))total+=(1-a)*populationWeight(p,run,filters)+a*populationWeight(run.frames[next].zones[name],run,filters);
  text('clock',`${String(h).padStart(2,'0')}:${String(Math.min(59,Math.floor(a*60))).padStart(2,'0')}`);
  el<HTMLInputElement>('timeline').value=String(clock);
  text('population',format(total));text('transfers',format(run.frames[h].trips.reduce((n,t)=>n+tripWeight(t,run,filters),0)));
  text('entities',format(visibleCount(frameBuffers,filters)));text('interval-label',h===23?'23:00 · terminal observed state':`${String(h).padStart(2,'0')} → ${String(next).padStart(2,'0')} · incoming deltas`);
  text('map-period',h===23?'End of recorded day':h<6?'The city at rest':h<10?'Morning movement':h<16?'Daytime circulation':h<19?'Evening gathering':h<22?'A city assembled':'The journey home');
  el<HTMLButtonElement>('play').textContent=playing?'Ⅱ':'▶';el('play').setAttribute('aria-label',playing?'Pause simulation':'Play simulation');
  if(!playing)text('fps','Paused');
  updateVenue();
}
function refresh() {buildLayers();updateUi();draw();}
function draw() {if(!particleLayer)return;overlay.setProps({layers:[...staticLayers,...concentrationLayers,particleLayer.clone({clock:alpha(),filters})]});}
function tick(now:number) {
  benchmark.animationFrame(now);
  const dt=previous?Math.min(.1,(now-previous)/1000):0;previous=now;
  if(playing) {
    if(benchmark.running)clock=18+((clock-18+dt*.05)%.95);
    else {clock=Math.min(23,clock+dt*speed);if(clock===23)playing=false;}
    if(hour()!==currentHour)buildLayers();
    if(now-lastConcentration>500&&(concentrationOptions.centers||concentrationOptions.pois)){updateConcentrations();lastConcentration=now;}
    draw();
  }
  if(now-lastUi>150){updateUi();lastUi=now;}
  requestAnimationFrame(tick);
}
function seek(value:number) {
  if(benchmark.running)return;
  clock=Math.max(0,Math.min(23,value));refresh();
}
function bind() {
  el('play').onclick=()=>{if(benchmark.running)return;if(clock>=23)seek(0);playing=!playing;updateUi();};
  el('timeline').oninput=()=>seek(Number(el<HTMLInputElement>('timeline').value));
  el('speed').onchange=()=>{speed=Number(el<HTMLSelectElement>('speed').value);};
  for(const id of ['ages','occupations','residency'])el(id).onchange=()=>{filters={age:mask('ages'),occupation:mask('occupations'),status:mask('residency')};refresh();};
  el('reset-filters').onclick=()=>{resetFilters();refresh();};
  for(const name of ['particles','boundaries','heat','sir'] as const)el('layer-'+name).onchange=()=>{layerOptions[name]=el<HTMLInputElement>('layer-'+name).checked;refresh();};
  for(const name of ['centers','pois'] as const)el('layer-'+name).onchange=()=>{concentrationOptions[name]=el<HTMLInputElement>('layer-'+name).checked;refresh();};
  el('particle-color').onchange=()=>{colorByOrigin=el<HTMLSelectElement>('particle-color').value==='origin';el<HTMLDetailsElement>('origin-legend').open=colorByOrigin;refresh();};
  el('jump-event').onclick=()=>{const v=run.venues[selectedVenue];const h=v?.hours.findIndex((n,i)=>i>0&&n>v.hours[i-1])??19;seek(Math.max(0,h-1));};
  el('zoom-in').onclick=()=>map.zoomIn();el('zoom-out').onclick=()=>map.zoomOut();
  el('home-view').onclick=()=>map.flyTo({center:[-51.205,-30.025],zoom:11.6,bearing:-12,pitch:30});
  el('venue-select').onchange=()=>{selectedVenue=Number(el<HTMLSelectElement>('venue-select').value);updateVenue();map.flyTo({center:run.venues[selectedVenue].position,zoom:12.5});};
  el('capacity').oninput=updateVenue;
  el('audit-button').onclick=()=>el<HTMLDialogElement>('audit').showModal();el('close-audit').onclick=()=>el<HTMLDialogElement>('audit').close();
  el('benchmark').onclick=()=>void runBenchmark();
  el('close-benchmark').onclick=()=>el<HTMLDialogElement>('benchmark-dialog').close();
  el('download-benchmark').onclick=()=>{if(benchmarkResult)downloadResult(benchmarkResult);};
  document.addEventListener('visibilitychange',()=>{if(document.hidden){playing=false;benchmark.cancel('Benchmark invalidated: browser tab was hidden.');}previous=0;});
}

async function runBenchmark() {
  if(benchmark.running)return;
  const controls=[...document.querySelectorAll<HTMLInputElement|HTMLButtonElement|HTMLSelectElement>('input,button,select')];
  const disabled=controls.map(c=>c.disabled),saved={clock,playing,filters:{...filters},options:{...layerOptions},concentrations:{...concentrationOptions},colorByOrigin,center:map.getCenter(),zoom:map.getZoom(),pitch:map.getPitch(),bearing:map.getBearing()};
  try {
    playing=false;controls.forEach(c=>c.disabled=true);
    text('benchmark-status','Checking idle browser animation cadence for 3 seconds…');
    const idleRafP50Ms=await measureIdleCadence();
    resetFilters();clock=18;playing=true;layerOptions.particles=true;layerOptions.boundaries=true;layerOptions.heat=true;layerOptions.sir=false;
    concentrationOptions.centers=true;concentrationOptions.pois=true;colorByOrigin=true;
    if(!run.frames[18].trips.length)throw Error('This bundle has no transfers at hour 18; benchmark requires an active interval.');
    stressBuffers=prepareParticles(run,atlas,18,50000,true);
    let minX=180,minY=90,maxX=-180,maxY=-90;
    for(const t of run.frames[18].trips)for(const [x,y] of run.routes[t.route].path){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
    map.fitBounds([[minX,minY],[maxX,maxY]],{padding:35,duration:0,bearing:0,pitch:0});
    refresh();controls.forEach(c=>c.disabled=true);
    text('benchmark-status','Warming GPU for 3s, then measuring 20s of completed renders. Keep this tab visible.');
    const measured=await benchmark.begin();
    if(graphicsError)throw Error('Rendering error occurred; performance result is invalid.');
    const canvas=overlay.getCanvas()!,gl=canvas.getContext('webgl2');
    const rendererInfo=gl?.getExtension('WEBGL_debug_renderer_info');
    const renderer=gl?String(gl.getParameter(rendererInfo?.UNMASKED_RENDERER_WEBGL??gl.RENDERER)):'unavailable';
    let inViewport=0;
    for(let i=0;i<stressBuffers.length;i++) {
      // Locate the corresponding route through the packed offset.
      const offset=stressBuffers.route[i*4],ri=offsetToRoute.get(offset)!;
      const p=routePosition(run.routes[ri],((alpha()/stressBuffers.route[i*4+3])+stressBuffers.route[i*4+2])%1);
      const screen=map.project(p as XY);
      if(screen.x>=0&&screen.y>=0&&screen.x<=map.getContainer().clientWidth&&screen.y<=map.getContainer().clientHeight)inViewport++;
    }
    benchmarkResult={schemaVersion:1,timestamp:new Date().toISOString(),userAgent:navigator.userAgent,renderer,viewport:[canvas.width,canvas.height],devicePixelRatio:devicePixelRatio,
      entities:stressBuffers.length,visibleEntities:inViewport,...measured,...benchmark.rafCadence(),idleRafP50Ms,
      notes:['Completed Deck renders after warmup; target = mean >=58 FPS and p95 <=20ms.','50,000 weighted stream samples; all filters, origin colors, center/POI/corridor density and boundaries on.','Full route extent in viewport; GPU time is not independently measured.']};
    text('benchmark-status',`${measured.targetMet?'TARGET MET':'BELOW TARGET'} · ${measured.fps.toFixed(1)} FPS\np95 ${measured.p95Ms.toFixed(1)}ms · ${format(inViewport)} in viewport`);
    text('benchmark-summary',`${measured.fps.toFixed(1)} FPS · ${format(stressBuffers.length)} entities`);
    text('benchmark-json',JSON.stringify(benchmarkResult,null,2));
    el<HTMLDialogElement>('benchmark-dialog').showModal();
  } catch(error) {text('benchmark-status',String(error));}
  finally {
    stressBuffers=undefined;clock=saved.clock;playing=saved.playing;filters=saved.filters;Object.assign(layerOptions,saved.options);Object.assign(concentrationOptions,saved.concentrations);colorByOrigin=saved.colorByOrigin;
    for(const [id,key] of [['ages','age'],['occupations','occupation'],['residency','status']] as const)el(id).querySelectorAll<HTMLInputElement>('input').forEach(i=>i.checked=Boolean(filters[key]&(1<<Number(i.value))));
    controls.forEach((c,i)=>c.disabled=disabled[i]);
    map.jumpTo({center:saved.center,zoom:saved.zoom,bearing:saved.bearing,pitch:saved.pitch});refresh();
  }
}
const offsetToRoute=new Map<number,number>();

async function start() {
  const startTime=performance.now();
  const load=async(path:string)=>{const response=await fetch(path);if(!response.ok)throw Error(`${path}: HTTP ${response.status}. Run python -m pipeline.build first.`);return response.json();};
  const [bundle,neighborhoods,roads,binary]=await Promise.all([load('./data/run.json'),load('./data/neighborhoods.geojson'),load('./data/roads.geojson'),fetch('./data/routes.bin').then(r=>{if(!r.ok)throw Error('Missing routes.bin; rebuild the data bundle');return r.arrayBuffer();})]);
  hydrateRoutes(bundle,binary);validateRun(bundle);run=bundle;neighborhoodData=neighborhoods;
  text('loading-message',`Preparing ${format(run.routes.length)} street routes and all 24 frames on a background worker…`);
  const worker=new Worker(new URL('./prepare.worker.ts',import.meta.url),{type:'module'});
  const packed=await new Promise<{atlas:Atlas;frames:ParticleBuffers[]}>((resolve,reject)=>{worker.onmessage=e=>e.data.error?reject(Error(e.data.error)):resolve(e.data);worker.onerror=reject;worker.postMessage(run);});worker.terminate();
  atlas=packed.atlas;prepared=packed.frames;atlas.offsets.forEach((v,i)=>offsetToRoute.set(v,i));
  map=new maplibregl.Map({container:'map',center:[-51.205,-30.025],zoom:11.6,bearing:-12,pitch:30,attributionControl:false,pixelRatio:Math.min(devicePixelRatio,1.5),
    style:{version:8,sources:{neighborhoods:{type:'geojson',data:neighborhoods},roads:{type:'geojson',data:roads}},layers:[
      {id:'water',type:'background',paint:{'background-color':'#081821'}},
      {id:'land',type:'fill',source:'neighborhoods',paint:{'fill-color':'#10232b','fill-opacity':.94}},
      {id:'roads',type:'line',source:'roads',paint:{'line-color':'#54747c','line-opacity':.25,'line-width':['interpolate',['linear'],['zoom'],9,.25,13,.7,16,2]}}
    ]}});
  map.addControl(new maplibregl.AttributionControl({compact:true,customAttribution:'© OpenStreetMap contributors · Prefeitura de Porto Alegre'}));
  overlay=new MapLibreOverlay({interleaved:false,useDevicePixels:1,parameters:{depthWriteEnabled:false},
    onError:error=>{graphicsError=true;console.error(error);text('benchmark-status',`Renderer error: ${error.message}`);},
    onAfterRender:()=>{const now=performance.now();if(now-lastRender>2){renderCount++;lastRender=now;benchmark.rendered();}if(now-fpsStart>1000){text('fps',playing?`${Math.round(renderCount*1000/(now-fpsStart))} fps`:'Paused');renderCount=0;fpsStart=now;}}
  });
  map.addControl(overlay);
  await new Promise<void>((resolve,reject)=>{map.once('load',()=>resolve());map.once('error',e=>reject(e.error));});
  text('scenario-name',run.venues.length?'Stadium gathering & return':run.meta.run);
  text('run-detail',`${Object.keys(run.zonePoints).length} neighborhoods · 24-hour run · ${run.meta.mode}`);
  text('region-count',String(Object.keys(run.zonePoints).length));text('day-label',`DAY ${String(run.meta.day+1).padStart(2,'0')}`);
  text('preload-status',`24 / 24 frames in memory`);text('mode-label',`${format(run.meta.graph.edges)} OSM street edges · ${run.meta.mode}`);
  for(const [i,v] of run.venues.entries()){const option=document.createElement('option');option.value=String(i);option.textContent=v.name;el('venue-select').append(option);}
  el<HTMLInputElement>('layer-sir').disabled=run.extensions.nodes_sir.length===0;
  const audit=el('audit-content'),p=document.createElement('p');p.textContent=`Run: ${run.meta.run}. Demographic source: ${run.meta.demographics.source}. Preloaded in ${((performance.now()-startTime)/1000).toFixed(1)} seconds. Deltas describe arrivals into each frame; there is no inferred 23 → 00 transition.`;audit.append(p);
  const ul=document.createElement('ul');for(const warning of run.meta.warnings){const li=document.createElement('li');li.textContent=warning;ul.append(li);}audit.append(ul);
  const names=Object.keys(run.zonePoints).sort();
  for(const name of names){const row=document.createElement('div'),swatch=document.createElement('i'),label=document.createElement('span');const color=originColor(name,names);swatch.style.background=`rgb(${color[0]},${color[1]},${color[2]})`;label.textContent=name;row.append(swatch,label);el('origin-colors').append(row);}
  bind();refresh();el('loading').remove();requestAnimationFrame(tick);
  // Read-only test/benchmark diagnostics; the app is also fully operable through the UI.
  Object.assign(window,{lodus:{get ready(){return true;},get state(){return {clock,playing,filters,entities:visibleCount(frameBuffers,filters),hour:hour(),graphicsError};},get benchmarkResult(){return benchmarkResult;}}});
}
start().catch(error=>{console.error(error);text('loading-message',`Unable to load the observatory: ${String(error)}`);});
