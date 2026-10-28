import {chromium} from 'playwright';
import fs from 'node:fs';
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
const url=process.argv[2]||'http://127.0.0.1:8790/public/c08-motion-lab/docs/lab/';
await page.goto(url);await page.waitForFunction(()=>window.motionTest?.setKeyboard);
const check=(v,m)=>{if(!v)throw Error(m)};
await page.mouse.click(500,350);await page.keyboard.down('w');await page.waitForFunction(()=>motionTest.selectedTest==='authored:Heavy_Walk_Cycle');await page.waitForTimeout(400);
check(await page.evaluate(()=>motionTest.keyboard.position.z<-.1),'walk displacement');
await page.keyboard.down('Shift');await page.waitForFunction(()=>motionTest.selectedTest==='own_run');
await page.keyboard.press('Space');await page.waitForFunction(()=>motionTest.selectedTest==='own_jump_over');check(await page.evaluate(()=>motionTest.keyboard.jumpKind==='running'),'running jump');
await page.keyboard.up('w');await page.keyboard.up('Shift');await page.waitForFunction(()=>!motionTest.keyboard.oneShot,{},{timeout:20000});await page.waitForFunction(()=>motionTest.selectedTest==='authored:Standby_Idle');
await page.keyboard.press('Space');await page.waitForFunction(()=>motionTest.selectedTest==='own_idle'&&motionTest.keyboard.jumpKind==='standing');check(await page.evaluate(()=>motionTest.duration===1.2),'standing jump distinct');
await page.waitForFunction(()=>!motionTest.keyboard.oneShot);
for(const [key,id] of [['u','mocap_ukemi'],['t','mocap_sumo_stomp'],['1','own_deep_crouch'],['0','fresh_skip']]){await page.keyboard.press(key);await page.waitForFunction(id=>motionTest.selectedTest===id,id);}
await page.keyboard.press('Escape');check(await page.evaluate(()=>!motionTest.keyboard.enabled),'escape');
await page.selectOption('#test','own_idle');await page.locator('#test').focus();await page.keyboard.press('u');check(await page.evaluate(()=>!motionTest.keyboard.enabled),'form focus guard');
await page.mouse.click(500,350);await page.keyboard.down('d');await page.waitForFunction(()=>motionTest.keyboard.keys.has('KeyD'));await page.evaluate(()=>window.dispatchEvent(new Event('blur')));check(await page.evaluate(()=>motionTest.keyboard.keys.size===0),'blur clears movement');
check(!errors.length,errors.join(';'));await page.screenshot({path:'logs/keyboard-control.png'});console.log(JSON.stringify({status:'passed',errors,url}));await browser.close();
