// Derive lateral fall candidates independently; preserve every earlier take.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {pathToFileURL} from 'node:url';
const R=process.env.KIMODO_WORKSPACE||'G:/Dev/Kimodo',M=process.env.MOTION_REVIEW_NODE_MODULES||'G:/Dev/MotionBricks/tools/review/node_modules',T=await import(pathToFileURL(path.join(M,'three/build/three.module.js'))),{GLTFLoader}=await import(pathToFileURL(path.join(M,'three/examples/jsm/loaders/GLTFLoader.js')));
globalThis.self=globalThis;globalThis.createImageBitmap=async()=>({width:1,height:1,close(){}});globalThis.ProgressEvent??=class{constructor(t,p){Object.assign(this,p)}};
const read=f=>JSON.parse(fs.readFileSync(f)),page=path.join(R,'web/kimodo-game'),catalog=read(path.join(page,'catalog.json')),entries=[],qa=[],bodies=['c08','brek43'],start=0,end=149,frames=150,duration=(frames-1)/30;
const specs=['left','right'].flatMap(side=>[4411,5522,6633].map(seed=>({id:'game-ukemi-side-'+side,source:'game-ukemi-side-'+side+'-seed'+seed,side,seed,round:'game-side-ukemi',label:'Side ukemi / '+side})));
const r6=x=>Math.round(x*1e6)/1e6,hash=b=>crypto.createHash('sha256').update(b).digest('hex');
// Check all inputs before writing output or modifying the catalog.
for(const spec of specs){for(const file of [`outputs/${spec.round}/${spec.source}/report.json`,`outputs/${spec.round}/${spec.source}/constraints.json`,...bodies.flatMap(body=>[`retarget/${spec.source}/${body}/retarget-report.json`,`retarget/${spec.source}/${body}/c08-mocap.glb`,`retarget/${spec.source}/${body}/source-preview.json`])])if(!fs.existsSync(path.join(R,file)))throw Error('Missing side-ukemi input: '+file)}
for(const spec of specs){
 const generation=read(path.join(R,'outputs',spec.round,spec.source,'report.json')),constraints=read(path.join(R,'outputs',spec.round,spec.source,'constraints.json')),standing=constraints.find(c=>c.type==='fullbody'&&c.frame_indices.includes(0)).root_positions[0][1],sourceDiagnostics={...generation.diagnostics,standing_hip_y_m:standing,hip_drop_m:standing-generation.diagnostics.min_hip_y_m};
 const automatic=sourceDiagnostics.hip_drop_m>=.25&&sourceDiagnostics.max_lateral_tilt>=.6;
 const limitations=automatic?['Candidate lateral roll/breakfall; ground contact and technique require visual review.']:['Source does not meet the minimum hip-drop and lateral-tilt screen; retained for manual preview only.'];
 const take={id:spec.source,motion:spec.id,label:spec.label,group:'ground',kind:'action',seed:spec.seed,version:1,method:'kimodo-game-side-ukemi',source_take:spec.source,source_round:spec.round,source_sha256:generation.motion_sha256,prompt:generation.case.prompt,style:generation.case.style,automatic_eligible:automatic,outputs:[],limitations};
 for(const body of bodies){
  const dir=path.join(R,'retarget',spec.source,body),report=read(path.join(dir,'retarget-report.json')),bytes=fs.readFileSync(path.join(dir,'c08-mocap.glb')),g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  if(report.frames!==150)throw Error('Expected 150 frames for '+spec.source+'/'+body+', got '+report.frames);
  const clip=g.animations[0],tracks=clip.tracks.filter(t=>t.name.endsWith('.quaternion')||['PELVIS.position','MOTION.position'].includes(t.name));
  const dataTracks=tracks.map(t=>{const inter=t.createInterpolant(),values=[];for(let f=start;f<=end;f++){const value=Array.from(inter.evaluate(Math.min(f/30,clip.duration)));if(t.name==='MOTION.position')value.fill(0);if(t.name==='PELVIS.position'){value[0]=0;value[2]=0}values.push(...value)}return {name:t.name,type:t.getValueSize()===4?'quaternion':'vector',times:Array.from({length:frames},(_,i)=>r6(i/30)),values}});
  const pelvis=dataTracks.find(t=>t.name==='PELVIS.position');if(!pelvis)throw Error('Missing pelvis track');
  const geometry=[];g.scene.updateMatrixWorld(true);g.scene.traverse(o=>{if(!o.isSkinnedMesh)return;geometry.push({mesh:o,pos:o.geometry.attributes.position,si:o.geometry.attributes.skinIndex,sw:o.geometry.attributes.skinWeight})});
  const derived=new T.AnimationClip(take.id,duration,dataTracks.map(t=>new(t.type==='quaternion'?T.QuaternionKeyframeTrack:T.VectorKeyframeTrack)(t.name,t.times,t.values))),mix=new T.AnimationMixer(g.scene),action=mix.clipAction(derived);action.setLoop(T.LoopOnce,1);action.clampWhenFinished=true;action.play();
  const required=[];
  for(let f=0;f<frames;f++){
   action.enabled=true;action.paused=false;mix.setTime(f/30);g.scene.updateMatrixWorld(true);let low=Infinity;
   for(const {mesh,pos,si,sw} of geometry){
    const base=new T.Matrix4().multiplyMatrices(mesh.matrixWorld,mesh.bindMatrixInverse),rows=mesh.skeleton.bones.map((bone,j)=>{const e=new T.Matrix4().multiplyMatrices(base,bone.matrixWorld).multiply(mesh.skeleton.boneInverses[j]).multiply(mesh.bindMatrix).elements;return [e[1],e[5],e[9],e[13]]});
    for(let i=0;i<pos.count;i++){const x=pos.getX(i),y=pos.getY(i),z=pos.getZ(i);let yy=0;for(let k=0;k<4;k++){const w=sw.getComponent(i,k);if(w){const row=rows[si.getComponent(i,k)];yy+=w*(row[0]*x+row[1]*y+row[2]*z+row[3])}}low=Math.min(low,yy)}
   }
   if(!Number.isFinite(low))throw Error('Nonfinite full-skin floor sample');required.push(.012-low);
  }
  // Identical sampled full-skin clearance recipe as the earlier approved ukemi.
  // This target cleanup is separate from the immutable retargeted raw source.
  const dilation=required.map((_,i)=>Math.max(...required.slice(Math.max(0,i-2),Math.min(frames,i+3)))),curve=dilation.map((_,i)=>{let total=0,w=0;for(let j=-2;j<=2;j++){const weight=[1,4,6,4,1][j+2];total+=dilation[Math.max(0,Math.min(frames-1,i+j))]*weight;w+=weight}return Math.max(required[i],total/w)});
  for(let f=0;f<frames;f++)pelvis.values[f*3+1]+=curve[f];for(const t of dataTracks)t.values=t.values.map(r6);
  const raw=read(path.join(dir,'source-preview.json')).contacts,contacts=Array.from({length:frames},(_,i)=>{const c=raw[Math.min(raw.length-1,start+i)]||[0,0],h=Math.ceil(c.length/2);return [Math.max(...c.slice(0,h)),Math.max(...c.slice(h))]});
  const samples=report.sample_positions_blender,offsets=samples.map(p=>p.HEAD[0]-p.PELVIS[0]),targetDiagnostics={head_side_offset_min_m:Math.min(...offsets),head_side_offset_max_m:Math.max(...offsets),hip_drop_m:samples[0].PELVIS[2]-Math.min(...samples.map(p=>p.PELVIS[2]))};
  const stem=take.id+'-'+body,data={schema:'kimodo-game-clip/1',recipe:1,name:stem,duration:r6(duration),fps:30,loop:false,tracks:dataTracks,contacts,jump:null,action_window:{start:0,end:r6(duration),duration:3.6},measured_target_speed_m_s:0,bind_height_m:body==='c08'?2.2854126167:2.7090001662,source_window:[start,end],source_sha256:take.source_sha256,processing:['Immutable generated/retargeted source preserved','In-place horizontal root','Full 150-frame source window retains idle anticipation and recovery keyframes','Target full-skin floor clearance envelope at 30Hz; not a support/balance solve'],limitations};
  const compact={schema:'side-ukemi-game-derivation/1',take:take.id,source_take:spec.source,body,side:spec.side,style:take.style,source_motion_sha256:take.source_sha256,source_asset_sha256:report.source_asset_sha256,source_glb_sha256:hash(bytes),source_window:[start,end],frames,source_diagnostics:sourceDiagnostics,target_diagnostics:targetDiagnostics,automatic_screen:{min_hip_drop_m:.25,min_lateral_tilt:.6,passed:automatic},floor_cleanup:{min_correction_m:Math.min(...curve),max_correction_m:Math.max(...curve),sampled_clearance_lower_bound_m:.012},conditioning:generation.conditioning,automatic_eligible:automatic,scope:'New Kimodo source prediction with native idle endpoint constraints. Target floor cleanup is authored and sampled; it does not validate support/balance, full environment collision or judo technique.'};
  fs.writeFileSync(path.join(page,'clips',stem+'.json'),JSON.stringify(data));fs.copyFileSync(path.join(dir,'c08-mocap.glb'),path.join(page,'models',stem+'-source.glb'));fs.writeFileSync(path.join(page,'reports',stem+'.json'),JSON.stringify(compact,null,2));take.outputs.push({body,clip:'clips/'+stem+'.json',source_glb:'models/'+stem+'-source.glb',report:'reports/'+stem+'.json',bind_height_m:data.bind_height_m,measured_target_speed_m_s:0,jump:null});qa.push(compact);console.log('DERIVED',stem,'frames',frames,'automatic',automatic,'skin correction',Math.max(...curve).toFixed(3));
  g.scene.traverse(o=>{o.geometry?.dispose();for(const m of o.material?(Array.isArray(o.material)?o.material:[o.material]):[])m.dispose()});
 }
 entries.push(take);
}
const before=catalog.takes.filter(t=>!t.motion.startsWith('game-ukemi-side-')),motionRows=['left','right'].map(side=>({id:'game-ukemi-side-'+side,label:'Side ukemi / '+side,group:'ground',kind:'action',addon:true,default_seed:4411}));
catalog.takes=before.concat(entries);catalog.motions=catalog.motions.filter(m=>!m.id.startsWith('game-ukemi-side-')).concat(motionRows);catalog.seeds=[...new Set(catalog.takes.map(t=>t.seed))].sort((a,b)=>a-b);fs.writeFileSync(path.join(page,'catalog.json'),JSON.stringify(catalog,null,2));
fs.writeFileSync(path.join(R,'logs/side-ukemi-derivation-validation.json'),JSON.stringify({status:'derived',new_motion_types:2,takes:entries.length,body_clips:qa.length,preserved_existing_takes:before.length,automatic_takes:entries.filter(t=>t.automatic_eligible).map(t=>t.id),results:qa},null,2));
console.log('Side ukemi derived:',entries.length,'takes;',before.length,'earlier takes preserved.');
