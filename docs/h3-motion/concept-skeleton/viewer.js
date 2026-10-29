import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const $=id=>document.getElementById(id),stage=$('stage'),video=$('video');
const data=await fetch('joint-trajectory.json').then(r=>r.json());
$('time').max=data.duration_s;
const scene=new T.Scene();scene.background=new T.Color('#172129');
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));stage.append(renderer.domElement);
const camera=new T.PerspectiveCamera(40,1,.01,100),controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
scene.add(new T.GridHelper(10,20,0x59717e,0x2f414c));scene.add(new T.AxesHelper(.3));
const offset=new T.Vector3(...data.display_offset),box=new T.Box3();
for(const pose of data.positions)for(const p of pose)box.expandByPoint(new T.Vector3(...p).sub(offset));
const center=box.getCenter(new T.Vector3()),extent=box.getSize(new T.Vector3()).length();
const pathCamera=center.clone().add(new T.Vector3(extent*.5,extent*.25,extent*.7));
function frameMode(){if($('follow').checked){controls.target.set(0,1.2,0);camera.position.set(3,2.3,4)}else{controls.target.copy(center);camera.position.copy(pathCamera)}controls.update()}
$('follow').onchange=frameMode;frameMode();
const skeleton=new T.LineSegments(new T.BufferGeometry(),new T.LineBasicMaterial({vertexColors:true}));scene.add(skeleton);
const points=new T.Points(new T.BufferGeometry(),new T.PointsMaterial({color:0xe1e9ef,size:.025}));scene.add(points);
function pose(time){
 const frame=Math.min(data.frame_count-1,Math.max(0,Math.round(time*data.fps))),p=data.positions[frame],positions=[],colors=[];
 const root=p[0],follow=$('follow').checked;
 const local=p.map(v=>new T.Vector3(...v).sub(offset).sub(new T.Vector3(follow?root[0]:0,0,follow?root[2]:0)));
 for(let i=0;i<p.length;i++){const parent=data.parent_indices[i];if(parent<0)continue;positions.push(...local[i].toArray(),...local[parent].toArray());const color=new T.Color(data.joint_names[i].startsWith('Left')?0x55b6ee:0xe6b461);colors.push(...color.toArray(),...color.toArray())}
 skeleton.geometry.setAttribute('position',new T.Float32BufferAttribute(positions,3));skeleton.geometry.setAttribute('color',new T.Float32BufferAttribute(colors,3));skeleton.geometry.computeBoundingSphere();
 points.geometry.setAttribute('position',new T.Float32BufferAttribute(local.flatMap(v=>v.toArray()),3));points.geometry.computeBoundingSphere();
 $('time').value=Math.min(time,data.duration_s);$('clock').textContent=time.toFixed(2)+' s';
}
function resize(){renderer.setSize(stage.clientWidth,stage.clientHeight);camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix()}new ResizeObserver(resize).observe(stage);resize();pose(0);
$('play').onclick=()=>{if(video.paused){if(video.ended)video.currentTime=0;video.play();$('play').textContent='Pause'}else{video.pause();$('play').textContent='Play'}};
$('rate').onchange=()=>video.playbackRate=Number($('rate').value);
$('time').oninput=()=>{video.pause();video.currentTime=Number($('time').value);$('play').textContent='Play';pose(video.currentTime)};
let mediaURL;
async function loadMedia(file,time=0){
 video.pause();const blob=await fetch(file).then(r=>r.blob()),previous=mediaURL;mediaURL=URL.createObjectURL(blob);video.src=mediaURL;
 await new Promise(resolve=>video.addEventListener('loadedmetadata',resolve,{once:true}));video.currentTime=time;if(previous)URL.revokeObjectURL(previous);
}
$('source').onchange=()=>loadMedia($('source').value,video.currentTime);
video.addEventListener('ended',()=>$('play').textContent='Play');
await loadMedia('../media/concept-recovery-overlay.mp4');
window.h3ConceptReview={data,video,scene,renderer,setTime(time){video.pause();video.currentTime=time;pose(time)}};
renderer.setAnimationLoop(()=>{if(document.hidden)return;pose(video.currentTime);controls.update();renderer.render(scene,camera)});
