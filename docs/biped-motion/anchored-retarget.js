import * as T from 'three';
// Bake the approved C08 clip to each target's original bind skeleton. No neural calls.
export function retargetAnchored(source,target,clip,contacts){
 const bones=root=>{const map=new Map();root.traverse(o=>{if(o.isBone)map.set(o.name,o)});return map};
 const sb=bones(source),tb=bones(target);let skeleton;target.traverse(o=>{if(o.isSkinnedMesh)skeleton=o.skeleton});skeleton.pose();target.updateMatrixWorld(true);
 let ss;source.traverse(o=>{if(o.isSkinnedMesh)ss=o.skeleton});ss.pose();source.updateMatrixWorld(true);
 const capture=map=>new Map([...map].map(([n,b])=>[n,{p:b.position.clone(),q:b.quaternion.clone(),wp:b.getWorldPosition(new T.Vector3()),wq:b.getWorldQuaternion(new T.Quaternion())}]));
 const sr=capture(sb),tr=capture(tb),ordered=[...tb.values()],scale=tr.get('PELVIS').wp.y/sr.get('PELVIS').wp.y;
 const mixer=new T.AnimationMixer(source),action=mixer.clipAction(clip);action.setLoop(T.LoopOnce,1);action.clampWhenFinished=true;action.play();action.paused=true;
 const fps=contacts.fps,count=contacts.weights.length,times=[],values=new Map(ordered.map(b=>[b.name,{p:[],q:[]}])),anchors=[null,null],lastIds=[null,null];let lift=0,neutralFeet=[],neutralRot=[],initialYaw=[],unreachable=0,maxLengthError=0;
 const worldQ=b=>b.getWorldQuaternion(new T.Quaternion()),worldP=b=>b.getWorldPosition(new T.Vector3());
 function setWorldQ(b,q){const parent=worldQ(b.parent);b.quaternion.copy(parent.invert().multiply(q)).normalize();b.updateWorldMatrix(false,true)}
 function aim(b,child,point){const a=worldP(b),from=worldP(child).sub(a).normalize(),to=point.clone().sub(a).normalize();setWorldQ(b,new T.Quaternion().setFromUnitVectors(from,to).multiply(worldQ(b)))}
 function solve(side,goal,weight,rotation){const hip=tb.get('HIP_'+side),knee=tb.get('KNEE_'+side),ankle=tb.get('ANKLE_'+side);if(!hip||!knee||!ankle||weight<=0)return;
  const saved=[hip,knee,ankle].map(b=>b.quaternion.clone()),h=worldP(hip),k=worldP(knee),a=worldP(ankle),l1=h.distanceTo(k),l2=k.distanceTo(a),ray=goal.clone().sub(h),raw=ray.length(),d=Math.max(Math.abs(l1-l2)+1e-5,Math.min(l1+l2-1e-5,raw));if(raw>l1+l2)unreachable++;
  ray.normalize();let pole=k.clone().sub(h).addScaledVector(ray,-k.clone().sub(h).dot(ray));if(pole.lengthSq()<1e-10)pole=new T.Vector3(0,0,1).addScaledVector(ray,-ray.z);pole.normalize();const along=(l1*l1-l2*l2+d*d)/(2*d),bend=Math.sqrt(Math.max(0,l1*l1-along*along)),middle=h.clone().addScaledVector(ray,along).addScaledVector(pole,bend),end=h.clone().addScaledVector(ray,d);
  aim(hip,knee,middle);aim(knee,ankle,end);setWorldQ(ankle,rotation);
  [hip,knee,ankle].forEach((b,i)=>{const solved=b.quaternion.clone();b.quaternion.copy(saved[i]).slerp(solved,weight)});target.updateMatrixWorld(true);
  maxLengthError=Math.max(maxLengthError,Math.abs(worldP(hip).distanceTo(worldP(knee))-l1),Math.abs(worldP(knee).distanceTo(worldP(ankle))-l2));
 }
 for(let f=0;f<count;f++){
  const time=Math.min(f/fps,clip.duration);action.time=time;mixer.update(0);source.updateMatrixWorld(true);
  for(const b of ordered){const rest=tr.get(b.name);b.position.copy(rest.p);b.quaternion.copy(rest.q);if(!sb.has(b.name))continue;
   const desired=worldQ(sb.get(b.name)).multiply(sr.get(b.name).wq.clone().invert()).multiply(rest.wq);setWorldQ(b,desired);
   if(b.name==='PELVIS'){const p=worldP(sb.get('PELVIS')).sub(sr.get('PELVIS').wp).multiplyScalar(scale).add(rest.wp);p.y+=lift;b.position.copy(b.parent.worldToLocal(p));b.updateWorldMatrix(false,true)}
  }
  target.updateMatrixWorld(true);
  if(f===0){lift=.006-new T.Box3().setFromObject(target,true).min.y;const pelvis=tb.get('PELVIS');pelvis.position.y+=lift;target.updateMatrixWorld(true);neutralFeet=['L','R'].map(s=>worldP(tb.get('ANKLE_'+s)));neutralRot=['L','R'].map(s=>worldQ(tb.get('ANKLE_'+s)));initialYaw=['L','R'].map(s=>new T.Euler().setFromQuaternion(worldQ(sb.get('ANKLE_'+s)),'YXZ').y)}
  for(const [i,side]of ['L','R'].entries()){
   const weight=contacts.weights[f][i],id=contacts.segments[f][i],ankle=tb.get('ANKLE_'+side);
   if(weight>0){if(lastIds[i]!==id||!anchors[i]){anchors[i]=worldP(ankle);anchors[i].y=neutralFeet[i].y}const sq=worldQ(sb.get('ANKLE_'+side)),yaw=new T.Euler().setFromQuaternion(sq,'YXZ').y,initial=initialYaw[i],rotation=new T.Quaternion().setFromAxisAngle(new T.Vector3(0,1,0),yaw-initial).multiply(neutralRot[i]);solve(side,anchors[i],weight,rotation)}else anchors[i]=null;
   lastIds[i]=id;
  }
  times.push(time);for(const b of ordered){b.quaternion.normalize();const out=values.get(b.name);out.p.push(...b.position.toArray());let q=b.quaternion.clone();if(out.q.length&&q.dot(new T.Quaternion().fromArray(out.q,out.q.length-4))<0)q.set(-q.x,-q.y,-q.z,-q.w);out.q.push(...q.toArray())}
 }
 const tracks=[];for(const b of ordered){if(!sb.has(b.name)||/^(ROOT$|MOTION$|SENSOR_YAW$|SOCKET_|FINGER_|THUMB_)/.test(b.name))continue;const v=values.get(b.name);tracks.push(new T.VectorKeyframeTrack(b.name+'.position',times,v.p),new T.QuaternionKeyframeTrack(b.name+'.quaternion',times,v.q))}
 mixer.stopAllAction();target.userData.anchoredRetarget={source:clip.name,scale,constant_floor_lift_m:lift,unreachable_frame_sides:unreachable,max_segment_length_error_m:maxLengthError,policy:'Fixed target bind lengths, source world rotation deltas, scaled pelvis travel, declared support-phase leg IK; no per-frame floor clamp. Target floor/armor contacts require visual review.'};
 return new T.AnimationClip('Anchored_'+clip.name,clip.duration,tracks);
}
