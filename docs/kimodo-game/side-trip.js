import * as T from 'three';
import {point,solveChain,setWorldRotation} from './kinematics.js?v=planted-trip-1';
export const SIDE_TRIP_RULES=Object.freeze({plantUntil:.50,releaseUntil:.76,foldUntil:.45,hipDrop:.18,rollStart:.48});
const smooth=x=>{x=T.MathUtils.clamp(x,0,1);return x*x*(3-2*x)},v=(x=0,y=0,z=0)=>new T.Vector3(x,y,z);
const worldQ=b=>b.getWorldQuaternion(new T.Quaternion());
export function captureTripContact(actor,flight,floor){
 const lead=actor.feet.reduce((best,f)=>point(f.sole).sub(actor.group.position).dot(flight.heading)>point(best.sole).sub(actor.group.position).dot(flight.heading)?f:best),side=lead===actor.feet[0]?'L':'R',other=side==='L'?'R':'L',sole=point(lead.sole),anchor=sole.clone();
 // Preserve the actual impact footprint. A foot already entering the collider
 // is clamped to its near face; the rest of the body is free to fold above it.
 const b=flight.obstacleRef,offset=actor.group.position.clone().sub(flight.start),hit={x:b.x+offset.x,z:b.z+offset.z};
 for(const axis of ['x','z'])if(Math.abs(flight.heading[axis])>.65){const half=(axis==='x'?b.w:b.d)/2,sign=Math.sign(flight.heading[axis]),edge=hit[axis]-sign*(half+.055);anchor[axis]=sign>0?Math.min(anchor[axis],edge):Math.max(anchor[axis],edge)}
 anchor.y=floor+.018;
 const otherFoot=actor.feet[side==='L'?1:0],otherAnchor=point(otherFoot.sole);otherAnchor.y=floor+.018;
 const flex=()=>{const a=point(lead.hip).sub(point(lead.knee)).normalize(),b=point(lead.ankle).sub(point(lead.knee)).normalize();return Math.PI-a.angleTo(b)};
 return {side,other,anchor,otherAnchor,hip:point(actor.bones.PELVIS),hipRotation:worldQ(actor.bones.PELVIS),knee:point(lead.knee),initialKneeFlexion:flex(),pose:actor.bind.map(n=>({p:n.b.position.clone(),q:n.b.quaternion.clone()})),offset};
}
export function plantedSideTrip(actor,flight){
 const c=flight.contacts?.[actor.id];if(!c)return null;const t=flight.elapsed,fold=smooth(t/SIDE_TRIP_RULES.foldUntil),w=1-smooth((t-SIDE_TRIP_RULES.plantUntil)/(SIDE_TRIP_RULES.releaseUntil-SIDE_TRIP_RULES.plantUntil));
 if(w<=0)return {kind:'planted-side-trip',weight:0,side:c.side};
 const before=actor.bind.map(n=>({p:n.b.position.clone(),q:n.b.quaternion.clone()}));
 for(let i=0;i<actor.bind.length;i++){actor.bind[i].b.position.copy(c.pose[i].p);actor.bind[i].b.quaternion.copy(c.pose[i].q)}
 const sign=flight.kind==='side-left'?1:-1,groupQ=worldQ(actor.group),turn=new T.Quaternion().setFromAxisAngle(v(0,0,1),-sign*.48*fold),twist=new T.Quaternion().setFromAxisAngle(v(0,1,0),sign*.18*fold),target=groupQ.clone().multiply(twist).multiply(turn).multiply(actor.rig.rotations.PELVIS);
 setWorldRotation(actor.bones.PELVIS,c.hipRotation.clone().slerp(target,fold));
 const away=flight.destination.clone().sub(flight.start).setY(0).normalize(),hip=c.hip.clone().addScaledVector(away,.10*fold);hip.y-=SIDE_TRIP_RULES.hipDrop*fold;
 actor.bones.PELVIS.position.copy(actor.bones.PELVIS.parent.worldToLocal(hip));actor.asset.updateMatrixWorld(true);
 // The blocked ankle/sole is a hard contact during the yielding phase. IK
 // bends the actual hip and knee rather than moving/scaling the leg bones.
 const solve=(side,anchor,pole)=>{const ankle=actor.bones['ANKLE_'+side],sole=actor.bones['SOCKET_SOLE_'+side]||ankle,flat=groupQ.clone().multiply(actor.rig.rotations['ANKLE_'+side]);setWorldRotation(ankle,flat);const goal=anchor.clone().add(point(ankle).sub(point(sole)));return solveChain(actor.bones['HIP_'+side],actor.bones['KNEE_'+side],ankle,goal,flat,pole)};
 const forward=v(Math.sin(flight.facing),0,Math.cos(flight.facing)),pole=c.knee.clone().addScaledVector(forward,.16*fold),a=solve(c.side,c.anchor,pole),freeGoal=c.otherAnchor.clone().addScaledVector(away,.08*fold),b=solve(c.other,freeGoal,point(actor.bones['KNEE_'+c.other]).addScaledVector(forward,.10));
 for(let i=0;i<actor.bind.length;i++){const n=actor.bind[i].b;n.position.lerpVectors(before[i].p,n.position,w);n.quaternion.copy(before[i].q.clone().slerp(n.quaternion,w))}
 actor.asset.updateMatrixWorld(true);
 const sole=point(actor.bones['SOCKET_SOLE_'+c.side]||actor.bones['ANKLE_'+c.side]),knee=point(actor.bones['KNEE_'+c.side]),angle=Math.PI-point(actor.bones['HIP_'+c.side]).sub(knee).angleTo(point(actor.bones['ANKLE_'+c.side]).sub(knee));
 return {kind:'planted-side-trip',weight:w,side:c.side,anchor:c.anchor.toArray(),foot:sole.toArray(),footError:sole.distanceTo(c.anchor),kneeFlexion:angle,initialKneeFlexion:c.initialKneeFlexion,pelvisDeltaY:point(actor.bones.PELVIS).y-c.hip.y,length:Math.max(a.length,b.length),reach:Math.max(a.reach,b.reach)};
}
