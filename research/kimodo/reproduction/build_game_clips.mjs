// Derive explicit, reproducible in-place game clips. Never edits a raw bake.
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';
const R='G:/Dev/Kimodo',N='G:/Dev/MotionBricks/tools/review/node_modules/three/';
const T=await import(pathToFileURL(N+'build/three.module.js'));
const {GLTFLoader}=await import(pathToFileURL(N+'examples/jsm/loaders/GLTFLoader.js'));
globalThis.self=globalThis;globalThis.createImageBitmap=async()=>({width:1,height:1,close(){}});globalThis.ProgressEvent??=class{constructor(t,p){Object.assign(this,p)}};
let source=JSON.parse(fs.readFileSync(R+'/game-derived/source-metadata.json'));
if(process.argv.includes('--partial'))source=Object.fromEntries(Object.entries(source).filter(([take])=>['c08','brek43'].every(b=>fs.existsSync(R+'/retarget/'+take+'/'+b+'/retarget-report.json'))));
const plan=JSON.parse(fs.readFileSync(R+'/tests-game.json')),page=R+'/web/kimodo-game';
for(const dir of ['clips','models','reports','packs'])fs.mkdirSync(page+'/'+dir,{recursive:true});
const bodies=[{id:'c08',label:'C08 Worker'},{id:'brek43',label:'B-REK43'}],entries=[],q=new T.Quaternion(),p=new T.Vector3();
const smooth=x=>x*x*(3-2*x),r6=x=>Math.round(x*1e6)/1e6;
for(const [take,meta]of Object.entries(source)){
 const entry={id:take,motion:meta.case.id,label:meta.case.label,group:meta.case.group,kind:meta.case.kind,seed:meta.seed,prompt:meta.case.prompt,version:1,method:'kimodo-game-kit',source_round:meta.source_round,source_sha256:meta.source_sha256,source_speed_m_s:meta.source_net_speed_m_s,desired_speed_m_s:meta.case.speed??0,direction:meta.case.direction,outputs:[]};
 for(const body of bodies){
  const folder=R+'/retarget/'+take+'/'+body.id,bytes=fs.readFileSync(folder+'/c08-mocap.glb');
  const report=JSON.parse(fs.readFileSync(folder+'/retarget-report.json'));
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  const clip=gltf.animations[0],tracks=clip.tracks.filter(t=>t.name.endsWith('.quaternion')||t.name==='PELVIS.position'),total=meta.frames;
  const samples=tracks.map(t=>{const size=t.getValueSize(),inter=t.createInterpolant(),values=[];for(let f=0;f<total;f++)values.push(Array.from(inter.evaluate(Math.min(f/30,clip.duration))));return {name:t.name,type:size===4?'quaternion':'vector',size,values}});
  // Gentle symmetric 3-tap rotation filter. Translation filter only on the pelvis.
  for(const t of samples){const old=t.values;t.values=old.map((v,i)=>{if(!i||i===total-1)return v;if(t.size===4){q.fromArray(old[i-1]).slerp(new T.Quaternion().fromArray(old[i+1]),.5).slerp(new T.Quaternion().fromArray(v),.8).normalize();return q.toArray()}return v.map((x,k)=>.8*x+.1*(old[i-1][k]+old[i+1][k]))})}
  const pelvis=samples.find(t=>t.name==='PELVIS.position');
  for(const v of pelvis.values){v[0]=0;v[2]=0}
  let start=0,end=total-1,blend=0,rawSeam=0;
  if(meta.case.kind==='loop'){
   const names=/^(HIP_|KNEE_|ANKLE_|UPPER_ARM_|FOREARM_|PELVIS\.)/;
   let best=Infinity;
   const idle=!meta.case.gait,min=idle?55:22,max=idle?100:80;
   for(let a=15;a<Math.min(65,total-max-1);a+=2)for(let len=min;len<=max;len++){
    const b=a+len;if(b>=total-10)continue;let score=0,count=0;
    for(const t of samples)if(t.size===4&&names.test(t.name)){const x=new T.Quaternion().fromArray(t.values[a]),y=new T.Quaternion().fromArray(t.values[b]);score+=x.angleTo(y)**2;count++}
    score=Math.sqrt(score/count)+Math.abs(pelvis.values[a][1]-pelvis.values[b][1])*2+(.005*min/len);
    if(score<best){best=score;start=a;end=b;rawSeam=score}
   }
   blend=Math.min(9,Math.floor((end-start)*.2));
  }else if(meta.jump){start=meta.jump.source_start_frame;end=meta.jump.source_end_frame}
  const first=start+blend,frames=end-first+1,duration=(frames-1)/30;
  const output=[];
  for(const t of samples){const values=[];for(let i=first;i<=end;i++){
   let value=t.values[i].slice();
   if(blend&&i>=end-blend){const u=smooth((i-(end-blend))/blend),target=t.values[start+i-(end-blend)];if(t.size===4)value=new T.Quaternion().fromArray(value).slerp(new T.Quaternion().fromArray(target),u).normalize().toArray();else value=value.map((x,k)=>x+(target[k]-x)*u)}
   // A controller supplies jump height. Preserve the source anticipation and landing,
   // but remove the airborne root arc to avoid adding the same height twice.
   if(meta.jump&&t.name==='PELVIS.position'){
    const a=start+Math.round(meta.jump.takeoff_s*30),b=start+Math.round(meta.jump.landing_s*30);
    if(i>=a&&i<=b){const u=(i-a)/Math.max(1,b-a);value[1]=pelvis.values[a][1]*(1-u)+pelvis.values[b][1]*u}
   }
   values.push(...value.map(r6));
  }if(blend)for(let k=0;k<t.size;k++)values[(frames-1)*t.size+k]=values[k];
   output.push({name:t.name,type:t.type,times:Array.from({length:frames},(_,i)=>r6(i/30)),values});
  }
  output.push({name:'MOTION.position',type:'vector',times:[0,r6(duration)],values:[0,0,0,0,0,0]});
  const contacts=[];for(let i=first;i<=end;i++){let c=meta.source_contacts[i].slice();if(blend&&i>=end-blend){const u=smooth((i-(end-blend))/blend),target=meta.source_contacts[start+i-(end-blend)];c=c.map((v,k)=>v+(target[k]-v)*u)}contacts.push([r6(Math.max(...c.slice(0,3))),r6(Math.max(...c.slice(3)))])}if(blend)contacts[contacts.length-1]=contacts[0].slice();
  const box=new T.Box3().setFromObject(gltf.scene,true),height=box.getSize(new T.Vector3()).y;
  const rootTrack=clip.tracks.find(t=>t.name==='MOTION.position'),ri=rootTrack.createInterpolant();
  const a=Array.from(ri.evaluate(first/30)),b=Array.from(ri.evaluate(end/30));
  const speed=Math.hypot(b[0]-a[0],b[2]-a[2])/Math.max(.01,duration);
  const phase=meta.jump?{...meta.jump}:null;
  const data={schema:'kimodo-game-clip/1',recipe:1,name:take+'-'+body.id,duration:r6(duration),fps:30,loop:meta.case.kind==='loop',tracks:output,contacts,jump:phase,measured_target_speed_m_s:speed,bind_height_m:height,raw_seam_score:rawSeam,source_window:[first,end],source_sha256:meta.source_sha256,processing:['30Hz resample','symmetric 3-tap rotation filter (80% center)','in-place horizontal root','loop phase search and overlap crossfade for cyclic states only','jump airborne root arc delegated to controller; anticipation and landing retained'],limitations:['Loop seam closure does not certify foot contacts or physical balance.','Runtime foot/hand IK and controller travel are not baked into this individual in-place clip.']};
  const stem=take+'-'+body.id;fs.writeFileSync(page+'/clips/'+stem+'.json',JSON.stringify(data));
  fs.copyFileSync(folder+'/c08-mocap.glb',page+'/models/'+stem+'-source.glb');
  const qa={recipe:1,raw_report:report,derived:{frames,duration_s:duration,loop:!!blend,source_window:[first,end],raw_seam_score:rawSeam,measured_target_speed_m_s:speed,jump:phase},limitations:data.limitations};
  delete qa.raw_report.sample_positions_blender;fs.writeFileSync(page+'/reports/'+stem+'.json',JSON.stringify(qa));
  entry.outputs.push({body:body.id,clip:'clips/'+stem+'.json',source_glb:'models/'+stem+'-source.glb',report:'reports/'+stem+'.json',raw_seam_score:rawSeam,bind_height_m:height,measured_target_speed_m_s:speed,jump:phase});
  gltf.scene.traverse(o=>{o.geometry?.dispose();for(const m of o.material?(Array.isArray(o.material)?o.material:[o.material]):[])m.dispose()});
 }
 entries.push(entry);console.log('DERIVED',take);
}
for(const b of bodies)b.model=(entries.find(e=>e.motion==='game-idle')||entries[0]).outputs.find(o=>o.body===b.id).source_glb;
const catalog={schema:'kimodo-game-kit/1',recipe:1,bodies,seeds:plan.seeds,motions:plan.cases.filter(c=>entries.some(e=>e.motion===c.id)).map(c=>({id:c.id,label:c.label,group:c.group,kind:c.kind,direction:c.direction,speed:c.speed})),takes:entries,scope:'Candidate game-motion kit. Source takes preserved; derived in-place loops and one-shots. C08 and B-REK43 only. Runtime transitions, contact IK, collision controller and props require visual acceptance.',backlog:['Swim and underwater locomotion','Ranged weapon rigs / reloads / aim offsets','Vehicle, rope and grapple interactions','Magic / flight / transformations','Paired combat and verified environmental hand contacts'],review_collection:'kimodo-game-kit-v1'};
fs.writeFileSync(page+'/catalog.json',JSON.stringify(catalog,null,2));
console.log('Game kit built:',entries.length,'takes',entries.length*2,'body clips');
