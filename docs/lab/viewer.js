import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';

const $=id=>document.getElementById(id),stage=$('stage');
const config=window.motionLabConfig||{catalog:'../motions/catalog.json',assetRoot:'../',authored:'../assets/c08_d0_lod1.glb'};
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;stage.prepend(renderer.domElement);
const scene=new T.Scene();scene.background=new T.Color('#13191d');
const camera=new T.PerspectiveCamera(38,1,.02,150),controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.maxPolarAngle=Math.PI*.49;
const room=new RoomEnvironment(),pmrem=new T.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();
scene.add(new T.HemisphereLight(0xdceeff,0x5d5141,2));const sun=new T.DirectionalLight(0xffe1b3,3);sun.position.set(3,6,4);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-12,right:12,top:12,bottom:-12});sun.shadow.normalBias=.002;scene.add(sun);
const floor=new T.Mesh(new T.PlaneGeometry(150,150),new T.MeshStandardMaterial({color:'#243139',roughness:.9}));floor.rotation.x=-Math.PI/2;floor.receiveShadow=true;floor.position.y=-.002;scene.add(floor);scene.add(new T.GridHelper(100,200,0x48616a,0x2c3c43));
const holder=new T.Group();scene.add(holder);const loader=new GLTFLoader();
const sourceGroup=new T.Group();sourceGroup.visible=false;sourceGroup.position.x=2;scene.add(sourceGroup);
const line=new T.LineSegments(new T.BufferGeometry(),new T.LineBasicMaterial({color:'#e8b85b'})),points=new T.Points(new T.BufferGeometry(),new T.PointsMaterial({color:'#fff0bc',size:.035}));sourceGroup.add(line,points);
let catalog={tests:[]},original,generated,active,mixer,action,helper,source=null,currentEntry=null,selectedTest='',lastGenerated='';
let time=0,duration=1,playing=false,continuous=false,advancing=false,loadToken=0,shuffleBag=[],transition=null;
const lastFollow=new T.Vector3(),playlistHistory=[];
const authoredMeta={Standby_Idle:{label:'Standby idle',loop:true},Heavy_Walk_Cycle:{label:'Heavy walk',speed:.55,loop:true},Carry_Walk_Cycle:{label:'Carry walk',speed:.36,loop:true},Work_Inspect:{label:'Inspect',loop:false},Crouch_Service:{label:'Service crouch',loop:false}};
const entryUrl=file=>config.assetRoot+file;
function disposeAsset(asset){asset?.scene.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const material of Array.isArray(o.material)?o.material:[o.material])material.dispose();o.skeleton?.dispose()}})}
function view(name='hero'){
 const p=active?.getObjectByName('PELVIS')?.getWorldPosition(new T.Vector3())||new T.Vector3(0,1.1,0);p.y=1.05;controls.target.copy(p);
 const offsets={hero:[3.5,1.7,5],front:[0,.4,5.8],side:[5.8,.4,0],wide:[4,2,8]};camera.position.copy(p).add(new T.Vector3(...offsets[name]));controls.update();lastFollow.copy(p);
}
function capturePose(){const pose=new Map();active?.traverse(o=>{if(o.isBone)pose.set(o.name,{p:o.position.clone(),q:o.quaternion.clone()})});return pose}
function sourcePose(){
 if(!source)return;
 const frame=Math.max(0,Math.min(source.frames-1,Math.floor(time*source.fps))),ps=source.positions[frame],segments=[];
 for(let i=0;i<ps.length;i++){const parent=source.body_names.indexOf(source.parents[source.body_names[i]]);if(parent>=0)segments.push(...ps[i],...ps[parent])}
 line.geometry.setAttribute('position',new T.Float32BufferAttribute(segments,3));line.geometry.computeBoundingSphere();points.geometry.setAttribute('position',new T.Float32BufferAttribute(ps.flat(),3));points.geometry.computeBoundingSphere();
}
function pose(){
 if(!action)return;
 time=Math.max(0,Math.min(time,duration));action.enabled=true;action.paused=false;mixer.setTime(time);
 if(continuous){const motion=active.getObjectByName('MOTION');if(motion){motion.position.x=0;motion.position.z=0}}
 if(transition){
  const u=Math.min(1,transition.elapsed/transition.duration),weight=u*u*(3-2*u);
  active.traverse(o=>{if(!o.isBone)return;const previous=transition.from.get(o.name);if(previous){o.position.lerpVectors(previous.p,o.position,weight);o.quaternion.slerpQuaternions(previous.q,o.quaternion,weight)}});
  if(u>=1)transition=null;
 }
 holder.position.set(0,0,0);if(currentEntry?.kind==='authored'&&!continuous)holder.position.z=(authoredMeta[currentEntry.authoredClip]?.speed||0)*time;
 holder.updateMatrixWorld(true);helper?.updateMatrixWorld(true);sourcePose();
 $('time').value=time;$('readout').textContent=`${time.toFixed(2)} / ${duration.toFixed(2)} s`;
 const p=active.getObjectByName('PELVIS')?.getWorldPosition(new T.Vector3())||new T.Vector3();p.y=1.05;
 if($('follow').checked){const delta=p.clone().sub(lastFollow);camera.position.add(delta);controls.target.add(delta)}lastFollow.copy(p);
}
function wireframe(){for(const asset of [generated,original])asset?.scene.traverse(o=>{if(o.isMesh)for(const material of Array.isArray(o.material)?o.material:[o.material])material.wireframe=$('wire').checked})}
function prepare(asset,clip,preserveView){
 if(mixer){mixer.stopAllAction();mixer.uncacheRoot(active)}
 if(active)holder.remove(active);if(helper){scene.remove(helper);helper.dispose()}
 active=asset.scene;holder.add(active);active.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false}});
 mixer=new T.AnimationMixer(active);duration=clip.duration;action=mixer.clipAction(clip);action.setLoop(T.LoopOnce,1);action.clampWhenFinished=true;action.play();time=0;
 helper=new T.SkeletonHelper(active);helper.visible=$('skeleton').checked;scene.add(helper);$('time').max=duration;pose();if(!preserveView)view();wireframe();
}
function authoredEntries(){return original.animations.map(clip=>({id:'authored:'+clip.name,label:'C08 authored · '+(authoredMeta[clip.name]?.label||clip.name),category:'Original C08 animations',kind:'authored',authoredClip:clip.name,duration_s:clip.duration}))}
function entries(){return [...catalog.tests.filter(c=>c.retarget==='passed'||c.kind==='video_mocap'),...authoredEntries()]}
function updateInformation(entry){
 const kind=entry.kind||'motionbricks';$('description').textContent=kind==='authored'?`${entry.label} · ${duration.toFixed(2)} seconds. Original C08 animation, independent of MotionBricks.`:kind==='video_mocap'?`${entry.label} · ${duration.toFixed(2)} seconds. Direct video recovery adapted to C08; this is not MotionBricks-generated motion.`:`${entry.label} · ${duration.toFixed(2)} seconds. MotionBricks G1 motion adapted to C08’s proportions.`;
 $('provenance').textContent=kind==='authored'?'Original C08 geometry and authored animation by jelaludo.':kind==='video_mocap'?'User-provided reference motion → GEM-X SOMA recovery → direct C08 retarget. Source videos remain local. Recovered occluded joints are estimates.':entry.provenance_type==='bundled_sample'?'Local internal evaluation only: NVIDIA/Bones sample motion was used as conditioning. C08 is an original asset by jelaludo.':'Original numerical conditioning; no NVIDIA/Bones sample motions used. C08 is an original asset by jelaludo.';
 const flags=entry.review_flags||[];$('assessment').textContent=flags.length?'Review findings: '+flags.join('; '):'Playable experiment. Visual and contact review still required.';$('assessment').style.color=flags.length?'#edba77':'#a6b7bf';
 $('status').textContent=(continuous?'Continuous · ':'')+entry.label+' · '+duration.toFixed(2)+' s';
 $('mode').value=kind==='authored'?'original':'generated';$('test').value=entry.id;
 sourceGroup.visible=!!source&&$('source').checked;$('source').disabled=!source;
 const base=entry.file?entry.file.slice(0,entry.file.lastIndexOf('/')+1):'';
 $('download-glb').href=kind==='authored'?config.authored:entryUrl(entry.file);
 $('download-blend').href=kind==='authored'?'https://jelaludo.github.io/SentryTowers_A6/source/blender/a6-c08-worker.blend':entryUrl(entry.blend_file||base+'c08-motionbricks-test.blend');
 $('download-blend').hidden=entry.has_blend===false;
 $('download-report').href=kind==='authored'?(config.authoredReport||config.assetRoot+'assets/c08-worker-source.json'):entryUrl(entry.report_file||base+'validation-report.json');
 const url=new URL(location.href);url.searchParams.set('test',entry.id);window.history.replaceState(null,'',url);
}
async function loadTest(id,options={}){
 const token=++loadToken,entry=entries().find(c=>c.id===id);
 if(!entry)throw Error('Unknown motion: '+id);
 const from=options.continuous?capturePose():null;playing=false;$('status').textContent='Loading '+entry.label+'…';$('error').textContent='';
 let asset,preview=null;
 if(entry.kind==='authored')asset=original;
 else{
  const base=entry.file.slice(0,entry.file.lastIndexOf('/')+1),previewFile=entry.preview_file||base+'g1-preview.json';
  [asset,preview]=await Promise.all([loader.loadAsync(entryUrl(entry.file)),fetch(entryUrl(previewFile)).then(r=>{if(!r.ok)throw Error('Source skeleton preview unavailable');return r.json()})]);
 }
 if(token!==loadToken||(options.continuous&&!continuous)){if(asset!==original)disposeAsset(asset);return false}
 const old=generated;source=preview;currentEntry=entry;selectedTest=id;if(asset!==original){generated=asset;lastGenerated=id}
 transition=from?{from,elapsed:0,duration:.65}:null;
 const clip=entry.kind==='authored'?asset.animations.find(c=>c.name===entry.authoredClip):asset.animations[0];
 prepare(asset,clip,!!options.continuous);if(old&&old!==asset&&old!==original)disposeAsset(old);
 if(asset===original)generated=null;
 updateInformation(entry);playing=options.play!==false;$('play').textContent=playing?'Pause':'Play';
 playlistHistory.push({id,time:performance.now()});if(playlistHistory.length>200)playlistHistory.shift();return true;
}
function setContinuous(enabled){
 continuous=enabled;shuffleBag=[];$('continuous').setAttribute('aria-pressed',String(enabled));$('continuous').textContent=enabled?'Continuous · On':'Continuous';
 $('continuous-note').textContent=enabled?'Shuffled playback with brief pose blends. Clips are centred for review; this is not a newly generated routine.':'Randomly plays each available motion before repeating. Selecting or scrubbing a motion stops the playlist.';
 if(!enabled){loadToken++;transition=null;advancing=false}
 else{pose();advanceContinuous()}
}
function nextRandom(){
 const choices=entries().map(e=>e.id);
 if(!shuffleBag.length){shuffleBag=[...choices];for(let i=shuffleBag.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[shuffleBag[i],shuffleBag[j]]=[shuffleBag[j],shuffleBag[i]]}if(shuffleBag.at(-1)===selectedTest&&shuffleBag.length>1)[shuffleBag[0],shuffleBag[shuffleBag.length-1]]=[shuffleBag.at(-1),shuffleBag[0]]}
 return shuffleBag.pop();
}
async function advanceContinuous(){
 if(!continuous||advancing)return;advancing=true;
 try{await loadTest(nextRandom(),{continuous:true})}catch(error){$('error').textContent='Playlist stopped: '+error.message;setContinuous(false);console.error(error)}finally{advancing=false}
}
function populate(){
 $('test').replaceChildren();const groups=new Map();
 for(const entry of entries()){const category=entry.category||'Video motion capture';if(!groups.has(category)){const group=document.createElement('optgroup');group.label=category;groups.set(category,group);$('test').append(group)}const option=document.createElement('option');option.value=entry.id;option.textContent=entry.label+(entry.review_flags?.length?' ⚑':'');groups.get(category).append(option)}
 $('gallery-count').textContent=`${catalog.tests.length} experiments + ${original.animations.length} original C08 actions`;
}
function manual(){if(continuous)setContinuous(false)}
$('continuous').onclick=()=>setContinuous(!continuous);
$('play').onclick=()=>{playing=!playing;if(playing&&time>=duration){if(continuous){advanceContinuous();return}time=0}$('play').textContent=playing?'Pause':'Play'};
$('restart').onclick=()=>{time=0;transition=null;playing=true;$('play').textContent='Pause';pose()};
$('time').oninput=()=>{manual();playing=false;time=Number($('time').value);$('play').textContent='Play';pose()};
$('test').onchange=()=>{manual();loadTest($('test').value).catch(error=>{$('error').textContent=error.message;console.error(error)})};
$('mode').onchange=()=>{manual();loadTest($('mode').value==='original'?'authored:Heavy_Walk_Cycle':lastGenerated||catalog.tests[0].id).catch(error=>{$('error').textContent=error.message;console.error(error)})};
$('skeleton').onchange=()=>{if(helper)helper.visible=$('skeleton').checked};$('source').onchange=()=>sourceGroup.visible=!!source&&$('source').checked;$('wire').onchange=wireframe;
for(const button of document.querySelectorAll('[data-view]'))button.onclick=()=>view(button.dataset.view);
function resize(){renderer.setSize(stage.clientWidth,stage.clientHeight);camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix()}new ResizeObserver(resize).observe(stage);resize();view();
try{
 [catalog,original]=await Promise.all([fetch(config.catalog).then(r=>{if(!r.ok)throw Error('Motion catalog unavailable');return r.json()}),loader.loadAsync(config.authored)]);
 populate();const requested=new URL(location.href).searchParams.get('test'),id=entries().some(e=>e.id===requested)?requested:catalog.tests[0].id;
 await loadTest(id);
 window.motionTest={scene,camera,renderer,original,get generated(){return generated},get active(){return active},get time(){return time},get selectedTest(){return selectedTest},get catalog(){return catalog},get continuous(){return continuous},get history(){return playlistHistory},get transition(){return transition},get duration(){return duration},setTime(t){manual();playing=false;time=t;pose()},select(value){return loadTest(value==='original'?'authored:Heavy_Walk_Cycle':lastGenerated||catalog.tests[0].id)},view,loadTest,setContinuous,advanceContinuous,entries};
}catch(error){$('error').textContent=error.message;$('status').textContent='Unable to load';console.error(error)}
let previous=performance.now();renderer.setAnimationLoop(now=>{
 const delta=Math.max(0,Math.min((now-previous)/1000,.1));previous=now;
 if(playing&&action){time+=delta*Number($('speed').value);if(transition)transition.elapsed+=delta;
  if(time>=duration){time=duration;if(continuous){pose();advanceContinuous()}else if($('repeat').checked)time=0;else{playing=false;$('play').textContent='Play'}}pose();
 }
 controls.update();renderer.render(scene,camera);
});
