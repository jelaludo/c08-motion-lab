import {chromium} from 'playwright';
import fs from 'node:fs';
const url=process.argv[2]||'http://127.0.0.1:8790/public/c08-motion-lab/docs/h3-motion/concept-skeleton/';
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1300,height:900}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
await page.goto(url);await page.waitForFunction(()=>window.h3ConceptReview?.data,{timeout:60000});
const samples=[];
for(const t of [0,3,6.13,10,12.2333]){
 await page.evaluate(t=>h3ConceptReview.setTime(t),t);
 await page.waitForTimeout(80);
 const s=await page.evaluate(()=>{
  const v=h3ConceptReview,geometry=[];
  v.scene.traverse(o=>{if(o.geometry?.attributes.position)geometry.push(...o.geometry.attributes.position.array)});
  return {videoTime:v.video.currentTime,verticesFinite:geometry.every(Number.isFinite),frames:v.data.frame_count,joints:v.data.joint_names.length,canvas:!!document.querySelector('canvas')};
 });
 if(!s.verticesFinite||s.frames!==368||s.joints!==77||Math.abs(s.videoTime-t)>.01)throw Error(JSON.stringify(s));samples.push(s);
}
await page.screenshot({path:'logs/h3-concept-skeleton.png'});
await page.setViewportSize({width:390,height:844});await page.waitForTimeout(100);
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2))throw Error('Mobile overflow');
if(errors.length)throw Error(errors.join('\n'));
const report={status:'passed',url,samples,checks:['finite skeleton at five times','media and skeleton timestamps match','77 joints / 368 frames','desktop and mobile render','no page errors']};
fs.writeFileSync('logs/h3-concept-browser-validation.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report));await browser.close();
