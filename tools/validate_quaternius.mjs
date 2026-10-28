import fs from 'node:fs';import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),out=path.join(root,'evaluation/quaternius');
const T=await import(pathToFileURL(path.join(root,'tools/review/node_modules/three/build/three.module.js')));
const {GLTFLoader}=await import(pathToFileURL(path.join(root,'tools/review/node_modules/three/examples/jsm/loaders/GLTFLoader.js')));
const validator=(await import(pathToFileURL(path.join(root,'tools/review/node_modules/gltf-validator/index.js')))).default;
globalThis.ProgressEvent??=class ProgressEvent{};
const bytes=fs.readFileSync(path.join(out,'c08-quaternius.glb')),g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const validation=await validator.validateBytes(new Uint8Array(bytes),{maxIssues:1000});const report=JSON.parse(fs.readFileSync(path.join(out,'retarget-report.json'))),results=[];let meshes=[];g.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o)});
const v=new T.Vector3(),w=new T.Vector3();
for(const clip of g.animations){
 const info=report.clips.find(x=>x.name===clip.name),m=new T.AnimationMixer(g.scene),a=m.clipAction(clip);a.setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play();
 const pose=t=>{a.enabled=true;a.paused=false;m.setTime(t);g.scene.updateMatrixWorld(true);for(const mesh of meshes)mesh.skeleton.update()};let fk=0,floor=Infinity,segment=0;const lengths={};
 for(let f=0;f<info.frames;f++){pose(f/info.fps);for(const [n,p] of Object.entries(info.sample_positions_blender[f])){g.scene.getObjectByName(n).getWorldPosition(v);fk=Math.max(fk,v.distanceTo(new T.Vector3(p[0],p[2],-p[1])))}}
 for(let tick=0;tick<=Math.ceil(clip.duration*120);tick++){pose(Math.min(tick/120,clip.duration));for(const s of ['L','R'])for(const [p,c] of [['HIP','KNEE'],['KNEE','ANKLE'],['UPPER_ARM','FOREARM'],['FOREARM','HAND']]){g.scene.getObjectByName(p+'_'+s).getWorldPosition(v);g.scene.getObjectByName(c+'_'+s).getWorldPosition(w);const key=p+s,d=v.distanceTo(w);lengths[key]??=d;segment=Math.max(segment,Math.abs(d-lengths[key]))}for(const mesh of meshes)for(let i=0;i<mesh.geometry.attributes.position.count;i++){mesh.getVertexPosition(i,v);v.applyMatrix4(mesh.matrixWorld);if(!Number.isFinite(v.y))throw Error('Nonfinite geometry');floor=Math.min(floor,v.y)}}
 pose(0);const first=new Map();g.scene.traverse(o=>{if(o.isBone)first.set(o.name,{p:o.position.clone(),q:o.quaternion.clone()})});pose(clip.duration);let seamP=0,seamQ=0;g.scene.traverse(o=>{if(o.isBone){seamP=Math.max(seamP,o.position.distanceTo(first.get(o.name).p));seamQ=Math.max(seamQ,o.quaternion.angleTo(first.get(o.name).q))}});
 const prohibited=clip.tracks.filter(t=>/^(ROOT|SENSOR_YAW|SOCKET_)/.test(t.name)||t.name.endsWith('.scale'));const r={name:clip.name,loop:info.loop,duration_s:clip.duration,floor_min_m:floor,max_fk_error_m:fk,max_segment_variation_m:segment,seam_position_m:seamP,seam_rotation_rad:seamQ,prohibited_tracks:prohibited.length};results.push(r);console.log(JSON.stringify(r));m.stopAllAction();m.uncacheRoot(g.scene);
 if(fk>.001||segment>.001||floor<-.003||prohibited.length)process.exitCode=1;
}
const result={gltf_errors:validation.issues.numErrors,gltf_warnings:validation.issues.numWarnings,messages:validation.issues.messages,sampling_hz:120,clips:results};fs.writeFileSync(path.join(out,'validation-report.json'),JSON.stringify(result,null,2));if(result.gltf_errors||result.gltf_warnings)process.exitCode=1;
