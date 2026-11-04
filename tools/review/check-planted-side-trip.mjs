import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const M=process.env.MOTION_REVIEW_NODE_MODULES||path.join(ROOT,'tools/review/node_modules');
const {chromium}=await import(pathToFileURL(path.join(M,'playwright/index.mjs')));
const ART=process.env.PLANTED_TRIP_QA_ART||path.join(os.tmpdir(),'motion-planted-side-trip');
const out=process.env.PLANTED_TRIP_QA_OUT||path.join(ROOT,'research/kimodo/planted-side-trip-validation.json');
const url=process.argv.find(a=>/^https?:/.test(a))||'http://127.0.0.1:8802/kimodo-game/?controls=hybrid';
const record=process.argv.includes('--record'),checks=[],errors=[];
fs.mkdirSync(ART,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-background-timer-throttling']});
const p=await browser.newPage({viewport:{width:1440,height:900},acceptDownloads:true});
p.on('pageerror',e=>errors.push(e.message));
if(process.argv.includes('--staged'))await p.route('https://raw.githubusercontent.com/jelaludo/c08-motion-lab/main/research/kimodo/assets/**',route=>route.fulfill({path:path.join(ROOT,'research/kimodo/assets',new URL(route.request().url()).pathname.split('/').at(-1)),headers:{'access-control-allow-origin':'*'}}));
const assert=(value,message)=>{if(!value)throw Error(message)};
const settle=()=>p.waitForFunction(()=>window.GameLab?.actors.length===2&&GameLab.actors.every(a=>a.data)&&GameLab.loadJobs===0,null,{timeout:120000});
async function step(seconds,input=null,dt=.025){
 for(let i=0;i<Math.ceil(seconds/dt);i++){
  await p.evaluate(({input,dt})=>GameLab.advance(dt,input??GameLab.controlInput()),{input,dt});
  if(i%10===0)await settle();
 }
 await settle();
}
async function release(){for(const key of ['a','d','s','w','Control','ControlRight'])await p.keyboard.up(key)}
async function reset(body){
 await release();
 await p.evaluate(body=>{
  GameLab.reset();document.querySelector('#body').value=body;
  document.querySelector('#zones').checked=false;
  document.querySelector('#companion').checked=true;document.querySelector('#companion').dispatchEvent(new Event('change'));
 },body);
 await settle();await p.locator('#game').focus();
}
async function impact(body,inputSide,seed,{tall=false,recording=false}={}){
 await reset(body);
 const fallSide=inputSide==='left'?'right':'left',id='game-ukemi-side-'+fallSide;
 await p.evaluate(({inputSide,id,seed,tall})=>{
  document.querySelector('#variety').checked=false;document.querySelector('#variety').dispatchEvent(new Event('change'));
  for(const actor of GameLab.actors)GameLab.state.preferred[actor.id+':'+id]=seed;
  if(tall){GameLab.setPosition(-17,23.5);GameLab.state.yaw=-Math.PI/2;GameLab.state.facing=-Math.PI/2}
  else GameLab.startTrial('trip-side-'+inputSide);
 },{inputSide,id,seed,tall});
 if(recording)await p.evaluate(()=>GameLab.startRecording());
 await p.keyboard.down('Control');await p.keyboard.down(inputSide==='left'?'a':'d');
 let found=false;
 for(let i=0;i<220;i++){
  await step(.025);
  if(await p.evaluate(()=>GameLab.state.flight?.type==='ukemi'&&GameLab.state.flight.kind.startsWith('side-'))){found=true;break}
 }
 await release();assert(found,'No planted side collision '+body+' '+inputSide+' seed'+seed);
 await settle();
 const selected=await p.evaluate(()=>({kind:GameLab.state.flight.kind,id:GameLab.state.action.id,take:GameLab.active.take.id,seed:GameLab.active.take.seed,start:GameLab.state.flight.start.toArray(),destination:GameLab.state.flight.destination.toArray(),duration:GameLab.state.flight.duration}));
 assert(selected.kind==='side-'+fallSide&&selected.id===id&&selected.seed===seed,'Wrong away-side take '+JSON.stringify(selected));
 assert(selected.destination[2]<selected.start[2]-1.5,'Reaction destination is not on the clear approach side '+JSON.stringify(selected));
 return selected;
}
async function sample(){return p.evaluate(()=>{
 const f=GameLab.state.flight;
 if(!f)throw Error('Contact flight ended before sample');
 const primary=GameLab.active;
 return {time:f.elapsed,root:GameLab.state.position.toArray(),kind:f.kind,actors:GameLab.actors.map(a=>{
  const c=f.contacts?.[a.id];if(!c)throw Error('Missing per-body impact contact '+a.id);
  const side=c.side;if(!['L','R'].includes(side))throw Error('Missing contact leg side '+a.id);
  const anchor=c.anchor||c.anchorSole;if(!anchor?.isVector3)throw Error('Missing world sole anchor '+a.id);
  const v=GameLab.state.position.clone(),point=name=>a.bones[name].getWorldPosition(v.clone());
  const hip=point('HIP_'+side),knee=point('KNEE_'+side),ankle=point('ANKLE_'+side),sole=point(a.bones['SOCKET_SOLE_'+side]?'SOCKET_SOLE_'+side:'ANKLE_'+side),pelvis=point('PELVIS');
  const thigh=hip.clone().sub(knee),calf=ankle.clone().sub(knee),cos=Math.max(-1,Math.min(1,thigh.dot(calf)/(thigh.length()*calf.length()))),kneeFlexion=Math.PI-Math.acos(cos);
  const relativeOffset=a.group.position.clone().sub(primary.group.position),b=f.obstacleRef;
  // Both action trials approach the near Z face; the comparison is an offset mirror.
  const face=b.z-b.d/2+relativeOffset.z;
  return {body:a.id,side,anchor:anchor.toArray(),sole:sole.toArray(),footError:sole.distanceTo(anchor),pelvisY:pelvis.y,kneeFlexion,hipAnkleDistance:hip.distanceTo(ankle),thigh:thigh.length(),calf:calf.length(),planeOvershoot:sole.z-face,take:a.take.id,seed:a.take.seed,diagnostics:GameLab.state.contactDiagnostics[a.id]};
 })};
})}
async function screen(name){
 const compare=await p.evaluate(()=>{const e=document.querySelector('#companion'),was=e.checked;e.checked=false;e.dispatchEvent(new Event('change'));GameLab.state.yaw=0;GameLab.state.distance=3.8;GameLab.state.pitch=.3;GameLab.advance(0,{});return was});
 await p.waitForTimeout(220);await p.screenshot({path:path.join(ART,name+'.png')});
 await p.evaluate(compare=>{const e=document.querySelector('#companion');e.checked=compare;e.dispatchEvent(new Event('change'));GameLab.advance(0,{})},compare);
}
async function saveRecording(body){
 await p.evaluate(()=>GameLab.stopRecording());
 const glb=p.waitForEvent('download',d=>d.suggestedFilename().endsWith('.glb')),json=p.waitForEvent('download',d=>d.suggestedFilename().endsWith('.json'));
 await p.click('#download-record');
 const name=body+'-planted-side-trip',file=path.join(ART,name+'.glb');
 await(await glb).saveAs(file);await(await json).saveAs(path.join(ART,name+'.json'));
 const meta=JSON.parse(fs.readFileSync(path.join(ART,name+'.json'))),validator=(await import(pathToFileURL(path.join(M,'gltf-validator/index.js')))).default;
 const qa=await validator.validateBytes(new Uint8Array(fs.readFileSync(file)),{maxIssues:100});
 assert(!qa.issues.numErrors&&!qa.issues.numWarnings,'Planted trip export is invalid '+JSON.stringify(qa.issues));
 assert(meta.events.some(e=>e.type==='variant-choice'&&e.seeds)&&meta.events.some(e=>e.type==='side-object-ukemi'),'Recorded reaction/seed trace missing');
 return {file:name+'.glb',bytes:fs.statSync(file).size,gltf_errors:qa.issues.numErrors,gltf_warnings:qa.issues.numWarnings,seed_trace:true};
}
try{
 await p.goto(url);await settle();await p.evaluate(()=>GameLab.setManual());
 for(const body of ['c08','brek43']){
  await reset(body);
  for(const side of ['left','right']){
   const id='game-ukemi-side-'+side;
   const variety=await p.evaluate(async id=>{
    document.querySelector('#variety').checked=true;document.querySelector('#variety').dispatchEvent(new Event('change'));
    const pool=GameLab.eligibleTakes(id).map(t=>t.seed),draws=[];
    for(let i=0;i<6;i++){await GameLab.motion(id,true);draws.push(GameLab.active.take.seed);if(GameLab.actors.some(a=>a.take.seed!==draws.at(-1)))throw Error('Comparison seeds differ')}
    return {pool,draws};
   },id);
   assert(variety.pool.length===3&&[4411,5522,6633].every(s=>variety.pool.includes(s)),'Seed pool changed '+JSON.stringify(variety));
   assert(new Set(variety.draws).size===3&&variety.draws.every((s,i)=>!i||s!==variety.draws[i-1]),'Shuffle repeats or misses variants');
   checks.push({body,side,variety});
  }
  for(const inputSide of ['left','right'])for(const seed of [4411,5522,6633]){
   const recording=record&&inputSide==='left'&&seed===4411,selected=await impact(body,inputSide,seed,{recording}),rows=[];
   await step(.05,{});rows.push(await sample());
   for(let i=0;i<7;i++){await step(.05,{});rows.push(await sample())}
   const initial=rows[0];
   for(const row of rows){
    assert(Math.abs(row.root[1]-selected.start[1])<.005,'Initial whole-character elevation '+JSON.stringify(row));
    for(const actor of row.actors){
     const first=initial.actors.find(a=>a.body===actor.body);
     assert(actor.footError<.015,'Collision foot is not planted '+JSON.stringify(actor));
     assert(actor.pelvisY-first.pelvisY<.015,'Pelvis initially rises '+JSON.stringify(actor));
     assert(actor.planeOvershoot<.015,'Collision foot passed the box face '+JSON.stringify(actor));
     assert(Math.abs(actor.thigh-first.thigh)<.001&&Math.abs(actor.calf-first.calf)<.001,'Leg bone length changed');
     assert(actor.seed===seed,'Seed changed during impact');
    }
   }
   const final=rows.at(-1);
   for(const actor of final.actors){
    const first=initial.actors.find(a=>a.body===actor.body);
    assert(actor.kneeFlexion-first.kneeFlexion>.08||first.hipAnkleDistance-actor.hipAnkleDistance>.03,'No measurable leg compression '+JSON.stringify({first,actor}));
    assert(first.pelvisY-actor.pelvisY>.05,'Body did not fall during planted leg compression '+JSON.stringify({first,actor}));
   }
   assert(initial.actors[0].anchor.some((v,i)=>Math.abs(v-initial.actors[1].anchor[i])>.5),'Compared bodies share one world foot anchor');
   if(seed===4411)await screen(body+'-'+inputSide+'-planted');
   const releaseRows=[];for(let i=0;i<16;i++){await step(.025,{});releaseRows.push(await sample())}if(seed===4411)await screen(body+'-'+inputSide+'-release');
   await step(3.4,{});
   const end=await p.evaluate(()=>({root:GameLab.state.position.toArray(),flight:GameLab.state.flight?.type,action:GameLab.state.action?.id,clear:GameLab.world.fits(GameLab.state.position,1.85),length:GameLab.state.maxLengthError,take:GameLab.active.take.id}));
   assert(!end.flight&&!end.action&&end.clear&&Math.abs(end.root[1]-selected.start[1])<.01,'Reaction did not recover on the floor '+JSON.stringify(end));
   assert(end.root[2]<selected.start[2]-1.5&&end.length<.001,'Reaction crosses the hurdle or stretches bones');
   checks.push({body,inputSide,seed,selected,impact_samples:rows,release_samples:releaseRows,end});
   if(recording)checks.push({body,recording:await saveRecording(body)});
  }
  const wall=await impact(body,'left',4411,{tall:true});await step(.35,{});const planted=await sample();
  assert(Math.abs(planted.root[1]-wall.start[1])<.005&&planted.actors.every(a=>a.footError<.015),'Tall wall contact is not grounded/planted');
  await step(4,{});assert(await p.evaluate(()=>!GameLab.state.flight&&!GameLab.state.action&&GameLab.world.fits(GameLab.state.position,1.85)),'Tall wall reaction stuck');
  checks.push({body,tall_wall_away:true,selected:wall,planted});
 }
 assert(!errors.length,errors.join('; '));
 fs.writeFileSync(out,JSON.stringify({status:'passed',url,checks,errors,scope:'Independent world-space sole anchor, leg length, knee compression, initial pelvis/root height, flat approach-side recovery and recorded-pose checks. This is a contact animation constraint, not a complete articulated rigid-body physics simulation.'},null,2));
 console.log('PASS',checks.length,'planted side-trip checks');
}catch(e){fs.writeFileSync(out,JSON.stringify({status:'failed',url,checks,errors,error:e.message},null,2));await p.screenshot({path:path.join(ART,'failure.png')});throw e}finally{await browser.close()}
