import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {clone} from 'three/addons/utils/SkeletonUtils.js';
const lookups=new WeakMap();
const identity=new T.Quaternion();
/** Retarget G1 joint directions onto B-REK43's existing rigid, articulated rig. */
export async function loadBrek(){
 const asset=await new GLTFLoader().loadAsync('../assets/b-rek43.glb?v=59a461ef42f5');
 function instance(){
  const group=new T.Group(),scene=clone(asset.scene),bones=[],bind=new Map(),meshes=[],samples=[];group.add(scene);group.updateMatrixWorld(true);
  scene.traverse(o=>{if(o.isBone){bones.push(o);bind.set(o.name,{p:o.getWorldPosition(new T.Vector3()),q:o.getWorldQuaternion(new T.Quaternion()),parentP:o.parent.getWorldPosition(new T.Vector3()),parentQ:o.parent.getWorldQuaternion(new T.Quaternion())})}if(o.isSkinnedMesh){o.frustumCulled=false;meshes.push(o);o.material=Array.isArray(o.material)?o.material.map(m=>m.clone()):o.material.clone();for(let i=0;i<o.geometry.attributes.position.count;i++)samples.push({mesh:o,i})}});
  const item={group,scene,bones,bind,meshes,height:2.709,lastLift:0,maxLift:0};
  function lookup(data){let result=lookups.get(data);if(!result){result=new Map(data.body_names.map((n,i)=>[n,i]));lookups.set(data,result)}return result}
  item.sourceScale=data=>{const names=lookup(data),ref=data.reference_positions;return (bind.get('PELVIS').p.y-bind.get('ANKLE_L').p.y)/(ref[names.get('pelvis')][1]-ref[names.get('left_ankle_roll_link')][1])};
  item.capture=()=>new Map(bones.map(b=>[b.name,{p:b.position.clone(),q:b.quaternion.clone()}]));
  item.blend=(previous,weight)=>{if(previous)for(const b of bones){const p=previous.get(b.name);if(p){b.position.lerpVectors(p.p,b.position,weight);b.quaternion.slerpQuaternions(p.q,b.quaternion,weight)}}};
  item.ground=()=>{group.position.y=0;group.updateMatrixWorld(true);for(const m of meshes)m.skeleton.update();let low=Infinity;const v=new T.Vector3();for(const {mesh,i} of samples){mesh.getVertexPosition(i,v);v.applyMatrix4(mesh.matrixWorld);low=Math.min(low,v.y)}item.lastLift=Math.max(0,.008-low);item.maxLift=Math.max(item.maxLift,item.lastLift);group.position.y=item.lastLift;group.updateMatrixWorld(true);return item.lastLift};
  item.pose=(data,time,centred=false)=>{
   if(!data?.rotation_deltas||!data.reference_positions)return false;
   const names=lookup(data),x=T.MathUtils.clamp(time*data.fps,0,data.frames-1),f=Math.floor(x),next=Math.min(f+1,data.frames-1),u=x-f,positions=new Map(),deltas=new Map(),worldRotations=new Map(),inherited=new Map();
   const src=n=>{const i=names.get(n);return new T.Vector3().fromArray(data.positions[f][i]).lerp(new T.Vector3().fromArray(data.positions[next][i]),u)};
   const rot=n=>{const i=names.get(n);return new T.Quaternion().fromArray(data.rotation_deltas[f][i]).slerp(new T.Quaternion().fromArray(data.rotation_deltas[next][i]),u)};
   const offset=(a,b)=>bind.get(b).p.clone().sub(bind.get(a).p);
   const direction=(a,b,sa,sb)=>new T.Quaternion().setFromUnitVectors(offset(a,b).normalize(),src(sb).sub(src(sa)).normalize());
   const scale=item.sourceScale(data),refPelvis=data.reference_positions[names.get('pelvis')][1],root=src('pelvis');
   positions.set('MOTION',new T.Vector3(centred?0:root.x*scale,0,centred?0:root.z*scale));deltas.set('MOTION',identity);
   positions.set('PELVIS',new T.Vector3(centred?0:root.x*scale,bind.get('PELVIS').p.y+(root.y-refPelvis)*scale,centred?0:root.z*scale));
   deltas.set('PELVIS',rot('pelvis'));deltas.set('WAIST',rot('waist_roll_link'));deltas.set('CHEST',rot('torso_link'));
   for(const [side,prefix] of [['L','left'],['R','right']]){
    deltas.set('HIP_'+side,direction('HIP_'+side,'KNEE_'+side,prefix+'_hip_pitch_link',prefix+'_knee_link'));
    deltas.set('KNEE_'+side,direction('KNEE_'+side,'ANKLE_'+side,prefix+'_knee_link',prefix+'_ankle_roll_link'));
    deltas.set('ANKLE_'+side,rot(prefix+'_ankle_roll_link'));
    deltas.set('UPPER_ARM_'+side,direction('UPPER_ARM_'+side,'FOREARM_'+side,prefix+'_shoulder_roll_link',prefix+'_elbow_link'));
    const forearm=direction('FOREARM_'+side,'HAND_'+side,prefix+'_elbow_link',prefix+'_wrist_yaw_link');deltas.set('FOREARM_'+side,forearm);
    deltas.set('HAND_'+side,rot(prefix+'_wrist_yaw_link').multiply(rot(prefix+'_elbow_link').invert()).multiply(forearm));
   }
   // Unmapped fingers, thumbs and sockets inherit their actual parent delta at
   // every depth. Their original local rest pose and rigid lengths are retained.
   for(const b of bones){const n=b.name,r=bind.get(n),parent=b.parent.isBone?b.parent.name:null,parentDelta=parent?inherited.get(parent):identity,delta=deltas.get(n)||parentDelta;
    inherited.set(n,delta);if(!positions.has(n))positions.set(n,parent?positions.get(parent).clone().add(offset(parent,n).applyQuaternion(parentDelta)):r.p.clone());
    const q=delta.clone().multiply(r.q),pp=parent?positions.get(parent):r.parentP,pq=parent?worldRotations.get(parent):r.parentQ;worldRotations.set(n,q);
    b.position.copy(positions.get(n)).sub(pp).applyQuaternion(pq.clone().invert());b.quaternion.copy(pq).invert().multiply(q).normalize();
   }
   group.updateMatrixWorld(true);return true;
  };
  return item;
 }
 return {asset,instance};
}
