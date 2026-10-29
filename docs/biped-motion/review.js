import {H3ReviewPanel} from '../h3-motion/review.js';
const download=(value,name)=>{const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
export class BipedReviewPanel extends H3ReviewPanel{
 constructor(options){super(options);this.$('export').onclick=()=>{this.store.persist();download({...this.store.export(),biped_manifest_snapshot:this.getManifestSnapshot?.()},'motion-lab-all-reviews.json')};this.$('export-shortlist').onclick=()=>download(this.keptManifest(),'biped-kept-tests.json')}
 keptManifest(){return {...super.keptManifest(),schema:'biped-kept-tests/1'}}
}
