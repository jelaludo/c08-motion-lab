import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {clone} from 'three/addons/utils/SkeletonUtils.js';
const names=new WeakMap();
export async function loadFighter(){
 const asset=await new GLTFLoader().loadAsync('../assets/meshy-fighter-rigged.glb');
 function instance(){
  const group=new T.Group(),scene=clone(asset.scene);group.add(scene);group.updateMatrixWorld(true);const bones=[],bind=new Map(),meshes=[];
  scene.traverse(o=>{if(o.isBone){bones.push(o);bind.set(o.name,{p:o.getWorldPosition(new T.Vector3()),q:o.getWorldQuaternion(new T.Quaternion()),parentP:o.parent.getWorldPosition(new T.Vector3()),parentQ:o.parent.getWorldQuaternion(new T.Quaternion())})}if(o.isSkinnedMesh){o.frustumCulled=false;meshes.push(o);o.material=Array.isArray(o.material)?o.material.map(m=>m.clone()):o.material.clone()}});
  const samples=[];
  for(const mesh of meshes){const n=mesh.geometry.attributes.position.count,skin=mesh.geometry.attributes.skinIndex,clusters=new Map();for(let i=0;i<n;i++){const b=skin.getX(i);if(!clusters.has(b))clusters.set(b,[]);clusters.get(b).push(i)}const v=new T.Vector3();for(const indices of clusters.values())for(let axis=0;axis<3;axis++){let lo=Infinity,hi=-Infinity,li=0,hiIndex=0;for(const i of indices){v.fromBufferAttribute(mesh.geometry.attributes.position,i);const x=v.getComponent(axis);if(x<lo){lo=x;li=i}if(x>hi){hi=x;hiIndex=i}}samples.push({mesh,i:li},{mesh,i:hiIndex})}for(let i=0;i<n;i+=Math.max(1,Math.floor(n/400)))samples.push({mesh,i})}
  const item={group,scene,bones,bind,meshes,lastLift:0,maxLift:0};
  item.capture=()=>new Map(bones.map(b=>[b.name,{p:b.position.clone(),q:b.quaternion.clone()}]));
  item.blend=(previous,weight)=>{if(!previous)return;for(const b of bones){const p=previous.get(b.name);if(p){b.position.lerpVectors(p.p,b.position,weight);b.quaternion.slerpQuaternions(p.q,b.quaternion,weight)}}};
  item.opacity=value=>{for(const m of meshes)for(const mat of Array.isArray(m.material)?m.material:[m.material]){mat.transparent=value<1;mat.opacity=value;mat.depthWrite=value===1}};
  item.ground=()=>{group.position.y=0;group.updateMatrixWorld(true);for(const m of meshes)m.skeleton.update();let low=Infinity;const p=new T.Vector3();for(const {mesh,i} of samples){mesh.getVertexPosition(i,p);p.applyMatrix4(mesh.matrixWorld);low=Math.min(low,p.y)}item.lastLift=Math.max(0,.008-low);item.maxLift=Math.max(item.maxLift,item.lastLift);group.position.y=item.lastLift;group.updateMatrixWorld(true)};
  item.pose=(data,time,centred=false)=>{
   if(!data?.rotation_deltas||!data.reference_positions)return false;
   let lookup=names.get(data);if(!lookup){lookup=new Map(data.body_names.map((n,i)=>[n,i]));names.set(data,lookup)}
   const x=T.MathUtils.clamp(time*data.fps,0,data.frames-1),f=Math.floor(x),next=Math.min(f+1,data.frames-1),u=x-f,positions=new Map(),deltas=new Map();
   const src=n=>{const i=lookup.get(n);return new T.Vector3().fromArray(data.positions[f][i]).lerp(new T.Vector3().fromArray(data.positions[next][i]),u)};
   const rot=n=>{const i=lookup.get(n);return new T.Quaternion().fromArray(data.rotation_deltas[f][i]).slerp(new T.Quaternion().fromArray(data.rotation_deltas[next][i]),u)};
   const offset=(a,b)=>bind.get(b).p.clone().sub(bind.get(a).p),direction=(a,b,sa,sb)=>new T.Quaternion().setFromUnitVectors(offset(a,b).normalize(),src(sb).sub(src(sa)).normalize());
   const ref=data.reference_positions,refPelvis=ref[lookup.get('pelvis')][1],refAnkle=ref[lookup.get('left_ankle_roll_link')][1],scale=(bind.get('PELVIS').p.y-bind.get('ANKLE_L').p.y)/(refPelvis-refAnkle),root=src('pelvis');
   deltas.set('MOTION',new T.Quaternion());positions.set('MOTION',new T.Vector3(centred?0:root.x*scale,0,centred?0:root.z*scale));positions.set('PELVIS',new T.Vector3(centred?0:root.x*scale,bind.get('PELVIS').p.y+(root.y-refPelvis)*scale,centred?0:root.z*scale));deltas.set('PELVIS',rot('pelvis'));deltas.set('WAIST',rot('waist_roll_link'));deltas.set('CHEST',rot('torso_link'));deltas.set('NECK',rot('torso_link'));deltas.set('HEAD',rot('torso_link'));
   for(const [side,prefix] of [['L','left'],['R','right']]){
    deltas.set('SHOULDER_'+side,rot('torso_link'));deltas.set('HIP_'+side,direction('HIP_'+side,'KNEE_'+side,prefix+'_hip_pitch_link',prefix+'_knee_link'));deltas.set('KNEE_'+side,direction('KNEE_'+side,'ANKLE_'+side,prefix+'_knee_link',prefix+'_ankle_roll_link'));deltas.set('ANKLE_'+side,rot(prefix+'_ankle_roll_link'));deltas.set('TOE_'+side,rot(prefix+'_ankle_roll_link'));deltas.set('UPPER_ARM_'+side,direction('UPPER_ARM_'+side,'FOREARM_'+side,prefix+'_shoulder_roll_link',prefix+'_elbow_link'));const forearm=direction('FOREARM_'+side,'HAND_'+side,prefix+'_elbow_link',prefix+'_wrist_yaw_link');deltas.set('FOREARM_'+side,forearm);deltas.set('HAND_'+side,rot(prefix+'_wrist_yaw_link').multiply(rot(prefix+'_elbow_link').invert()).multiply(forearm));
   }
   const orientations=new Map();
   for(const b of bones){const n=b.name,r=bind.get(n),parent=b.parent.isBone?b.parent.name:null,delta=deltas.get(n)||deltas.get(parent)||new T.Quaternion();if(!positions.has(n))positions.set(n,positions.get(parent).clone().add(offset(parent,n).applyQuaternion(deltas.get(parent))));const q=delta.clone().multiply(r.q);orientations.set(n,q);const pp=parent?positions.get(parent):r.parentP,pq=parent?orientations.get(parent):r.parentQ;b.position.copy(positions.get(n)).sub(pp).applyQuaternion(pq.clone().invert());b.quaternion.copy(pq).invert().multiply(q);}
   group.updateMatrixWorld(true);return true;
  };
  return item;
 }
 return {ai:instance(),linear:instance(),asset};
}
