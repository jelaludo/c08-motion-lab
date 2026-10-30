import {createPanel,initViewerShell} from '../shared/viewer-shell.js';
/** Reparent existing controls; animation and review instances keep their original IDs. */
export function setupLegacyViewer(kind){
 const $=id=>document.getElementById(id),make=(tag,content,className)=>{const n=document.createElement(tag);if(content)n.textContent=content;if(className)n.className=className;return n},isVanilla=kind==='vanilla',prefix='compact-'+kind;
 document.body.classList.add('legacy-viewer',kind+'-viewer');initViewerShell();
 const oldMain=document.querySelector('main'),aside=oldMain.querySelector('aside'),nav=document.querySelector('body>nav'),stage=$('stage'),oldHeading=stage.querySelector('header,.heading'),status=$('status');
 const header=make('header',null,'legacy-bar'),home=make('a','C08 LAB','legacy-home');home.href='../';header.append(home,make('h1',isVanilla?'Vanilla 15':'Quaternius'));
 const tools=make('div',null,'legacy-tools');function openButton(label,id){const b=make('button',label);b.type='button';b.dataset.openPanel=id;return b}tools.append(openButton('About',prefix+'-about'),openButton('View',prefix+'-options'),openButton(isVanilla?'Review':'Keys',prefix+(isVanilla?'-review':'-keys')));header.append(tools);
 const workspace=make('main',null,'legacy-workspace'),selector=make('div',null,'legacy-selector'),transport=isVanilla?$('transport'):make('div');transport.id='transport';transport.classList.add('legacy-transport');document.body.prepend(header,workspace);workspace.append(selector);
 const about=make('section'),options=make('section');if(nav){nav.removeAttribute('style');about.append(nav)}if(oldHeading){oldHeading.remove();const intro=make('p',oldHeading.innerText||oldHeading.textContent);about.append(intro)}
 if(isVanilla){
  selector.append($('previous'),$('motion'),$('next'));$('motion').setAttribute('aria-label','Animation');
  const filterLabel=aside.querySelector('label[for="filter"]');if(filterLabel)options.append(filterLabel);options.append($('filter'));
  const repeat=$('repeat');options.append(repeat.closest('label'));const skeleton=$('skeleton');options.append(skeleton.closest('label'));
  const review=$('review-panel');createPanel({id:prefix+'-review',title:'Review and keep takes',content:[review]});
  aside.querySelector('h2')?.remove();aside.querySelector('label[for="motion"]')?.remove();
 }else{
  selector.append($('clip'),$('keyboard-button'),$('random-button'));$('clip').setAttribute('aria-label','Animation');$('keyboard-button').textContent='WASD';$('random-button').textContent='Random';
  transport.append($('play'),$('restart'),$('timeline'),$('readout'));
  const modeLabel=aside.querySelector('label[for="mode"]');if(modeLabel)options.append(modeLabel);options.append($('mode'));
  options.append($('source').closest('label'),$('skeleton').closest('label'),$('camera'));
  const keys=aside.querySelector('details');if(keys){keys.open=true;createPanel({id:prefix+'-keys',title:'Keyboard shortcuts',content:[keys]})}
  aside.querySelector('label[for="clip"]')?.remove();aside.querySelector('label[for="timeline"]')?.remove();
 }
 for(const child of [...aside.childNodes]){if(child.nodeType===1&&child.classList?.contains('row')&&!child.children.length){child.remove();continue}about.append(child)}
 createPanel({id:prefix+'-about',title:isVanilla?'Vanilla 15: notes and provenance':'Quaternius: notes and downloads',content:[about]});createPanel({id:prefix+'-options',title:'View and playback options',content:[options]});
 workspace.append(selector,stage,transport,status);oldMain.remove();document.body.prepend(header,workspace);
}
