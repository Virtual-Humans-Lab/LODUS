import type {Run,Atlas,ParticleBuffers,Filters,Route,Trip,Population} from './types';

export function hydrateRoutes(value:unknown,buffer:ArrayBuffer):void {
  const bundle=value as {routes:(Route&{offset:number;vertices:number})[]};
  if(!bundle || !Array.isArray(bundle.routes) || buffer.byteLength%24!==0)throw Error('Malformed routing cache');
  const view=new DataView(buffer);
  for(const route of bundle.routes) {
    if(!Number.isInteger(route.offset)||!Number.isInteger(route.vertices)||route.offset<0||route.vertices<2||(route.offset+route.vertices)*24>buffer.byteLength)throw Error('Route cache offset out of bounds');
    route.path=[];route.seconds=[];
    for(let i=0;i<route.vertices;i++) {
      const offset=(route.offset+i)*24;
      route.path.push([view.getFloat64(offset,true),view.getFloat64(offset+8,true)]);
      route.seconds.push(view.getFloat64(offset+16,true));
    }
  }
}

export function validateRun(value:unknown):asserts value is Run {
  const run = value as Run;
  if (!run || run.meta?.version!==1 || run.frames?.length!==24 || !Array.isArray(run.routes)) throw Error('Expected a version 1 bundle containing 24 frames.');
  for(const [i,f] of run.frames.entries()) {
    if(f.hour!==i || !f.zones || !Array.isArray(f.trips)) throw Error(`Invalid frame ${i}`);
    for(const p of Object.values(f.zones)) {
      if(!Object.values(p).every(Number.isFinite) || p.Total<0 || Math.abs(p.Total-p.Locals-p.Outsiders)>1e-4) throw Error(`Invalid population at frame ${i}`);
    }
    for(const t of f.trips) if(!Number.isInteger(t.route) || !run.routes[t.route] || !Number.isFinite(t.mass) || t.mass<0 || t.localFraction<0 || t.localFraction>1 || t.occupation.length!==3 || t.occupation.some(x=>!Number.isFinite(x)||x<0)) throw Error(`Invalid trip at frame ${i}`);
  }
  for(const r of run.routes) {
    if(r.path.length<2 || r.path.length!==r.seconds.length || !(r.duration>0) || !Number.isFinite(r.duration)) throw Error('Invalid street route');
    r.path.forEach((xy,i)=> {
      if(xy.length!==2 || !xy.every(Number.isFinite) || Math.abs(xy[0])>180 || Math.abs(xy[1])>90 || !Number.isFinite(r.seconds[i]) || (i>0 && r.seconds[i]<=r.seconds[i-1])) throw Error('Invalid route geometry/timing');
    });
  }
  for(const a of [run.meta.demographics.age,run.meta.demographics.occupation]) if(!Array.isArray(a)||a.some(x=>!Number.isFinite(x)||x<0)||a.reduce((x,y)=>x+y,0)<=0) throw Error('Invalid demographic prior');
}

export function createAtlas(routes:Route[]):Atlas {
  const width=2048, count=routes.reduce((n,r)=>n+r.path.length,0),height=Math.max(1,Math.ceil(count/width));
  const data=new Float32Array(width*height*4),offsets=new Uint32Array(routes.length),lengths=new Uint32Array(routes.length);
  let cursor=0;
  routes.forEach((r,index)=> {
    offsets[index]=cursor; lengths[index]=r.path.length;
    r.path.forEach((p,i)=> {data.set([p[0],p[1],r.seconds[i]/r.duration,0],cursor++*4);});
  });
  return {width,height,data,offsets,lengths};
}

export function random(seed:number):()=>number {
  let state=seed>>>0;
  return ()=> {state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296;};
}
export function originColor(name:string,names:string[]):[number,number,number,number] {
  // Golden-angle palette gives every neighborhood a stable, distinct hue.
  const index=Math.max(0,names.indexOf(name.split('//')[0]));
  const hue=((index*137.507764+18)%360)/60,s=.72,l=.66;
  const c=(1-Math.abs(2*l-1))*s,x=c*(1-Math.abs(hue%2-1)),m=l-c/2;
  const rgb=hue<1?[c,x,0]:hue<2?[x,c,0]:hue<3?[0,c,x]:hue<4?[0,x,c]:hue<5?[x,0,c]:[c,0,x];
  return [...rgb.map(v=>Math.round((v+m)*255)),245] as [number,number,number,number];
}
function category(weights:number[],value:number):number {
  const total=weights.reduce((a,b)=>a+b,0);
  let threshold=value*total;
  for(let i=0;i<weights.length;i++){threshold-=weights[i];if(threshold<0)return i;}
  return weights.length-1;
}

/** Stratified weighted samples. A point is a representative stream, not a recovered agent. */
export function prepareParticles(run:Run, atlas:Atlas, hour:number, limit=50000, stress=false):ParticleBuffers {
  const trips=run.frames[hour].trips, total=trips.reduce((n,t)=>n+t.mass,0);
  const length=total>0 ? (stress?limit:Math.min(limit,Math.ceil(total))) : 0;
  const route=new Float32Array(length*4), demographic=new Float32Array(length*3),histogram=new Uint32Array(24),colors=new Uint8Array(length*4);
  const names=Object.keys(run.zonePoints??{}).sort();
  const palette=new Map(trips.map(t=>[t.origin,originColor(t.origin,names)]));
  const rng=random(20260925+hour);
  let index=0,cumulative=trips[0]?.mass??0;
  for(let i=0;i<length;i++) {
    const threshold=(i+rng())/length*total;
    while(index<trips.length-1 && cumulative<threshold)cumulative+=trips[++index].mass;
    const trip=trips[index],r=run.routes[trip.route];
    route.set([atlas.offsets[trip.route],atlas.lengths[trip.route],rng(),r.duration/3600],i*4);
    const a=category(run.meta.demographics.age,rng()),o=category(trip.occupation,rng()),s=rng()<trip.localFraction?0:1;
    demographic.set([a,o,s],i*3); histogram[a*6+o*2+s]++;
    colors.set(palette.get(trip.origin)!,i*4);
  }
  return {length,route,demographic,histogram,colors};
}

export function visibleCount(p:ParticleBuffers,f:Filters):number {
  let n=0;
  for(let a=0;a<4;a++)for(let o=0;o<3;o++)for(let s=0;s<2;s++) if((f.age&(1<<a))&&(f.occupation&(1<<o))&&(f.status&(1<<s)))n+=p.histogram[a*6+o*2+s];
  return n;
}
export function fraction(weights:number[],mask:number):number {
  return weights.reduce((n,w,i)=>n+((mask&(1<<i))?w:0),0)/weights.reduce((a,b)=>a+b,0);
}
export function tripWeight(trip:Trip,run:Run,f:Filters):number {
  return trip.mass*fraction(run.meta.demographics.age,f.age)*fraction(trip.occupation,f.occupation)*(((f.status&1)?trip.localFraction:0)+((f.status&2)?1-trip.localFraction:0));
}
export function populationWeight(p:Population,run:Run,f:Filters):number {
  return (((f.status&1)?p.Locals:0)+((f.status&2)?p.Outsiders:0))*fraction(run.meta.demographics.age,f.age)*fraction(run.meta.demographics.occupation,f.occupation);
}
export function routePosition(r:Route,progress:number):number[] {
  const t=Math.max(0,Math.min(1,progress))*r.duration;
  let lo=0,hi=r.seconds.length-1;
  while(hi-lo>1){const m=(hi+lo)>>1;if(r.seconds[m]<=t)lo=m;else hi=m;}
  const alpha=(t-r.seconds[lo])/(r.seconds[hi]-r.seconds[lo]);
  return r.path[lo].map((x,i)=>x+(r.path[hi][i]-x)*alpha);
}
