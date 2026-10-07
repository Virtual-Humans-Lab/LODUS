export type BenchmarkResult={
  schemaVersion:1;timestamp:string;userAgent:string;renderer:string;viewport:number[];devicePixelRatio:number;
  entities:number;visibleEntities:number;durationSeconds:number;renderedFrames:number;fps:number;p50Ms:number;p95Ms:number;p99Ms:number;
  framesOver20Ms:number;targetMet:boolean;notes:string[];
  rafP50Ms:number;rafP95Ms:number;
  idleRafP50Ms:number;
};
export async function measureIdleCadence(duration=3000):Promise<number> {
  return new Promise((resolve,reject)=>{
    const samples:number[]=[];let previous=0,started=0;
    const deadline=setTimeout(()=>reject(Error('Browser animation frames did not arrive.')),duration+10000);
    const sample=(now:number)=>{
      if(document.hidden){clearTimeout(deadline);reject(Error('Benchmark tab is hidden.'));return;}
      if(!started)started=now;
      if(previous)samples.push(now-previous);previous=now;
      if(now-started>=duration){clearTimeout(deadline);samples.sort((a,b)=>a-b);resolve(samples[Math.floor(samples.length/2)]??0);}
      else requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  });
}
export class RenderBenchmark {
  private times:number[]=[];
  private start=0;
  private previous=0;
  private resolve:((value:Pick<BenchmarkResult,'durationSeconds'|'renderedFrames'|'fps'|'p50Ms'|'p95Ms'|'p99Ms'|'framesOver20Ms'|'targetMet'>)=>void)|null=null;
  private reject:((reason:Error)=>void)|null=null;
  private timer:ReturnType<typeof setTimeout>|undefined;
  running=false;
  begin(duration=20000) {
    if(this.running)throw Error('Benchmark already running');
    this.running=true;this.times=[];this.start=performance.now()+3000;this.previous=0;
    return new Promise<Pick<BenchmarkResult,'durationSeconds'|'renderedFrames'|'fps'|'p50Ms'|'p95Ms'|'p99Ms'|'framesOver20Ms'|'targetMet'>>((resolve,reject)=> {
      this.resolve=resolve;this.reject=reject;
      this.timer=setTimeout(()=>this.cancel('No rendered frames arrived before the benchmark timeout.'),duration+12000);
      this.duration=duration;
    });
  }
  private duration=20000;
  private rafTimes:number[]=[];
  private rafPrevious=0;
  animationFrame(now:number) {
    if(!this.running){this.rafPrevious=0;return;}
    if(now>=this.start && this.rafPrevious)this.rafTimes.push(now-this.rafPrevious);
    this.rafPrevious=now;
  }
  rafCadence() {
    const values=this.rafTimes.sort((a,b)=>a-b);
    this.rafTimes=[];
    return {rafP50Ms:values[Math.floor(values.length*.5)]??0,rafP95Ms:values[Math.floor(values.length*.95)]??0};
  }
  cancel(message:string) {
    if(!this.running)return;
    this.running=false;clearTimeout(this.timer);this.reject?.(new Error(message));this.resolve=null;this.reject=null;
  }
  rendered() {
    if(!this.running)return;
    if(document.hidden){this.cancel('Benchmark invalidated: browser tab was hidden.');return;}
    const now=performance.now();
    if(now<this.start)return;
    if(this.previous)this.times.push(now-this.previous);
    this.previous=now;
    if(now-this.start<this.duration)return;
    const values=this.times.filter(v=>v>0).sort((a,b)=>a-b);
    if(values.length<10){this.cancel('Insufficient rendered frames.');return;}
    const total=this.times.reduce((a,b)=>a+b,0),percentile=(p:number)=>values[Math.min(values.length-1,Math.floor(values.length*p))];
    const fps=this.times.length*1000/total,p95=percentile(.95);
    this.running=false;clearTimeout(this.timer);
    this.resolve?.({durationSeconds:total/1000,renderedFrames:values.length,fps,p50Ms:percentile(.5),p95Ms:p95,p99Ms:percentile(.99),framesOver20Ms:values.filter(v=>v>20).length,targetMet:fps>=58&&p95<=20});
    this.resolve=null;this.reject=null;
  }
}
export function downloadResult(result:BenchmarkResult) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='lodus-benchmark.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
