import {loadPublishedClip} from '../shared/motion-asset-io.js';
import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

export function captureBindPose(asset){
 const skeletons=new Set();asset.traverse(o=>{if(o.isSkinnedMesh)skeletons.add(o.skeleton)});for(const s of skeletons)s.pose();asset.updateMatrixWorld(true);
 const pose=[];asset.traverse(b=>{if(b.isBone)pose.push({b,p:b.position.clone(),q:b.quaternion.clone().normalize()})});return pose;
}
const poseOf=v=>v.neutral.map(({b})=>({b,p:b.position.clone(),q:b.quaternion.clone().normalize()}));
const smooth=t=>{t=Math.max(0,Math.min(1,t));return t*t*(3-2*t)};
function apply(v,a,b,t){for(let i=0;i<a.length;i++){a[i].b.position.lerpVectors(a[i].p,b[i].p,t);a[i].b.quaternion.copy(a[i].q).slerp(b[i].q,t).normalize()}v.asset.updateMatrixWorld(true);v.previous.copy(v.follow.getWorldPosition(new T.Vector3()))}
function neutral(v,from){return v.neutral.map((n,i)=>{const p=n.p.clone();if(n.b.name==='MOTION')p.copy(from[i].p);return {b:n.b,p,q:n.q.clone()}})}
function discard(asset){asset.traverse(o=>{o.geometry?.dispose();for(const m of o.material?(Array.isArray(o.material)?o.material:[o.material]):[]){for(const x of Object.values(m))if(x?.isTexture)x.dispose();m.dispose()}})}
const wp=b=>b.getWorldPosition(new T.Vector3()),wq=b=>b.getWorldQuaternion(new T.Quaternion());
function feet(v){return ['L','R'].map(side=>{const hip=v.asset.getObjectByName('HIP_'+side),knee=v.asset.getObjectByName('KNEE_'+side),ankle=v.asset.getObjectByName('ANKLE_'+side);return {hip,knee,ankle,p:wp(ankle),q:wq(ankle)}})}
function setWorldRotation(b,q){b.quaternion.copy(wq(b.parent).invert().multiply(q)).normalize();b.updateWorldMatrix(false,true)}
function aim(b,child,target){const p=wp(b),from=wp(child).sub(p).normalize(),to=target.clone().sub(p).normalize();setWorldRotation(b,new T.Quaternion().setFromUnitVectors(from,to).multiply(wq(b)))}
function legIK(foot,goal,rotation){
 const {hip,knee,ankle}=foot,h=wp(hip),k=wp(knee),a=wp(ankle),l1=h.distanceTo(k),l2=k.distanceTo(a),ray=goal.clone().sub(h),distance=ray.length(),d=Math.max(Math.abs(l1-l2)+1e-6,Math.min(l1+l2-1e-6,distance));ray.normalize();
 let pole=k.clone().sub(h);pole.addScaledVector(ray,-pole.dot(ray));if(pole.lengthSq()<1e-10){pole=Math.abs(ray.y)<.9?new T.Vector3(0,1,0):new T.Vector3(0,0,1);pole.addScaledVector(ray,-pole.dot(ray))}pole.normalize();
 const x=(l1*l1-l2*l2+d*d)/(2*d),y=Math.sqrt(Math.max(0,l1*l1-x*x)),middle=h.clone().addScaledVector(ray,x).addScaledVector(pole,y),end=h.clone().addScaledVector(ray,d);
 aim(hip,knee,middle);aim(knee,ankle,end);setWorldRotation(ankle,rotation);
 return {reach:Math.abs(distance-d),length:Math.max(Math.abs(wp(hip).distanceTo(wp(knee))-l1),Math.abs(wp(knee).distanceTo(wp(ankle))-l2))};
}

export function createGallery({catalog,views,current,select,commit,setTime,setPlaying,resetCamera,assetURL}){
 const $=id=>document.getElementById(id),loader=new GLTFLoader(),cache=new Map();
 const definitions=catalog.categories||[{id:'all',label:'All'}];
 const query=new URLSearchParams(location.search),requested=query.get('test');
 let category=query.get('category')||(requested?catalog.category_by_test?.[requested]:'fight')||'all';
 if(!definitions.some(c=>c.id===category))category='all';
 const tabs=document.createElement('nav');tabs.className='motion-tabs';tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label','Motion categories');
 $('stages').setAttribute('role','tabpanel');tabs.id='motion-categories';document.querySelector('.viewer-workspace').prepend(tabs);
 const random=document.createElement('button');random.type='button';random.id='continuous-random';random.textContent='Random';random.title='Continuous random: current category, with a neutral stance between moves';random.setAttribute('aria-label','Continuous random');random.setAttribute('aria-pressed','false');document.querySelector('.header-tools').prepend(random);
 const about=document.createElement('p');about.textContent='Continuous random uses moves from the selected tab. Every move eases to a shared relaxed rig stance, holds, then eases into the next move. Standing entries/returns add sequential foot lifts and bounded two-link leg IK. These are authored preview blends with short playback ramps, not learned or physically solved stand-up transitions. Ground transitions need visual review. GLB downloads remain the original individual takes; the random preview transitions are not baked into them.';$('about-content').append(about);
 const visible=()=>catalog.tests.filter(t=>category==='all'||catalog.category_by_test?.[t.id]===category);
 const updateTabs=()=>{for(const b of tabs.children){const active=b.dataset.category===category;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1}const selectBox=$('test-select');selectBox.replaceChildren();for(const test of visible())selectBox.add(new Option(test.title||test.id,test.id));if(current())selectBox.value=current().id;const u=new URL(location.href);u.searchParams.set('category',category);history.replaceState({},'',u)};
 const trace=[];
 const record=phase=>{trace.push({phase,take:current()?.id});if(trace.length>300)trace.shift()};
 const state={active:false,paused:false,phase:'off',elapsed:0,from:[],to:[],cameras:[],anchors:[],feetFrom:[],feetTo:[],maxReachProjection:0,maxLegLengthError:0,pending:null,pendingId:null,token:0,bag:[]};
 const getGround=()=>catalog.category_by_test?.[current()?.id]==='ground';
 function stop(){state.active=false;state.paused=false;state.token++;state.phase='off';state.bag=[];random.textContent='Random';random.setAttribute('aria-pressed','false');setPlaying(false)}
 function choose(){let items=visible().filter(t=>t.id!==current()?.id);if(!items.length)items=visible();if(!state.bag.length)state.bag=items.map(t=>t.id).sort(()=>Math.random()-.5);const family=id=>id?.replace(/-seed\d+$/,''),index=state.bag.findLastIndex(id=>family(id)!==family(current()?.id));return index>=0?state.bag.splice(index,1)[0]:state.bag.pop()}
 async function clips(id){
  if(current()?.id===id&&views.length===catalog.bodies.length)return views.map(v=>({body:v.card.dataset.body,clip:v.clip}));
  if(!cache.has(id))cache.set(id,Promise.all(catalog.tests.find(t=>t.id===id).outputs.map(async output=>{const clip=await loadPublishedClip(output,assetURL);return {body:output.body,clip}})));
  while(cache.size>6)cache.delete(cache.keys().next().value);
  return cache.get(id);
 }
 function queue(id){state.pendingId=id;state.pending=clips(id);state.pending.catch(()=>{})}
 function camera(v,pose){
  const from=poseOf(v),startP=v.camera.position.clone(),startT=v.controls.target.clone();apply(v,pose,pose,1);
  const root=v.follow.getWorldPosition(new T.Vector3());v.framingBounds.union(new T.Box3().setFromObject(v.asset,true).translate(new T.Vector3(-root.x,0,-root.z)));
  resetCamera(v);const targetP=v.camera.position.clone(),targetT=v.controls.target.clone();v.camera.position.copy(startP);v.controls.target.copy(startT);apply(v,from,from,1);
  return {v,startP,startT,targetP,targetT};
 }
 function blendCamera(t){for(const c of state.cameras){c.v.camera.position.lerpVectors(c.startP,c.targetP,t);c.v.controls.target.lerpVectors(c.startT,c.targetT,t)}}
 function prepareFeet(){state.feetFrom=[];state.feetTo=[];for(let i=0;i<views.length;i++){const v=views[i],saved=poseOf(v);apply(v,state.from[i],state.from[i],1);state.feetFrom.push(feet(v));apply(v,state.to[i],state.to[i],1);state.feetTo.push(feet(v));apply(v,saved,saved,1)}}
 function stepFeet(fraction){if(getGround()||fraction<=0||fraction>=1)return;for(let i=0;i<views.length;i++)for(let j=0;j<2;j++){
  const first=state.feetFrom[i][j],last=state.feetTo[i][j],u=Math.max(0,Math.min(1,(fraction-(j===0?.04:.54))/.42)),a=smooth(u),goal=first.p.clone().lerp(last.p,a),leg=wp(first.hip).distanceTo(wp(first.knee))+wp(first.knee).distanceTo(wp(first.ankle));goal.y+=.09*leg*Math.sin(Math.PI*u)**2;
  const solved=legIK(first,goal,first.q.clone().slerp(last.q,a));state.maxReachProjection=Math.max(state.maxReachProjection,solved.reach);state.maxLegLengthError=Math.max(state.maxLegLengthError,solved.length);
 }}
 function returnToNeutral(){state.phase='return';state.elapsed=0;state.anchors=views.map(v=>v.follow.getWorldPosition(new T.Vector3()));state.from=views.map(poseOf);state.to=views.map((v,i)=>neutral(v,state.from[i]));prepareFeet();state.cameras=views.map((v,i)=>camera(v,state.to[i]));record('return')}
 function pause(){state.paused=!state.paused;$('play').textContent=state.paused?'Play':'Pause'}
 function start(){if(views.length!==catalog.bodies.length)return;setPlaying(false);state.active=true;state.paused=false;state.maxReachProjection=0;state.maxLegLengthError=0;state.token++;state.bag=[];queue(current().id);returnToNeutral();random.textContent='Stop random';random.setAttribute('aria-pressed','true');$('play').textContent='Pause'}
 async function enter(force=false){
  state.phase='loading';record('loading');const token=state.token,id=state.pendingId;
  try{
   const loaded=await state.pending;while(state.active&&token===state.token&&state.paused&&!force)await new Promise(resolve=>setTimeout(resolve,100));if(!state.active||token!==state.token)return;
   const anchors=new Map(views.map(v=>[v.card.dataset.body,v.follow.getWorldPosition(new T.Vector3())]));
   const starts=[],targets=[];
   for(const v of views){
    const body=v.card.dataset.body;v.mixer.stopAllAction();v.mixer.uncacheClip(v.clip);v.clip=loaded.find(c=>c.body===body).clip;v.action=v.mixer.clipAction(v.clip);v.action.setLoop(T.LoopOnce,1);v.action.clampWhenFinished=true;v.action.play();v.action.paused=true;v.action.time=0;v.mixer.update(0);v.asset.updateMatrixWorld(true);
    const delta=anchors.get(body).sub(v.follow.getWorldPosition(new T.Vector3()));v.asset.position.x+=delta.x;v.asset.position.z+=delta.z;v.asset.updateMatrixWorld(true);
    v.framingBounds=new T.Box3();for(let sample=0;sample<=16;sample++){v.action.time=v.clip.duration*sample/16;v.mixer.update(0);v.asset.updateMatrixWorld(true);const p=v.follow.getWorldPosition(new T.Vector3());v.framingBounds.union(new T.Box3().setFromObject(v.asset,true).translate(new T.Vector3(-p.x,0,-p.z)))}
    v.action.time=0;v.mixer.update(0);v.asset.updateMatrixWorld(true);const target=poseOf(v),start=neutral(v,target);targets.push(target);starts.push(start);apply(v,start,start,1);const neutralRoot=v.follow.getWorldPosition(new T.Vector3());v.framingBounds.union(new T.Box3().setFromObject(v.asset,true).translate(new T.Vector3(-neutralRoot.x,0,-neutralRoot.z)));
   }
   commit(catalog.tests.find(t=>t.id===id));state.from=starts;state.to=targets;prepareFeet();state.cameras=views.map((v,i)=>camera(v,state.to[i]));state.phase='entry';state.elapsed=0;record('entry');queue(choose());
  }catch(error){stop();$('status').textContent='Continuous playback stopped: '+error.message}
 }
 function update(dt,force=false){
  if(!state.active||(state.paused&&!force))return;state.elapsed+=dt;
  if(state.phase==='return'||state.phase==='entry'){
   const length=getGround()?(state.phase==='return'?3.2:2.4):1.4,fraction=Math.min(1,state.elapsed/length),alpha=smooth(fraction);views.forEach((v,i)=>apply(v,state.from[i],state.to[i],alpha));stepFeet(fraction);blendCamera(alpha);
   if(state.elapsed>=length){state.elapsed=0;if(state.phase==='return'){state.phase='neutral';record('neutral')}else{state.phase='action';record('action')}}
  }else if(state.phase==='neutral'&&state.elapsed>=.6){enter(force)}
  else if(state.phase==='action'){
   const duration=Math.max(...views.map(v=>v.clip.duration)),ramp=Math.min(.3,duration/4),t=state.elapsed;
   let source;if(t<ramp)source=.5*(t-ramp/Math.PI*Math.sin(Math.PI*t/ramp));else if(t<duration)source=t-.5*ramp;else{const u=Math.min(ramp,t-duration);source=duration-.5*ramp+.5*(u+ramp/Math.PI*Math.sin(Math.PI*u/ramp))}
   setTime(Math.min(duration,source));if(t>=duration+ramp)returnToNeutral();
  }
  $('status').textContent=`Continuous ${state.paused?'paused / ':''}${state.phase} · ${current()?.title||''} · authored neutral transitions`;
 }
 function setCategory(id,chooseFirst=true){stop();category=definitions.some(c=>c.id===id)?id:'all';updateTabs();if(chooseFirst&&!visible().some(t=>t.id===current()?.id)&&visible().length)select(visible()[0].id)}
 for(const definition of definitions){const button=document.createElement('button');button.type='button';button.textContent=definition.label;button.dataset.category=definition.id;button.setAttribute('role','tab');button.setAttribute('aria-controls','stages');button.onclick=()=>setCategory(definition.id);tabs.append(button)}
 tabs.addEventListener('keydown',e=>{const buttons=[...tabs.children],index=buttons.indexOf(document.activeElement);let next;if(e.key==='ArrowRight')next=(index+1)%buttons.length;else if(e.key==='ArrowLeft')next=(index-1+buttons.length)%buttons.length;else if(e.key==='Home')next=0;else if(e.key==='End')next=buttons.length-1;else return;e.preventDefault();e.stopPropagation();buttons[next].click();buttons[next].focus()});
 random.onclick=()=>state.active?stop():start();updateTabs();
 return {start,stop,pause,update,setCategory,visible,get category(){return category},get active(){return state.active},get phase(){return state.phase},get paused(){return state.paused},get history(){return trace},get diagnostics(){return {max_reach_projection_m:state.maxReachProjection,max_leg_length_error_m:state.maxLegLengthError}},onSelect(id){stop();if(category!=='all'&&catalog.category_by_test?.[id]!==category){category=catalog.category_by_test?.[id]||'all';updateTabs()}},neutralError(){let angle=0,position=0,drift=0;for(const [i,v] of views.entries()){for(const n of v.neutral){angle=Math.max(angle,n.b.quaternion.angleTo(n.q));if(n.b.name!=='MOTION')position=Math.max(position,n.b.position.distanceTo(n.p))}if(state.anchors[i]){const p=v.follow.getWorldPosition(new T.Vector3());drift=Math.max(drift,Math.hypot(p.x-state.anchors[i].x,p.z-state.anchors[i].z))}}return {angle_rad:angle,position_m:position,root_horizontal_drift_m:drift}}};
}
