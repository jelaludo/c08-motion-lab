import * as T from 'three';
import {CONTACT_RULES} from './contact-actions.js?v=contact-actions-1';

// Deliberately tagged surfaces only: roofs, props and perimeter walls cannot
// become traversal targets merely because they happen to be close to Space.
export function traversalTarget(world, position, heading) {
 const dir=heading.clone().setY(0).normalize();if(dir.lengthSq()<.5)return null;
 const candidates=[];
 for(const b of world.obstacles){
  if(!b.traversal||Math.abs(b.bottom-position.y)>.12)continue;
  let near=-Infinity,far=Infinity,valid=true;
  for(const axis of ['x','z']){
   const half=(axis==='x'?b.w:b.d)/2,lo=b[axis]-half,hi=b[axis]+half,d=dir[axis];
   if(Math.abs(d)<1e-7){if(position[axis]<lo+.30||position[axis]>hi-.30)valid=false;continue}
   const p=(lo-position[axis])/d,q=(hi-position[axis])/d;near=Math.max(near,Math.min(p,q));far=Math.min(far,Math.max(p,q));
  }
  const h=b.top-position.y,vault=b.traversal==='vault',ledge=!vault&&h>=1.9,range=vault?1.65:1.05;
  if(!valid||near>far||near<.28||near>range||h<.25||h>(vault?1:CONTACT_RULES.maxLedgeHeight)||vault&&far-near>1.8)continue;
  const destination=position.clone().addScaledVector(dir,vault?far+.5:near+.48);destination.y=vault?world.floor(destination.x,destination.z,position.y):b.top;
  if(!world.fits(destination,1.85))continue;
  const edge=position.clone().addScaledVector(dir,near);edge.y=b.top;
  if(ledge&&((Math.abs(edge.z-b.z)>b.d/2-.01&&Math.abs(edge.x-b.x)>b.w/2-.55)||(Math.abs(edge.x-b.x)>b.w/2-.01&&Math.abs(edge.z-b.z)>b.d/2-.55)))continue;
  candidates.push({type:vault?'vault':ledge?'ledge':'mantle',id:vault?'game-vault':'game-mantle',label:vault?'Vault barrier':ledge?'Jump / grab ledge / pull up':'Climb onto wall',obstacle:b.name,edge,destination,top:b.top,distance:near,duration:vault?.84:ledge?CONTACT_RULES.ledgeDuration:1.18});
 }
 return candidates.sort((a,b)=>a.distance-b.distance)[0]||null;
}

export function traversalPosition(flight) {
 const u=T.MathUtils.clamp(flight.elapsed/flight.duration,0,1),s=x=>{x=T.MathUtils.clamp(x,0,1);return x*x*(3-2*x)};
 if(flight.type==='ledge'){
  const t=flight.elapsed,part=(a,b)=>s((t-a)/(b-a)),dir=flight.destination.clone().sub(flight.start).setY(0).normalize(),approach=flight.edge.clone().addScaledVector(dir,-.31),out=flight.start.clone().lerp(approach,part(.07,.42));
  const hang=flight.hangY,catchLift=T.MathUtils.lerp(flight.start.y,hang,part(.13,.46))+.10*Math.sin(Math.PI*part(.13,.60));
  out.y=T.MathUtils.lerp(catchLift,flight.top-.40,part(.97,1.64));out.y=T.MathUtils.lerp(out.y,flight.top+.14,part(1.64,1.93));out.lerp(flight.destination,part(1.93,2.25));out.y=T.MathUtils.lerp(out.y,flight.destination.y,part(2.25,2.45));return out;
 }
 const mantle=flight.type==='mantle';
 if(mantle){
  const dir=flight.destination.clone().sub(flight.start).setY(0).normalize(),approach=flight.edge.clone().addScaledVector(dir,-.34),out=flight.start.clone().lerp(approach,s(u/.18));
  out.lerp(flight.destination,s((u-.77)/.17));
  const hang=Math.max(flight.start.y,flight.top-.9),lift=T.MathUtils.lerp(flight.start.y,hang,s((u-.12)/.27));
  out.y=T.MathUtils.lerp(lift,flight.top+.14,s((u-.4)/.36));out.y=T.MathUtils.lerp(out.y,flight.destination.y,s((u-.9)/.1));return out;
 }
 const cross=s((u-.25)/.5),out=flight.start.clone().lerp(flight.destination,cross);
 const peak=flight.top+.36,up=s(u/.3),down=s((u-.78)/.22);
 out.y=T.MathUtils.lerp(T.MathUtils.lerp(flight.start.y,peak,up),flight.destination.y,down);
 return out;
}
