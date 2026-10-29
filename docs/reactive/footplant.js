import * as T from 'three';
const cache=new WeakMap(),epsilon=.000001;
/** Deterministic, explicitly enabled contact IK. Never trusts raw NN labels. */
export function applyFootplants(item,data,time){
 const sample=T.MathUtils.clamp(time*data.fps,0,data.frames-1),frame=Math.floor(sample);
 if(!data.contact_ik_mask?.[frame]){item.footplantDiagnostics=[];return}
 let lookup=cache.get(data);if(!lookup){lookup=new Map(data.body_names.map((n,i)=>[n,i]));cache.set(data,lookup)}
 const bones=new Map(item.bones.map(b=>[b.name,b])),scale=item.sourceScale(data),out=[];
 const active=(f,side)=>!!data.contact_ik_mask?.[f]&&Math.max(...data.contacts[f].slice(side==='L'?0:2,side==='L'?2:4))>=.65;
 const worldQuaternion=(bone,q)=>{bone.parent.updateMatrixWorld(true);bone.quaternion.copy(bone.parent.getWorldQuaternion(new T.Quaternion())).invert().multiply(q).normalize();bone.updateMatrixWorld(true)};
 for(const [side,prefix]of [['L','left'],['R','right']]){
  if(!active(frame,side))continue;let start=frame,end=frame;while(start>0&&active(start-1,side))start--;while(end<data.frames-1&&active(end+1,side))end++;
  item.group.updateWorldMatrix(true,true);
  const weight=Math.min(1,(sample-start+1)/2,(end+1-sample)/2),hip=bones.get('HIP_'+side),knee=bones.get('KNEE_'+side),ankle=bones.get('ANKLE_'+side),index=lookup.get(prefix+'_ankle_roll_link'),anchor=new T.Vector3().fromArray(data.positions[start][index]).multiplyScalar(scale).add(item.bind.get('ANKLE_'+side).p).addScaledVector(new T.Vector3().fromArray(data.reference_positions[index]),-scale).applyMatrix4(item.group.matrixWorld);
  const h=hip.getWorldPosition(new T.Vector3()),k=knee.getWorldPosition(new T.Vector3()),a=ankle.getWorldPosition(new T.Vector3()),aLength=h.distanceTo(k),bLength=k.distanceTo(a),target=a.clone().lerp(anchor,weight),direction=target.clone().sub(h),requested=direction.length(),maximum=aLength+bLength-.001,minimum=Math.abs(aLength-bLength)+.001,length=T.MathUtils.clamp(requested,minimum,maximum),released=Math.abs(length-requested)>.0001;direction.multiplyScalar(1/Math.max(epsilon,requested));target.copy(h).addScaledVector(direction,length);
  let pole=k.clone().sub(h);pole.addScaledVector(direction,-pole.dot(direction));if(pole.lengthSq()<1e-10){pole.set(0,0,1).addScaledVector(direction,-direction.z)}pole.normalize();const along=(aLength*aLength-bLength*bLength+length*length)/(2*length),desiredKnee=h.clone().addScaledVector(direction,along).addScaledVector(pole,Math.sqrt(Math.max(0,aLength*aLength-along*along))),hipQ=hip.getWorldQuaternion(new T.Quaternion()),oldThigh=k.clone().sub(h).normalize(),newThigh=desiredKnee.clone().sub(h).normalize();worldQuaternion(hip,new T.Quaternion().setFromUnitVectors(oldThigh,newThigh).multiply(hipQ));
  const movedKnee=knee.getWorldPosition(new T.Vector3()),movedAnkle=ankle.getWorldPosition(new T.Vector3()),kneeQ=knee.getWorldQuaternion(new T.Quaternion());worldQuaternion(knee,new T.Quaternion().setFromUnitVectors(movedAnkle.sub(movedKnee).normalize(),target.clone().sub(movedKnee).normalize()).multiply(kneeQ));
  // Prepared crouch support is flat. Preserve the native ankle rest frame and
  // source heading; never replace the model's finger/glove pose.
  const delta=new T.Quaternion().fromArray(data.rotation_deltas[start][index]),flat=item.group.getWorldQuaternion(new T.Quaternion()).multiply(delta).multiply(item.bind.get('ANKLE_'+side).q),current=ankle.getWorldQuaternion(new T.Quaternion());worldQuaternion(ankle,current.slerp(flat,weight));
  out.push({side,start_frame:start,end_frame:end,weight,requested_length_m:requested,released,ankle_error_m:ankle.getWorldPosition(new T.Vector3()).distanceTo(anchor)})
 }
 item.group.updateMatrixWorld(true);item.footplantDiagnostics=out;
}
