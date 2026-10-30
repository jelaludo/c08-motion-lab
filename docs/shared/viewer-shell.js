/** Move existing controls into accessible panels without replacing their state. */
const panels=new Map();let initialized=false;
export function initViewerShell(){
 if(initialized)return;initialized=true;
 document.addEventListener('click',event=>{
  const opener=event.target.closest('[data-open-panel]');
  if(opener){event.preventDefault();openPanel(opener.dataset.openPanel,opener);return}
  const closer=event.target.closest('[data-close-panel]');
  if(closer){event.preventDefault();const id=closer.dataset.closePanel||closer.closest('dialog')?.id;panels.get(id)?.close()}
 });
 // Inputs keep their native keys; page-level playback/game shortcuts stay outside panels.
 document.addEventListener('keydown',event=>{
  const target=event.target;
  if(target?.closest?.('dialog[open]')||(['Space','Enter'].includes(event.code)&&target?.closest?.('button,a,[role="button"]')))event.stopImmediatePropagation();
 });
}
export function createPanel({id,title,content=[],nodes,onOpen}={}){
 if(!id)throw Error('A viewer panel needs an id');
 removePanel(id);initViewerShell();
 const dialog=document.createElement('dialog');dialog.id=id;dialog.className='viewer-panel';
 const header=document.createElement('div');header.className='viewer-panel-header';
 const heading=document.createElement('h2');heading.id=id+'-title';heading.textContent=title||'Details';dialog.setAttribute('aria-labelledby',heading.id);
 const close=document.createElement('button');close.type='button';close.className='viewer-panel-close';close.textContent='Close';close.setAttribute('aria-label','Close '+(title||'details'));close.dataset.closePanel=id;
 header.append(heading,close);
 const body=document.createElement('div');body.className='viewer-panel-body';for(const node of nodes||content){if(node)body.append(node)}
 dialog.append(header,body);document.body.append(dialog);let previousFocus=null;
 const api={dialog,body,open(trigger){previousFocus=trigger instanceof HTMLElement?trigger:document.activeElement;if(!dialog.open){dialog.showModal();onOpen?.()}close.focus()},close(){if(dialog.open)dialog.close()},remove(){api.close();dialog.remove();if(panels.get(id)===api)panels.delete(id)}};
 dialog.addEventListener('close',()=>{if(previousFocus?.isConnected&&!previousFocus.disabled)previousFocus.focus({preventScroll:true});previousFocus=null});
 dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)api.close()});
 panels.set(id,api);return api;
}
export function openPanel(id,trigger){panels.get(id)?.open(trigger)}
export function removePanel(id){panels.get(id)?.remove()}
/** Fit the box to the actual screen aspect, rather than fitting its bounding sphere. */
export function fitCameraToBox(camera,controls,box,padding=1.08){
 const center=box.getCenter(camera.position.clone()),direction=camera.position.clone().set(.9,.45,1.8).normalize();
 const right=camera.up.clone().cross(direction).normalize(),up=direction.clone().cross(right).normalize();
 const vertical=Math.tan(camera.fov*Math.PI/360),horizontal=vertical*camera.aspect;let distance=.1;
 for(const x of[box.min.x,box.max.x])for(const y of[box.min.y,box.max.y])for(const z of[box.min.z,box.max.z]){
  const offset=camera.position.clone().set(x,y,z).sub(center);
  distance=Math.max(distance,offset.dot(direction)+Math.max(Math.abs(offset.dot(right))/horizontal,Math.abs(offset.dot(up))/vertical));
 }
 camera.position.copy(center).addScaledVector(direction,distance*padding);controls.target.copy(center);controls.update();return distance*padding;
}
