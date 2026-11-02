"""Package the owned static viewers; run prepare_kimodo_assets.mjs first.

Large, content-addressed playback assets live under research/ and use GitHub raw
URLs. Pages serves UI/catalogs only, preserving the existing deployment budget.
"""
from pathlib import Path
import argparse,hashlib,json,re,shutil
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--kimodo-root',type=Path,default=Path('G:/Dev/Kimodo'));args=p.parse_args();K=args.kimodo_root;WEB=K/'web';DOC=R/'docs';OUT=R/'research/kimodo';OUT.mkdir(exist_ok=True)
manifest=json.loads((OUT/'assets-manifest.json').read_text())
def read(p):return p.read_text(encoding='utf-8')
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8',newline='\n')
def dump(p,obj):write(p,json.dumps(obj,indent=2)+'\n')
def replace(s,a,b,count=1):
 assert s.count(a)==count,('Unexpected source template match count',a[:100],s.count(a));return s.replace(a,b)
def clean(value):
 if isinstance(value,list):return [clean(v) for v in value]
 if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k not in ['local_path','source_local_path','source_path','constraint_file']}
 if isinstance(value,str) and re.match(r'^[A-Z]:[\\/]',value,re.I):return '[local path omitted]'
 return value
game=DOC/'kimodo-game';gallery=DOC/'kimodo-bipeds';game.mkdir(exist_ok=True);gallery.mkdir(exist_ok=True)
for name in ['index.html','game.css','game.js','world.js','kinematics.js','export.js','controls.html','controls-study.css','controls-study.js','controls-research.json','control-audit.json']:
 shutil.copy2(WEB/'kimodo-game'/name,game/name)
exporter=read(game/'export.js').replace("import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';","import {normalizedGLB} from '../shared/normalized-gltf-export.js';").replace('await new GLTFExporter().parseAsync(','await normalizedGLB(')
write(game/'export.js',exporter)
catalog=json.loads(read(WEB/'kimodo-game/catalog.json'))
for body in catalog['bodies']:
 body['model']=manifest['game']['models'][body['id']]['url'];body['pack']=manifest['game']['packs'][body['id']]['url']
for take in catalog['takes']:
 for o in take['outputs']:
  packed=manifest['game']['takes'][take['id']][o['body']]
  o.update(clip=packed['processed']['url'],raw_clip=packed['raw']['url'],source_glb=manifest['game']['models'][o['body']]['url'],report=packed['report']['url'],source_glb_sha256=packed['raw']['source_glb_sha256'])
catalog['publication']={'kind':'static recorded motion with a browser game controller','transport':'Shared character meshes plus lossless compressed tracks; no browser inference. Reconstructed source-motion GLBs differ from original file bytes and use the displayed 1.9 m character scale.','reviews':'Browser origin-local. Export/import to transfer localhost feedback.'}
dump(game/'catalog.json',catalog)
js=read(game/'game.js');js="import {readMotionJSON,loadMotionModel} from '../shared/motion-asset-io.js';\n"+js
js=replace(js,"fetch(out.clip).then(r=>{if(!r.ok)throw Error('Missing clip '+out.clip);return r.json()})","readMotionJSON(out.clip)")
js=replace(js,'await loader.loadAsync(def.model)','await loadMotionModel(loader,def.model)')
old="function updateLinks(){const t=candidate();if(!t)return;$('source-link').href=outputFor(t,active().id).source_glb;$('pack-link').href='packs/'+active().id+'-game-kit.glb';$('pack-link').textContent=active().label+' · 94-clip GLB';}"
new="""function updateLinks(){const t=candidate();if(!t)return;$('source-link').href=outputFor(t,active().id).raw_clip;$('source-link').textContent='Source-motion GLB (rebuilt)';$('source-link').onclick=async e=>{e.preventDefault();const a=active(),data=await readMotionJSON(outputFor(candidate(),a.id).raw_clip);await exportClips(a,[data],candidate().id+'-'+a.id+'-source-motion-rebuilt.glb')};$('pack-link').href=catalog.bodies.find(b=>b.id===active().id).pack;$('pack-link').textContent=active().label+' · 94-clip GLB';}"""
js=replace(js,old,new);write(game/'game.js',js)
html=read(game/'index.html').replace('href="packs/c08-game-kit.glb"','href="'+manifest['game']['packs']['c08']['url']+'"')
notice='<p>Public playback uses recorded Kimodo takes. Movement, transitions, collision and IK run in this browser; fresh AI generation runs offline. Reviews save for this site only. Export reviews locally, then import here to transfer them. Source-motion GLBs are rebuilt downloads; character recordings exclude prop meshes and trajectories.</p>'
html=replace(html,'</dialog>\n<script type="module"',notice+'</dialog>\n<script type="module"');write(game/'index.html',html)
state=json.loads(read(WEB/'kimodo-game/packs/game-state-machine.json'))
for body,b in state['bodies'].items():b['file']=manifest['game']['packs'][body]['url']
dump(game/'packs/game-state-machine.json',state)
audit=json.loads(read(game/'control-audit.json'));audit['local_source_runtime_sha256']=audit['runtime_source_sha256'];audit['runtime_source_sha256']=hashlib.sha256(js.encode()).hexdigest();audit['publication_transport']='Compressed static track assets; animation/controller behavior retained.';dump(game/'control-audit.json',audit)
for name in ['gallery.css','gallery-controller.js']:
 shutil.copy2(K/'tools'/name,gallery/name)
js=read(K/'tools/gallery-biped.js')
js="import {loadPublishedAsset} from '../shared/motion-asset-io.js';\nimport {exportClips} from '../kimodo-game/export.js';\n"+js
js=js.replace("from './anchored-retarget.js'","from '../biped-motion/anchored-retarget.js'").replace("from './review.js'","from '../biped-motion/review.js'")
js=replace(js,'await loader.loadAsync(assetURL(output.model))','await loadPublishedAsset(loader,output,assetURL)')
js=replace(js,'v.neutral=captureBindPose(v.asset);',"v.neutral=captureBindPose(v.asset);if(body.attribution)v.asset.userData.attribution=body.attribution;")
js=replace(js,"if(!v.clip)throw Error('GLB has no animation clip');","""if(!v.clip)throw Error('GLB has no animation clip');if(output.animation){const downloadLink=links.querySelector('a');downloadLink.textContent='Export source-motion GLB (rebuilt)';downloadLink.onclick=async e=>{e.preventDefault();await exportClips({asset:v.asset,bind:v.neutral},[T.AnimationClip.toJSON(v.clip)],selected+'-'+body.id+'-source-motion-rebuilt.glb')};details.append(node('p','This GLB is rebuilt from exact source animation tracks and a shared character asset; it is not the original binary file. Original source hashes are retained in provenance. Continuous preview bridges are not included.'))};""")
old=".map(o=>({label:o.runtime_retarget?'Retarget recipe (use Export GLB for the animated body)':'Supplied animation GLB',url:o.runtime_retarget?assetURL('catalog.json'):assetURL(o.model)}))"
new=".flatMap(o=>o.animation?[{label:'Exact source animation tracks (gzip JSON)',url:assetURL(o.animation)},{label:'Shared character asset (reference motion only)',url:assetURL(o.model)}]:[{label:'Supplied animation GLB',url:assetURL(o.model)}])"
js=replace(js,old,new)
js=js.replace("'http://127.0.0.1:8801/'","'../dev-log/#kimodo-setup'")
write(gallery/'biped.js',js)
controller=read(gallery/'gallery-controller.js');controller="import {loadPublishedClip} from '../shared/motion-asset-io.js';\n"+controller
old="const gltf=await loader.loadAsync(assetURL(output.model));const clip=gltf.animations[0];discard(gltf.scene);if(!clip)throw Error('No clip for '+id);return {body:output.body,clip}"
controller=replace(controller,old,"const clip=await loadPublishedClip(output,assetURL);return {body:output.body,clip}");write(gallery/'gallery-controller.js',controller)
html=read(WEB/'kimodo-bipeds/index.html').replace('../biped-motion/biped.js?v=kimodo-combat-1','biped.js?v=kimodo-public-1').replace('../biped-motion/gallery.css?v=combat-1','gallery.css?v=kimodo-public-1')
html=html.replace('http://127.0.0.1:8790/public/c08-motion-lab/docs/','../').replace('http://127.0.0.1:8801/','../dev-log/#kimodo-setup').replace('Open the original Kimodo human preview','Generation notes').replace('Original Kimodo preview','Generation notes')
html=replace(html,'<p id="experiment-summary"></p>','<p id="experiment-summary"></p><p>These recorded takes share character meshes and exact compressed animation tracks. Source-motion GLB downloads are rebuilt files. Reviews are stored for this website origin; use Export/Import to transfer feedback from localhost. No inference service or model download is required to play.</p>')
write(gallery/'index.html',html)
catalog=json.loads(read(WEB/'kimodo-bipeds/catalog.json'))
for t in catalog['tests']:
 for o in t['outputs']:
  packed=manifest['gallery']['takes'][t['id']][o['body']];model=manifest['gallery']['models'][o['body']]
  o['source_glb_sha256']=o['sha256'];o.update(model=model['url'],animation=packed['animation']['url'],report=packed['report']['url'],sha256=model['sha256'])
catalog['publication_transport']=manifest['transport'];dump(gallery/'catalog.json',catalog)
reports=['game-source-validation.json','game-pack-validation.json','controls-study-validation.json','control-inventory-audit.json','game-tour-validation.json','game-integrity-validation.json','game-export-integration-validation.json','combat-release.json','kimodo-combat-regression.json','viewer-validation.json']
for name in reports:
 source=K/'logs'/name
 if source.exists():dump(OUT/'local-evidence'/name,{'evidence_scope':'Recorded local test result; separate public playback validation accompanies publication.','result':clean(json.loads(read(source)))})
summary={'schema':'kimodo-publication/1','generated_gallery':{'takes':90,'bodies':4,'body_clips':360},'game_kit':{'motion_types':94,'takes':188,'bodies':2,'body_clips':376,'default_packs':2},'transport':manifest['validation'],'model':manifest['model'],'model_revision':manifest['model_revision'],'upstream_commit':manifest['upstream_commit'],'scope':'Recorded generated output, browser playback/controller and compact transport. Source motion tracks are float32-exact; reconstructed GLBs have new binary bytes. Contacts, balance and consuming-engine acceptance remain open.','rights':{'model_outputs':'NVIDIA Open Model License says outputs are not Derivative Models and NVIDIA claims no ownership in outputs; user remains responsible for their use.','model_license':'https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/','model_card':'https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2','characters':'Creator-owned robots. Meshy-described fighter by Tulio Portela, CC BY 4.0, test-only; full attribution retained in gallery and asset.','not_redistributed':['Model weights / text encoder / credentials','Bundled training motion datasets','Private human reference videos','Third-party manuals and game screenshots']}}
dump(OUT/'publication.json',summary);dump(game/'reports/validation-summary.json',summary)
write(game/'methods.txt','Kimodo game-motion candidates: see ../dev-log/#game-kit and controls.html.\nThis public site uses recorded generated clips with a browser controller.\nSource-motion GLBs are rebuilt; in-place packs exclude runtime controller and IK.\nSave take bakes the displayed character movement/IK, excluding props.\nTechnical checks do not establish physical balance or production game acceptance.\n')
print('Public Kimodo pages staged; lossless track arrays and original candidate identities retained.')
