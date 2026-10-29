import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const url=process.argv[2]||'http://127.0.0.1:8790/public/c08-motion-lab/docs/dev-log/';
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
await page.goto(url);await page.locator('h1').waitFor();
const content=await page.evaluate(()=>{
 const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);
 const broken=[...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.getElementById(a.hash.slice(1))).map(a=>a.hash);
 return {entries:document.querySelectorAll('.entry').length,words:document.body.innerText.split(/\s+/).length,duplicateIds:ids.filter((id,i)=>ids.indexOf(id)!==i),broken,lead:document.querySelector('.status').innerText,links:[...new Set([...document.querySelectorAll('a[href],img[src],iframe[src]')].map(e=>e.href||e.src))]};
});
if(content.entries!==18||content.words<3500||content.duplicateIds.length||content.broken.length)throw Error(JSON.stringify(content));
if(!content.lead.includes('centre of gravity')||!content.lead.includes('unresolved'))throw Error('Current quality concerns are not prominent');
const checked=[];
for(const link of content.links){const u=new URL(link);if(u.origin===new URL(url).origin&&!u.hash){const r=await page.request.get(link);if(!r.ok())throw Error('Broken local URL '+link+' '+r.status());checked.push(link)}if(u.hostname==='github.com'&&u.pathname.startsWith('/jelaludo/c08-motion-lab/blob/main/')){const file=decodeURIComponent(u.pathname.split('/blob/main/')[1]);if(!fs.existsSync(path.join('public/c08-motion-lab',file)))throw Error('Missing cited report '+file)}}
for(const name of ['index.html','reactive/index.html','vanilla/index.html','quaternius/index.html','mb-predictive/index.html','lab/index.html','diorama.html']){const html=fs.readFileSync('public/c08-motion-lab/docs/'+name,'utf8');if(!/href="(?:\.\.\/)?dev-log\/"/.test(html))throw Error('Missing Dev log navigation '+name)}
await page.screenshot({path:'logs/dev-log-desktop.png'});
await page.locator('iframe.arms-frame').scrollIntoViewIfNeeded();const frame=await page.locator('iframe.arms-frame').contentFrame();await frame.locator('canvas').waitFor();
const child=page.frames().find(f=>f.url().includes('arms-comparison.html'));await child.waitForFunction(()=>window.__armsComparison?.loaded,null,{timeout:60000});
await child.locator('#play').click();const before=await child.evaluate(()=>__armsComparison.time);await page.waitForTimeout(150);if(Math.abs(await child.evaluate(()=>__armsComparison.time)-before)>.001)throw Error('Embedded comparison did not pause');
await page.screenshot({path:'logs/dev-log-arms-comparison.png'});
await page.setViewportSize({width:390,height:844});await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:'logs/dev-log-mobile.png'});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile page overflows');
await page.locator('iframe.arms-frame').scrollIntoViewIfNeeded();if(await child.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile iframe overflows');
if(errors.length)throw Error(errors.join(';'));
const report={status:'passed',url,entries:content.entries,words:content.words,checks:['prominent unresolved crouch/arm feedback','18 dated entries and working in-page index','all local destinations and cited repository reports exist','navigation added to all seven principal pages','live embedded synchronized comparison loads and pauses','desktop/mobile page and iframe have no horizontal overflow','no page errors'],local_urls_checked:checked.length,errors};
fs.writeFileSync('logs/dev-log-browser-validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));await browser.close();
