// Keep the versioned animation recipe unchanged; presentation is a separate layer.
import {setupLegacyViewer} from './compact-viewer.js';
setupLegacyViewer('vanilla');
const selector=document.getElementById('motion');
new MutationObserver(()=>{for(const option of selector.options)option.label=option.textContent.replace(' ? ',' · ')}).observe(selector,{childList:true,subtree:true});
await import('./vanilla.js?v=kept-body-2');
