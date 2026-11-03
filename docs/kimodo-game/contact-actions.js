import * as T from 'three';
import {point,solveChain,setWorldRotation} from './kinematics.js?v=contact-actions-1';

export const CONTACT_RULES=Object.freeze({ledgeDuration:2.45,landingDuration:1.65,heroDrop:1.6,heroImpactSpeed:4.5,maxLedgeHeight:2.85});
const v=(x=0,y=0,z=0)=>new T.Vector3(x,y,z),s=x=>{x=T.MathUtils.clamp(x,0,1);return x*x*(3-2*x)},phase=(t,a,b)=>s((t-a)/(b-a));
const qX=a=>new T.Quaternion().setFromAxisAngle(v(1,0,0),a);
export function calibrateRig(a){
 a.group.updateMatrixWorld(true);const points={},rotations={},gq=a.group.getWorldQuaternion(new T.Quaternion()).invert();
 for(const n of a.bind){points[n.b.name]=a.group.worldToLocal(point(n.b));rotations[n.b.name]=gq.clone().multiply(n.b.getWorldQuaternion(new T.Quaternion()))}
 const length=(a,b)=>points[a].distanceTo(points[b]),arm=Math.min(...['L','R'].map(s=>length('UPPER_ARM_'+s,'FOREARM_'+s)+length('FOREARM_'+s,'HAND_'+s)));
 return {points,rotations,arm,shoulderHeight:points.UPPER_ARM_L.y,handSpread:Math.abs(points.UPPER_ARM_L.x),thigh:length('HIP_R','KNEE_R'),calf:length('KNEE_R','ANKLE_R'),ankleHeight:points.ANKLE_R.y-points.SOCKET_SOLE_R.y};
}
const local=(a,x,y,z)=>a.group.localToWorld(v(x,y,z));
function orient(a,name,pitch=0){const b=a.bones[name];if(!b)return;setWorldRotation(b,a.group.getWorldQuaternion(new T.Quaternion()).multiply(qX(pitch)).multiply(a.rig.rotations[name]))}
function pelvis(a,x,y,z){const b=a.bones.PELVIS;b.position.copy(b.parent.worldToLocal(local(a,x,y,z)));b.updateWorldMatrix(false,true)}
function blendPose(a,w,solve){
 if(w<=0)return;const before=a.bind.map(n=>({p:n.b.position.clone(),q:n.b.quaternion.clone()})),report=solve();
 if(w<1)for(let i=0;i<a.bind.length;i++){const b=a.bind[i].b;b.position.lerpVectors(before[i].p,b.position,w);b.quaternion.copy(before[i].q.clone().slerp(b.quaternion,w))}
 a.asset.updateMatrixWorld(true);return report;
}
function solveArm(a,side,goal,pole,rotation){return solveChain(a.bones['UPPER_ARM_'+side],a.bones['FOREARM_'+side],a.bones['HAND_'+side],goal,rotation,pole)}
function fist(a,side){
 // Rig-local hinge axis is derived from each finger's own bind direction,
 // toward the palm centre; no rig-wide guessed finger rotation axis.
 const hand=a.bones['HAND_'+side],centre=point(hand);
 for(const n of a.bind){if(!n.b.name.startsWith('FINGER_'+side))continue;const child=n.b.children.find(b=>b.isBone);if(!child)continue;
  const b=n.b,p=point(b),from=point(child).sub(p).normalize(),to=centre.clone().sub(p).add(v(0,.02,0)).normalize(),turn=new T.Quaternion().setFromUnitVectors(from,to),target=turn.multiply(b.getWorldQuaternion(new T.Quaternion()));setWorldRotation(b,b.getWorldQuaternion(new T.Quaternion()).slerp(target,.78));
 }
}
export function heroLandingPose(a,elapsed){
 const w=phase(elapsed,0,.14)*(1-phase(elapsed,.92,CONTACT_RULES.landingDuration));
 const report=blendPose(a,w,()=>{
  const r=a.rig,hipY=.40,handY=a.id==='c08'?.11:.085,torso=r.shoulderHeight-r.points.PELVIS.y,pitch=Math.acos(T.MathUtils.clamp((handY+r.arm*.82-hipY)/torso,.25,.65));
  orient(a,'PELVIS',pitch);pelvis(a,0,hipY,-.13);orient(a,'CHEST',pitch);orient(a,'NECK',.12);orient(a,'HEAD',-.08);a.asset.updateMatrixWorld(true);
  // Calibrated knee-shell clearance for the two normalized original meshes.
  const kneeOffset=a.id==='c08'?.14:.065,hip=point(a.bones.HIP_R),kneeY=a.group.position.y+kneeOffset,dy=hip.y-kneeY,knee=hip.clone();knee.y=kneeY;knee.addScaledVector(v(Math.sin(a.group.rotation.y),0,Math.cos(a.group.rotation.y)),Math.sqrt(Math.max(.001,r.thigh*r.thigh-dy*dy)));
  const ankle=knee.clone().addScaledVector(v(Math.sin(a.group.rotation.y),0,Math.cos(a.group.rotation.y)),-Math.sqrt(Math.max(.001,r.calf*r.calf-(kneeOffset-r.ankleHeight)**2)));ankle.y=a.group.position.y+r.ankleHeight;
  const restFoot=side=>a.group.getWorldQuaternion(new T.Quaternion()).multiply(r.rotations['ANKLE_'+side]);
  const legs=[solveChain(a.bones.HIP_R,a.bones.KNEE_R,a.bones.ANKLE_R,ankle,restFoot('R'),knee),solveChain(a.bones.HIP_L,a.bones.KNEE_L,a.bones.ANKLE_L,local(a,Math.abs(r.points.ANKLE_L.x)+.035,r.ankleHeight,.56),restFoot('L'),local(a,.2,.75,1))];
  const shoulder=a.group.worldToLocal(point(a.bones.UPPER_ARM_L)),groundFist=local(a,shoulder.x+.15,handY,shoulder.z+.065),down=solveArm(a,'L',groundFist,local(a,.8,.4,.3));
  const raised=point(a.bones.UPPER_ARM_R),facing=a.group.getWorldQuaternion(new T.Quaternion()),handGoal=raised.clone().add(v(-.08,.07,.16).applyQuaternion(facing)),elbow=raised.clone().add(v(-.55,.65,-.15).applyQuaternion(facing));
  const up=solveArm(a,'R',handGoal,elbow);fist(a,'L');fist(a,'R');
  return {kneeError:point(a.bones.KNEE_R).distanceTo(knee),fistError:point(a.bones.HAND_L).distanceTo(groundFist),length:Math.max(...legs.map(l=>l.length),down.length,up.length),reach:Math.max(...legs.map(l=>l.reach),down.reach,up.reach)};
 });return {weight:w,...report};
}
export function ledgeGrabPose(a,flight){
 const t=flight.elapsed,reach=phase(t,.12,.48)*(1-phase(t,1.25,1.65)),w=phase(t,.12,.42)*(1-phase(t,2.12,2.45));let length=0,error=0;
 blendPose(a,w,()=>{
  const hang=1-phase(t,1.04,1.72);orient(a,'PELVIS',-.10*hang);orient(a,'CHEST',-.08*hang);orient(a,'NECK',-.12*hang);orient(a,'HEAD',-.18*hang);a.asset.updateMatrixWorld(true);
  const offset=a.group.position.clone().sub(flight.controllerPosition),forward=flight.destination.clone().sub(flight.start).setY(0).normalize(),side=v(forward.z,0,-forward.x);
  for(const suffix of ['L','R']){
   const sign=suffix==='L'?1:-1,edge=flight.edge.clone().addScaledVector(side,a.rig.handSpread*sign).addScaledVector(forward,.025).add(offset);edge.y+=.035;
   const goal=point(a.bones['HAND_'+suffix]).lerp(edge,reach),pole=local(a,sign*.6,1.4,-.4),ik=solveArm(a,suffix,goal,pole);length=Math.max(length,ik.length);if(reach>.999)error=Math.max(error,point(a.bones['HAND_'+suffix]).distanceTo(edge));
  }
  return {};
 });return {weight:w,handWeight:reach,length,handError:error};
}
