import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const $=id=>document.getElementById(id);
try{
const catalog=await fetch('../catalog.json').then(r=>{if(!r.ok)throw Error('Catalog unavailable');return r.json()});
const id=new URLSearchParams(location.search).get('test'),test=catalog.tests.find(t=>t.id===id)||catalog.tests[0];
if(!test||!/^[a-z0-9-]+$/.test(test.id))throw Error('No valid test selected');
$('title').textContent=`${test.title}: raw recovered skeleton`;$('back').href=`../?test=${encodeURIComponent(test.id)}`;
const response=await fetch(`../data/${test.id}-skeleton.json.gz`);if(!response.ok)throw Error('Recovered skeleton is unavailable');
const stream=response.body.pipeThrough(new DecompressionStream('gzip')),data=await new Response(stream).json();
if(data.joint_names.length!==77||data.positions.some(p=>p.length!==77||p.some(v=>v.length!==3||v.some(x=>!Number.isFinite(x)))))throw Error('Invalid skeleton data');
const scene=new T.Scene();scene.background=new T.Color('#172129');
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));$('stage').append(renderer.domElement);
const camera=new T.PerspectiveCamera(40,1,.01,500),controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
scene.add(new T.GridHelper(20,40,0x59717e,0x2f414c));scene.add(new T.AxesHelper(.3));
const offset=new T.Vector3(...data.display_offset),box=new T.Box3(),hips=data.joint_names.indexOf('Hips');
for(const pose of data.positions)for(const p of pose)box.expandByPoint(new T.Vector3(...p).sub(offset));
const center=box.getCenter(new T.Vector3()),extent=Math.max(2,box.getSize(new T.Vector3()).length());
function frameMode(){if($('follow').checked){controls.target.set(0,1,0);camera.position.set(3,2,4)}else{controls.target.copy(center);camera.position.copy(center).add(new T.Vector3(extent*.5,extent*.3,extent*.8))}controls.update()}
$('follow').onchange=()=>{frameMode();pose(time)};frameMode();
const skeleton=new T.LineSegments(new T.BufferGeometry(),new T.LineBasicMaterial({vertexColors:true})),points=new T.Points(new T.BufferGeometry(),new T.PointsMaterial({color:0xe1e9ef,size:.025}));scene.add(skeleton,points);
let time=0,playing=false,last=performance.now(),frame=0;
function pose(t){frame=Math.min(data.frame_count-1,Math.max(0,Math.round(t*data.fps)));const raw=data.positions[frame],root=raw[hips],shift=$('follow').checked?new T.Vector3(root[0]-offset.x,0,root[2]-offset.z):new T.Vector3(),vertices=[],colors=[],all=[];
for(let i=0;i<raw.length;i++){const v=new T.Vector3(...raw[i]).sub(offset).sub(shift);all.push(v.x,v.y,v.z);const parent=data.parent_indices[i];if(parent<0)continue;const p=new T.Vector3(...raw[parent]).sub(offset).sub(shift);vertices.push(v.x,v.y,v.z,p.x,p.y,p.z);const c=new T.Color(data.joint_names[i].startsWith('Left')?0xf5b43c:0x46d2fa);colors.push(c.r,c.g,c.b,c.r,c.g,c.b)}
skeleton.geometry.setAttribute('position',new T.Float32BufferAttribute(vertices,3));skeleton.geometry.setAttribute('color',new T.Float32BufferAttribute(colors,3));skeleton.geometry.computeBoundingSphere();points.geometry.setAttribute('position',new T.Float32BufferAttribute(all,3));points.geometry.computeBoundingSphere();$('time').value=t;$('clock').textContent=`${t.toFixed(2)} / ${data.duration_s.toFixed(2)} s`;
}
$('time').max=data.duration_s;$('time').oninput=()=>{playing=false;$('play').textContent='Play';time=Number($('time').value);pose(time)};
$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Pause':'Play';last=performance.now()};
document.addEventListener('visibilitychange',()=>{if(document.hidden){playing=false;$('play').textContent='Play'}});
new ResizeObserver(()=>{const w=$('stage').clientWidth,h=$('stage').clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()}).observe($('stage'));
$('status').textContent=`${data.frame_count} frames · ${data.fps} fps · raw estimation, not an accepted game take`;
window.BipedSkeleton={data,get time(){return time},get frame(){return frame},get playing(){return playing},scene,skeleton,points};pose(0);
renderer.setAnimationLoop(now=>{if(playing){time=(time+Math.min(.1,(now-last)/1000)*Number($('rate').value))%data.duration_s;pose(time)}last=now;controls.update();renderer.render(scene,camera)});
}catch(error){$('status').textContent=error.message;$('status').className='error';$('play').disabled=true;console.error(error)}
