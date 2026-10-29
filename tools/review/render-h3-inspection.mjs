import {chromium} from 'playwright';
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
const [testId,output,fpsArg='24']=process.argv.slice(2),fps=Number(fpsArg);
if(!testId||!output)throw Error('Usage: node tools/review/render-h3-inspection.mjs test-id output.mp4 [fps]');
const base='http://127.0.0.1:8790/public/c08-motion-lab/docs/h3-motion/';
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1050,height:900},deviceScaleFactor:1}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
await page.goto(base+'?test='+encodeURIComponent(testId));
await page.waitForFunction(()=>window.H3Lab?.catalog);
const test=await page.evaluate(id=>H3Lab.catalog.tests.find(t=>t.id===id),testId);
const artifact=test.outputs.filter(o=>o.model).at(-1);
if(!artifact)throw Error('No model artifact for '+testId);
const buttons=page.locator('button.inspect-model');
// The recovered artifact is the last model, following any posted native control.
await buttons.last().click();
const dialog=page.locator('.model-dialog');
await page.waitForFunction(()=>document.querySelector('.model-dialog')?.textContent.includes('supplied animation'));
const slider=dialog.getByRole('slider'),canvas=dialog.locator('canvas');
const duration=Number(await slider.getAttribute('max')),frames=Math.round(duration*fps);
const ffmpeg=process.env.H3_FFMPEG||'video-mocap/tools/ffmpeg.exe';
const encoder=spawn(ffmpeg,['-y','-f','image2pipe','-framerate',String(fps),'-vcodec','png','-i','pipe:0','-an','-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',output],{stdio:['pipe','ignore','pipe']});
let stderr='';encoder.stderr.on('data',b=>{stderr=(stderr+b).slice(-2000)});
const finished=once(encoder,'close');
for(let i=0;i<frames;i++){
 await slider.evaluate((el,t)=>{el.value=t;el.dispatchEvent(new Event('input',{bubbles:true}))},i/fps);
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const image=await canvas.screenshot();
 if(!encoder.stdin.write(image))await once(encoder.stdin,'drain');
}
encoder.stdin.end();const [code]=await finished;
await browser.close();
if(code)throw Error('FFmpeg failed '+code+' '+stderr);
if(errors.length)throw Error(errors.join('\n'));
const report={testId,output,frames,fps,duration_s:frames/fps,source_model:artifact.model,method:'Deterministic Three.js GLB inspection frames. Camera follows the body; no motion keys, floor correction or retiming added. Every source-time sample retained at the stated frame rate.',errors};
fs.writeFileSync(output+'.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
