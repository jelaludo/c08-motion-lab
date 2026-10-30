import {createPanel,initViewerShell} from '../shared/viewer-shell.js';
const $=id=>document.getElementById(id),main=document.querySelector('body>main'),aside=main.querySelector('aside'),stage=$('stage');
document.body.classList.add('compact-reactive');initViewerShell();
const dock=document.createElement('section');dock.className='arena-dock';dock.setAttribute('aria-label','Reactive test controls');
const selectors=document.createElement('div');selectors.className='arena-selectors';
const name=document.createElement('strong');name.textContent='REACTIVE ARENA';name.className='dock-name';selectors.append(name);
for(const[id,title]of[['scenario','Scenario'],['seed','Seed'],['body','Body']]){const old=document.querySelector(`label[for="${id}"]`);old?.remove();const label=document.createElement('label');label.append(title+' ',$(id));selectors.append(label)}
const actions=document.createElement('div');actions.className='arena-actions';for(const[id,title]of[['reactive-about','About / results'],['reactive-options','Camera / sections'],['reactive-review','Review / export']]){const b=document.createElement('button');b.type='button';b.textContent=title;b.dataset.openPanel=id;actions.append(b)}selectors.append(actions);dock.append(selectors,$('transport'));main.prepend(dock);
const pause=()=>{if($('play').textContent==='Pause')$('play').click()};
const review=document.createElement('section');for(const id of ['review-side','queue']){const label=document.querySelector(`label[for="${id}"]`);if(label)review.append(label);review.append($(id))}review.append($('next-queue'));
const reviewTitle=document.createElement('h3');reviewTitle.textContent='Record and export';review.append(reviewTitle,$('recording-description'),$('downloads'));
const markRow=$('mark-in').parentElement;review.append(markRow,$('range'),$('save-selection'),$('review-panel'));
const options=document.createElement('section');options.append($('camera-controls'),$('playlist-panel'));
const header=stage.querySelector('header');header.classList.add('compact-about-heading');aside.prepend(header);aside.querySelector('h2')?.remove();
createPanel({id:'reactive-about',title:'Reactive targets — results and method',content:[aside],onOpen:pause});createPanel({id:'reactive-options',title:'Camera and automatic sections',content:[options],onOpen:pause});createPanel({id:'reactive-review',title:'Review and export a take',content:[review],onOpen:pause});
