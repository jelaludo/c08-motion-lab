import fs from 'node:fs';import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const THREE=await import(pathToFileURL(path.join(root,'tools/review/node_modules/three/build/three.module.js')));
const {GLTFLoader}=await import(pathToFileURL(path.join(root,'tools/review/node_modules/three/examples/jsm/loaders/GLTFLoader.js')));
const {clone}=await import(pathToFileURL(path.join(root,'tools/review/node_modules/three/examples/jsm/utils/SkeletonUtils.js')));
const validator=(await import(pathToFileURL(path.join(root,'tools/review/node_modules/gltf-validator/index.js')))).default;
globalThis.ProgressEvent??=class ProgressEvent{constructor(type,init){Object.assign(this,init);this.type=type}};
for(const name of process.argv.slice(2).length?process.argv.slice(2):['ukemi']){
 const out=path.join(root,'video-mocap/c08-retarget',name);const bytes=fs.readFileSync(path.join(out,'c08-mocap.glb'));
 const report=JSON.parse(fs.readFileSync(path.join(out,'retarget-report.json')));
 const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
 const check=await validator.validateBytes(new Uint8Array(bytes),{maxIssues:1000});
 const clip=gltf.animations[0];if(clip.name!==report.clip)throw Error('Incorrect clip name');
 const mixer=new THREE.AnimationMixer(gltf.scene),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
 const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o)});
 function pose(t){action.enabled=true;action.paused=false;mixer.setTime(t);gltf.scene.updateMatrixWorld(true);for(const mesh of meshes)mesh.skeleton.update()}
 const v=new THREE.Vector3(),w=new THREE.Vector3();let fk=0,floor=Infinity,segmentError=0;const rest={};let inverted=0;
 const pairs=['L','R'].flatMap(s=>[[`HIP_${s}`,`KNEE_${s}`],[`KNEE_${s}`,`ANKLE_${s}`],[`UPPER_ARM_${s}`,`FOREARM_${s}`],[`FOREARM_${s}`,`HAND_${s}`]]);
 for(let f=0;f<report.frames;f++){
  pose(f/30);for(const [n,p] of Object.entries(report.sample_positions_blender[f])){gltf.scene.getObjectByName(n).getWorldPosition(v);fk=Math.max(fk,v.distanceTo(new THREE.Vector3(p[0],p[2],-p[1])))}
  const head=gltf.scene.getObjectByName('HEAD').getWorldPosition(v),pelvis=gltf.scene.getObjectByName('PELVIS').getWorldPosition(w);if(head.y<pelvis.y)inverted++;
 }
 for(let tick=0;tick<=Math.round(clip.duration*120);tick++){
  pose(Math.min(tick/120,clip.duration));
  for(const [a,b] of pairs){const key=a+'/'+b;gltf.scene.getObjectByName(a).getWorldPosition(v);gltf.scene.getObjectByName(b).getWorldPosition(w);const distance=v.distanceTo(w);rest[key]??=distance;segmentError=Math.max(segmentError,Math.abs(distance-rest[key]))}
  for(const mesh of meshes)for(let i=0;i<mesh.geometry.attributes.position.count;i++){mesh.getVertexPosition(i,v);v.applyMatrix4(mesh.matrixWorld);if(!Number.isFinite(v.y))throw Error('Nonfinite skinned vertex');floor=Math.min(floor,v.y)}
 }
 const copy=clone(gltf.scene);let copyMesh;copy.traverse(o=>{if(o.isSkinnedMesh&&!copyMesh)copyMesh=o});const independent=copyMesh.skeleton.bones[0]!==meshes[0].skeleton.bones[0];
 const prohibited=clip.tracks.filter(t=>/^(ROOT|SENSOR_YAW|SOCKET_)/.test(t.name)||t.name.endsWith('.scale')).map(t=>t.name);
 const result={kind:'video_mocap',pipeline:report.pipeline,clip:clip.name,frames:report.frames,fps:30,duration_s:clip.duration,three_revision:THREE.REVISION,gltf_errors:check.issues.numErrors,gltf_warnings:check.issues.numWarnings,gltf_messages:check.issues.messages,sampling_hz:120,skinned_geometry_min_floor_y_m:floor,max_exported_joint_position_error_m:fk,max_segment_length_variation_m:segmentError,inverted_head_below_pelvis_frames:inverted,independent_clones:independent,prohibited_animation_tracks:prohibited,max_abs_whole_body_ground_offset_m:report.max_abs_ground_correction_m,limitations:report.limitations};
 fs.writeFileSync(path.join(out,'validation-report.json'),JSON.stringify(result,null,2));console.log(name,JSON.stringify(result,null,2));
 if(check.issues.numErrors||fk>.001||segmentError>.001||!independent||prohibited.length)process.exitCode=1;
}
