import * as T from 'three';
import {point,solveChain,setWorldRotation} from './kinematics.js?v=momentum-trip-1';
export const SIDE_TRIP_RULES=Object.freeze({plantUntil:.50,releaseUntil:.76,foldUntil:.45,hipDrop:.18,rollStart:.48});
const smooth=x=>{x=T.MathUtils.clamp(x,0,1);return x*x*(3-2*x)},v=(x=0,y=0,z=0)=>new T.Vector3(x,y,z);
const worldQ=b=>b.getWorldQuaternion(new T.Quaternion());
// Sample torso skin, not the upright controller capsule, during a beam roll.
// Limbs receive their own leg solve; a foot touching the beam must not lift
// the entire body before it has fallen.
function torsoSamples(actor){
 if(actor.tripTorsoSamples)return actor.tripTorsoSamples;const samples=[];
 actor.asset.traverse(mesh=>{if(!mesh.isSkinnedMesh)return;const g=mesh.geometry,si=g.attributes.skinIndex,sw=g.attributes.skinWeight,pos=g.attributes.position,stride=Math.max(1,Math.floor(pos.count/1800));for(let i=0;i<pos.count;i+=stride){let torso=0,shoulder=0,shoulderBone=null;for(let j=0;j<4;j++){const bone=mesh.skeleton.bones[si.getComponent(i,j)],w=sw.getComponent(i,j);if(/^(PELVIS|CHEST|SPINE|NECK|HEAD)/.test(bone.name))torso+=w;else if(/^UPPER_ARM_[LR]$/.test(bone.name)){shoulder+=w;shoulderBone=bone}}if(torso>.6)samples.push({mesh,index:i});else if(shoulder>.6)samples.push({mesh,index:i,shoulderBone})}});
 return actor.tripTorsoSamples=samples;
}
function limbSamples(actor){
 if(actor.tripLimbSamples)return actor.tripLimbSamples;const groups={armL:[],armR:[],legL:[],legR:[]};
 actor.asset.traverse(mesh=>{if(!mesh.isSkinnedMesh)return;const g=mesh.geometry,si=g.attributes.skinIndex,sw=g.attributes.skinWeight,pos=g.attributes.position,stride=Math.max(1,Math.floor(pos.count/2200));for(let i=0;i<pos.count;i+=stride){const weights={armL:0,armR:0,legL:0,legR:0};for(let j=0;j<4;j++){const name=mesh.skeleton.bones[si.getComponent(i,j)].name,w=sw.getComponent(i,j),arm=name.match(/^(?:UPPER_ARM_|FOREARM_|HAND_|FINGER_|THUMB_)([LR])/),leg=name.match(/^(?:HIP_|KNEE_|ANKLE_|FOOT_|TOE_|SOCKET_SOLE_)([LR])/);if(arm)weights['arm'+arm[1]]+=w;else if(leg)weights['leg'+leg[1]]+=w}for(const key of Object.keys(groups))if(weights[key]>.6)groups[key].push({mesh,index:i})}});
 return actor.tripLimbSamples=groups;
}
export function beamRollContact(actor,flight){
 if(flight.path!=='planted-side-over'||flight.elapsed<SIDE_TRIP_RULES.releaseUntil)return null;
 const b=flight.obstacleRef,c=flight.contacts?.[actor.id],offset=c?.offset||v(),p=v();let minimum=Infinity,contacts=0;
 const inside=p=>Math.abs(p.x-b.x-offset.x)<b.w/2+.012&&Math.abs(p.z-b.z-offset.z)<b.d/2+.012;
 actor.asset.updateMatrixWorld(true);
 for(const {mesh,index,shoulderBone} of torsoSamples(actor)){p.fromBufferAttribute(mesh.geometry.attributes.position,index);mesh.applyBoneTransform(index,p);mesh.localToWorld(p);if(shoulderBone&&p.distanceTo(point(shoulderBone))>.20)continue;if(inside(p)){minimum=Math.min(minimum,p.y);contacts++}}
 const lift=contacts?Math.max(0,b.top+.015-minimum):0;
 if(lift>0){const hip=point(actor.bones.PELVIS);hip.y+=lift;actor.bones.PELVIS.position.copy(actor.bones.PELVIS.parent.worldToLocal(hip));actor.asset.updateMatrixWorld(true)}
 let length=0,reach=0;const limbs={},groups=limbSamples(actor),heading=flight.heading,axis=Math.abs(heading.x)>Math.abs(heading.z)?'x':'z',sign=Math.sign(heading[axis]),centre=(b[axis]+offset[axis])*sign,half=(axis==='x'?b.w:b.d)/2,near=centre-half,far=centre+half;
 const penetration=samples=>{let count=0,minY=Infinity,minAxis=Infinity,maxAxis=-Infinity;for(const {mesh,index} of samples){p.fromBufferAttribute(mesh.geometry.attributes.position,index);mesh.applyBoneTransform(index,p);mesh.localToWorld(p);if(inside(p)&&p.y>b.bottom-.05&&p.y<b.top+.012){count++;minY=Math.min(minY,p.y);minAxis=Math.min(minAxis,p[axis]*sign);maxAxis=Math.max(maxAxis,p[axis]*sign)}}return {count,minY,minAxis,maxAxis}};
 for(const kind of ['arm','leg'])for(const side of ['L','R']){const chain=kind==='arm'?['UPPER_ARM_','FOREARM_','HAND_']:['HIP_','KNEE_','ANKLE_'],a=actor.bones[chain[0]+side],mid=actor.bones[chain[1]+side],end=actor.bones[chain[2]+side],samples=groups[kind+side],rotation=worldQ(end);let hit=penetration(samples),first=hit.count,iterations=0;
  // Once the attachment is beyond a face, withdraw the trailing limb toward
  // that face. Do not raise the whole body merely to clear an arm or foot.
  while(hit.count&&iterations<6){iterations++;const parent=point(a)[axis]*sign,delta=v();if(parent>far+.025)delta[axis]=sign*(far-hit.minAxis+.035);else if(parent<near-.025)delta[axis]=-sign*(hit.maxAxis-near+.035);else delta.y=b.top+.035-hit.minY;
   const goal=point(end).add(delta),pole=point(mid).add(delta);pole.y+=.025;const result=solveChain(a,mid,end,goal,rotation,pole);length=Math.max(length,result.length);reach=Math.max(reach,result.reach);actor.asset.updateMatrixWorld(true);hit=penetration(samples);
  }
  limbs[kind+side]={initialContacts:first,remainingContacts:hit.count,clearance:hit.count?hit.minY-b.top:null,iterations};
 }
 return {torsoSamples:contacts,torsoMinBefore:Number.isFinite(minimum)?minimum:null,torsoLift:lift,torsoClearance:contacts?minimum+lift-b.top:null,limbs,length,reach};
}
export function captureTripContact(actor,flight,floor,referencePosition=flight.start){
 const lead=actor.feet.reduce((best,f)=>point(f.sole).sub(actor.group.position).dot(flight.heading)>point(best.sole).sub(actor.group.position).dot(flight.heading)?f:best),side=lead===actor.feet[0]?'L':'R',other=side==='L'?'R':'L',sole=point(lead.sole),anchor=sole.clone();
 // Preserve the actual impact footprint. A foot already entering the collider
 // is clamped to its near face; the rest of the body is free to fold above it.
 const b=flight.obstacleRef,offset=actor.group.position.clone().sub(referencePosition),hit={x:b.x+offset.x,z:b.z+offset.z};
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
 const fallDirection=flight.destination.clone().sub(flight.start).setY(0).normalize(),hip=c.hip.clone().addScaledVector(fallDirection,.10*fold);hip.y-=SIDE_TRIP_RULES.hipDrop*fold;
 actor.bones.PELVIS.position.copy(actor.bones.PELVIS.parent.worldToLocal(hip));actor.asset.updateMatrixWorld(true);
 // The blocked ankle/sole is a hard contact during the yielding phase. IK
 // bends the actual hip and knee rather than moving/scaling the leg bones.
 const solve=(side,anchor,pole)=>{const ankle=actor.bones['ANKLE_'+side],sole=actor.bones['SOCKET_SOLE_'+side]||ankle,flat=groupQ.clone().multiply(actor.rig.rotations['ANKLE_'+side]);setWorldRotation(ankle,flat);const goal=anchor.clone().add(point(ankle).sub(point(sole)));return solveChain(actor.bones['HIP_'+side],actor.bones['KNEE_'+side],ankle,goal,flat,pole)};
 const forward=v(Math.sin(flight.facing),0,Math.cos(flight.facing)),pole=c.knee.clone().addScaledVector(forward,.16*fold),a=solve(c.side,c.anchor,pole),freeGoal=c.otherAnchor.clone().addScaledVector(fallDirection,.08*fold),b=solve(c.other,freeGoal,point(actor.bones['KNEE_'+c.other]).addScaledVector(forward,.10));
 for(let i=0;i<actor.bind.length;i++){const n=actor.bind[i].b;n.position.lerpVectors(before[i].p,n.position,w);n.quaternion.copy(before[i].q.clone().slerp(n.quaternion,w))}
 actor.asset.updateMatrixWorld(true);
 const sole=point(actor.bones['SOCKET_SOLE_'+c.side]||actor.bones['ANKLE_'+c.side]),knee=point(actor.bones['KNEE_'+c.side]),angle=Math.PI-point(actor.bones['HIP_'+c.side]).sub(knee).angleTo(point(actor.bones['ANKLE_'+c.side]).sub(knee));
 return {kind:'planted-side-trip',weight:w,side:c.side,anchor:c.anchor.toArray(),foot:sole.toArray(),footError:sole.distanceTo(c.anchor),kneeFlexion:angle,initialKneeFlexion:c.initialKneeFlexion,pelvisDeltaY:point(actor.bones.PELVIS).y-c.hip.y,length:Math.max(a.length,b.length),reach:Math.max(a.reach,b.reach)};
}
