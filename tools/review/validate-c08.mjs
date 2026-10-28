import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {clone} from 'three/addons/utils/SkeletonUtils.js';
import validator from 'gltf-validator';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const out=process.env.MB_TEST_DIRECTORY||path.join(root,'evaluation/c08-worker');
globalThis.ProgressEvent??=class ProgressEvent{constructor(type,init){Object.assign(this,init);this.type=type}};
const bytes=fs.readFileSync(path.join(out,'c08-motionbricks-test.glb'));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const validation=await validator.validateBytes(new Uint8Array(bytes),{maxIssues:1000});
const report=JSON.parse(fs.readFileSync(path.join(out,'retarget-report.json')));
const source=JSON.parse(fs.readFileSync(path.join(out,'g1-preview.json')));
const clip=gltf.animations[0];
if(!clip||clip.name!==report.clip)throw Error('Missing test animation');
const mixer=new THREE.AnimationMixer(gltf.scene);
const action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o)});
const v=new THREE.Vector3(),p=new THREE.Vector3();
let minY=Infinity,maxFK=0,maxSegmentError=0;
const restLengths={};
const pairs=['L','R'].flatMap(s=>[[`HIP_${s}`,`KNEE_${s}`],[`KNEE_${s}`,`ANKLE_${s}`]]);
const stance={L:[],R:[]};
function pose(t){action.enabled=true;action.paused=false;mixer.setTime(t);gltf.scene.updateMatrixWorld(true);for(const mesh of meshes)mesh.skeleton.update()}
for(let frame=0;frame<report.frames;frame++){
 pose(frame/30);
 for(const [name,xyz] of Object.entries(report.sample_positions_blender[frame])){
  gltf.scene.getObjectByName(name).getWorldPosition(v);
  maxFK=Math.max(maxFK,v.distanceTo(new THREE.Vector3(xyz[0],xyz[2],-xyz[1])));
 }
 for(const side of ['L','R']){
  gltf.scene.getObjectByName(`SOCKET_SOLE_${side}`).getWorldPosition(v);
  const ci=side==='L'?0:2;
  stance[side].push({position:v.clone(),supported:Math.max(...source.contacts[frame].slice(ci,ci+2))>=.65});
 }
}
let maxSoleDrift=0;
for(const states of Object.values(stance)){
 let anchor=null;
 for(const s of states){if(!s.supported){anchor=null;continue}if(!anchor)anchor=s.position.clone();maxSoleDrift=Math.max(maxSoleDrift,Math.hypot(s.position.x-anchor.x,s.position.z-anchor.z))}
}
for(let tick=0;tick<=Math.round(clip.duration*120);tick++){
 pose(Math.min(tick/120,clip.duration));
 for(const [a,b] of pairs){const key=a+'-'+b;gltf.scene.getObjectByName(a).getWorldPosition(v);gltf.scene.getObjectByName(b).getWorldPosition(p);const length=v.distanceTo(p);restLengths[key]??=length;maxSegmentError=Math.max(maxSegmentError,Math.abs(length-restLengths[key]))}
 for(const mesh of meshes){const count=mesh.geometry.attributes.position.count;for(let i=0;i<count;i++){mesh.getVertexPosition(i,v);v.applyMatrix4(mesh.matrixWorld);if(!Number.isFinite(v.y))throw Error('Nonfinite skinned vertex');minY=Math.min(minY,v.y)}}
}
const copied=clone(gltf.scene);const originalMesh=meshes[0];let copyMesh;copied.traverse(o=>{if(o.isSkinnedMesh&&!copyMesh)copyMesh=o});
if(copyMesh.skeleton.bones[0]===originalMesh.skeleton.bones[0])throw Error('Shared cloned skeleton');
const independentMixer=new THREE.AnimationMixer(copied);independentMixer.clipAction(clip).play();independentMixer.setTime(.3);copied.updateMatrixWorld(true);
const before=copied.getObjectByName('ANKLE_L').getWorldPosition(new THREE.Vector3()).clone();pose(1.2);
const after=copied.getObjectByName('ANKLE_L').getWorldPosition(new THREE.Vector3());
const cloneIndependent=before.distanceTo(after)<1e-10;
const prohibited=clip.tracks.filter(t=>/^(ROOT|SENSOR_YAW|SOCKET_)/.test(t.name)||t.name.endsWith('.scale')).map(t=>t.name);
const results={three_revision:THREE.REVISION,clip:clip.name,duration_s:clip.duration,frames:report.frames,gltf_errors:validation.issues.numErrors,gltf_warnings:validation.issues.numWarnings,gltf_messages:validation.issues.messages,sampling_hz:120,skinned_geometry_min_floor_y_m:minY,max_exported_joint_position_error_m:maxFK,max_segment_length_variation_m:maxSegmentError,heuristic_stance_sole_xz_drift_m:maxSoleDrift,independent_clones:cloneIndependent,prohibited_animation_tracks:prohibited,limitations:['Contacts use unreviewed prediction intervals; contact acceptance remains pending','No general self-collision or game acceptance test']};
fs.writeFileSync(path.join(out,'validation-report.json'),JSON.stringify(results,null,2));
console.log(JSON.stringify(results,null,2));
if(validation.issues.numErrors||maxFK>.001||maxSegmentError>.001||!cloneIndependent||prohibited.length)process.exitCode=1;
