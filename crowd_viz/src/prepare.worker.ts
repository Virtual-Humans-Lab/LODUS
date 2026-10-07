import {createAtlas,prepareParticles,validateRun} from './data';
import type {Run} from './types';
self.onmessage=(event:MessageEvent<Run>)=> {
  try {
    const run=event.data;validateRun(run);
    const atlas=createAtlas(run.routes);
    const frames=run.frames.map((_,i)=>prepareParticles(run,atlas,i));
    const transfer:Transferable[]=[atlas.data.buffer,atlas.offsets.buffer,atlas.lengths.buffer];
    frames.forEach(f=>transfer.push(f.route.buffer,f.demographic.buffer,f.histogram.buffer,f.colors.buffer));
    self.postMessage({atlas,frames}, {transfer});
  } catch(error) {self.postMessage({error:String(error)});}
};
