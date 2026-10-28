import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';

const $=id=>document.getElementById(id),stage=$('stage');
const renderer=new THREE.WebGLRenderer({canvas:$('canvas'),antialias:true,alpha:false});
renderer.setPixelRatio(Math.min(devicePixelRatio,innerWidth<800?1.5:2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;
const scene=new THREE.Scene();scene.background=new THREE.Color('#becab7');scene.fog=new THREE.Fog('#becab7',28,65);
const camera=new THREE.OrthographicCamera(-7,7,7,-7,.05,100);camera.position.set(9,9,13);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minZoom=.5;controls.maxZoom=3;controls.maxPolarAngle=Math.PI*.47;controls.minPolarAngle=.2;
let cameraMode='duo',cameraTouched=false;
controls.addEventListener('start',()=>{cameraTouched=true});
const room=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();
scene.add(new THREE.HemisphereLight(0xf3f2df,0x5a7266,2.2));
const sun=new THREE.DirectionalLight(0xffe7bf,3.3);sun.position.set(-4,9,7);sun.castShadow=true;sun.shadow.mapSize.set(innerWidth<800?1024:2048,innerWidth<800?1024:2048);
Object.assign(sun.shadow.camera,{left:-9,right:9,top:8,bottom:-8,near:.5,far:30});sun.shadow.normalBias=.0015;sun.shadow.bias=-.00003;scene.add(sun);
const fill=new THREE.DirectionalLight(0xbce4e1,1);fill.position.set(6,5,-5);scene.add(fill);
const mat=(color,roughness=.85,metalness=.05)=>new THREE.MeshStandardMaterial({color,roughness,metalness});
const floorMat=mat('#aeb3a0'),edgeMat=mat('#577168'),darkMat=mat('#294743'),goldMat=mat('#c49b55'),mintMat=mat('#c5d7ba'),lineMat=mat('#d6d9bc');
function box(w,h,d,x,y,z,material){const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material);mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);return mesh}
function cylinder(r,h,x,y,z,material,vertices=24){const mesh=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,vertices),material);mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);return mesh}
// A bounded workshop island, with all props kept outside the actors' central play area.
box(13.6,.28,11.2,0,-.22,0,darkMat);box(13.35,.12,10.95,0,-.06,0,floorMat);
box(13.65,.07,11.25,0,-.39,0,edgeMat);
const ground=new THREE.Mesh(new THREE.PlaneGeometry(200,200),mat('#b9c6b3'));ground.rotation.x=-Math.PI/2;ground.position.y=-.43;ground.receiveShadow=true;scene.add(ground);
for(let x=-6;x<=6;x++)box(.012,.002,10.4,x,.001,0,lineMat);
for(let z=-5;z<=5;z++)box(12.8,.002,.012,0,.001,z,lineMat);
for(const x of [-6.2,6.2])for(const z of [-4.8,4.8]){
 cylinder(.11,.12,x,.06,z,goldMat);cylinder(.04,.7,x,.45,z,darkMat);cylinder(.065,.07,x,.83,z,mintMat);
}
for(const x of [-5.6,5.6]){
 box(.8,.45,1.5,x,.225,-4.4,edgeMat);box(.86,.08,1.56,x,.49,-4.4,goldMat);
 for(let i=0;i<4;i++)cylinder(.12,.35,x+(i%2-.5)*.3,.68,-4.6+Math.floor(i/2)*.35,mintMat,8);
}
box(2.2,.12,.7,4.25,.8,4.7,goldMat);for(const x of [3.4,5.1])box(.1,.8,.5,x,.4,4.7,darkMat);
for(let i=0;i<3;i++){const crate=box(.6,.55,.6,-5.7+i*.8,.275,4.65,i%2?goldMat:edgeMat);box(.64,.045,.64,crate.position.x,.57,4.65,darkMat)}
const ring=new THREE.Mesh(new THREE.RingGeometry(3.75,3.77,96),mat('#c8cbb4'));ring.rotation.x=-Math.PI/2;ring.position.y=.004;scene.add(ring);
function stencil(text,x,z,width=2){const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=128;const c=canvas.getContext('2d');c.fillStyle='#47675d';c.font='600 54px monospace';c.textAlign='center';c.fillText(text,512,85);const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;const mesh=new THREE.Mesh(new THREE.PlaneGeometry(width,width/8),new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false}));mesh.rotation.x=-Math.PI/2;mesh.position.set(x,.006,z);scene.add(mesh)}
stencil('C08  /  K0-TECH',0,4.7,3);stencil('OFF SHIFT — MOTION LAB',0,-4.8,3.5);

let catalog,robot,cat,chapters=[],total=1,time=0,playing=true,loop=true,ready=false,currentChapter=-1;
const vec=(x,z,y=0)=>new THREE.Vector3(x,y,z);
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const smooth=v=>{v=clamp(v);return v*v*(3-2*v)};
const smoother=v=>{v=clamp(v);return v*v*v*(v*(v*6-15)+10)};
const lerp=(a,b,t)=>a+(b-a)*t;
function stripTravel(clip,robotRig){
 const result=clip.clone();result.tracks=result.tracks.flatMap(track=>{
  if(track.name==='MOTION.quaternion'&&robotRig)return [];
  if(track.name==='MOTION.position'){const t=track.clone();for(let i=0;i<t.values.length;i+=3){t.values[i]=0;t.values[i+2]=0}return [t]}
  return [track.clone()];
 });return result;
}
function closeLoop(clip,start,end){
 const source=THREE.AnimationUtils.subclip(clip,'loop',Math.round(start*30),Math.round(end*30),30);
 source.tracks.forEach(track=>{
  const size=track.getValueSize(),count=track.times.length;if(count<2)return;
  const first=Array.from(track.values.slice(0,size)),last=Array.from(track.values.slice(-size));
  for(let i=0;i<count;i++){
   const u=smooth(track.times[i]/source.duration);
   if(track instanceof THREE.QuaternionKeyframeTrack){
    const a=new THREE.Quaternion().fromArray(first),b=new THREE.Quaternion().fromArray(last),delta=a.multiply(b.invert());
    const correction=new THREE.Quaternion().slerp(delta,u),q=new THREE.Quaternion().fromArray(track.values,i*size);correction.multiply(q).normalize().toArray(track.values,i*size);
   }else for(let j=0;j<size;j++)track.values[i*size+j]-=(last[j]-first[j])*u;
  }
 });return source;
}
function setupActor(asset,clips,isRobot){
 const group=new THREE.Group();scene.add(group);group.add(asset.scene);
 const actor={group,scene:asset.scene,clips,raw:new Map(),actions:new Map(),isRobot,support:[],floorLift:0};
 actor.mixer=new THREE.AnimationMixer(asset.scene);
 for(const [key,source] of clips){
  const travel=source.tracks.find(t=>t.name==='MOTION.position'),heading=source.tracks.find(t=>t.name==='MOTION.quaternion');
  actor.raw.set(key,{position:travel?.createInterpolant(),quaternion:heading?.createInterpolant(),duration:source.duration});
  const entry=catalog.tests.find(t=>t.id===key);
  let clip=stripTravel(source,isRobot);clip.name=key;
  if(entry?.loop_window){clip=closeLoop(clip,entry.loop_window.start_s,entry.loop_window.end_s);clip.name=key;actor.clips.set(key,clip)}
  else actor.clips.set(key,clip);
  const action=actor.mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();action.enabled=false;actor.actions.set(key,action);
 }
 asset.scene.updateMatrixWorld(true);
 const directions=[];for(let x=-1;x<=1;x++)for(let y=-1;y<=1;y++)for(let z=-1;z<=1;z++)if(x||y||z)directions.push(new THREE.Vector3(x,y,z).normalize());
 for(let i=0;i<160;i++){const y=1-2*(i+.5)/160,r=Math.sqrt(1-y*y),angle=i*Math.PI*(3-Math.sqrt(5));directions.push(new THREE.Vector3(Math.cos(angle)*r,y,Math.sin(angle)*r))}
 asset.scene.traverse(mesh=>{
  if(!mesh.isSkinnedMesh)return;mesh.castShadow=true;mesh.receiveShadow=true;mesh.frustumCulled=false;mesh.skeleton.update();
  const position=mesh.geometry.attributes.position,indices=mesh.geometry.attributes.skinIndex,weights=mesh.geometry.attributes.skinWeight;
  const groups=new Map();const temp=new THREE.Vector3();
  for(let i=0;i<position.count;i++){
   const bone=mesh.skeleton.bones[indices.getX(i)];
   if(weights.getX(i)>.999){temp.fromBufferAttribute(position,i).applyMatrix4(mesh.bindMatrix).applyMatrix4(mesh.skeleton.boneInverses[indices.getX(i)]);if(!groups.has(bone.name))groups.set(bone.name,[]);groups.get(bone.name).push([i,temp.clone()])}
  }
  const support=new Set();for(const candidates of groups.values())for(const direction of directions){let best=Infinity,index=-1;for(const [i,p] of candidates){const dot=p.dot(direction);if(dot<best){best=dot;index=i}}if(index>=0)support.add(index)}
  if(support.size)actor.support.push({mesh,indices:[...support]});
 });
 return actor;
}
function rawPosition(actor,key,t){const raw=actor.raw.get(key);if(!raw?.position)return new THREE.Vector3();return new THREE.Vector3().fromArray(raw.position.evaluate(clamp(t,0,raw.duration))).sub(new THREE.Vector3().fromArray(raw.position.evaluate(0)))}
function rawYaw(actor,key,t){const raw=actor.raw.get(key);if(!raw?.quaternion)return 0;const q=new THREE.Quaternion().fromArray(raw.quaternion.evaluate(clamp(t,0,raw.duration))),q0=new THREE.Quaternion().fromArray(raw.quaternion.evaluate(0));return new THREE.Euler().setFromQuaternion(q.multiply(q0.invert()),'YXZ').y}
function sample(actor,specs){
 for(const action of actor.actions.values()){action.enabled=false;action.setEffectiveWeight(0)}
 const combined=new Map();for(const s of specs){if(!s||s.weight<=0)continue;const current=combined.get(s.key);if(current){current.weight+=s.weight;if(s.weight>current.best){current.time=s.time;current.best=s.weight}}else combined.set(s.key,{...s,best:s.weight})}
 for(const [key,s] of combined){const action=actor.actions.get(key);if(!action)continue;action.enabled=true;action.paused=false;action.time=clamp(s.time,0,action.getClip().duration-1e-7);action.setEffectiveWeight(s.weight)}
 actor.mixer.update(0);actor.group.updateMatrixWorld(true);actor.scene.traverse(o=>{if(o.isSkinnedMesh)o.skeleton.update()});
}
function action(actor,key,t,looping=false,rate=1){const d=actor.clips.get(key).duration;return {key,time:looping?(Math.max(0,t)*rate)%d:clamp(t*rate,0,d),weight:1}}
function sequence(actor,keyA,keyB,t,split,blend=.45){
 if(t<split-blend)return [action(actor,keyA,t)];
 if(t>split)return [action(actor,keyB,t-split,true)];
 const w=smooth((t-split+blend)/blend);return [{...action(actor,keyA,t),weight:1-w},{...action(actor,keyB,0),weight:w}];
}
function route(points){if(points.length===1)return {curve:null,length:0,start:points[0],end:points[0]};const curve=new THREE.CatmullRomCurve3(points,false,'centripetal');return {curve,length:curve.getLength(),start:points[0],end:points.at(-1)}}
function atRoute(path,u){return path.curve?path.curve.getPointAt(clamp(smoother(u))):path.start.clone()}
function routeYaw(path,u,fallback=0){if(!path.curve)return fallback;const tangent=path.curve.getTangentAt(clamp(smoother(u),.0001,.9999));return Math.atan2(tangent.x,tangent.z)}
function buildStory(){
 let cursor=0;
 function add(title,duration,type,r,c,extra={}){const chapter={title,duration,type,start:cursor,end:cursor+duration,r:route(r),c:route(c),...extra};chapters.push(chapter);cursor+=duration}
 const r0=vec(-2,0),c0=vec(1.5,1),c1=vec(-.95,.85);
 add('A friend arrives',8,'greet',[r0],[c0,vec(.1,.95),c1]);
 add('Checking in',7,'hello',[r0],[c1]);
 add('A very good roll',6,'roll',[r0],[c1]);
 add('On your feet',3,'stand',[r0],[c1]);
 const rEnd=vec(-2.5,1),cEnd=vec(-1,2);
 add('You’re it',14,'chase',[r0,vec(-1.5,2.8),vec(2.5,2.5),vec(3.1,0),vec(.5,-2.6),vec(-2.9,-1.3),rEnd],[c1,vec(-.5,3.5),vec(3.5,2),vec(4,-1),vec(1.5,-3.3),vec(-2.5,-2.8),vec(-3.7,0),cEnd]);
 const jumpStart=vec(-2,-1),jumpDelta=rawPosition(robot,'own_jump_over',robot.raw.get('own_jump_over').duration),jumpEnd=jumpStart.clone().add(jumpDelta);
 const catWatch=jumpStart.clone().add(jumpDelta.clone().multiplyScalar(.5));
 add('A little courage',5,'lineup',[rEnd,vec(-3.1,.2),jumpStart],[cEnd,vec(.1,1),catWatch]);
 add('C08 clears K0',robot.raw.get('own_jump_over').duration,'robotJump',[jumpStart,jumpEnd],[catWatch]);
 const catLaunch=jumpEnd.clone().add(vec(0,2.4)),catLand=jumpEnd.clone().add(vec(0,-2.4));
 add('Your turn, little one',6,'catSetup',[jumpEnd],[catWatch,vec(-.5,2.4),catLaunch]);
 add('K0 returns the favour',4,'catJump',[jumpEnd],[catLaunch,catLand]);
 const restR=vec(-2,.2),restC=vec(-.9,-1.1);
 add('Now K0 gives chase',13,'reverseChase',[jumpEnd,vec(-.5,1.4),vec(2.5,0),vec(2.8,-2.3),vec(.2,-2.5),vec(-2.8,-1.5),restR],[catLand,jumpEnd.clone(),vec(-.5,1.4),vec(2.5,0),vec(2.8,-2.3),vec(.2,-2.5),restC]);
 add('The quiet part',7,'rest',[restR],[restC]);
 const backwards=Math.abs(rawPosition(robot,'own_backward_steps',robot.raw.get('own_backward_steps').duration).z);
 let lo=0,hi=robot.raw.get('own_forward_steps').duration;for(let i=0;i<40;i++){const mid=(lo+hi)/2;if(rawPosition(robot,'own_forward_steps',mid).z<backwards)lo=mid;else hi=mid}
 const footwork=[{key:'own_left_steps',axis:'x'},{key:'own_right_steps',axis:'x'},{key:'own_backward_steps',axis:'z'},{key:'own_forward_steps',axis:'z',duration:(lo+hi)/2}];
 footwork.forEach(step=>step.duration??=robot.raw.get(step.key).duration);
 add('Follow my feet',footwork.reduce((n,s)=>n+s.duration,0),'footwork',[restR],[restC,vec(.1,-1.6),vec(.1,-.2),restC],{footwork});
 const turns=['own_turn_left90','own_turn_right90','own_turn180','own_turn180'];
 add('A little footwork',turns.reduce((n,key)=>n+robot.raw.get(key).duration,0),'turns',[restR],[restC],{turns});
 add('One more trick',6,'reach',[restR],[restC]);
 add('A stretch together',4,'stretch',[restR],[restC]);
 add('Back to the beginning',8,'return',[restR,vec(-2,.1),r0],[restC,vec(2.4,-1.3),vec(2.8,1),c0]);
 total=cursor;$('timeline').max=total;
 chapters.forEach((chapter,i)=>{const button=document.createElement('button');button.innerHTML=`<span>${String(i+1).padStart(2,'0')}</span>${chapter.title}`;button.onclick=()=>{time=chapter.start;playing=true;cameraTouched=false;update(time,true)};$('chapters').append(button)});
}
function evaluate(chapter,t){
 const u=clamp(t/chapter.duration),ru=chapter.type==='reverseChase'?clamp((t-1.7)/(chapter.duration-1.7)):u,cu=chapter.type==='reverseChase'?clamp((t-2.8)/(chapter.duration-2.8)):u,rp=atRoute(chapter.r,ru),cp=atRoute(chapter.c,cu);
 let ry=routeYaw(chapter.r,ru,Math.atan2(chapter.c.end.x-rp.x,chapter.c.end.z-rp.z)),cy=routeYaw(chapter.c,cu,Math.atan2(rp.x-cp.x,rp.z-cp.z));
 let rs=[action(robot,'own_idle',t,true)],cs=[action(cat,'Watch_Idle',t,true)];
 const rdist=chapter.r.length*smoother(ru),cdist=chapter.c.length*smoother(cu);
 const runSpeed=catalog.tests.find(c=>c.id==='own_run').source_metrics.root_horizontal_travel_m/(robot.raw.get('own_run').duration)*1.18911573855;
 function run(){return [action(robot,'own_run',rdist/runSpeed,true)]}
 function walk(){return [action(robot,'own_forward_steps',rdist/.42,true)]}
 function gallop(){return [action(cat,'Gallop_Cycle',cdist/2.688889,true)]}
 switch(chapter.type){
  case 'greet':cs=[action(cat,'Feline_Walk_Cycle',cdist/.2383333,true)];break;
  case 'hello':rs=sequence(robot,'own_crouch_down','own_crouch_hold',t,robot.raw.get('own_crouch_down').duration);cs=[action(cat,'Give_Paw',Math.max(0,t-.7))];break;
  case 'roll':rs=[action(robot,'own_crouch_hold',t,true)];cs=[action(cat,'Roll_Over',t)];break;
  case 'stand':rs=[action(robot,'own_stand_up',t)];break;
  case 'chase':rs=run();cs=gallop();break;
  case 'lineup':rs=walk();cs=[action(cat,'Feline_Walk_Cycle',cdist/.2383333,true)];break;
  case 'robotJump':rp.copy(chapter.r.start).add(rawPosition(robot,'own_jump_over',t));ry=0;rs=[action(robot,'own_jump_over',t)];cy=Math.PI/2;break;
  case 'catSetup':rs=[action(robot,'own_deep_crouch',Math.min(t,2.4))];cs=gallop();break;
  case 'catJump':{
   rs=[action(robot,'own_deep_crouch',2.4)];ry=0;cy=Math.PI;
   let clipTime;if(t<.8)clipTime=t/.8*.815;else if(t<2.2)clipTime=.815+(t-.8)/1.4*(1.34-.815);else clipTime=1.34+(t-2.2)/1.8*(3.2-1.34);
   cs=[action(cat,'Pounce',clipTime)];const flight=clamp((t-.8)/1.4);
   cp.lerpVectors(chapter.c.start,chapter.c.end,flight);
   cp.y=2.25*smooth(flight/.2)*smooth((1-flight)/.2);break;
  }
  case 'reverseChase':rs=t<1.7?[action(robot,'own_stand_up',t)]:run();cs=t<2.8?[action(cat,'Watch_Idle',t,true)]:gallop();break;
  case 'rest':rs=[action(robot,'own_idle',t,true)];cs=[action(cat,'Sit_Down',t)];break;
  case 'footwork':{
   let local=t,offset=new THREE.Vector3();ry=0;
   for(const step of chapter.footwork){if(local>step.duration){const delta=rawPosition(robot,step.key,step.duration);offset[step.axis]+=delta[step.axis];local-=step.duration}else{const delta=rawPosition(robot,step.key,local);offset[step.axis]+=delta[step.axis];rs=[action(robot,step.key,local)];break}}
   rp.copy(chapter.r.start).add(offset);cs=[action(cat,'Feline_Walk_Cycle',cdist/.2383333,true)];break;
  }
  case 'turns':{
   let local=t,yaw=0;for(const key of chapter.turns){const d=robot.raw.get(key).duration;if(local>d){yaw+=rawYaw(robot,key,d);local-=d}else{yaw+=rawYaw(robot,key,local);rs=[action(robot,key,local)];break}}ry=yaw;break;
  }
  case 'reach':rs=sequence(robot,'own_reach_right','own_reach_both',t,robot.raw.get('own_reach_right').duration);cs=[action(cat,'Watch_Idle',t,true)];break;
  case 'stretch':rs=[action(robot,'own_hands_high',t)];cs=[action(cat,'Give_Paw',t)];break;
  case 'return':{
   rs=[action(robot,'own_turn_right90',t/chapter.duration*robot.raw.get('own_turn_right90').duration)];
   const first=chapters[0],startYaw=Math.atan2(chapter.c.start.x-chapter.r.start.x,chapter.c.start.z-chapter.r.start.z),endYaw=Math.atan2(first.c.end.x-first.r.start.x,first.c.end.z-first.r.start.z);
   ry=blendYaw(startYaw,endYaw,smooth(u));cs=[action(cat,'Feline_Walk_Cycle',cdist/.2383333,true)];break;
  }
 }
 return {rp,cp,ry,cy,rs,cs};
}
function blendYaw(a,b,w){return a+Math.atan2(Math.sin(b-a),Math.cos(b-a))*w}
function poseStory(t){
 let i=chapters.findIndex(c=>t<c.end);if(i<0)i=chapters.length-1;
 const chapter=chapters[i],local=clamp(t-chapter.start,0,chapter.duration),state=evaluate(chapter,local);
 if(i>0&&local<.65){
  const prev=evaluate(chapters[i-1],chapters[i-1].duration),w=smooth(local/.65);
  // Root routes meet exactly; blend only the heading and skeleton across scene boundaries.
  state.ry=blendYaw(prev.ry,state.ry,w);state.cy=blendYaw(prev.cy,state.cy,w);
  state.rs=[...prev.rs.map(s=>({...s,weight:s.weight*(1-w)})),...state.rs.map(s=>({...s,weight:s.weight*w}))];
  state.cs=[...prev.cs.map(s=>({...s,weight:s.weight*(1-w)})),...state.cs.map(s=>({...s,weight:s.weight*w}))];
 }
 if(i===chapters.length-1&&local>chapter.duration-.65){
  const first=evaluate(chapters[0],0),w=smooth((local-chapter.duration+.65)/.65);
  state.ry=blendYaw(state.ry,first.ry,w);state.cy=blendYaw(state.cy,first.cy,w);
  state.rs=[...state.rs.map(s=>({...s,weight:s.weight*(1-w)})),...first.rs.map(s=>({...s,weight:s.weight*w}))];
  state.cs=[...state.cs.map(s=>({...s,weight:s.weight*(1-w)})),...first.cs.map(s=>({...s,weight:s.weight*w}))];
 }
 robot.group.position.copy(state.rp);cat.group.position.copy(state.cp);robot.group.rotation.set(0,state.ry,0);cat.group.rotation.set(0,state.cy,0);
 sample(robot,state.rs);sample(cat,state.cs);
 const p=new THREE.Vector3();
 for(const actor of [robot,cat]){
  let min=Infinity;for(const {mesh,indices} of actor.support)for(const index of indices){mesh.getVertexPosition(index,p);p.applyMatrix4(mesh.matrixWorld);min=Math.min(min,p.y)}
  actor.floorLift=Math.max(0,.003-min);actor.group.position.y+=actor.floorLift;actor.group.updateMatrixWorld(true);actor.scene.traverse(o=>{if(o.isSkinnedMesh)o.skeleton.update()});
 }
 if(i!==currentChapter){currentChapter=i;$('chapter-label').textContent=chapter.title;$('chapter-number').textContent=`${String(i+1).padStart(2,'0')} / ${chapters.length}`;[...$('chapters').children].forEach((b,j)=>b.setAttribute('aria-current',j===i?'true':'false'))}
 return {chapter:chapter.title,type:chapter.type,index:i,...state};
}
function cameraUpdate(force=false){
 if(cameraTouched&&!force)return;
 const rp=robot.scene.getObjectByName('PELVIS').getWorldPosition(new THREE.Vector3()),cp=cat.group.position.clone();cp.y+=.3;
 let target=rp.clone().lerp(cp,.4),size=Math.max(5.8,rp.distanceTo(cp)+3.7);
 if(cameraMode==='wide'){target.set(0,.7,0);size=14.5}
 if(cameraMode==='robot'){target.copy(rp);size=4.6}
 if(cameraMode==='cat'){target.copy(cp);size=2.6}
 const factor=force?1:.07;controls.target.lerp(target,factor);camera.position.lerp(target.clone().add(new THREE.Vector3(7,6.2,9)),factor);
 const aspect=stage.clientWidth/stage.clientHeight;if(aspect<.8&&cameraMode==='duo')size=Math.max(size,7.2);
 const half=size/2;camera.left=-half*aspect;camera.right=half*aspect;camera.top=half;camera.bottom=-half;camera.updateProjectionMatrix();
}
const timeText=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
function update(t,forceCamera=false){if(!ready)return;const state=poseStory(t);$('timeline').value=t;$('time-label').textContent=`${timeText(t)} / ${timeText(total)}`;$('play').textContent=playing?'Ⅱ':'▶';$('play').setAttribute('aria-label',playing?'Pause animation':'Play animation');cameraUpdate(forceCamera);controls.update();renderer.render(scene,camera);return state}
function resize(){renderer.setSize(stage.clientWidth,stage.clientHeight);if(ready)cameraUpdate(true)}new ResizeObserver(resize).observe(stage);resize();
$('play').onclick=()=>{playing=!playing;update(time)};$('restart').onclick=()=>{time=0;playing=true;cameraTouched=false;update(time,true)};
$('timeline').oninput=()=>{time=Number($('timeline').value);playing=false;cameraTouched=false;update(time,true)};
$('loop').onclick=()=>{loop=!loop;$('loop').setAttribute('aria-pressed',String(loop))};
for(const button of document.querySelectorAll('[data-camera]'))button.onclick=()=>{cameraMode=button.dataset.camera;cameraTouched=false;document.querySelectorAll('[data-camera]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));update(time,true)};
document.addEventListener('keydown',event=>{if(event.code==='Space'&&!/INPUT|SELECT|BUTTON/.test(document.activeElement.tagName)){event.preventDefault();playing=!playing;update(time)}});
try{
 const loader=new GLTFLoader();catalog=await fetch('motions/catalog.json').then(r=>r.json());
 const storyIds=new Set(['own_idle','own_crouch_down','own_crouch_hold','own_stand_up','own_deep_crouch','own_reach_right','own_reach_both','own_hands_high','own_turn_left90','own_turn_right90','own_turn180','own_forward_steps','own_backward_steps','own_left_steps','own_right_steps','own_run','own_jump_over']);
 const storyTests=catalog.tests.filter(entry=>storyIds.has(entry.id));
 const assets=await Promise.all(storyTests.map(async(entry,i)=>{const asset=await loader.loadAsync(entry.file);$('loading-text').textContent=`Preparing movement ${i+1} / ${storyTests.length}`;return [entry,asset]}));
 const base=assets.find(([entry])=>entry.id==='own_idle')[1],clips=new Map(assets.map(([entry,asset])=>[entry.id,asset.animations[0]]));
 robot=setupActor(base,clips,true);
 for(const [,asset] of assets)if(asset!==base)asset.scene.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();o.skeleton?.dispose()}});
 const feline=await loader.loadAsync('assets/k0_tech_01_d0_lod1.glb');cat=setupActor(feline,new Map(feline.animations.map(c=>[c.name,c])),false);
 buildStory();ready=true;$('loading').hidden=true;update(0,true);
 window.offShift={THREE,scene,camera,renderer,robot,cat,chapters,catalog,get duration(){return total},get time(){return time},get state(){return poseStory(time)},seek(t){time=clamp(t,0,total);playing=false;return update(time,true)},play(){playing=true},pause(){playing=false},captureBounds(){
  const result={};for(const [name,actor] of [['robot',robot],['cat',cat]]){const bounds=new THREE.Box3();const p=new THREE.Vector3();actor.group.updateMatrixWorld(true);actor.scene.traverse(mesh=>{if(!mesh.isSkinnedMesh)return;mesh.skeleton.update();for(let i=0;i<mesh.geometry.attributes.position.count;i++){mesh.getVertexPosition(i,p);p.applyMatrix4(mesh.matrixWorld);bounds.expandByPoint(p)}});result[name]={min:bounds.min.toArray(),max:bounds.max.toArray()}}return result;
 }};
}catch(error){$('loading-text').textContent='Unable to load the scene: '+error.message;console.error(error)}
let previous=performance.now();renderer.setAnimationLoop(now=>{const delta=clamp((now-previous)/1000,0,.06);previous=now;if(ready&&playing){time+=delta*Number($('speed').value);if(time>=total){if(loop)time%=total;else{time=total;playing=false}}update(time)}else if(ready){controls.update();renderer.render(scene,camera)}});
