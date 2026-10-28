import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
const $=id=>document.getElementById(id),stage=$('stage');
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;stage.prepend(renderer.domElement);
const scene=new T.Scene();scene.background=new T.Color('#13191d');const camera=new T.PerspectiveCamera(38,1,.02,150);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.maxPolarAngle=Math.PI*.49;
const room=new RoomEnvironment(),pmrem=new T.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();
scene.add(new T.HemisphereLight(0xdceeff,0x5d5141,2));const sun=new T.DirectionalLight(0xffe1b3,3);sun.position.set(3,6,4);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-12,right:12,top:12,bottom:-12});sun.shadow.normalBias=.002;scene.add(sun);
const floor=new T.Mesh(new T.PlaneGeometry(150,150),new T.MeshStandardMaterial({color:'#243139',roughness:.9}));floor.rotation.x=-Math.PI/2;floor.receiveShadow=true;floor.position.y=-.002;scene.add(floor);scene.add(new T.GridHelper(100,200,0x48616a,0x2c3c43));
const holder=new T.Group();scene.add(holder);const loader=new GLTFLoader();let generated,original,active,mixer,action,helper,source,time=0,playing=true,duration=3.8333333,mode='generated',lastFollow=new T.Vector3();
let line,pointCloud;const sourceGroup=new T.Group();sourceGroup.visible=false;scene.add(sourceGroup);const sourceOffset=new T.Vector3(1.9,0,0);
function view(name='hero') {const p=active?active.getObjectByName('PELVIS').getWorldPosition(new T.Vector3()):new T.Vector3(0,1.1,0);p.y=1.1;controls.target.copy(p);const offsets={hero:[3.5,1.7,5],front:[0,.4,5.8],side:[5.8,.4,0],wide:[4,2,8]};camera.position.copy(p).add(new T.Vector3(...offsets[name]));controls.update();lastFollow.copy(p)}
function sourcePose(){if(!source)return;const f=Math.max(0,Math.min(source.frames-1,Math.floor(time*source.fps)));const ps=source.positions[f],flat=[];for(let i=0;i<ps.length;i++){const parent=source.parents[source.body_names[i]],j=source.body_names.indexOf(parent);if(j>=0)flat.push(...ps[i],...ps[j])}line.geometry.setAttribute('position',new T.Float32BufferAttribute(flat,3));line.geometry.computeBoundingSphere();pointCloud.geometry.setAttribute('position',new T.Float32BufferAttribute(ps.flat(),3));pointCloud.geometry.computeBoundingSphere();sourceGroup.position.copy(sourceOffset);}
function pose(){if(!action)return;action.enabled=true;action.paused=false;mixer.setTime(Math.min(time,duration));holder.position.set(0,0,0);if(mode==='original')holder.position.z=.55*time;holder.updateMatrixWorld(true);helper.updateMatrixWorld(true);sourcePose();$('time').value=time;$('readout').textContent=`${time.toFixed(2)} / ${duration.toFixed(2)} s`;if($('follow').checked){const p=active.getObjectByName('PELVIS').getWorldPosition(new T.Vector3());p.y=1.1;const delta=p.clone().sub(lastFollow);camera.position.add(delta);controls.target.add(delta);lastFollow.copy(p)}else{lastFollow.copy(active.getObjectByName('PELVIS').getWorldPosition(new T.Vector3()));lastFollow.y=1.1}}
function select(value){mode=value;if(active)holder.remove(active);if(helper){scene.remove(helper);helper.dispose()}const asset=mode==='generated'?generated:original;active=asset.scene;holder.add(active);mixer=new T.AnimationMixer(active);const clip=mode==='generated'?asset.animations[0]:asset.animations.find(c=>c.name==='Heavy_Walk_Cycle');if(!clip)throw Error('Missing animation');duration=clip.duration;action=mixer.clipAction(clip);action.setLoop(T.LoopOnce,1);action.clampWhenFinished=true;action.play();time=0;helper=new T.SkeletonHelper(active);helper.visible=$('skeleton').checked;scene.add(helper);$('time').max=duration;pose();view();$('status').textContent=mode==='generated'?`MotionBricks G1 → C08 · ${source.frames} frames · experimental`:'Original C08 authored walk · 0.55 m/s';}
function resize(){renderer.setSize(stage.clientWidth,stage.clientHeight);camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix()}new ResizeObserver(resize).observe(stage);resize();view();
$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Pause':'Play';if(playing&&time>=duration)time=0};$('restart').onclick=()=>{time=0;playing=true;$('play').textContent='Pause';pose()};$('time').oninput=()=>{playing=false;$('play').textContent='Play';time=Number($('time').value);pose()};$('mode').onchange=()=>select($('mode').value);$('skeleton').onchange=()=>helper.visible=$('skeleton').checked;$('source').onchange=()=>sourceGroup.visible=$('source').checked;$('wire').onchange=()=>{for(const asset of [generated,original])asset.scene.traverse(o=>{if(o.isMesh)for(const m of (Array.isArray(o.material)?o.material:[o.material]))m.wireframe=$('wire').checked})};for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>view(b.dataset.view);

let catalog={tests:[]},selectedTest='baseline',loadToken=0;
function disposeAsset(asset){asset?.scene.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const material of Array.isArray(o.material)?o.material:[o.material])material.dispose();o.skeleton?.dispose()}})}
async function loadTest(id){
 const token=++loadToken;playing=false;$('status').textContent='Loading motion…';$('error').textContent='';
 const candidate=catalog.tests.find(c=>c.id===id)||null;
 if(id!=='baseline'&&!candidate)throw Error('Unknown motion test');
 const prefix=id==='baseline'?'../motions/own_idle/':`../motions/${candidate.directory}/`;
 const [asset,preview]=await Promise.all([loader.loadAsync(prefix+'c08-motionbricks-test.glb'),fetch(prefix+'g1-preview.json').then(r=>{if(!r.ok)throw Error('Missing source preview');return r.json()})]);
 if(token!==loadToken){disposeAsset(asset);return}
 const old=generated;generated=asset;source=preview;selectedTest=id;
 generated.scene.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false}});
 $('test').value=id;$('mode').value='generated';select('generated');disposeAsset(old);
 playing=true;$('play').textContent='Pause';
 $('status').textContent=`${candidate?.label||'Original neutral idle'} · ${duration.toFixed(2)} s · experimental`;
 $('description').textContent=`${candidate?.label||'Original neutral idle'} · ${duration.toFixed(2)} seconds. C08 keeps its own rig and geometry; G1 motion is adapted to its proportions.`;
 const own=candidate?.provenance_type==='original';
 $('provenance').textContent=own?'Original numeric G1 conditioning poses authored in this workspace. No NVIDIA sample motions used for this test. C08 geometry is user-owned; Models by jelaludo.':'Internal evaluation: this test uses bundled NVIDIA/Bones motion samples as conditioning. C08 geometry is user-owned; Models by jelaludo.';
 const flags=candidate?.review_flags||[];
 $('assessment').textContent=candidate?`Export checks: ${candidate.technical_validation}. ${flags.length?'Review findings: '+flags.join('; '):'No automatic limit flags; visual/contact review still required.'}`:'Select one of the 18 original-input tests above.';
 $('assessment').style.color=flags.length?'#edba77':'#a6b7bf';
 $('download-glb').href=prefix+'c08-motionbricks-test.glb';$('download-blend').href=prefix+'c08-motionbricks-test.blend';$('download-report').href=prefix+'validation-report.json';
 const url=new URL(location.href);if(id==='baseline')url.searchParams.delete('test');else url.searchParams.set('test',id);history.replaceState(null,'',url);
}
async function setupGallery(){
 const response=await fetch('../motions/catalog.json');if(!response.ok)return;catalog=await response.json();
 const groups=new Map();
 for(const test of catalog.tests){
  if(test.retarget!=='passed')continue;
  if(!groups.has(test.category)){const group=document.createElement('optgroup');group.label=test.category;groups.set(test.category,group);$('test').append(group)}
  const option=document.createElement('option');option.value=test.id;option.textContent=test.label+(test.review_flags?.length?' ⚑':'');groups.get(test.category).append(option);
 }
 $('test').onchange=()=>loadTest($('test').value).catch(e=>{$('error').textContent=e.message;console.error(e)});
 const requested=new URL(location.href).searchParams.get('test')||'own_idle';
 if(catalog.tests.some(c=>c.id===requested))await loadTest(requested);
}

try{[generated,original,source]=await Promise.all([loader.loadAsync('../motions/own_idle/c08-motionbricks-test.glb'),loader.loadAsync('../assets/c08_d0_lod1.glb'),fetch('../motions/own_idle/g1-preview.json').then(r=>r.json())]);for(const asset of [generated,original])asset.scene.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false}});line=new T.LineSegments(new T.BufferGeometry(),new T.LineBasicMaterial({color:'#e8b85b'}));pointCloud=new T.Points(new T.BufferGeometry(),new T.PointsMaterial({color:'#fff0bc',size:.035}));sourceGroup.add(line,pointCloud);select('generated');window.motionTest={scene,camera,renderer,get generated(){return generated},original,get active(){return active},get time(){return time},setTime(t){playing=false;time=t;pose()},select,view,loadTest,get catalog(){return catalog},get selectedTest(){return selectedTest}};await setupGallery();}catch(e){$('error').textContent=e.message;$('status').textContent='Unable to load';console.error(e)}
let previous=performance.now();renderer.setAnimationLoop(now=>{const dt=Math.max(0,Math.min((now-previous)/1000,.1));previous=now;if(playing&&action){time+=dt*Number($('speed').value);if(time>=duration){if($('repeat').checked)time=0;else{time=duration;playing=false;$('play').textContent='Play'}}pose()}controls.update();renderer.render(scene,camera)});
