import * as T from 'three';
export const BREAKFALL_RULES=Object.freeze({minHeight:.12,maxHeight:.70,minSpeed:.65,recoveryFraction:.72,cooldownAfter:.8});
const smooth=x=>{x=T.MathUtils.clamp(x,0,1);return x*x*(3-2*x)};
export function breakfallPlan(world,position,velocity,facing,hits){
 const speed=velocity.length();if(speed<BREAKFALL_RULES.minSpeed)return null;
 const heading=velocity.clone().setY(0).normalize(),forward=new T.Vector3(Math.sin(facing),0,Math.cos(facing)),dot=heading.dot(forward);
 const floor=world.floor(position.x,position.z,position.y);if(Math.abs(position.y-floor)>.06)return null;
 for(const hit of hits){const b=hit.obstacle,h=b.top-floor;if(b.trip===false||b.bottom>floor+.05||h<BREAKFALL_RULES.minHeight)continue;
  const lateral=Math.abs(dot)<.65,bodyLeft=new T.Vector3(Math.cos(facing),0,-Math.sin(facing)),sideOf=d=>d.dot(bodyLeft)>0?'left':'right';
  if(lateral&&h<=BREAKFALL_RULES.maxHeight){
   let far=Infinity;for(const axis of ['x','z'])if(Math.abs(heading[axis])>1e-6){const half=(axis==='x'?b.w:b.d)/2;far=Math.min(far,(b[axis]+Math.sign(heading[axis])*half-position[axis])/heading[axis])}
   if(!Number.isFinite(far)||far<0||far>2.5)continue;
   const destination=position.clone().addScaledVector(heading,far+2.05);destination.y=world.floor(destination.x,destination.z,position.y+.06);
   const side=sideOf(heading),plan={type:'ukemi',path:'planted-side-over',kind:'side-'+side,id:'game-ukemi-side-'+side,start:position.clone(),destination,facing,heading,elapsed:0,duration:3.6,obstacle:b.name,obstacleRef:b,redirected:false};
   // A lying/rolling body is not an upright capsule. The target beam is
   // handled by pose contacts; all OTHER solid geometry still blocks travel.
   if([.05,.15,.3,.5,.75,1].every(u=>world.fits(breakfallPosition({...plan,elapsed:u*plan.duration}),1.85,.27,b)))return plan;
   continue;
  }
  if(lateral){
   // The impacting leg stops at the object. Buckle into clear approach-side
   // space instead of raising the entire actor over the hurdle like a vault.
   const away=heading.clone().negate(),destination=position.clone().addScaledVector(away,2.2);destination.y=world.floor(destination.x,destination.z,position.y+.06);
   const side=sideOf(away),plan={type:'ukemi',path:'planted-side-roll',kind:'side-'+side,id:'game-ukemi-side-'+side,start:position.clone(),destination,facing,heading,elapsed:0,duration:3.6,obstacle:b.name,obstacleRef:b,redirected:true};
   if([.05,.15,.3,.5,.75,1].every(u=>world.fits(breakfallPosition({...plan,elapsed:u*plan.duration}),1.85)))return plan;
   continue;
  }
  if(h>BREAKFALL_RULES.maxHeight)continue;
  // Find the far side along travel, then leave room for the rolling torso.
  let far=Infinity;for(const axis of ['x','z'])if(Math.abs(heading[axis])>1e-6){const half=(axis==='x'?b.w:b.d)/2,edge=b[axis]+Math.sign(heading[axis])*half;far=Math.min(far,(edge-position[axis])/heading[axis])}
  if(!Number.isFinite(far)||far<0||far>2.5)continue;
  const clear=position.clone().addScaledVector(heading,far+.95),distance=Math.max(far+2.05,Math.min(4.8,speed*.5+2.0)),destination=position.clone().addScaledVector(heading,distance);destination.y=world.floor(destination.x,destination.z,position.y+.06);clear.y=b.top+.075;
  if(!world.fits(destination,1.85))continue;
  const kind=lateral?'side-'+sideOf(heading):dot<0?'backward':'forward';
  const plan={type:'ukemi',kind,id:'game-ukemi-'+kind,start:position.clone(),clear,destination,top:b.top,facing,elapsed:0,duration:lateral?3.6:speed>4.8?1.95:speed>2?2.25:2.8,obstacle:b.name,obstacleRef:b};
  if([.10,.15,.25,.35,.50,.75,1].every(u=>world.fits(breakfallPosition({...plan,elapsed:u*plan.duration}),1.85)))return plan;
 }
 return null;
}
export function breakfallPosition(f){
 if(f.path==='planted-side-roll'||f.path==='planted-side-over')return f.start.clone().lerp(f.destination,smooth((f.elapsed-.48)/2.65));
 const u=T.MathUtils.clamp(f.elapsed/f.duration,0,1),up=smooth(u/.12),cross=smooth((u-.14)/.21),roll=smooth((u-.35)/.55),out=f.start.clone().lerp(f.clear,cross);out.lerp(f.destination,roll);
 out.y=T.MathUtils.lerp(f.start.y,f.top+.075,up);out.y=T.MathUtils.lerp(out.y,f.destination.y,smooth((u-.35)/.17));return out;
}
