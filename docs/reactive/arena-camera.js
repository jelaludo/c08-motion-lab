import * as T from 'three';
/** Shared orbit angle, independently framed paired lanes. No actor poses change. */
export class ArenaCamera{
 constructor({camera,orbit,container,controlsDom,getLanes,getReviewSide=()=> 'reactive',onFocus=()=>{}}){
  this.camera=camera;this.orbit=orbit;this.container=container||controlsDom;this.getLanes=getLanes;this.getReviewSide=getReviewSide;this.mode='actor';this.focus='pair';this.zoom=1;this.initialDistance=camera.position.distanceTo(orbit.target);this.bounds=new WeakMap();this.lastFrames=new Map();
  this.container.innerHTML='<label>Camera <select id="camera-mode"><option value="actor">Follow actor</option><option value="cat">Follow K0-Tech</option><option value="overview">Whole arena</option></select></label><label>View <select id="camera-focus"><option value="pair">Paired views</option><option value="baseline">Baseline only</option><option value="reactive">Reactive only</option></select></label><button id="camera-zoom-out" title="Zoom out" aria-label="Zoom out">−</button><label class="camera-zoom">Zoom <input id="camera-zoom" type="range" min=".5" max="2.5" step=".05" value="1"><output id="camera-zoom-value">1.00×</output></label><button id="camera-zoom-in" title="Zoom in" aria-label="Zoom in">+</button><button id="camera-reset">Reset camera</button><span class="camera-note">Follow centers each subject separately. Whole arena compares routes and progress.</span>';
  const $=id=>this.container.querySelector('#'+id);this.$=$;
  $('camera-mode').onchange=()=>{this.mode=$('camera-mode').value;this.lastFrames.clear()};$('camera-focus').onchange=()=>{this.focus=$('camera-focus').value;onFocus(this.focus)};
  const setZoom=value=>{this.zoom=T.MathUtils.clamp(value,.5,2.5);$('camera-zoom').value=this.zoom;$('camera-zoom-value').textContent=this.zoom.toFixed(2)+'×'};
  $('camera-zoom').oninput=()=>setZoom(Number($('camera-zoom').value));$('camera-zoom-in').onclick=()=>setZoom(this.zoom+.2);$('camera-zoom-out').onclick=()=>setZoom(this.zoom-.2);
  this.startPosition=camera.position.clone();this.startTarget=orbit.target.clone();$('camera-reset').onclick=()=>{camera.position.copy(this.startPosition);orbit.target.copy(this.startTarget);orbit.update();this.mode='actor';this.focus='pair';$('camera-mode').value=this.mode;$('camera-focus').value=this.focus;setZoom(1);this.lastFrames.clear()};
  orbit.minDistance=this.initialDistance*.25;orbit.maxDistance=this.initialDistance*4;
  // Keep controls beside the stage so neither large single-body views nor phones
  // lose the head/shoulders underneath a toolbar.
  const stage=this.container.closest('#stage'),aside=stage?.parentElement?.querySelector('aside');
  if(stage&&aside){const bodySelect=aside.querySelector('#body');if(bodySelect)bodySelect.after(this.container);else aside.prepend(this.container)}

 }
 configure(){this.bounds=new WeakMap();this.lastFrames.clear()}
 update(){}
 visibleLanes({mobile=false}={}){const lanes=this.getLanes();if(this.focus!=='pair')return lanes.filter(l=>l.condition===this.focus);if(mobile)return lanes.filter(l=>l.condition===this.getReviewSide());return lanes;}
 nativePoint(lane,p){const display=lane.ep.display,xyz=[p[0],p[1],p[2]||0];return new T.Vector3(...display.display_basis.map((r,i)=>(r.reduce((s,v,j)=>s+v*xyz[j],0)-display.display_origin[i])*lane.scale)).applyMatrix4(lane.group.matrixWorld)}
 arenaBounds(lane){let box=this.bounds.get(lane);if(box)return box.clone();box=new T.Box3();lane.group.updateMatrixWorld(true);const env=lane.ep.environment,points=[...(lane.ep.raw_root_path||[]),...(env.cat_path||[])];if(env.goal)points.push(env.goal);for(const ob of env.obstacles||[]){for(const x of [-1,1])for(const y of [-1,1])for(const z of [0,ob.height])points.push([ob.center[0]+x*ob.radius,ob.center[1]+y*ob.radius,z])}for(const z of env.speed_zones||[])for(const x of [z.x_min,z.x_max])for(const y of [z.y_min??-2,z.y_max??2])points.push([x,y,0]);const b=env.arena_bounds||(env.bounds?{x_min:env.bounds[0],x_max:env.bounds[1],y_min:env.bounds[2],y_max:env.bounds[3]}:null);if(b&&Number.isFinite(b.x_min))for(const x of [b.x_min,b.x_max])for(const y of [b.y_min,b.y_max])points.push([x,y,0]);for(const p of points)box.expandByPoint(this.nativePoint(lane,p));if(box.isEmpty())box.setFromCenterAndSize(lane.group.position.clone(),new T.Vector3(10,3,10));box.min.y=Math.min(box.min.y,0);box.max.y=Math.max(box.max.y,lane.brek?.height||2.3);box.expandByScalar(.7);this.bounds.set(lane,box.clone());return box;}
 frame(c,lane){const direction=this.camera.position.clone().sub(this.orbit.target).normalize(),aspect=c.aspect,half=Math.min(T.MathUtils.degToRad(c.fov)/2,Math.atan(Math.tan(T.MathUtils.degToRad(c.fov)/2)*aspect));let target,radius;
  if(this.mode==='overview'){const box=this.arenaBounds(lane);target=box.getCenter(new T.Vector3());radius=box.getSize(new T.Vector3()).length()/2;}
  else if(this.mode==='cat'&&lane.catRoot){target=lane.catRoot.getWorldPosition(new T.Vector3());const scale=lane.scale/lane.ep.display.display_scale;target.y+=.21*scale;radius=.55*scale;}
  else{const pelvis=lane.model?.getObjectByName('PELVIS');target=pelvis?pelvis.getWorldPosition(new T.Vector3()):lane.group.getWorldPosition(new T.Vector3());const height=lane.brek?.height||2.3;target.y=lane.group.position.y+height*.52;radius=height*.58;}
  const wheelScale=this.camera.position.distanceTo(this.orbit.target)/this.initialDistance,distance=Math.max(.6,radius/Math.sin(half)*1.12*wheelScale/this.zoom);c.position.copy(target).addScaledVector(direction,distance);c.near=.02;c.far=Math.max(200,distance*4+radius*2);c.lookAt(target);c.updateProjectionMatrix();c.updateMatrixWorld(true);this.lastFrames.set(lane.condition,{mode:this.mode,target:target.toArray(),position:c.position.toArray(),distance,radius,aspect});return c;
 }
 updateLane(lane,c){return this.frame(c,lane)}
}
export const createArenaCamera=options=>new ArenaCamera(options);
