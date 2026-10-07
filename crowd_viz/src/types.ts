export type XY = [number, number];
export type Population = {Total:number; Locals:number; Outsiders:number; dTotals:number; dLocals:number; dOutsiders:number};
export type Route = {id:string; origin:string; destination:string; path:XY[]; seconds:number[]; duration:number; meters:number};
export type Trip = {origin:string; destination:string; route:number; mass:number; localFraction:number; occupation:number[]};
export type Frame = {hour:number; zones:Record<string,Population>; trips:Trip[]; report:{production:number; attraction:number; residual:number; attraction_scale:number; iterations:number; max_marginal_error:number; colocatedMass:number}};
export type Venue = {id:string;name:string;region:string;position:XY;capacity:number|null;hours:number[];locals:number[]};
export type POI = {id:string;name:string;region:string;position:XY;hours:number[];locals:number[]};
export type Run = {
  meta:{version:number;city:string;run:string;day:number;level:string;mode:string;k:number;warnings:string[];inference:string;demographics:{age:number[];occupation:number[];source:string}; graph:{nodes:number;edges:number;snapMeters:Record<string,number>}};
  frames:Frame[];routes:Route[];venues:Venue[];pois:POI[];zonePoints:Record<string,XY>;
  boundaryVectors:{region:string;outer:XY;inner:XY}[];
  extensions:{nodes_sir:Record<string,string|number>[];diss:Record<string,string|number>[];node_positions:Record<string,string|number>[]};
};
export type Filters = {age:number; occupation:number; status:number};
export type ParticleBuffers = {length:number; route:Float32Array; demographic:Float32Array; histogram:Uint32Array;colors:Uint8Array};
export type Atlas = {width:number;height:number;data:Float32Array;offsets:Uint32Array;lengths:Uint32Array};
