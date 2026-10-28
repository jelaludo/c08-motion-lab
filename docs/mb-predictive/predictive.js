import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
const $=id=>document.getElementById(id),stage=$('stage'),scene=new T.Scene();scene.background=new T.Color('#10191e');
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;stage.prepend(renderer.domElement);
const camera=new T.PerspectiveCamera(40,1,.03,120),orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.maxPolarAngle=Math.PI*.49;
const room=new RoomEnvironment(),pmrem=new T.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();scene.add(new T.HemisphereLight(0xdceeff,0x5d5141,2));const light=new T.DirectionalLight(0xffe1b3,3);light.position.set(3,6,4);scene.add(light);
const floor=new T.Mesh(new T.PlaneGeometry(100,100),new T.MeshStandardMaterial({color:'#243139',roughness:.9}));floor.rotation.x=-Math.PI/2;floor.position.y=-.004;scene.add(floor,new T.GridHelper(60,120,0x48616a,0x2c3c43));
const aiGroup=new T.Group(),linearGroup=new T.Group(),ghostGroup=new T.Group(),pathGroup=new T.Group();linearGroup.position.x=3.4;scene.add(aiGroup,linearGroup,ghostGroup,pathGroup);
let catalog,trace,report,validation,asset,baseline,mixer,baselineMixer,action,baselineAction,time=0,duration=1,step=1,playing=false,wait=0,token=0,currentId='',currentBase='',ghostSets=[],busy=false;
const history=[],caseBases=new Map();
function view(){const centre=$('compare').checked&&step===3?1.7:0;orbit.target.set(centre,1.05,.7);const offset=new T.Vector3(4,2.15,6.6),width=centre?6.4:3.2;offset.multiplyScalar(Math.max(1,width/(2*Math.tan(T.MathUtils.degToRad(camera.fov/2))*offset.length()*camera.aspect)));camera.position.copy(orbit.target).add(offset);orbit.update()}
function disposeAsset(g){g?.scene.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();o.skeleton?.dispose()}})}
function clear(group){for(const o of [...group.children]){group.remove(o);o.traverse(c=>{c.geometry?.dispose();c.material?.dispose()})}}
function skeleton(points,color,opacity){const lines=[];for(let i=0;i<points.length;i++){const p=trace.body_names.indexOf(trace.parents[trace.body_names[i]]);if(p>=0)lines.push(...points[i],...points[p])}const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(lines,3));const line=new T.LineSegments(g,new T.LineBasicMaterial({color,transparent:true,opacity,depthTest:false}));line.renderOrder=5;return line}
function displayPoint(p){return [p[1]*trace.display_scale,p[2]*trace.display_scale+trace.display_pelvis_offset,p[0]*trace.display_scale]}
function makeGuides(){
 clear(ghostGroup);clear(pathGroup);ghostSets=[];
 for(const [index,s] of trace.skeletons_g1_zup.entries()){
  const group=new T.Group();for(const [i,p] of s.context.entries())group.add(skeleton(p.map(displayPoint),0x73cfcd,.25+i*.2));ghostGroup.add(group);
  const target=new T.Group();for(const p of s.target)target.add(skeleton(p.map(displayPoint),0xe8bc68,.9));ghostGroup.add(target);
  const root=s.target[0][trace.body_names.indexOf('pelvis')],p=displayPoint(root),ring=new T.Mesh(new T.RingGeometry(.18,.22,32),new T.MeshBasicMaterial({color:0xe8bc68,side:T.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.set(p[0],.02,p[2]);target.add(ring);ghostSets.push({context:group,target});
 }
 const points=report.root_path.map(p=>new T.Vector3(...p));const path=new T.Line(new T.BufferGeometry().setFromPoints(points),new T.LineBasicMaterial({color:0x73cfcd}));pathGroup.add(path);
 const goals=trace.metadata.segments.map(s=>displayPoint(s.skeleton||trace.skeletons_g1_zup[s.index].target[0][trace.body_names.indexOf('pelvis')]));const start=report.root_path[0];const straight=[new T.Vector3(start[0]+3.4,.02,start[2]),...goals.map(p=>new T.Vector3(p[0]+3.4,.02,p[2]))];pathGroup.add(new T.Line(new T.BufferGeometry().setFromPoints(straight),new T.LineBasicMaterial({color:0xe8bc68})));
}
function setStep(value){step=value;for(const b of document.querySelectorAll('[data-step]'))b.setAttribute('aria-pressed',String(Number(b.dataset.step)===step));if(step<3){playing=false;time=0;$('play').textContent='Play prediction'}apply();view()}
function apply(){
 if(!action)return;action.enabled=true;action.paused=false;baselineAction.enabled=true;baselineAction.paused=false;mixer.setTime(time);baselineMixer.setTime(time);
 aiGroup.updateMatrixWorld(true);linearGroup.updateMatrixWorld(true);linearGroup.visible=step===3&&$('compare').checked;
 for(const g of [asset,baseline])g.scene.traverse(o=>{if(o.isMesh)for(const material of Array.isArray(o.material)?o.material:[o.material]){material.transparent=step<3;material.opacity=step<3?.3:1;material.depthWrite=step===3}});
 const index=Math.max(0,trace.metadata.segments.findLastIndex(s=>time*30>=s.start_frame)),segment=trace.metadata.segments[index];
 for(const [i,g] of ghostSets.entries()){g.context.visible=$('ghosts').checked&&i===index;g.target.visible=$('ghosts').checked&&step>=2&&(i===index||step===2)}
 pathGroup.visible=step===3&&$('paths').checked;pathGroup.children[1].visible=$('compare').checked;
 $('timeline').value=time;$('readout').textContent=`${time.toFixed(2)} / ${duration.toFixed(2)} s`;
 $('step-text').textContent=step===1?'Four recent G1 poses describe the starting movement. The first request begins from four identical neutral poses; later chained requests use the actual preceding prediction.':step===2?'One target pose specifies arrival position, heading and posture. It does not prescribe the stepping between them. Amber shows the requested G1 target, scaled for display.':'The AI predicts the intervening movement and duration. Compare the generated steps with interpolation that only slides the same joints between endpoints.';
 $('segment').textContent=`Prediction ${index+1} / ${trace.metadata.segments.length} · ${segment.frames} frames · context ${index?'from preceding generated motion':'from original neutral stance'} · ${(segment.inference_seconds*1000).toFixed(1)} ms GPU inference`;
 $('status').textContent=(step===3?'Generated playback':step===2?'Requested destination':'Recent context')+' · '+currentId;
}
async function loadCase(id,base){
 base=base||caseBases.get(id)||'cases/'+id+'/';caseBases.set(id,base);
 const ticket=++token;playing=false;$('status').textContent='Loading experiment…';$('error').textContent='';const loader=new GLTFLoader();
 const fetchJSON=file=>fetch(base+file).then(r=>{if(!r.ok)throw Error('Missing experiment data');return r.json()});
 const [g,b,tr,r,v]=await Promise.all([loader.loadAsync(base+'c08-motionbricks-test.glb'),loader.loadAsync(base+'linear/c08-motionbricks-test.glb'),fetchJSON('prediction-trace.json'),fetchJSON('retarget-report.json'),fetchJSON('validation-report.json')]);
 if(ticket!==token){disposeAsset(g);disposeAsset(b);return}
 clear(ghostGroup);clear(pathGroup);aiGroup.clear();linearGroup.clear();disposeAsset(asset);disposeAsset(baseline);asset=g;baseline=b;trace=tr;report=r;validation=v;currentId=id;currentBase=base;
 aiGroup.add(g.scene);linearGroup.add(b.scene);for(const a of [g,b])a.scene.traverse(o=>{if(o.isMesh)o.frustumCulled=false});mixer=new T.AnimationMixer(g.scene);baselineMixer=new T.AnimationMixer(b.scene);action=mixer.clipAction(g.animations[0]);baselineAction=baselineMixer.clipAction(b.animations[0]);for(const a of [action,baselineAction]){a.setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play()}
 duration=g.animations[0].duration;time=0;wait=0;$('timeline').max=duration;makeGuides();$('motion-duration').textContent=duration.toFixed(2)+' s';$('inference').textContent=(trace.metadata.inference_seconds*1000).toFixed(1)+' ms';
 const violations=trace.metadata.joint_limit_audit?.violations||[];$('findings').textContent=`Export: ${v.gltf_errors} glTF errors, ${v.gltf_warnings} warnings. ${violations.length?'Generated joint-limit findings: '+violations.length+'. ':''}C08 contacts and armor overlap remain research findings. GPU timing excludes startup, retargeting and export.`;
 $('trace-link').href=base+'prediction-trace.json';$('report-link').href=base+'validation-report.json';if(![...$('case').options].some(o=>o.value===id)){const option=document.createElement('option');option.value=id;option.textContent='Local / custom target ('+id.slice(-6)+')';$('case').append(option)}$('case').value=id;history.push(id);setStep(1);
}
for(const b of document.querySelectorAll('[data-step]'))b.onclick=()=>setStep(Number(b.dataset.step));
$('case').onchange=()=>loadCase($('case').value).catch(showError);function showError(e){$('error').textContent=e.message;console.error(e)}
$('play').onclick=()=>{if(step!==3){setStep(3);time=0;playing=true}else{playing=!playing;if(time>=duration){time=0;wait=0}}$('play').textContent=playing?'Pause':'Play prediction';apply()};
$('restart').onclick=()=>{time=0;wait=0;setStep(3);playing=true;$('play').textContent='Pause';apply()};$('timeline').oninput=()=>{step=3;playing=false;time=Number($('timeline').value);for(const b of document.querySelectorAll('[data-step]'))b.setAttribute('aria-pressed',String(b.dataset.step==='3'));$('play').textContent='Play prediction';apply()};
for(const id of ['ghosts','paths'])$(id).onchange=apply;$('compare').onchange=()=>{apply();view()};$('camera').onclick=view;
function resize(){renderer.setSize(stage.clientWidth,stage.clientHeight);camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix();view()}new ResizeObserver(resize).observe(stage);resize();view();
try{catalog=await fetch('catalog.json').then(r=>r.json());for(const c of catalog.cases){const option=document.createElement('option');option.value=c.id;option.textContent=c.label;$('case').append(option)}await loadCase(catalog.cases[0].id);
 window.predictiveTest={scene,camera,renderer,loadCase,setStep,get trace(){return trace},get asset(){return asset},get baseline(){return baseline},get time(){return time},get duration(){return duration},get step(){return step},get id(){return currentId},get history(){return history},get playing(){return playing},setTime(t){step=3;playing=false;time=Math.max(0,Math.min(t,duration));apply()}};
}catch(e){showError(e)}
async function connectLocal(){if(!['127.0.0.1','localhost'].includes(location.hostname))return;try{const r=await fetch('/api/predictive/status');if(!r.ok)return;const s=await r.json();if(s.service!=='mb-predictive')return;$('local-controls').hidden=false;$('hosting-note').textContent='Local GPU generation is available. Public presets remain recorded examples; Generate runs a fresh prediction and comparison on this PC.';$('local-status').textContent='Ready. First generation may need model initialization.'}catch{}}
$('generate').onclick=async()=>{
 if(busy)return;busy=true;$('generate').disabled=true;$('local-status').textContent='Queued for local GPU generation…';
 try{const response=await fetch('/api/predictive/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({x:Number($('target-x').value),y:Number($('target-y').value),yaw:Number($('target-yaw').value),pose:$('target-pose').value})});const job=await response.json();if(!response.ok)throw Error(job.error||'Generation unavailable');
 let state;for(let i=0;i<300;i++){await new Promise(r=>setTimeout(r,500));state=await fetch('/api/predictive/jobs/'+job.id).then(r=>r.json());$('local-status').textContent=state.message||state.status;if(state.status==='complete'||state.status==='failed')break}
 if(state?.status!=='complete')throw Error(state?.error||'Generation did not complete; check the local service log.');await loadCase('local-'+job.id,state.base);$('local-status').textContent='Fresh prediction loaded. Follow steps 1 → 2 → 3; generated files remain local.';
 }catch(e){$('local-status').textContent=e.message}finally{busy=false;$('generate').disabled=false}
};connectLocal();
let previous=performance.now();renderer.setAnimationLoop(now=>{const dt=Math.min(.1,Math.max(0,(now-previous)/1000));previous=now;if(playing&&action){if(time>=duration){if($('repeat').checked){wait+=dt;if(wait>=1.2){time=0;wait=0}}else{playing=false;$('play').textContent='Play prediction'}}else time=Math.min(duration,time+dt);apply()}orbit.update();renderer.render(scene,camera)});
