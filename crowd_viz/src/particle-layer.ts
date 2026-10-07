import {ScatterplotLayer} from '@deck.gl/layers';
import type {UpdateParameters} from '@deck.gl/core';
import type {Texture} from '@luma.gl/core';
import type {Atlas,Filters} from './types';

const mobility={
  name:'mobility',
  vs:`layout(std140) uniform mobilityUniforms {
    float clock;
    int width;
    int ageMask;
    int occupationMask;
    int statusMask;
  } mobility;
  uniform sampler2D routeTexture;
  vec4 waypoint(int index) {return texelFetch(routeTexture,ivec2(index % mobility.width,index / mobility.width),0);}`,
  uniformTypes:{clock:'f32',width:'i32',ageMask:'i32',occupationMask:'i32',statusMask:'i32'}
} as const;
type Props={atlas:Atlas;clock:number;filters:Filters;getRoute:unknown;getDemographic:unknown};

/** O(log route vertices) GPU interpolation; only a clock uniform changes per tick. */
export class StreetParticleLayer extends ScatterplotLayer<unknown,Props> {
  static layerName='StreetParticleLayer';
  static defaultProps={...ScatterplotLayer.defaultProps, getRoute:{type:'accessor',value:[0,2,0,1]},getDemographic:{type:'accessor',value:[0,0,0]},clock:0};
  declare state: ScatterplotLayer['state'] & {routeTexture?:Texture};
  getShaders() {
    const shaders=super.getShaders();
    // Local variable replaces the ordinary static scatterplot position.
    const vs=shaders.vs!.replaceAll('project_position_to_clipspace(instancePositions, instancePositions64Low','project_position_to_clipspace(movingPosition, vec3(0.0)')
      .replace('geometry.worldPosition = instancePositions','geometry.worldPosition = movingPosition');
    return {...shaders,vs,modules:[...shaders.modules!,mobility],inject:{
      ...shaders.inject,
      'vs:#decl':`in vec4 instanceRoute; in vec3 instanceDemographic;`,
      'vs:#main-start':`
        int offset=int(instanceRoute.x); int count=int(instanceRoute.y);
        float progress=fract(mobility.clock / max(instanceRoute.w,0.00001)+instanceRoute.z);
        int lo=0; int hi=count-1;
        for(int step=0;step<24;step++) {
          if(hi-lo<=1)break;
          int mid=(lo+hi)/2;
          if(waypoint(offset+mid).z<=progress)lo=mid;else hi=mid;
        }
        vec4 a=waypoint(offset+lo); vec4 b=waypoint(offset+hi);
        vec3 movingPosition=vec3(mix(a.xy,b.xy,clamp((progress-a.z)/max(b.z-a.z,0.00000001),0.0,1.0)),0.0);
        bool sampleEnabled=(mobility.ageMask & (1<<int(instanceDemographic.x)))!=0
          && (mobility.occupationMask & (1<<int(instanceDemographic.y)))!=0
          && (mobility.statusMask & (1<<int(instanceDemographic.z)))!=0;
      `,
      'vs:#main-end':`if(!sampleEnabled)gl_Position=vec4(2.0,2.0,2.0,1.0);`
    }};
  }
  initializeState() {
    super.initializeState();
    this.getAttributeManager()!.addInstanced({instanceRoute:{size:4,accessor:'getRoute'},instanceDemographic:{size:3,accessor:'getDemographic'}});
  }
  updateState(params:UpdateParameters<this>) {
    super.updateState(params);
    if(!this.state.routeTexture || params.props.atlas!==params.oldProps.atlas) {
      this.state.routeTexture?.destroy();
      const a=this.props.atlas;
      if(a.width>this.context.device.limits.maxTextureDimension2D || a.height>this.context.device.limits.maxTextureDimension2D)throw Error('Routing atlas exceeds this GPU texture limit');
      this.setState({routeTexture:this.context.device.createTexture({id:'street-route-atlas',width:a.width,height:a.height,format:'rgba32float',data:a.data,sampler:{minFilter:'nearest',magFilter:'nearest'}})});
    }
  }
  draw(params:Parameters<ScatterplotLayer['draw']>[0]) {
    const f=this.props.filters;
    this.state.model?.shaderInputs.setProps({mobility:{clock:this.props.clock,width:this.props.atlas.width,ageMask:f.age,occupationMask:f.occupation,statusMask:f.status},bindings:{routeTexture:this.state.routeTexture!}});
    super.draw(params);
  }
  finalizeState(context:Parameters<ScatterplotLayer['finalizeState']>[0]) {
    this.state.routeTexture?.destroy();super.finalizeState(context);
  }
}
