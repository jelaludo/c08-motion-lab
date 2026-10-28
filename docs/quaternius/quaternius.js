import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
const $=id=>document.getElementById(id),stage=$('stage'),scene=new T.Scene();scene.background=new T.Color('#13191d');
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;renderer.shadowMap.enabled=true;stage.prepend(renderer.domElement);
const camera=new T.PerspectiveCamera(38,1,.03,160),orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.maxPolarAngle=Math.PI*.49;
const room=new RoomEnvironment(),pmrem=new T.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();scene.add(new T.HemisphereLight(0xdceeff,0x5d5141,2));
const sun=new T.DirectionalLight(0xffe1b3,3);sun.position.set(3,6,4);scene.add(sun);
const floor=new T.Mesh(new T.PlaneGeometry(150,150),new T.MeshStandardMaterial({color:'#243139',roughness:.9}));floor.rotation.x=-Math.PI/2;floor.position.y=-.002;scene.add(floor,new T.GridHelper(100,200,0x48616a,0x2c3c43));
const actor=new T.Group(),sourceActor=new T.Group();sourceActor.position.x=2.7;sourceActor.visible=false;scene.add(actor,sourceActor);
const keys=new Set(),position=new T.Vector3(),lastFollow=new T.Vector3();let gltf,source,mixer,sourceMixer,actions={},sourceActions={},current,currentSource,name='',mode='preview',playing=true,elapsed=0,demoTime=0,crouched=false,seated=false,sequence=[],oneShot=false,helper,groundVertices=[];
const pretty=n=>n.replaceAll('_',' '),loop=n=>n.endsWith('_Loop');
const locomotion=new Set(['Walk_Loop','Jog_Fwd_Loop','Sprint_Loop']);
function view(){const p=position.clone().add(new T.Vector3(sourceActor.visible?1.1:0,1.05,0));orbit.target.copy(p);camera.position.copy(p).add(new T.Vector3(3.5,1.7,6.5));orbit.update();lastFollow.copy(position)}
function choose(n,{fade=.25,sync=false,force=false}={}){
 if(name===n&&!force)return;const old=current,oldSource=currentSource,phase=sync&&old?(old.time/old.getClip().duration)%1:0;
 current=actions[n];currentSource=sourceActions[n];if(!current)throw Error('Missing clip '+n);
 for(const a of [current,currentSource]){if(!a)continue;a.reset();a.enabled=true;a.setEffectiveTimeScale(1);a.setEffectiveWeight(1);a.setLoop(loop(n)?T.LoopRepeat:T.LoopOnce,loop(n)?Infinity:1);a.clampWhenFinished=true;a.time=phase*a.getClip().duration;a.play()}
 if(old&&old!==current){old.fadeOut(fade);current.fadeIn(fade)}if(oldSource&&oldSource!==currentSource){oldSource.fadeOut(fade);currentSource?.fadeIn(fade)}
 name=n;elapsed=0;$('clip').value=n;$('timeline').max=current.getClip().duration;$('clip-info').textContent=`${pretty(n)} · ${current.getClip().duration.toFixed(2)} s · ${loop(n)?'repeating cycle':'one-shot / transition'}`;
}
function setMode(value){mode=value;$('mode').value=value;keys.clear();sequence=[];oneShot=false;crouched=false;seated=false;demoTime=0;playing=true;$('play').textContent='Pause';position.set(0,0,0);actor.rotation.y=0;choose('Idle_Loop',{force:true});view()}
function playSequence(names){sequence=[...names];oneShot=true;choose(sequence.shift(),{force:true})}
function desiredMovement(){const d=new T.Vector3(Number(keys.has('KeyD'))-Number(keys.has('KeyA')),0,Number(keys.has('KeyS'))-Number(keys.has('KeyW'))).normalize();const fast=keys.has('ShiftLeft')||keys.has('ShiftRight');return {d,fast,moving:d.lengthSq()>0}}
function updateController(dt){
 if(mode==='demo'){demoTime+=dt;const phase=demoTime%18,n=phase<3?'Idle_Loop':phase<6?'Walk_Loop':phase<9?'Jog_Fwd_Loop':phase<12?'Sprint_Loop':phase<15?'Walk_Loop':'Idle_Loop';choose(n,{sync:locomotion.has(name)&&locomotion.has(n)});return}
 if(mode!=='keyboard')return;
 if(oneShot){if(elapsed>=current.getClip().duration){if(sequence.length)choose(sequence.shift());else{oneShot=false;if(name==='Sitting_Enter'){seated=true;choose('Sitting_Idle_Loop')}else if(name==='Sitting_Exit'){seated=false;choose('Idle_Loop')}else choose(seated?'Sitting_Idle_Loop':crouched?'Crouch_Idle_Loop':'Idle_Loop')}}return}
 if(seated)return;
 const {d,fast,moving}=desiredMovement(),n=crouched?(moving?'Crouch_Fwd_Loop':'Crouch_Idle_Loop'):moving?(fast?'Sprint_Loop':'Walk_Loop'):'Idle_Loop';choose(n,{sync:locomotion.has(name)&&locomotion.has(n)});
 if(moving){const target=Math.atan2(d.x,d.z),angle=T.MathUtils.euclideanModulo(target-actor.rotation.y+Math.PI,Math.PI*2)-Math.PI;actor.rotation.y+=angle*Math.min(1,dt*10);position.addScaledVector(d,dt*(crouched?.6:fast?3.6:1.1));position.x=T.MathUtils.clamp(position.x,-30,30);position.z=T.MathUtils.clamp(position.z,-30,30)}
}
$('mode').onchange=()=>setMode($('mode').value);$('clip').onchange=()=>{mode='preview';$('mode').value=mode;keys.clear();sequence=[];oneShot=false;choose($('clip').value,{force:true})};
$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Pause':'Play'};$('restart').onclick=()=>{choose(name,{force:true});playing=true;$('play').textContent='Pause'};
$('timeline').oninput=()=>{mode='preview';$('mode').value=mode;keys.clear();oneShot=false;sequence=[];playing=false;$('play').textContent='Play';current.time=Number($('timeline').value);if(currentSource)currentSource.time=current.time;elapsed=current.time;mixer.update(0);sourceMixer.update(0)};
$('source').onchange=()=>{sourceActor.visible=$('source').checked;view()};$('skeleton').onchange=()=>{if(helper)helper.visible=$('skeleton').checked};$('camera').onclick=view;
window.addEventListener('keydown',e=>{if(e.target.closest('input,select,textarea,button,[contenteditable="true"]')||e.ctrlKey||e.altKey||e.metaKey||!gltf)return;if(e.code==='Escape'){setMode('preview');return}if(mode!=='keyboard')return;
 const mapping={Digit1:'Roll',Digit2:'Dance_Loop',Digit3:'Interact',Digit4:'PickUp_Table',Digit5:'Fixing_Kneeling',Digit6:'Punch_Jab',Digit7:'Punch_Cross'};
 if(!['KeyW','KeyA','KeyS','KeyD','ShiftLeft','ShiftRight','Space','KeyC','KeyE',...Object.keys(mapping)].includes(e.code))return;e.preventDefault();keys.add(e.code);if(e.repeat||oneShot)return;
 if(e.code==='Space'&&!seated)playSequence(['Jump_Start','Jump_Loop','Jump_Land']);else if(e.code==='KeyC'&&!seated)crouched=!crouched;else if(e.code==='KeyE')playSequence([seated?'Sitting_Exit':'Sitting_Enter']);else if(mapping[e.code]&&!seated){playSequence([mapping[e.code]]);if(loop(mapping[e.code]))sequence=['Idle_Loop']}
});
window.addEventListener('keyup',e=>keys.delete(e.code));window.addEventListener('blur',()=>keys.clear());document.addEventListener('visibilitychange',()=>{if(document.hidden)keys.clear()});
function resize(){renderer.setSize(stage.clientWidth,stage.clientHeight);camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix()}new ResizeObserver(resize).observe(stage);resize();view();
try{
 const loader=new GLTFLoader();[gltf,source]=await Promise.all([loader.loadAsync('c08-quaternius.glb'),loader.loadAsync('quaternius-source.glb')]);actor.add(gltf.scene);sourceActor.add(source.scene);mixer=new T.AnimationMixer(gltf.scene);sourceMixer=new T.AnimationMixer(source.scene);
 for(const clip of gltf.animations){const n=clip.name.replace(/^Q_/,'');actions[n]=mixer.clipAction(clip);const original=source.animations.find(c=>c.name===n);if(original)sourceActions[n]=sourceMixer.clipAction(original);const option=document.createElement('option');option.value=n;option.textContent=pretty(n);$('clip').append(option)}
 gltf.scene.traverse(o=>{if(o.isSkinnedMesh){o.frustumCulled=false;const skin=o.geometry.attributes.skinIndex;for(let i=0;i<o.geometry.attributes.position.count;i++)groundVertices.push({mesh:o,index:i})}});helper=new T.SkeletonHelper(gltf.scene);helper.visible=false;scene.add(helper);
 choose('Idle_Loop');window.quaterniusTest={scene,actor,camera,renderer,actions,sourceActions,choose,setMode,playSequence,get name(){return name},get mode(){return mode},get position(){return position},get keys(){return keys},get oneShot(){return oneShot},get elapsed(){return elapsed},get playing(){return playing},get current(){return current},get source(){return sourceActor}};
}catch(e){$('error').textContent=e.message;console.error(e)}
const v=new T.Vector3();let previous=performance.now();renderer.setAnimationLoop(now=>{const dt=Math.min(.05,Math.max(0,(now-previous)/1000));previous=now;if(mixer){if(playing){elapsed+=dt;updateController(dt);mixer.update(dt);sourceMixer.update(dt)}actor.position.copy(position);actor.updateMatrixWorld(true);
 // A blend can lower armor between individually grounded clips. Lift the complete actor only.
 let low=Infinity;gltf.scene.traverse(o=>{if(o.isSkinnedMesh)o.skeleton.update()});for(const {mesh,index} of groundVertices){mesh.getVertexPosition(index,v);v.applyMatrix4(mesh.matrixWorld);low=Math.min(low,v.y)}if(low<.006)actor.position.y+=.006-low;
 sourceActor.position.z=position.z;sourceActor.position.x=position.x+2.7;sourceActor.rotation.y=actor.rotation.y;
 const delta=position.clone().sub(lastFollow);camera.position.add(delta);orbit.target.add(delta);lastFollow.copy(position);$('timeline').value=current.time;$('readout').textContent=`${current.time.toFixed(2)} / ${current.getClip().duration.toFixed(2)} s`;$('status').textContent=`${mode==='keyboard'?'Keyboard · ':mode==='demo'?'Blend demo · ':''}${pretty(name)}`;
 }orbit.update();renderer.render(scene,camera)});
