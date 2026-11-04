import {readMotionJSON,loadMotionModel} from '../shared/motion-asset-io.js';
import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {ReviewStore,SCORE_FIELDS} from '../shared/review-store.js';
import {groundFeet,carryHands,mantleHands,point} from './kinematics.js?v=momentum-trip-1';
import {createWorld} from './world.js?v=momentum-trip-1';
import {traversalTarget,traversalPosition} from './traversal.js?v=momentum-trip-1';
import {CONTACT_RULES,calibrateRig,heroLandingPose,ledgeGrabPose} from './contact-actions.js?v=momentum-trip-1';
import {createVariationPicker} from './variation.js?v=momentum-trip-1';
import {BREAKFALL_RULES,breakfallPlan,breakfallPosition} from './breakfalls.js?v=momentum-trip-1';
import {SIDE_TRIP_RULES,captureTripContact,plantedSideTrip,beamRollContact} from './side-trip.js?v=momentum-trip-1';
const variationPicker=createVariationPicker();
const actionProfiles=await fetch('action-profiles.json?v=responsive-2').then(r=>{if(!r.ok)throw Error('Action windows unavailable');return r.json()}).then(d=>d.profiles);
import {exportClips,createRecorder,download} from './export.js';
const $=id=>document.getElementById(id),canvas=$('game');
const renderer=new T.WebGLRenderer({canvas,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.toneMapping=T.ACESFilmicToneMapping;renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;
const scene=new T.Scene();scene.background=new T.Color('#a7bfc0');scene.fog=new T.Fog('#a7bfc0',65,170);
scene.add(new T.HemisphereLight(0xe7f3ff,0x596e51,2.5));const sun=new T.DirectionalLight(0xffecd4,3);sun.position.set(-16,30,-10);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-20,right:20,top:20,bottom:-20,near:1,far:80});sun.shadow.bias=-.0004;scene.add(sun,sun.target);
const camera=new T.PerspectiveCamera(55,1,.03,220),world=createWorld(scene),loader=new GLTFLoader(),actors=[],cache=new Map(),keys=new Set(),recorder=createRecorder(),store=new ReviewStore();
const state={position:new T.Vector3(0,0,0),velocity:new T.Vector3(),yaw:0,pitch:.24,distance:5.8,facing:0,gait:'jog',stance:'stand',carrying:false,action:null,mode:'play',preview:null,paused:false,time:0,seed:411,preferred:{},tour:null,collisions:0,lastMotion:null,maxIKReach:0,maxLengthError:0,events:[],manualStep:false};
state.flight=null;state.fallSpeed=0;state.fallPeak=null;state.contactDiagnostics={};state.crouchTap=-Infinity;state.attackIndex=0;
state.tripCooldownUntil=0;state.tripBlockedObstacle=null;state.variety=true;state.entry=null;try{state.variety=localStorage.getItem('kimodo-game-variety-v1')!=='false'}catch{}
let profile='lab',sprintMode='hold';state.sprintLatch=false;state.shoulder=1;
try{sprintMode=localStorage.getItem('kimodo-game-sprint-mode-v1')==='toggle'?'toggle':'hold'}catch{}
const focused=()=>profile==='hybrid'&&keys.has('MouseRight');
const ctrlMove=()=>keys.has('ControlLeft')||keys.has('ControlRight');
const strafing=()=>$('strafe').checked||focused()||ctrlMove();
function recordLabel(){return 'Record · '+(profile==='hybrid'?'Shift+R':'R')}
function applyProfile(value){
 if(recorder.active)stopRecording();profile=value==='hybrid'?'hybrid':'lab';keys.clear();drag=false;state.sprintLatch=false;$('profile').value=profile;$('strafe').checked=profile==='lab';
 $('lab-controls').hidden=profile!=='lab';$('hybrid-controls').hidden=profile!=='hybrid';$('record').textContent=recordLabel();$('sprint-mode').value=sprintMode;
 $('hint').textContent=profile==='hybrid'?'Hybrid · WASD · Ctrl+S back / A,D strafe · Shift sprint · Space jump · Alt evade · E context · RMB focus':'Lab · WASD move · right mouse look · Shift sprint · C crouch · Space jump · E box · Q dodge';
 try{localStorage.setItem('kimodo-game-controls-profile-v1',profile)}catch{}
 const u=new URL(location.href);u.searchParams.set('controls',profile);history.replaceState({},'',u);if(catalog)log('controls-profile',{profile});
}
try{state.preferred=JSON.parse(localStorage.getItem('kimodo-game-preferred-v1')||'{}')}catch{}
let catalog,elapsed=0,drag=false,last=performance.now(),reviewCandidate=null,loadJobs=0;
const vec=(x=0,y=0,z=0)=>new T.Vector3(x,y,z),smooth=x=>x*x*(3-2*x),wrap=a=>Math.atan2(Math.sin(a),Math.cos(a));
const active=()=>actors.find(a=>a.id===$('body').value)||actors[0];
const modal=()=>!!document.querySelector('dialog[open]');
const takeFor=(motion,body,seed=null)=>{const pool=catalog.takes.filter(t=>t.motion===motion&&t.outputs.some(o=>o.body===body)),wanted=seed??state.preferred[body+':'+motion]??catalog.motions.find(m=>m.id===motion)?.default_seed??411;return pool.find(t=>t.seed===wanted)||(seed===null?pool[0]:null)};
function eligibleTakes(id){const visible=actors.filter(a=>a===active()||$('companion').checked);return catalog.takes.filter(t=>t.motion===id&&t.automatic_eligible!==false&&actors.every(a=>t.outputs.some(o=>o.body===a.id))&&!visible.some(a=>{const r=store.latest('kimodo-game-kit-v1',t.id,a.id);return r?.decision==='reject'&&r.version==='kimodo-game-kit:v1:'+t.source_sha256.slice(0,12)}))}
function beginEntry(id,force=false,seed=null){
 if(!force&&state.entry?.id===id&&state.entry.explicitSeed===seed)return state.entry;
 const seeds={},pool=eligibleTakes(id);let draw=null;
 if(seed!==null){for(const a of actors){const t=takeFor(id,a.id,seed);if(!t)return null;seeds[a.id]=t.seed}}
 else if(state.variety){draw=variationPicker.pick(id+':'+active().id,pool);if(!draw){$('hint').textContent='No eligible takes for '+id+'. Preview or review the rejected takes in Motions.';return null}for(const a of actors)seeds[a.id]=draw.take.seed}
 else for(const a of actors){const preferred=takeFor(id,a.id),t=pool.find(t=>t.id===preferred?.id)||pool[0];if(!t)return null;seeds[a.id]=t.seed}
 const entry={id,seeds,explicitSeed:seed,takes:Object.fromEntries(actors.map(a=>[a.id,takeFor(id,a.id,seeds[a.id]).id]))};state.entry=entry;log('variant-choice',{motion:id,seeds,takes:entry.takes,policy:seed!==null?'explicit':state.variety?'shuffle-bag-no-repeat':'preferred',draw:draw?.draw,pool:draw?.pool});return entry;
}
const outputFor=(take,body)=>take.outputs.find(o=>o.body===body);
const candidate=()=>active()?.take;
function log(type,value={}){const e={type,...value};state.events.push({time:state.time,...e});if(state.events.length>1500)state.events.shift();recorder.event(e,state.time)}
async function dataFor(take,body){const out=outputFor(take,body),key=take.id+':'+body;if(!cache.has(key)){cache.set(key,readMotionJSON(out.clip).then(data=>{for(const t of data.tracks){const C=t.type==='quaternion'?T.QuaternionKeyframeTrack:T.VectorKeyframeTrack;t.interpolant=new C(t.name,t.times,t.values).createInterpolant()}return data}));}return cache.get(key)}
function capture(a){return a.bind.map(n=>({p:n.b.position.clone(),q:n.b.quaternion.clone()}))}
async function motion(id,force=false,seed=null,selection=null){
 if(!catalog)return;const entry=selection||beginEntry(id,force,seed);if(!entry)return false;await Promise.all(actors.map(async a=>{
  const take=takeFor(id,a.id,entry.seeds[a.id]);if(!take)return;if(!force&&(a.take?.id===take.id||a.pending===take.id))return;
  const token=++a.token;a.pending=take.id;a.heldTime=a.sampleTime??a.phase;loadJobs++;
  try{const data=await dataFor(take,a.id);if(token!==a.token)return;a.from=capture(a);a.blend=0;a.phase=0;a.heldTime=null;a.data=data;a.take=take;a.pending=null;for(const f of a.feet)f.lock=null;if(a===active()){state.lastMotion=id;log('motion',{id:take.id,body:a.id,source_sha256:take.source_sha256})}}
  catch(e){a.pending=null;$('hint').textContent=e.message;console.error(e)}finally{loadJobs--}
 }));updateLinks();
}
function apply(a,time,dt){
 const data=a.data;if(!data)return;for(const n of a.bind){n.b.position.copy(n.p);n.b.quaternion.copy(n.q)}
 const t=data.loop?((time%data.duration)+data.duration)%data.duration:T.MathUtils.clamp(time,0,data.duration);
 a.sampleTime=t;
 for(const track of data.tracks){const [name,property]=track.name.split('.'),b=a.bones[name];if(!b)continue;const value=track.interpolant.evaluate(t);if(property==='quaternion')b.quaternion.fromArray(value).normalize();else b.position.fromArray(value)}
 // Traversal travel already supplies height. Bound the source pelvis lift so
 // it cannot add a second obstacle-height arc to the controller trajectory.
 if(state.mode==='play'&&['game-mantle','game-vault'].includes(a.take?.motion)&&a.bones.PELVIS){const n=a.bind.find(n=>n.b===a.bones.PELVIS),x=state.action,w=x&&['ledge','mantle','vault'].includes(x.type)?1-smooth(T.MathUtils.clamp((x.elapsed/x.duration-.85)/.15,0,1)):0;n.b.position.y=n.p.y+T.MathUtils.clamp((n.b.position.y-n.p.y)*.15,-.12/a.scale,.08/a.scale)*w}
 a.blend=Math.min(1,a.blend+dt/(state.action?.blend??(state.stance==='crouch'||state.stance==='seiza'?.1:.14)));const w=smooth(a.blend);
 if(a.from&&w<1)for(let i=0;i<a.bind.length;i++){const n=a.bind[i];n.b.position.lerpVectors(a.from[i].p,n.b.position,w);n.b.quaternion.copy(a.from[i].q.clone().slerp(n.b.quaternion,w))}
 a.asset.updateMatrixWorld(true);const index=Math.min(data.contacts.length-1,Math.floor(t*30)),contacts=data.contacts[index];
 const grounded=state.position.y<=world.floor(state.position.x,state.position.z,state.position.y)+.06;
 const support=state.mode==='play'&&grounded&&state.stance!=='prone'&&state.stance!=='down'&&state.stance!=='seiza'&&a.take?.group!=='ground'&&!state.flight&&(!state.action||state.action.type==='jump');
 const ik=groundFeet(a,contacts,support,dt,world.floor(state.position.x,state.position.z,state.position.y));state.maxIKReach=Math.max(state.maxIKReach,ik.reach);state.maxLengthError=Math.max(state.maxLengthError,ik.length);
 if(state.mode==='play'&&['planted-side-roll','planted-side-over'].includes(state.flight?.path)){const report=plantedSideTrip(a,state.flight);if(report){const beam=beamRollContact(a,state.flight);state.contactDiagnostics[a.id]={...report,beam};state.maxLengthError=Math.max(state.maxLengthError,report.length||0,beam?.length||0)}}
 if(state.mode==='play'&&state.flight?.type==='ledge'){const report=ledgeGrabPose(a,{...state.flight,controllerPosition:state.position});state.contactDiagnostics[a.id]={kind:'ledge',...report};state.maxLengthError=Math.max(state.maxLengthError,report.length)}
 if(state.mode==='play'&&state.action?.type==='hero-land'){const report=heroLandingPose(a,state.action.elapsed);state.contactDiagnostics[a.id]={kind:'hero-land',...report};state.maxLengthError=Math.max(state.maxLengthError,report.length||0)}
 if(state.mode==='play'&&state.flight?.type==='mantle'){const hands=mantleHands(a,state.flight,state.position);state.maxLengthError=Math.max(state.maxLengthError,hands.length)}
}
function direction(input){const forward=vec(Math.sin(state.yaw),0,Math.cos(state.yaw)),right=vec(-Math.cos(state.yaw),0,Math.sin(state.yaw));return forward.multiplyScalar(input.z||0).addScaledVector(right,input.x||0).normalize()}
const directionName=(x,z)=>z>.4?(x<-.4?'forward-left':x>.4?'forward-right':'forward'):z<-.4?(x<-.4?'backward-left':x>.4?'backward-right':'backward'):x<0?'left':'right';
function controlInput(){return {x:(keys.has('KeyD')?1:0)-(keys.has('KeyA')?1:0),z:(keys.has('KeyW')?1:0)-(keys.has('KeyS')?1:0),modifierWalk:ctrlMove(),sprint:!ctrlMove()&&(sprintMode==='toggle'?state.sprintLatch:keys.has('ShiftLeft')||keys.has('ShiftRight'))}}
function height(){return state.stance==='crouch'?Math.max(.98,(active()?.bones.HEAD?point(active().bones.HEAD).y-state.position.y+.16:1.25)):state.stance==='prone'||state.stance==='down'?.4:1.85}
function movementClip(input,speed){
 const moving=speed>.08,d=directionName(input.x,input.z);
 if(state.stance==='seiza')return 'game-crouch-down';if(state.stance==='sit')return 'game-sit';if(state.stance==='down')return 'game-death';
 if(state.stance==='prone')return moving?'game-crawl-'+(Math.abs(input.x)>Math.abs(input.z)?input.x<0?'left':'right':input.z<0?'backward':'forward'):'game-prone-idle';
 if(state.stance==='crouch')return 'game-crouch-'+(moving?d:'forward');
 if(state.carrying)return moving?(speed>1.5?'game-carry-jog':'game-carry-'+(Math.abs(input.x)>Math.abs(input.z)?input.x<0?'left':'right':input.z<0?'backward':'forward')):'game-carry-idle';
 if(!moving)return 'game-idle';const g=speed>4.8?'sprint':speed>3?'run':speed>1.7?'jog':'walk';return g==='sprint'?'game-sprint-forward':'game-'+g+'-'+d;
}
function invalidateMotion(){for(const a of actors){a.token++;a.pending=null}}
function placeBox(){world.crate.position.copy(state.position).addScaledVector(direction({z:1}),.8);world.crate.position.y=world.floor(world.crate.position.x,world.crate.position.z,state.position.y)+.23;world.crate.rotation.set(0,state.facing,0)}
function cancelAction(reason='input'){const a=state.action;if(!a)return;for(const actor of actors)actor.heldTime=mappedTime(actor);state.action=null;invalidateMotion();log('action-cancel',{id:a.id,reason});}
function endAction(){const a=state.action;if(!a)return;for(const actor of actors)actor.heldTime=mappedTime(actor);if(a.stance)state.stance=a.stance;if(a.carry!==undefined&&!a.attached){state.carrying=a.carry;if(!a.carry)placeBox()}state.action=null;log('action-end',{id:a.id});}
function actionWindow(actor,id){const take=actor.take?.motion===id?actor.take:takeFor(id,actor.id,state.entry?.id===id?state.entry.seeds[actor.id]:null);return actor.take?.id===take?.id&&actor.data?.action_window||actionProfiles[take?.id+':'+actor.id]}
async function action(id,{type='action',stance=null,carry,duration,blend=.065,seed=null}={}){
 if(state.mode==='preview')exitPreview();if(!takeFor(id,active().id))return false;
 if(state.flight?.type==='ukemi'&&type!=='ukemi'&&!releaseBreakfall())return false;
 if(state.flight?.type==='ledge'&&type!=='ledge'){state.flight=null;state.fallSpeed=0;log('ledge-release',{reason:id})}
 cancelAction('superseded');const entry=beginEntry(id,true,seed);if(!entry)return false;const take=takeFor(id,active().id,entry.seeds[active().id]);
 const profile=(actionProfiles[take.id+':'+active().id]),ref={id,type,elapsed:0,stance,carry,attached:false,ready:false,duration:duration??profile?.duration??take.duration_s??6,blend,facing:state.facing};
 ref.takes=entry.takes;ref.seeds=entry.seeds;state.action=ref;log('action-start',{id,takes:entry.takes,seeds:entry.seeds});await motion(id,true,null,entry);if(state.action!==ref)return false;if(duration===undefined&&!profile)ref.duration=active().data.action_window?.duration??active().data.duration;ref.ready=true;return true;
}
function contextualJump(input=controlInput()){const heading=Math.hypot(input.x||0,input.z||0)>.1?direction(input):vec(Math.sin(state.facing),0,Math.cos(state.facing));return traversalTarget(world,state.position,heading)}
async function jump(high=false,input=controlInput()){
 if(state.mode==='preview')exitPreview();
 if(state.flight?.type==='ukemi'&&!releaseBreakfall())return false;
 if(state.flight||state.position.y>world.floor(state.position.x,state.position.z,state.position.y)+.08){
  const f=state.flight;if(f?.type==='jump'&&state.action?.type!=='jump'){const pending=action(f.animation,{type:'jump',duration:f.pre+f.air+f.recovery});Object.assign(state.action,{elapsed:f.elapsed,pre:f.pre,air:f.air,height:f.height});return pending}return false;
 }
 cancelAction('jump priority');
 if(state.carrying){$('hint').textContent='Put down the box before jumping.';return false}
 if(!world.fits(state.position,1.85)){$('hint').textContent='Jump blocked: not enough headroom.';return false}
 state.stance='stand';state.crouchTap=-Infinity;
 const target=high?null:contextualJump(input);
 if(target){const reach=Math.min(...actors.map(a=>a.rig.shoulderHeight+Math.sqrt(Math.max(.02,a.rig.arm*a.rig.arm-.34*.34))*.86));state.flight={...target,start:state.position.clone(),elapsed:0,hangY:Math.max(state.position.y+.20,target.top-reach+.04)};state.facing=Math.atan2(target.destination.x-state.position.x,target.destination.z-state.position.z);state.velocity.set(0,0,0);log('traversal-start',{kind:target.type,obstacle:target.obstacle,destination:target.destination.toArray()});return action(target.id,{type:target.type,duration:target.duration})}
 const speed=Math.hypot(state.velocity.x,state.velocity.z),d=directionName(input.x,input.z);
 const suffix=high?'high':speed<.2?'standing':d==='backward'||d==='left'||d==='right'?d:speed<1.7?'walk':speed<3?'jog':speed<4.8?'run':'sprint';
 const h=high?1.25:suffix==='standing'?.65:speed>4.8?1.05:speed>3?.9:.72,air=2*Math.sqrt(2*h/9.81),pre=.065;
 const flight={type:'jump',animation:'game-jump-'+suffix,elapsed:0,pre,air,recovery:.16,height:h,launchY:state.position.y,velocity:state.velocity.clone(),landed:false};state.flight=flight;
 const pending=action('game-jump-'+suffix,{type:'jump',duration:pre+air+.16});Object.assign(state.action,{pre,air,height:h});return pending;
}
function mappedTime(a){
 const d=a.data,x=state.action;if(!x||a.take?.motion!==x.id||x.takes&&a.take.id!==x.takes[a.id])return a.heldTime??a.phase;
 if(x.type==='hero-land')return d.duration;
 if(x.type==='jump'){
  const f=state.flight?.type==='jump'?state.flight:x,p=d.jump||{takeoff_s:.3,landing_s:Math.max(.5,d.duration-.5)},t=x.elapsed;
  if(t<f.pre)return t/Math.max(.01,f.pre)*p.takeoff_s;if(t<f.pre+f.air)return p.takeoff_s+(t-f.pre)/f.air*(p.landing_s-p.takeoff_s);return p.landing_s+Math.min(1,(t-f.pre-f.air)/.16)*(d.duration-p.landing_s);
 }
 const w=actionWindow(a,x.id),u=T.MathUtils.clamp(x.elapsed/x.duration,0,1);if(['planted-side-roll','planted-side-over'].includes(state.flight?.path)&&w){const onset=a.take.contact_fall_onset_s??1,plant=SIDE_TRIP_RULES.plantUntil;return x.elapsed<plant?onset*smooth(x.elapsed/plant):T.MathUtils.lerp(onset,w.end,T.MathUtils.clamp((x.elapsed-plant)/(x.duration-plant),0,1))}return w?T.MathUtils.lerp(w.start,w.end,u):Math.min(x.elapsed,d.duration);
}
function movementIntent(){if(state.mode==='preview')exitPreview();if(state.action&&['game-dodge-','game-jab','game-cross','game-kick','game-block','game-land-hard'].some(id=>state.action.id.startsWith(id)))cancelAction('movement');if(state.stance==='seiza'||state.stance==='sit')state.stance='crouch'}
function attack(){if(state.stance==='seiza')state.stance='crouch';return action(state.attackIndex++%2?'game-cross':'game-jab')}
function landed(floor,impact){
 const drop=Math.max(0,(state.fallPeak??floor)-floor);state.fallPeak=null;
 if(drop>=CONTACT_RULES.heroDrop&&impact>=CONTACT_RULES.heroImpactSpeed&&!state.carrying&&!['prone','down','sit'].includes(state.stance)){state.flight=null;state.stance='stand';state.velocity.set(0,0,0);log('hero-landing',{drop_m:drop,impact_m_s:impact});void action('game-land-hard',{type:'hero-land',duration:CONTACT_RULES.landingDuration,blend:.07});return true}return false;
}
function releaseBreakfall(){const f=state.flight;if(f?.type!=='ukemi')return true;if(f.elapsed/f.duration<BREAKFALL_RULES.recoveryFraction)return false;state.flight=null;state.position.y=world.floor(state.position.x,state.position.z,state.position.y);state.fallSpeed=0;cancelAction('ukemi recovery interrupted');return true}
function tripOnContact(input,hits,incoming){
 const blocked=state.tripBlockedObstacle;if(blocked&&!state.flight){const dx=Math.max(0,Math.abs(state.position.x-blocked.x)-blocked.w/2),dz=Math.max(0,Math.abs(state.position.z-blocked.z)-blocked.d/2);if(Math.hypot(dx,dz)>.7)state.tripBlockedObstacle=null}
 if(state.flight||state.action||state.stance!=='stand'||state.carrying||state.time<state.tripCooldownUntil||Math.hypot(input.x||0,input.z||0)<.1)return false;
 const plan=breakfallPlan(world,state.position,incoming,state.facing,hits);if(!plan)return false;
 const pool=eligibleTakes(plan.id);if(!pool.length)return false;
 const b=plan.obstacleRef;if(state.tripBlockedObstacle===b)return false;
 state.tripBlockedObstacle=b;state.tripCooldownUntil=state.time+plan.duration+BREAKFALL_RULES.cooldownAfter;state.flight=plan;state.velocity.set(0,0,0);state.fallPeak=null;
 if(['planted-side-roll','planted-side-over'].includes(plan.path)){plan.contacts=Object.fromEntries(actors.map(a=>[a.id,captureTripContact(a,plan,world.floor(state.position.x,state.position.z,state.position.y),active().group.position)]));log('trip-foot-plant',{obstacle:plan.obstacle,contacts:Object.fromEntries(Object.entries(plan.contacts).map(([body,c])=>[body,{side:c.side,anchor:c.anchor.toArray(),initialKneeFlexion:c.initialKneeFlexion}]))})}
 const preferred=takeFor(plan.id,active().id),seed=state.variety?null:(pool.find(t=>t.id===preferred?.id)||pool[0]).seed;
 log(plan.kind.startsWith('side-')?'side-object-ukemi':'low-object-trip',{obstacle:plan.obstacle,direction:plan.kind,redirected:!!plan.redirected,incoming_speed_m_s:incoming.length(),destination:plan.destination.toArray()});void action(plan.id,{type:'ukemi',duration:plan.duration,blend:.10,seed});return true;
}
function physics(dt,target){
 const f=state.flight,oldY=state.position.y;
 if(f||oldY>world.floor(state.position.x,state.position.z,oldY)+.015)state.fallPeak=Math.max(state.fallPeak??oldY,oldY);
 if(f){
  f.elapsed+=dt;
  if(f.type==='jump'){
   const t=f.elapsed;
   if(t>=f.pre&&t<=f.pre+f.air){const u=(t-f.pre)/f.air;state.position.y=f.launchY+4*f.height*u*(1-u);target.copy(f.velocity)}
   else if(t>f.pre+f.air){const floor=world.floor(state.position.x,state.position.z,oldY);if(oldY>floor+.08){state.flight=null;cancelAction('jump continues as fall');state.fallSpeed=-Math.sqrt(2*9.81*f.height);return}state.position.y=floor;if(!f.landed&&landed(floor,Math.abs(state.fallSpeed))){target.set(0,0,0);return}f.landed=true;target.multiplyScalar(.7)}else target.copy(f.velocity).multiplyScalar(.8);
   const floor=world.floor(state.position.x,state.position.z,oldY);
   if(t>f.pre+f.air/2&&state.position.y<floor){state.position.y=floor;if(!f.landed&&landed(floor,Math.abs(state.fallSpeed))){target.set(0,0,0);return}f.elapsed=f.pre+f.air;f.landed=true;if(state.action?.type==='jump')state.action.elapsed=f.elapsed}
   if(!world.fits(state.position,1.85)){state.position.y=oldY;state.flight=null;state.fallSpeed=0;cancelAction('jump clearance collision');return}
  }else{
   const desired=f.type==='ukemi'?breakfallPosition(f):traversalPosition(f),vertical=state.position.clone().setY(desired.y);
   const contactBeam=f.path==='planted-side-over'?f.obstacleRef:null;if(!world.fits(vertical,1.85,.27,contactBeam)){state.flight=null;cancelAction('blocked traversal clearance');log('traversal-blocked',{obstacle:f.obstacle});target.set(0,0,0);return}
   state.position.y=desired.y;
   const delta=desired.clone().sub(state.position).setY(0),moved=world.move(state.position,delta,1.85,.27,contactBeam);
   if(moved.distanceTo(desired)>.04){state.flight=null;cancelAction('blocked traversal route');log('traversal-blocked',{obstacle:f.obstacle});target.set(0,0,0);return}
   state.position.copy(moved);target.set(0,0,0);state.velocity.set(0,0,0);state.fallPeak=state.position.y;
  }
  state.fallSpeed=(state.position.y-oldY)/Math.max(.001,dt);
  if(f.type==='jump'&&f.elapsed>=f.pre+f.air+f.recovery||f.type!=='jump'&&f.elapsed>=f.duration){state.flight=null;state.fallSpeed=0;if(f.type!=='jump'){state.fallPeak=null}if(f.type!=='jump')log('traversal-end',{kind:f.type,obstacle:f.obstacle})}
  return;
 }
 const floor=world.floor(state.position.x,state.position.z,state.position.y);
 if(state.position.y>floor+1e-6){state.fallSpeed=Math.min(0,state.fallSpeed)-9.81*dt;state.position.y=Math.max(floor,state.position.y+state.fallSpeed*dt);if(state.position.y<=floor+1e-6){if(landed(floor,Math.abs(state.fallSpeed)))target.set(0,0,0);state.fallSpeed=0}}else{state.position.y=floor;if(state.fallPeak!==null&&state.fallSpeed<0&&landed(floor,Math.abs(state.fallSpeed)))target.set(0,0,0);state.fallSpeed=0}
}

function boxPose(actor,mesh){const pelvis=point(actor.bones.PELVIS),forward=vec(Math.sin(state.facing),0,Math.cos(state.facing));mesh.position.copy(pelvis).addScaledVector(forward,.39);mesh.position.y=actor.group.position.y+1.04;mesh.rotation.set(0,state.facing,0);mesh.updateMatrixWorld(true);const ik=carryHands(actor,mesh);state.maxIKReach=Math.max(state.maxIKReach,ik.reach);state.maxLengthError=Math.max(state.maxLengthError,ik.length)}
function updateActorPositions(){const offset=vec(Math.cos(state.facing),0,-Math.sin(state.facing)).multiplyScalar(2.8);for(const a of actors){a.group.visible=a===active()||$('companion').checked;a.group.position.copy(state.position);if(a!==active())a.group.position.add(offset);a.group.rotation.y=state.facing;a.group.updateMatrixWorld(true)}}
function advance(dt,input=controlInput()){
 if(!catalog||!actors.length||state.paused||modal())return;
 dt=Math.min(.05,Math.max(0,dt));state.time+=dt;
 if(state.tour)input=advanceTour(dt);
 if(state.mode==='preview'){
  const primary=active(),d=primary?.data,p=d?.jump,t=primary?.phase||0,u=p?(t-p.takeoff_s)/Math.max(.01,p.landing_s-p.takeoff_s):-1;
  state.position.y=u>0&&u<1?4*.8*u*(1-u):0;updateActorPositions();
  for(const a of actors){a.phase+=dt;if(a.data&&!a.data.loop&&a.phase>a.data.duration+1){a.phase=0;a.blend=0;a.from=capture(a)}apply(a,a.phase,dt)}
 }else{
  if(state.action)state.action.elapsed+=dt;
  if(state.stance==='seiza'&&Math.hypot(input.x||0,input.z||0)>.1)state.stance='crouch';
  const moving=Math.hypot(input.x||0,input.z||0)>.1,zone=world.zone(state.position);
  let speed=({walk:1.25,jog:2.4,run:3.8,sprint:6})[input.gait||state.gait];if(input.sprint)speed=6;
  if($('zones').checked&&moving&&!input.modifierWalk){if(zone==='orange')speed=Math.max(speed,3.8);if(zone==='red')speed=6}
  if(strafing()&&(input.z<.5||Math.abs(input.x)>.1))speed=Math.min(speed,3.8);
  if(input.modifierWalk)speed=1.25;
  if(state.stance==='crouch')speed=.75;if(state.stance==='prone')speed=.45;if(state.carrying)speed=Math.min(speed,1.9);if(['sit','down','seiza'].includes(state.stance))speed=0;
  if(state.carrying&&(input.z<.5||Math.abs(input.x)>.1))speed=Math.min(speed,.95);
  const target=direction(input).multiplyScalar(moving?speed:0);
  if(state.action&&state.action.type!=='jump')target.set(0,0,0);
  if(state.action?.id.startsWith('game-dodge-')&&!state.flight){const a=state.action;target.copy(a.direction||direction({z:1})).multiplyScalar(4.6*Math.sin(Math.PI*Math.min(1,a.elapsed/a.duration)))}
  physics(dt,target);

  state.velocity.lerp(target,1-Math.exp(-dt*(moving?9:12)));
  const incoming=state.velocity.clone(),delta=state.velocity.clone().multiplyScalar(dt);delta.y=0;const before=state.position.clone();state.position.copy(world.move(state.position,delta,height()));
  tripOnContact(input,world.state.moveHits,incoming);
  const actual=dt?state.position.clone().sub(before).length()/dt:0;
  // Vertical motion has its own lifetime, independent of animation cancellation.
  const facing=state.flight?.type==='ukemi'?state.flight.facing:state.flight&&state.flight.type!=='jump'?Math.atan2(state.flight.destination.x-state.flight.start.x,state.flight.destination.z-state.flight.start.z):state.action?.id.startsWith('game-dodge-')||state.action?.type==='hero-land'?state.action.facing:strafing()?state.yaw:actual>.05?Math.atan2(state.velocity.x,state.velocity.z):state.facing;
  state.facing+=wrap(facing-state.facing)*(1-Math.exp(-dt*12));updateActorPositions();
  const local=strafing()?input:{x:0,z:moving?1:0};
  const desired=state.action?.id||movementClip(local,moving?speed:0);motion(desired);
  for(const a of actors){
   const scaleSpeed=(a.data?.measured_target_speed_m_s||0)*a.scale;
   const rate=a.data?.loop&&actual>.04&&scaleSpeed>.1?T.MathUtils.clamp(actual/scaleSpeed,.45,2):1;
   a.phase+=dt*rate;const stillCrouch=state.stance==='crouch'&&!moving&&!state.action;apply(a,state.action?mappedTime(a):a.heldTime??(state.stance==='seiza'?a.data.duration:stillCrouch?.18:a.phase),dt);
  }
  if(state.action){const a=state.action;
   if(!a.attached&&a.elapsed>a.duration*.55&&a.carry!==undefined){a.attached=true;state.carrying=a.carry;if(!a.carry)placeBox()}
   if(a.elapsed>=a.duration)endAction();
  }

 }
 if(state.carrying){boxPose(active(),world.crate);world.ghostCrate.visible=$('companion').checked;if(world.ghostCrate.visible)boxPose(actors.find(a=>a!==active()),world.ghostCrate)}else world.ghostCrate.visible=false;
 recorder.sample(actors.find(a=>a.id===recorder.body)||active(),state.time);if(recorder.active&&recorder.seconds>=120)stopRecording();
 updateHUD();
 if($('interaction')){const target=profile==='hybrid'&&!state.action?contextTarget():null,jumpTarget=!state.flight&&!state.carrying&&world.fits(state.position,1.85)?contextualJump(input):null,prompts=[target?'E · '+target.label:'',jumpTarget?'Space · '+jumpTarget.label+' (contact prototype)':''].filter(Boolean);$('interaction').hidden=!prompts.length;$('interaction').textContent=prompts.join(' | ')}
}
function updateHUD(){
 const a=active();if(!a)return;const f=state.flight,x=state.action,speed=Math.hypot(state.velocity.x,state.velocity.z),zone=world.zone(state.position);
 let mode=state.stance;
 if(state.mode==='preview')mode='motion preview';else if(f?.type==='ledge')mode='ledge / '+(f.elapsed<.13?'load':f.elapsed<.5?'leap':f.elapsed<.97?'catch / hang':f.elapsed<1.93?'pull up':'top out');else if(x?.type==='hero-land')mode='hero landing / '+(x.elapsed<.14?'impact':x.elapsed<.92?'knee + fist':'recover');else if(f?.type==='jump')mode='jump / '+(f.elapsed<f.pre?'load':f.elapsed<f.pre+f.air?'air':'land');else if(f?.type==='ukemi')mode=f.kind+' ukemi / '+(f.elapsed/f.duration<.72?'breakfall':'recover');else if(f)mode=f.type;
 $('mode').textContent=`${a.label} · ${mode} · ${speed.toFixed(1)} m/s${state.carrying?' · carrying':''}${state.paused?' · paused':''}`;
 const layered=f?.type==='ukemi'?f.kind+' ukemi / obstacle reaction':f?.type==='ledge'?'Ledge grab + pull-up':x?.type==='hero-land'?'Superhero landing':null;
 $('motion-status').textContent=`${layered?layered+' · contact layer / ':''}${a.take?.label||'Loading'} · seed ${a.take?.seed||'…'}${a.pending?' · loading next':''}${a.data?.jump&&!a.data.jump.valid_airborne_detection?' · source flight unverified':''}${a.take?.group==='traversal'?' · contact probe':''}`;
 $('zone').textContent=`${zone==='orange'?'ORANGE / RUN':zone==='red'?'RED / SPRINT':'FREE PLAY'} · ${state.position.x.toFixed(1)}, ${state.position.z.toFixed(1)}${world.state.lastCollision?' · contact: '+world.state.lastCollision:''}${recorder.active?' · REC '+recorder.seconds.toFixed(1)+'s':''}`;
}
function reset(){state.tripCooldownUntil=0;state.tripBlockedObstacle=null;if(recorder.active)stopRecording();state.sprintLatch=false;state.entry=null;invalidateMotion();state.flight=null;state.fallSpeed=0;state.fallPeak=null;state.contactDiagnostics={};state.crouchTap=-Infinity;state.attackIndex=0;state.action=null;state.mode='play';state.preview=null;state.previewContext=null;state.stance='stand';state.carrying=false;state.tour=null;state.position.set(0,0,0);state.velocity.set(0,0,0);state.facing=state.yaw=0;state.pitch=.24;world.reset();keys.clear();updateActorPositions();motion('game-idle',true);$('tour').textContent='Course tour';log('reset');}
function startTrial(kind){reset();state.paused=false;$('pause').textContent='Pause';$('pause').setAttribute('aria-pressed','false');if(state.trialStrafe!==undefined){$('strafe').checked=state.trialStrafe;state.trialStrafe=undefined}if(kind==='ledge')state.position.set(20,0,4.7);else if(kind==='trip-forward')state.position.set(-30,0,10);else if(kind==='trip-backward'){state.position.set(-30,0,16);state.trialStrafe=$('strafe').checked;$('strafe').checked=true}else if(kind==='trip-side-left'||kind==='trip-side-right'){state.position.set(-30,0,10);state.yaw=kind==='trip-side-left'?-Math.PI/2:Math.PI/2;state.facing=state.yaw}else state.position.set(20,2.65,14.5);updateActorPositions();canvas.focus();log('trial',{kind})}
function exitPreview(){const context=state.previewContext;if(context){state.carrying=context.carrying;world.crate.position.copy(context.p);world.crate.quaternion.copy(context.q)}state.previewContext=null;state.flight=null;state.fallSpeed=0;state.fallPeak=null;state.mode='play';state.preview=null;state.action=null;state.stance='stand';state.position.y=0;motion(state.carrying?'game-carry-idle':'game-idle',true)}
async function preview(id,seed=Number($('seed').value)){
 const seeds=catalog.takes.filter(t=>t.motion===id).map(t=>t.seed);if(!seeds.includes(seed))seed=seeds[0];$('seed').replaceChildren(...seeds.map(s=>new Option(String(s),String(s))));$('seed').value=String(seed);
 if(state.mode!=='preview')state.previewContext={carrying:state.carrying,p:world.crate.position.clone(),q:world.crate.quaternion.clone()};
 state.carrying=id.startsWith('game-carry-');if(!state.carrying&&state.previewContext){world.crate.position.copy(state.previewContext.p);world.crate.quaternion.copy(state.previewContext.q)}
 state.tour=null;state.flight=null;state.fallSpeed=0;state.fallPeak=null;state.action=null;state.mode='preview';state.preview=id;state.velocity.set(0,0,0);state.position.y=0;state.paused=false;await motion(id,true,seed);updateActorPositions();renderList();updateLinks();
}
function cameraUpdate(dt){
 const compare=$('companion').checked,target=state.position.clone().add(vec(0,1.05,0));if(compare)target.add(vec(Math.cos(state.facing)*1.4,0,-Math.sin(state.facing)*1.4));
 if(focused())target.add(vec(-Math.cos(state.yaw),0,Math.sin(state.yaw)).multiplyScalar(.32*state.shoulder));
 const distance=state.distance*(compare?1.35:1),desired=target.clone().add(vec(-Math.sin(state.yaw)*Math.cos(state.pitch)*distance,Math.sin(state.pitch)*distance,-Math.cos(state.yaw)*Math.cos(state.pitch)*distance));
 const ray=new T.Raycaster(target,desired.clone().sub(target).normalize(),0,distance),hits=ray.intersectObjects(world.obstacles.map(b=>b.mesh),false);if(hits[0])desired.copy(target).addScaledVector(ray.ray.direction,Math.max(.55,hits[0].distance-.2));
 camera.position.lerp(desired,1-Math.exp(-dt*12));camera.lookAt(target);sun.position.copy(state.position).add(vec(-16,30,-10));sun.target.position.copy(state.position);sun.target.updateMatrixWorld();
}
function frame(now){const dt=Math.min(.05,(now-last)/1000);last=now;if(!state.manualStep)advance(dt);cameraUpdate(dt);renderer.render(scene,camera);requestAnimationFrame(frame)}
new ResizeObserver(()=>{const w=canvas.clientWidth,h=canvas.clientHeight;if(w&&h){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix()}}).observe($('stage'));
function togglePause(){state.paused=!state.paused;$('pause').textContent=state.paused?'Resume':'Pause';$('pause').setAttribute('aria-pressed',String(state.paused));keys.clear();state.sprintLatch=false}
function stopTour(){state.tour=null;$('tour').textContent='Course tour'}
async function interact(){cancelAction('interact');if(state.stance!=='stand')return;if(state.carrying)return action('game-putdown',{carry:false});if(world.crate.position.clone().sub(state.position).setY(0).length()<1.7)return action('game-pickup',{carry:true});$('hint').textContent='Move within 1.7 m of the box in the box yard (near x −2, z 2).';}
function contextTarget(){
 if(state.stance==='sit')return {label:'Stand from bench (contact probe)',id:'game-stand-seat',options:{stance:'stand'}};
 if(state.stance!=='stand')return null;if(state.carrying)return {label:'Put down carried box',id:'game-putdown',options:{carry:false}};
 const candidates=[{label:'Pick up box',id:'game-pickup',options:{carry:true},p:world.crate.position,range:1.7},{label:'Use terminal',id:'game-panel',p:vec(-8,0,20),range:2},{label:'Sit on bench (contact probe)',id:'game-sit',options:{stance:'sit'},p:vec(-8,0,13),range:2}];
 return candidates.map(c=>({...c,distance:Math.hypot(c.p.x-state.position.x,c.p.z-state.position.z)})).filter(c=>c.distance<c.range).sort((a,b)=>a.distance-b.distance)[0]||null;
}
async function contextInteract(){cancelAction('interact');const target=contextTarget();if(!target){$('hint').textContent='No usable object in range. Move closer to the box, terminal or bench.';return false}return action(target.id,target.options)}
function recenter(){state.yaw=state.facing;state.pitch=.24;$('hint').textContent='Camera centered. Target lock is not implemented; RMB provides focus/strafe only.'}
function dodge(){
 if(state.flight)return false;state.stance=state.stance==='seiza'?'crouch':state.stance;
 const i=controlInput(),facing=state.facing,forward=vec(Math.sin(facing),0,Math.cos(facing)),right=vec(-Math.cos(facing),0,Math.sin(facing)),heading=Math.hypot(i.x,i.z)>.1?direction(i):forward.clone(),x=heading.dot(right),z=heading.dot(forward),d=Math.abs(x)>Math.abs(z)?x<0?'left':'right':z<0?'backward':'forward';
 const pending=action('game-dodge-'+d,{duration:.32});state.action.direction=heading;state.action.facing=facing;return pending;
}
function crouch(doubleTap=false){
 if(state.flight?.type==='ukemi'&&!releaseBreakfall())return false;
 if(state.flight?.type==='ledge'){state.flight=null;state.fallSpeed=0;cancelAction('release ledge');log('ledge-release',{reason:'C'});return true}
 if(state.mode==='preview')exitPreview();cancelAction('crouch input');if(state.flight||state.carrying)return false;
 if(doubleTap){state.stance='seiza';state.velocity.set(0,0,0);motion('game-crouch-down',true);log('stance',{stance:'seiza'});return true}
 if(state.stance==='crouch'||state.stance==='seiza'){
  if(!world.fits(state.position,1.85)){$('hint').textContent='There is not enough headroom to stand here.';return false}state.stance='stand';
 }else state.stance='crouch';
 motion(state.stance==='crouch'?'game-crouch-forward':'game-idle',true);log('stance',{stance:state.stance});return true;
}

function startRecording(){if(state.mode==='preview')exitPreview();recorder.start(active(),state.time);log('record-start',{body:active().id});$('record').textContent='Stop recording';$('record').setAttribute('aria-pressed','true');$('body').disabled=true;}
function stopRecording(){recorder.stop();$('record').textContent=recordLabel();$('record').setAttribute('aria-pressed','false');$('body').disabled=false;$('download-record').disabled=!recorder.ready}
function open(id){keys.clear();if(document.pointerLockElement)document.exitPointerLock();$(id).showModal();if(id==='review')loadReview();}
async function shortcut(code,modifiers={}){
 if(code==='ShiftLeft'||code==='ShiftRight'){state.sprintBeforeShift=state.sprintLatch;if(sprintMode==='toggle')state.sprintLatch=!state.sprintLatch;return}
 if(profile==='hybrid'){
  if(code==='AltLeft')return dodge();if(code==='KeyE')return contextInteract();if(code==='KeyQ')return recenter();
  if(code==='KeyR'){if(modifiers.shift||keys.has('ShiftLeft')||keys.has('ShiftRight')){if(sprintMode==='toggle')state.sprintLatch=state.sprintBeforeShift??false;if(recorder.active)stopRecording();else startRecording()}else $('hint').textContent='R is reserved for reload. This unarmed lab has no reload; Shift+R records.';return}
  if(code==='KeyV'){state.shoulder*=-1;return}if(['KeyG','KeyX','KeyH','KeyK','KeyJ'].includes(code))return;
  if(code==='Escape'){if(document.pointerLockElement)document.exitPointerLock();if(!state.paused)togglePause();return}
  if(code==='Tab'){open('library');return}
 }
 if(['Digit1','Digit2','Digit3','Digit4'].includes(code)){state.gait=['walk','jog','run','sprint'][Number(code.slice(-1))-1];$('gait').value=state.gait;return}
 if(code==='CapsLock'){state.gait=state.gait==='walk'?'jog':'walk';$('gait').value=state.gait}
 else if(code==='Space')jump(modifiers.ctrl===true);
 else if(code==='KeyC'){const now=performance.now(),doubleTap=now-state.crouchTap<300;state.crouchTap=doubleTap?-Infinity:now;crouch(doubleTap);}else if(code==='KeyZ'){cancelAction('prone input');if(state.stance==='prone')action('game-getup-front',{type:'transition',stance:'stand'});else if(!state.action&&!state.carrying)action('game-prone-down',{type:'transition',stance:'prone'})}
 else if(code==='KeyE')interact();else if(code==='KeyQ')dodge();
 else if(code==='KeyF')action('game-kick');else if(code==='KeyB')action('game-block');
 else if(code==='KeyG'){if(state.position.distanceTo(vec(-8,0,20))<2)action('game-panel');else $('hint').textContent='The terminal is at x −8, z 20.'}
 else if(code==='KeyX'){if(state.stance==='sit')action('game-stand-seat',{stance:'stand'});else if(state.position.distanceTo(vec(-8,0,13))<2)action('game-sit',{stance:'sit'});else $('hint').textContent='The bench is at x −8, z 14; approach from the front.'}
 else if(code==='KeyV')action('game-wave');else if(code==='KeyH')action('game-hit-front');else if(code==='KeyK')action('game-knockdown',{stance:'down'});else if(code==='KeyJ'&&(state.stance==='down'||state.stance==='prone'))action(state.stance==='down'?'game-getup-back':'game-getup-front',{stance:'stand'});
 else if(code==='KeyR'){if(recorder.active)stopRecording();else startRecording()}else if(code==='KeyP')togglePause();else if(code==='Digit0')reset();
}
document.addEventListener('keydown',e=>{if(modal()||e.target.closest('input,textarea,select,button,[contenteditable]'))return;const mappedCtrl=e.ctrlKey&&['KeyA','KeyS','KeyD','Space','ControlLeft','ControlRight'].includes(e.code)&&document.activeElement===canvas;if(e.metaKey||e.ctrlKey&&!mappedCtrl){keys.clear();state.sprintLatch=false;state.crouchTap=-Infinity;return}if(mappedCtrl){e.preventDefault();if(!keys.has('ControlLeft')&&!keys.has('ControlRight'))keys.add('ControlLeft')}if(['Space','Tab','ArrowUp','ArrowDown'].includes(e.code)||profile==='hybrid'&&e.code==='AltLeft')e.preventDefault();keys.add(e.code);if(!e.repeat){stopTour();if(e.code!=='KeyC')state.crouchTap=-Infinity;if(['KeyW','KeyA','KeyS','KeyD'].includes(e.code)||['ShiftLeft','ShiftRight'].includes(e.code)&&Math.hypot(controlInput().x,controlInput().z)>.1)movementIntent();shortcut(e.code,{shift:e.shiftKey,ctrl:e.ctrlKey})}});
document.addEventListener('keyup',e=>{if(profile==='hybrid'&&e.code==='AltLeft'&&!modal()&&document.activeElement===canvas)e.preventDefault();keys.delete(e.code);if(e.code.startsWith('Control')||!e.ctrlKey){keys.delete('ControlLeft');keys.delete('ControlRight')}});window.addEventListener('blur',()=>{keys.clear();state.sprintLatch=false;drag=false});document.addEventListener('visibilitychange',()=>{if(document.hidden){keys.clear();state.sprintLatch=false;state.paused=true;$('pause').textContent='Resume';$('pause').setAttribute('aria-pressed','true')}});
canvas.addEventListener('contextmenu',e=>e.preventDefault());canvas.addEventListener('pointerdown',e=>{canvas.focus();stopTour();state.crouchTap=-Infinity;if(e.button===2){drag=true;keys.add('MouseRight');canvas.setPointerCapture(e.pointerId)}else if(e.button===1&&profile==='hybrid'){e.preventDefault();recenter()}else if(e.button===0&&!modal()){
 if(profile==='hybrid'&&document.pointerLockElement!==canvas){try{canvas.requestPointerLock()?.catch?.(()=>$('hint').textContent='Use Mouse look, or right-drag to orbit. Click in the captured view to attack.')}catch{$('hint').textContent='Use Mouse look, or right-drag to orbit.'}}
 attack()
}});canvas.addEventListener('pointerup',()=>drag=false);document.addEventListener('pointerup',e=>{if(e.button===2)keys.delete('MouseRight')});canvas.addEventListener('auxclick',e=>{if(e.button===1&&profile==='hybrid')e.preventDefault()});
document.addEventListener('mousemove',e=>{if((drag||document.pointerLockElement===canvas)&&!modal()){state.yaw-=e.movementX*.003;state.pitch=T.MathUtils.clamp(state.pitch+e.movementY*.002,-.05,1.15)}});canvas.addEventListener('wheel',e=>{e.preventDefault();state.distance=T.MathUtils.clamp(state.distance+e.deltaY*.008,2.5,12)},{passive:false});
$('capture-mouse').onclick=async()=>{canvas.focus();try{await canvas.requestPointerLock()}catch{$('hint').textContent='Pointer capture unavailable; hold the right mouse button and drag to look.'}};
$('profile').onchange=()=>applyProfile($('profile').value);$('sprint-mode').onchange=()=>{sprintMode=$('sprint-mode').value==='toggle'?'toggle':'hold';state.sprintLatch=false;try{localStorage.setItem('kimodo-game-sprint-mode-v1',sprintMode)}catch{}};
let requestedProfile=new URLSearchParams(location.search).get('controls');if(!requestedProfile)try{requestedProfile=localStorage.getItem('kimodo-game-controls-profile-v1')}catch{}applyProfile(requestedProfile||'lab');
$('variety').checked=state.variety;$('variety').onchange=()=>{state.variety=$('variety').checked;try{localStorage.setItem('kimodo-game-variety-v1',String(state.variety))}catch{};log('variety-mode',{enabled:state.variety});canvas.focus()};
$('trial').onchange=()=>{const kind=$('trial').value;if(kind)startTrial(kind);$('trial').value=''};
$('gait').onchange=()=>state.gait=$('gait').value;$('body').onchange=()=>{updateActorPositions();updateLinks();log('body',{body:active().id});if(state.mode==='preview')preview(state.preview)};$('companion').onchange=updateActorPositions;$('reset').onclick=reset;$('pause').onclick=togglePause;
for(const id of ['library','review','help'])$(id+'-open').onclick=()=>open(id);
$('play-mode').onclick=()=>{$('library').close();exitPreview();canvas.focus()};$('record').onclick=()=>recorder.active?stopRecording():startRecording();$('download-record').onclick=async()=>{try{await recorder.save(actors.find(a=>a.id===recorder.body))}catch(e){$('hint').textContent=e.message}};
function renderList(){if(!catalog)return;const group=$('category').value,term=$('search').value.toLowerCase();$('motion-list').replaceChildren();for(const m of catalog.motions.filter(m=>(group==='all'||group===m.group)&&m.label.toLowerCase().includes(term))){const b=document.createElement('button');b.textContent=m.label;const s=document.createElement('small'),probe=['ground','traversal'].includes(m.group)||['game-sit','game-stand-seat'].includes(m.id);s.textContent=m.kind+' · '+m.group+(probe?' · contact probe':'');b.append(s);b.classList.toggle('selected',m.id===(state.preview||state.lastMotion));b.onclick=()=>{$('library').close();preview(m.id)};$('motion-list').append(b)}}
$('category').onchange=renderList;$('search').oninput=renderList;$('seed').onchange=()=>{if(state.mode==='preview')preview(state.preview)};
function updateLinks(){const t=candidate();if(!t)return;$('source-link').href=outputFor(t,active().id).raw_clip;$('source-link').textContent='Source-motion GLB (rebuilt)';$('source-link').onclick=async e=>{e.preventDefault();const a=active(),data=await readMotionJSON(outputFor(candidate(),a.id).raw_clip);await exportClips(a,[data],candidate().id+'-'+a.id+'-source-motion-rebuilt.glb')};$('pack-link').href=catalog.bodies.find(b=>b.id===active().id).pack;$('pack-link').textContent=active().label+' · 94-clip GLB';}
$('export-clip').onclick=async()=>{const a=active();if(a?.take)await exportClips(a,[await dataFor(a.take,a.id)],a.take.id+'-'+a.id+'-in-place.glb')};
async function exportChosen(onlyKept=false){
 const a=active(),button=$(onlyKept?'export-kept':'export-preferred');button.disabled=true;
 try{const takes=catalog.motions.map(m=>takeFor(m.id,a.id)).filter(t=>{if(!onlyKept)return true;const r=store.latest('kimodo-game-kit-v1',t.id,a.id);return r?.decision==='keep'&&r.version==='kimodo-game-kit:v1:'+t.source_sha256.slice(0,12)});
  if(!takes.length){$('hint').textContent='No current preferred takes have Keep reviews for this character yet.';return}
  const data=await Promise.all(takes.map(t=>dataFor(t,a.id))),stem=a.id+'-'+(onlyKept?'kept':'preferred')+'-game-kit';await exportClips(a,data,stem+'.glb');
  download(JSON.stringify({schema:'kimodo-game-chosen-pack/1',body:a.id,recipe:1,source_state_machine:'packs/game-state-machine.json',clips:takes.map((t,i)=>({motion:t.motion,clip:data[i].name,candidate:t.id,seed:t.seed,source_sha256:t.source_sha256,loop:data[i].loop,duration_s:data[i].duration,jump:data[i].jump})),runtime_not_baked:['World controller','Foot/hand IK','Prop transforms','Inter-clip blends']},null,2),stem+'.json');$('hint').textContent=takes.length+' selected clips exported with their source mapping.';
 }catch(e){$('hint').textContent=e.message}finally{button.disabled=false}
}
$('export-preferred').onclick=()=>exportChosen(false);$('export-kept').onclick=()=>exportChosen(true);
function loadReview(){reviewCandidate=candidate();if(!reviewCandidate)return;const r=store.latest('kimodo-game-kit-v1',reviewCandidate.id,active().id);$('review-title').textContent=reviewCandidate.label+' · '+active().label+' · seed '+reviewCandidate.seed;$('reviewer').value=store.profile.name;$('decision').value=r?.decision||'unreviewed';$('notes').value=r?.notes||'';for(const k of Object.keys(SCORE_FIELDS))$('score-'+k).value=r?.scores[k]??'';$('saved').textContent='Saved in this browser.'}
function saveReview(){if(!reviewCandidate)return;store.save({collection:'kimodo-game-kit-v1',candidate:reviewCandidate.id,version:'kimodo-game-kit:v1:'+reviewCandidate.source_sha256.slice(0,12),body:active().id,reviewer:$('reviewer').value,decision:$('decision').value,scores:Object.fromEntries(Object.keys(SCORE_FIELDS).map(k=>[k,$('score-'+k).value?Number($('score-'+k).value):null])),notes:$('notes').value});$('saved').textContent=store.available?'Saved in this browser.':store.error}
for(const [key,label]of Object.entries(SCORE_FIELDS)){const l=document.createElement('label');l.textContent=label;const s=document.createElement('select');s.id='score-'+key;s.add(new Option('—',''));for(let i=1;i<=5;i++)s.add(new Option(String(i),String(i)));s.onchange=saveReview;l.append(s);$('scores').append(l)}for(const id of ['reviewer','decision','notes'])$(id).addEventListener(id==='decision'?'change':'input',saveReview);
$('export-reviews').onclick=()=>{store.persist();download(JSON.stringify({...store.export(),game_manifest_snapshot:{schema:catalog.schema,motions:catalog.motions,preferred:state.preferred}},null,2),'motion-lab-all-reviews.json')};$('import-reviews').onchange=async e=>{try{const n=store.import(JSON.parse(await e.target.files[0].text()));loadReview();$('saved').textContent='Imported '+n+' reviews.'}catch(err){$('saved').textContent=err.message}};
$('use-take').onclick=()=>{if(!reviewCandidate)return;state.preferred[active().id+':'+reviewCandidate.motion]=reviewCandidate.seed;localStorage.setItem('kimodo-game-preferred-v1',JSON.stringify(state.preferred));$('saved').textContent='Preferred take saved. Disable Variety to use it in play. Default base pack stays seed 411; Preferred pack includes added ukemi.'};
const tourSteps=[{x:0,z:7,gait:'walk'},{x:0,z:18,gait:'jog'},{x:0,z:39,gait:'run'},{x:0,z:64,gait:'sprint'},{x:12,z:64,gait:'run'},{x:12,z:43,gait:'run',jumpAt:49.5},{x:12,z:40,gait:'walk'},{action:'crouch'},{x:12,z:26,gait:'walk'},{action:'crouch'},{x:12,z:13,gait:'jog',jumpAt:19.25},{x:-2,z:3,gait:'run'},{action:'box'},{x:-9,z:8,gait:'walk'},{action:'box'},{action:'game-wave'},{action:'game-combo'},{action:'game-hit-front'},{action:'game-knockdown',stance:'down'},{action:'game-getup-back',stance:'stand'}];
function advanceTour(dt){const tour=state.tour;if(!tour)return {x:0,z:0};const step=tourSteps[tour.index];if(!step){stopTour();$('hint').textContent='Course tour complete. Record a manual run or inspect any motion in Motions.';return {x:0,z:0}};
 if(step.action){if(!tour.started){tour.started=true;const p=step.action==='crouch'?crouch():step.action==='box'?interact():action(step.action,{stance:step.stance});Promise.resolve(p).then(()=>{if(state.tour===tour)tour.launched=true})}if(tour.launched&&!state.action){tour.index++;tour.started=tour.launched=false}return {x:0,z:0}}
 const to=vec(step.x-state.position.x,0,step.z-state.position.z),distance=to.length();if(distance<.6){tour.index++;tour.jumped=false;return {x:0,z:0}}
 state.yaw=Math.atan2(to.x,to.z);if(step.jumpAt&&!tour.jumped&&state.position.z<step.jumpAt){tour.jumped=true;jump(false,{x:0,z:1})}return {x:0,z:1,gait:step.gait};
}
$('tour').onclick=()=>{if(state.tour){stopTour();return}reset();$('zones').checked=true;state.tour={index:0};$('tour').textContent='Stop tour';canvas.focus()};
try{
 const response=await fetch('catalog.json',{cache:'no-cache'});if(!response.ok)throw Error('Game catalog is still being built.');catalog=await response.json();
 for(const def of catalog.bodies){const gltf=await loadMotionModel(loader,def.model),asset=gltf.scene,group=new T.Group();group.name='GameActor_'+def.id;group.add(asset);scene.add(group);const skeletons=new Set();asset.traverse(o=>{if(o.isSkinnedMesh){skeletons.add(o.skeleton);o.frustumCulled=false;o.castShadow=true;o.receiveShadow=true}});for(const s of skeletons)s.pose();asset.updateMatrixWorld(true);
  const box=new T.Box3().setFromObject(asset,true),scale=1.9/box.getSize(vec()).y;asset.scale.multiplyScalar(scale);const bones={},bind=[];asset.traverse(b=>{if(b.isBone){bones[b.name]=b;bind.push({b,p:b.position.clone(),q:b.quaternion.clone()})}});
  const a={id:def.id,label:def.label,asset,group,scale,bones,bind,feet:['L','R'].map(s=>({hip:bones['HIP_'+s],knee:bones['KNEE_'+s],ankle:bones['ANKLE_'+s],sole:bones['SOCKET_SOLE_'+s]||bones['ANKLE_'+s],lock:null})),token:0,pending:null,take:null,data:null,phase:0,blend:1};actors.push(a);
 }
 for(const a of actors)a.rig=calibrateRig(a);
 for(const group of [...new Set(catalog.motions.map(m=>m.group))])$('category').add(new Option(group[0].toUpperCase()+group.slice(1),group));renderList();updateActorPositions();
 await motion('game-idle',true);const query=new URLSearchParams(location.search),requestedBody=query.get('body');if(catalog.bodies.some(b=>b.id===requestedBody))$('body').value=requestedBody;const requested=query.get('motion');if(catalog.motions.some(m=>m.id===requested))await preview(requested,Number(query.get('seed'))||411);else if(query.get('tour')==='1')$('tour').click();else if(query.get('course')==='traversal'){state.position.set(7,0,5.6);updateActorPositions();}else if(['ledge','hero-landing','trip-forward','trip-backward','trip-side-left','trip-side-right'].includes(query.get('course')))startTrial(query.get('course'));
 camera.position.set(0,2,-6);updateHUD();
 // Warm only common transitions; the rest load on demand and are cached as clips,
 // without loading another mesh or creating another WebGL renderer.
 const warm=['game-walk-forward','game-jog-forward','game-run-forward','game-sprint-forward','game-crouch-idle','game-crouch-forward','game-crouch-down','game-crouch-up','game-jump-standing','game-jump-run','game-dodge-forward','game-jab','game-cross','game-vault','game-mantle','game-land-hard','game-pickup','game-putdown','game-carry-idle'];
 (async()=>{const ids=[...warm,'game-ukemi-forward','game-ukemi-backward','game-ukemi-side-left','game-ukemi-side-right'],jobs=ids.flatMap(id=>catalog.takes.filter(t=>t.motion===id&&t.automatic_eligible!==false).flatMap(t=>actors.map(a=>()=>dataFor(t,a.id))));await Promise.all(Array.from({length:4},async()=>{while(jobs.length)await jobs.shift()()}))})().catch(console.error);
}catch(e){$('mode').textContent=e.message;console.error(e)}
window.GameLab={state,actors,world,camera,renderer,recorder,store,get profile(){return profile},get sprintMode(){return sprintMode},ctrlMove,applyProfile,contextTarget,contextInteract,focused,strafing,controlInput,get catalog(){return catalog},get active(){return active()},get loadJobs(){return loadJobs},get variationDraws(){return variationPicker.draws},eligibleTakes,motion,preview,action,jump,interact,crouch,cancelAction,attack,contextualJump,startTrial,tripOnContact,get breakfallRules(){return BREAKFALL_RULES},get contactRules(){return CONTACT_RULES},reset,advance,shortcut,dataFor,takeFor,
 setManual(value=true){state.manualStep=value},setPosition(x,z,y=0){state.position.set(x,y,z);state.fallPeak=null;state.fallSpeed=0;state.flight=null;state.velocity.set(0,0,0);updateActorPositions()},
 async exportPack(body,save=true){const a=actors.find(a=>a.id===body),data=[];for(const m of catalog.motions.filter(m=>!m.addon))data.push(await dataFor(takeFor(m.id,body),body));return exportClips(a,data,body+'-game-kit.glb',save)},
 async exportCurrent(save=true){const a=active();return exportClips(a,[await dataFor(a.take,a.id)],a.take.id+'-'+a.id+'-in-place.glb',save)},exportChosen,startRecording,stopRecording,loadReview,saveReview};
requestAnimationFrame(frame);
