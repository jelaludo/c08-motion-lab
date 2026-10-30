import{chromium}from'playwright';import fs from'node:fs';
const base=process.argv[2]||'http://127.0.0.1:8790/public/c08-motion-lab/docs/';
const cases=[['mocap-rebuild','RebuildLab',4,'.method-stage'],['biped-motion','BipedLab',4,'.body-stage'],['h3-motion','H3Lab',2,'.media-card'],['lab','motionTest',1,'#stage'],['reactive','reactiveTest',1,'#stage'],['mb-predictive','predictiveTest',1,'#stage'],['vanilla','vanillaTest',1,'#stage'],['quaternius','quaterniusTest',1,'#stage']];
const essentials={'mocap-rebuild':['test-select','play','timeline'],'biped-motion':['test-select','play','timeline'],'h3-motion':['quick-test','play-all','pause-all','timeline'],lab:['test','mode','play','time','continuous','keyboard'],reactive:['scenario','seed','body','play','timeline'],'mb-predictive':['case','body','play','timeline'],vanilla:['motion','play','timeline'],quaternius:['clip','play','timeline','keyboard-button','random-button']};
const sizes=[[1366,768],[1440,900],[390,844],[844,390]],browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true}),context=await browser.newContext(),rows=[];
try{for(const[folder,api,count,selector]of cases.filter(c=>!process.argv[3]||c[0]===process.argv[3])){
 console.log('VIEWPORT_CHECK',folder);const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:1366,height:768});await page.goto(new URL(folder+'/',base).href);
 await page.waitForFunction(name=>!!window[name],api,{timeout:90000});
 if(folder==='reactive')await page.waitForFunction(()=>!reactiveTest.loading);
 const layouts=[];
 for(const[width,height]of sizes){await page.setViewportSize({width,height});await page.waitForTimeout(180);
  const measured=await page.evaluate(({selector,controls})=>{const rect=n=>{const r=n.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};return{viewport:[innerWidth,innerHeight],page:[document.documentElement.scrollWidth,document.documentElement.scrollHeight],visible:[...document.querySelectorAll(selector)].filter(n=>n.getClientRects().length&&getComputedStyle(n).visibility!=='hidden').map(rect),controls:controls.map(id=>({id,...rect(document.getElementById(id))})),duplicateIds:[...document.querySelectorAll('[id]')].map(n=>n.id).filter((id,i,a)=>a.indexOf(id)!==i),dialogs:document.querySelectorAll('dialog.viewer-panel').length}}, {selector,controls:essentials[folder]});
  if(measured.page[0]>width+1||measured.page[1]>height+1)throw Error(folder+' page scrolls '+JSON.stringify(measured));
  if(measured.visible.length!==count)throw Error(folder+' hidden primary view '+JSON.stringify(measured));
  if(measured.visible.some(r=>r.x<-.5||r.y<-.5||r.right>width+.5||r.bottom>height+.5||r.height<80))throw Error(folder+' clipped viewport '+JSON.stringify(measured));
  if(measured.controls.some(r=>r.width<10||r.height<10||r.x<-.5||r.y<-.5||r.right>width+.5||r.bottom>height+.5))throw Error(folder+' hidden/clipped essential controls '+JSON.stringify(measured.controls));
  if(measured.duplicateIds.length)throw Error(folder+' duplicate IDs '+measured.duplicateIds);
  layouts.push(measured);
  if(width===1366||width===390)await page.screenshot({path:`logs/viewer-layout-${folder}-${width}x${height}.png`});
 }
 const trigger=page.locator('button[data-open-panel]:visible').first();let panel=false;
 if(await trigger.count()){
  await trigger.focus();await page.keyboard.press('Space');await page.waitForFunction(()=>!!document.querySelector('dialog.viewer-panel[open]'));
  panel=await page.evaluate(()=>{const d=document.querySelector('dialog.viewer-panel[open]'),label=document.getElementById(d.getAttribute('aria-labelledby'));return !!label?.textContent&&d.contains(document.activeElement)});
  if(!panel)throw Error(folder+' panel is not labelled/focused');await page.keyboard.press('Escape');await page.waitForFunction(()=>!document.querySelector('dialog.viewer-panel[open]'));
  if(!await trigger.evaluate(n=>n===document.activeElement))throw Error(folder+' panel did not restore focus');
 }
 if(errors.length)throw Error(folder+' '+errors.join(';'));
 rows.push({folder,layouts,panel_label_focus_escape_restore:panel,errors});await page.close();
}
const report={status:'passed',base_url:base,pages:rows.length,viewport_cases:rows.reduce((n,r)=>n+r.layouts.length,0),checks:['All main animation/video views and essential controls stay in the first viewport','No page scrolling across desktop and portrait/landscape phones','No duplicate DOM ids','Native panels have labels, focus containment, Escape dismissal and focus restoration','No page errors'],results:rows};fs.writeFileSync('logs/viewer-layout-validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,pages:report.pages,viewport_cases:report.viewport_cases}));
}finally{await browser.close()}
