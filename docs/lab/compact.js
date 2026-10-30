import {createPanel,initViewerShell} from '../shared/viewer-shell.js';
const $=id=>document.getElementById(id),aside=document.querySelector('aside'),main=document.querySelector('main'),nav=aside.querySelector('nav');
document.body.classList.add('research-compact');initViewerShell();
nav.classList.add('research-nav');document.body.prepend(nav);
for(const [href,label]of[['../biped-motion/','Biped capture'],['../mocap-rebuild/','Mocap rebuild']]){const a=document.createElement('a');a.href=href;a.textContent=label;nav.append(a)}
const toolbar=document.createElement('div');toolbar.className='research-toolbar';const title=document.createElement('strong');title.textContent='Research gallery';toolbar.append(title);
const field=(name,node)=>{const label=document.createElement('label'),span=document.createElement('span');span.textContent=name;label.append(span,node);return label};
toolbar.append(field('Motion',$('test')),field('Source',$('mode')),$('continuous'),$('keyboard'));
const button=document.createElement('button');button.textContent='Details & options';button.dataset.openPanel='research-options';toolbar.append(button);main.before(toolbar);
const transport=document.createElement('div');transport.className='research-transport';transport.append($('play'),$('restart'),field('Speed',$('speed')),$('time'),$('readout'));
const repeat=$('repeat').closest('label');transport.append(repeat);main.after(transport);
const panel=createPanel({id:'research-options',title:'Research details, downloads & options',content:[aside]});
document.querySelector('#stage>header').hidden=true;
for(const details of aside.querySelectorAll('details'))details.open=false;
window.ResearchCompact={panel};
