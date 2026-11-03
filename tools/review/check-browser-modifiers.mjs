import fs from 'node:fs';import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),modules=process.env.MOTION_REVIEW_NODE_MODULES||path.join(ROOT,'tools/review/node_modules');
const {chromium}=await import(pathToFileURL(path.join(modules,'playwright/index.mjs'))),url=process.argv[2]||'http://127.0.0.1:8802/kimodo-game/?controls=hybrid',out=process.env.BROWSER_MODIFIER_QA_OUT||path.join(ROOT,'research/kimodo/browser-modifier-validation.json');
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true}),context=await browser.newContext(),page=await context.newPage(),errors=[],checks=[];
page.on('pageerror',e=>errors.push(e.message));const assert=(v,msg)=>{if(!v)throw Error(msg)},settle=()=>page.waitForFunction(()=>window.GameLab?.actors.length===2&&GameLab.actors.every(a=>a.data)&&GameLab.loadJobs===0,null,{timeout:90000});
try{
 await page.goto(url);await settle();await page.evaluate(()=>GameLab.setManual());
 for(const profile of ['hybrid','lab'])for(const body of ['c08','brek43']){
  await page.evaluate(({profile,body})=>{GameLab.reset();GameLab.applyProfile(profile);document.querySelector('#body').value=body}, {profile,body});await settle();await page.locator('#game').focus();
  const synthetic=await page.evaluate(()=>{
   const rejected=[];for(const modifier of ['ctrlKey','metaKey'])for(const code of ['KeyC','KeyW','KeyA','KeyS','KeyD','KeyZ','KeyF','KeyB','KeyP','KeyR']){
    const before=GameLab.state.events.length,event=new KeyboardEvent('keydown',{code,key:code.slice(-1).toLowerCase(),[modifier]:true,bubbles:true,cancelable:true});document.querySelector('#game').dispatchEvent(event);
    if(GameLab.state.events.length!==before||GameLab.state.action||GameLab.state.stance!=='stand'||GameLab.recorder.active||GameLab.state.paused||GameLab.controlInput().x||GameLab.controlInput().z||event.defaultPrevented)throw Error('Browser shortcut leaked into game '+modifier+' '+code);
    document.querySelector('#game').dispatchEvent(new KeyboardEvent('keyup',{code,bubbles:true}));rejected.push(modifier+':'+code);
   }return rejected;
  });
  // Use trusted browser input for Copy; synthetic events above deliberately
  // avoid actually closing/reloading tabs, opening Print/Find or undoing data.
  await page.keyboard.press('Control+KeyC');await page.keyboard.press('Control+KeyC');assert(await page.evaluate(()=>GameLab.state.stance==='stand'&&GameLab.state.crouchTap===-Infinity),'Actual Ctrl+C triggered crouch/seiza');
  await page.keyboard.press('KeyC');await settle();assert(await page.evaluate(()=>GameLab.state.stance==='crouch'),'Plain C no longer crouches');await page.keyboard.press('Space');assert(await page.evaluate(()=>GameLab.state.flight?.type==='jump'&&GameLab.state.flight.height===.65),'Normal crouch jump inherited Ctrl');
  await page.evaluate(()=>{GameLab.reset()});await settle();await page.keyboard.press('Control+Space');assert(await page.evaluate(()=>GameLab.state.flight?.type==='jump'&&GameLab.state.flight.height===1.25),'Explicit Ctrl+Space high jump lost');await page.evaluate(()=>GameLab.reset());await settle();
  await page.keyboard.press('KeyC');await page.keyboard.press('KeyC');assert(await page.evaluate(()=>GameLab.state.stance==='seiza'),'Plain C C no longer enters seiza');
  await page.evaluate(()=>GameLab.reset());await settle();await page.keyboard.down('KeyW');assert(await page.evaluate(()=>GameLab.controlInput().z===1),'W did not start');await page.keyboard.press('Control+KeyC');await page.keyboard.up('KeyW');assert(await page.evaluate(()=>GameLab.controlInput().z===0&&GameLab.state.stance==='stand'),'Browser shortcut left held movement or crouch state');
  checks.push({profile,body,synthetic_browser_shortcuts:synthetic.length,actual_copy_does_not_crouch:true,plain_c_and_cc:true,normal_crouch_jump:true,explicit_ctrl_space_high_jump:true,held_input_cleared:true});console.log('PASS',profile,body);
 }
 assert(!errors.length,errors.join('; '));fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify({status:'passed',url,checked:new Date().toISOString(),scope:'Actual Ctrl+C/C/CC/Space/Ctrl+Space; synthetic Ctrl/Meta shortcut events for browser commands with disruptive native effects.',checks,errors},null,2)+'\n');
}catch(e){fs.writeFileSync(out,JSON.stringify({status:'failed',url,checks,errors,error:e.message},null,2));throw e}finally{await browser.close()}
