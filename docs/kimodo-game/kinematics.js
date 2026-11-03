import * as T from 'three';
export const point=b=>b.getWorldPosition(new T.Vector3());
const rotation=b=>b.getWorldQuaternion(new T.Quaternion());
function worldQ(b,q){b.quaternion.copy(rotation(b.parent).invert().multiply(q)).normalize();b.updateWorldMatrix(false,true)}
function aim(b,child,goal){const p=point(b),from=point(child).sub(p).normalize(),to=goal.clone().sub(p).normalize();worldQ(b,new T.Quaternion().setFromUnitVectors(from,to).multiply(rotation(b)))}
export function solveChain(a,b,c,goal,endRotation,poleGoal){
 const h=point(a),k=point(b),end=point(c),l1=h.distanceTo(k),l2=k.distanceTo(end),ray=goal.clone().sub(h),distance=ray.length();
 const d=T.MathUtils.clamp(distance,Math.abs(l1-l2)+1e-5,l1+l2-1e-5);ray.normalize();
 let pole=(poleGoal||k).clone().sub(h);pole.addScaledVector(ray,-pole.dot(ray));if(pole.lengthSq()<1e-9){pole.set(0,0,1).addScaledVector(ray,-ray.z);if(pole.lengthSq()<1e-9)pole.set(1,0,0)}pole.normalize();
 const x=(l1*l1-l2*l2+d*d)/(2*d),y=Math.sqrt(Math.max(0,l1*l1-x*x));
 aim(a,b,h.clone().addScaledVector(ray,x).addScaledVector(pole,y));aim(b,c,h.clone().addScaledVector(ray,d));if(endRotation)worldQ(c,endRotation);
 return {reach:Math.abs(distance-d),length:Math.max(Math.abs(point(a).distanceTo(point(b))-l1),Math.abs(point(b).distanceTo(point(c))-l2))};
}
export {worldQ as setWorldRotation};
export function groundFeet(actor,contacts,enabled,dt,ground=0){
 const diagnostics={reach:0,length:0};actor.asset.updateMatrixWorld(true);
 for(let side=0;side<2;side++){
  const f=actor.feet[side];if(!enabled){f.lock=null;continue}
  const ankle=point(f.ankle),sole=point(f.sole),prob=contacts?.[side]??0;
  const support=prob>.6&&sole.y-ground<.20&&sole.y-ground>-.25;
  if(!support){f.lock=null;continue}
  if(!f.lock||f.lock.distanceTo(new T.Vector3(sole.x,ground+.02,sole.z))>.24){f.lock=new T.Vector3(sole.x,ground+.02,sole.z)}
  const goal=ankle.clone().add(f.lock.clone().sub(sole)),flat=new T.Quaternion().setFromAxisAngle(new T.Vector3(0,1,0),actor.group.rotation.y);
  const r=solveChain(f.hip,f.knee,f.ankle,goal,rotation(f.ankle).slerp(flat,.35));diagnostics.reach=Math.max(diagnostics.reach,r.reach);diagnostics.length=Math.max(diagnostics.length,r.length);
 }
 return diagnostics;
}
export function carryHands(actor,box){
 if(!box)return {reach:0,length:0};box.updateMatrixWorld(true);let reach=0,length=0;
 for(const [side,x]of [['L',.29],['R',-.29]]){
  const goal=box.localToWorld(new T.Vector3(x,0,0));
  const r=solveChain(actor.bones['UPPER_ARM_'+side],actor.bones['FOREARM_'+side],actor.bones['HAND_'+side],goal);reach=Math.max(reach,r.reach);length=Math.max(length,r.length);
 }
 return {reach,length};
}
export function mantleHands(actor,flight,controllerPosition){
 const u=flight.elapsed/flight.duration,s=x=>{x=T.MathUtils.clamp(x,0,1);return x*x*(3-2*x)},weight=s((u-.08)/.1)*(1-s((u-.4)/.13));let reach=0,length=0;
 if(weight<=0)return {reach,length};
 const dir=flight.destination.clone().sub(flight.start).setY(0).normalize(),side=new T.Vector3(dir.z,0,-dir.x),offset=actor.group.position.clone().sub(controllerPosition);
 for(const [suffix,sign]of [['L',1],['R',-1]]){
  const upper=actor.bones['UPPER_ARM_'+suffix],fore=actor.bones['FOREARM_'+suffix],hand=actor.bones['HAND_'+suffix],edge=flight.edge.clone().addScaledVector(side,.23*sign).addScaledVector(dir,.03).add(offset);edge.y+=.035;
  const goal=point(hand).lerp(edge,weight),r=solveChain(upper,fore,hand,goal);reach=Math.max(reach,r.reach);length=Math.max(length,r.length);
 }
 return {reach,length};
}
