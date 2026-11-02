import * as T from 'three';
import {clone} from 'three/addons/utils/SkeletonUtils.js';
import {normalizedGLB} from '../shared/normalized-gltf-export.js';
export function animation(data){return new T.AnimationClip(data.name,data.duration,data.tracks.map(t=>new (t.type==='quaternion'?T.QuaternionKeyframeTrack:T.VectorKeyframeTrack)(t.name,t.times,t.values)))}
export function download(data,name,type='application/json'){const url=URL.createObjectURL(new Blob([data],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),3000)}
function sceneFor(root){
 // glTF skinning uses joint world transforms. Keep skinned mesh nodes at scene
 // roots with identity transforms, so engine importers do not ignore an animated
 // mesh parent. Skeleton ancestors retain normalization and actor root motion.
 const scene=new T.Scene();scene.add(root);const meshes=[];root.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o)});
 for(const mesh of meshes){scene.add(mesh);mesh.position.set(0,0,0);mesh.quaternion.identity();mesh.scale.set(1,1,1)}scene.updateMatrixWorld(true);return scene;
}
export async function exportClips(actor,data,name,save=true){
 const asset=clone(actor.asset);asset.position.set(0,0,0);asset.quaternion.identity();asset.scale.copy(actor.asset.scale);
 // A pack starts in a neutral bind pose, independent of the live IK / preview pose.
 for(const n of actor.bind){const b=asset.getObjectByName(n.b.name);if(b){b.position.copy(n.p);b.quaternion.copy(n.q)}}asset.updateMatrixWorld(true);
 const bytes=await normalizedGLB(sceneFor(asset),{binary:true,animations:data.map(animation),onlyVisible:false});if(save)download(bytes,name,'model/gltf-binary');return bytes;
}
export function createRecorder(){
 let active=false,frames=[],events=[],start=0,actorId=null,lastSample=-1,ended=null;
 function sample(actor,time){if(!active||time-lastSample<1/30-1e-6)return;lastSample=time;frames.push({t:time-start,p:actor.group.position.toArray(),q:actor.group.quaternion.toArray(),bones:actor.bind.map(n=>[...n.b.position.toArray(),...n.b.quaternion.toArray()])})}
 return {get active(){return active},get seconds(){return frames.at(-1)?.t||0},get count(){return frames.length},get body(){return actorId},get ready(){return !!ended},
  start(actor,time){active=true;frames=[];events=[];start=time;lastSample=-1;actorId=actor.id;ended=null;sample(actor,time)},
  sample(actor,time){if(active&&actor.id===actorId)sample(actor,time);if(frames.length>=3600)this.stop()},
  event(value,time){if(active)events.push({time:time-start,...value})},
  stop(){if(active){active=false;ended=new Date().toISOString()}},
  async save(actor){if(!ended||frames.length<2)throw Error('Record at least two frames first.');const group=new T.Group();group.name='RecordedActor';const asset=clone(actor.asset);group.add(asset);
   const times=frames.map(f=>f.t),tracks=[new T.VectorKeyframeTrack('RecordedActor.position',times,frames.flatMap(f=>f.p)),new T.QuaternionKeyframeTrack('RecordedActor.quaternion',times,frames.flatMap(f=>f.q))];
   for(let i=0;i<actor.bind.length;i++){const name=actor.bind[i].b.name;tracks.push(new T.VectorKeyframeTrack(name+'.position',times,frames.flatMap(f=>f.bones[i].slice(0,3))),new T.QuaternionKeyframeTrack(name+'.quaternion',times,frames.flatMap(f=>f.bones[i].slice(3))))}
   const clip=new T.AnimationClip('GameLab_recorded_'+actorId,times.at(-1),tracks),bytes=await normalizedGLB(sceneFor(group),{binary:true,animations:[clip],onlyVisible:false});
   const stem='kimodo-game-take-'+actorId+'-'+ended.replace(/[:.]/g,'-');download(bytes,stem+'.glb','model/gltf-binary');download(JSON.stringify({schema:'kimodo-game-recording/1',body:actorId,ended,duration_s:times.at(-1),frames:frames.length,events,baked:['controller world translation and rotation','retargeted skeletal poses','runtime foot and carrying-hand IK'],scope:'Sampled live play session. Review collision, contacts, props and balance before shipping. Prop mesh and its trajectory are not included in this character recording.'},null,2),stem+'.json');return bytes;
  }};
}
