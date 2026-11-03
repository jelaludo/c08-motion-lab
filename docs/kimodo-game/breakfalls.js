import * as T from 'three';
export const BREAKFALL_RULES=Object.freeze({minHeight:.12,maxHeight:.70,minSpeed:.65,recoveryFraction:.72,cooldownAfter:.8});
const smooth=x=>{x=T.MathUtils.clamp(x,0,1);return x*x*(3-2*x)};
export function breakfallPlan(world,position,velocity,facing,hits){
 const speed=velocity.length();if(speed<BREAKFALL_RULES.minSpeed)return null;
 const heading=velocity.clone().setY(0).normalize(),forward=new T.Vector3(Math.sin(facing),0,Math.cos(facing)),dot=heading.dot(forward);
 const floor=world.floor(position.x,position.z,position.y);if(Math.abs(position.y-floor)>.06)return null;
 for(const hit of hits){const b=hit.obstacle,h=b.top-floor;if(b.trip===false||b.bottom>floor+.05||h<BREAKFALL_RULES.minHeight)continue;
  if(Math.abs(dot)<.65){
   // A lateral stumble stays on the approach side: no roll through the object.
   const destination=position.clone().addScaledVector(heading,-.20);destination.y=floor;
   if(!world.fits(destination,1.85))continue;
   const side=heading.dot(new T.Vector3(Math.cos(facing),0,-Math.sin(facing)))>0?'L':'R';
   return {type:'stumble',kind:side==='L'?'side-left':'side-right',side,id:'game-land-hard',start:position.clone(),destination,facing,elapsed:0,duration:1.55,obstacle:b.name,obstacleRef:b};
  }
  if(h>BREAKFALL_RULES.maxHeight)continue;
  // Find the far side along travel, then leave room for the rolling torso.
  let far=Infinity;for(const axis of ['x','z'])if(Math.abs(heading[axis])>1e-6){const half=(axis==='x'?b.w:b.d)/2,edge=b[axis]+Math.sign(heading[axis])*half;far=Math.min(far,(edge-position[axis])/heading[axis])}
  if(!Number.isFinite(far)||far<0||far>2.5)continue;
  const clear=position.clone().addScaledVector(heading,far+.95),distance=Math.max(far+2.05,Math.min(4.8,speed*.5+2.0)),destination=position.clone().addScaledVector(heading,distance);destination.y=world.floor(destination.x,destination.z,position.y+.06);clear.y=b.top+.075;
  if(!world.fits(destination,1.85))continue;
  const plan={type:'ukemi',kind:dot<0?'backward':'forward',id:dot<0?'game-ukemi-backward':'game-ukemi-forward',start:position.clone(),clear,destination,top:b.top,facing,elapsed:0,duration:speed>4.8?1.95:speed>2?2.25:2.8,obstacle:b.name,obstacleRef:b};
  if([.10,.15,.25,.35,.50,.75,1].every(u=>world.fits(breakfallPosition({...plan,elapsed:u*plan.duration}),1.85)))return plan;
 }
 return null;
}
export function breakfallPosition(f){
 if(f.type==='stumble')return f.start.clone().lerp(f.destination,smooth(f.elapsed/.28));
 const u=T.MathUtils.clamp(f.elapsed/f.duration,0,1),up=smooth(u/.12),cross=smooth((u-.14)/.21),roll=smooth((u-.35)/.55),out=f.start.clone().lerp(f.clear,cross);out.lerp(f.destination,roll);
 out.y=T.MathUtils.lerp(f.start.y,f.top+.075,up);out.y=T.MathUtils.lerp(out.y,f.destination.y,smooth((u-.35)/.17));return out;
}
