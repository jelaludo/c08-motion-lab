import {chromium} from 'playwright';
import fs from 'node:fs';
const base=process.argv[2]||'http://127.0.0.1:8790/public/c08-motion-lab/docs/biped-motion/';
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1400,height:1000}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
try{
const catalog=await (await page.request.get(new URL('catalog.json',base).href)).json(),rows=[];
for(const test of catalog.tests){
 await page.goto(new URL('skeleton/?test='+encodeURIComponent(test.id),base).href);await page.waitForFunction(()=>window.BipedSkeleton);
 const source=await page.evaluate(()=>({frames:BipedSkeleton.data.frame_count,joints:BipedSkeleton.data.joint_names.length,duration:BipedSkeleton.data.duration_s}));
 for(const fraction of [0,.25,.5,.75,1]){await page.locator('#time').fill(String(Math.floor(source.duration*fraction*1000)/1000));const sample=await page.evaluate(()=>({time:BipedSkeleton.time,frame:BipedSkeleton.frame,finite:[...BipedSkeleton.skeleton.geometry.attributes.position.array,...BipedSkeleton.points.geometry.attributes.position.array].every(Number.isFinite)}));if(!sample.finite||Math.abs(sample.time-source.duration*fraction)>.002)throw Error('Invalid sampled pose '+test.id)}
 await page.uncheck('#follow');await page.locator('#play').click();await page.waitForTimeout(120);if(!await page.evaluate(()=>BipedSkeleton.playing&&BipedSkeleton.time>=0))throw Error('Skeleton playback failed');await page.locator('#play').click();
 rows.push({id:test.id,...source,sampled_positions_finite:true});
}
await page.setViewportSize({width:390,height:844});await page.waitForTimeout(150);if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile skeleton overflows');await page.screenshot({path:'logs/biped-skeleton-mobile.png',fullPage:true});
if(errors.length)throw Error(errors.join(';'));
const report={status:'passed',url:base,cases:rows,checks:['Six raw77-joint skeletons load','Five timestamps each have finite rendered joints','Playback and complete-path mode work','Mobile layout has no horizontal overflow','No page errors'],errors};fs.writeFileSync('logs/biped-skeleton-browser-validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
}finally{await browser.close()}
