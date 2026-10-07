import test from 'node:test';
import assert from 'node:assert/strict';
import {routePosition,createAtlas,prepareParticles,visibleCount,populationWeight,tripWeight,hydrateRoutes} from '../src/data.ts';
import type {Route,Run} from '../src/types.ts';
const route:Route={id:'a-b',origin:'a',destination:'b',path:[[0,0],[1,0],[1,1]],seconds:[0,10,30],duration:30,meters:200};
const trip={origin:'a',destination:'b',route:0,mass:100000,localFraction:.25,occupation:[2,1,1]};
const run={routes:[route],frames:[{trips:[trip]}],meta:{demographics:{age:[1,1,1,1],occupation:[2,1,1]}}} as unknown as Run;
test('interpolation follows the street bend and edge travel time',()=>{
  assert.deepEqual(routePosition(route,1/3),[1,0]);
  assert.deepEqual(routePosition(route,2/3),[1,.5]);
  assert.deepEqual(routePosition(route,1),[1,1]);
});
test('50k deterministic stream samples preserve filter categories',()=>{
  const atlas=createAtlas([route]);const p=prepareParticles(run,atlas,0);
  assert.equal(p.length,50000);assert.equal(visibleCount(p,{age:15,occupation:7,status:3}),50000);
  assert.equal(visibleCount(p,{age:0,occupation:7,status:3}),0);
  const local=visibleCount(p,{age:15,occupation:7,status:1});assert.ok(local>12000&&local<13000);
  assert.deepEqual(p.demographic,prepareParticles(run,atlas,0).demographic);
});
test('filter weights use local stocks and OD-specific occupation composition',()=>{
  const p={Total:100,Locals:20,Outsiders:80,dTotals:0,dLocals:0,dOutsiders:0};
  assert.equal(populationWeight(p,run,{age:15,occupation:7,status:2}),80);
  assert.equal(tripWeight(trip,run,{age:1,occupation:1,status:1}),3125);
});
test('routing binary checks bounds and little-endian coordinates',()=>{
  const bundle={routes:[{offset:0,vertices:2}]};
  const buffer=new ArrayBuffer(48),v=new DataView(buffer);
  [-51,-30,0,-51.1,-30.1,10].forEach((n,i)=>v.setFloat64(i*8,n,true));
  hydrateRoutes(bundle,buffer);assert.deepEqual((bundle.routes[0] as unknown as Route).path,[[-51,-30],[-51.1,-30.1]]);
  assert.throws(()=>hydrateRoutes({routes:[{offset:1,vertices:2}]},buffer));
});
