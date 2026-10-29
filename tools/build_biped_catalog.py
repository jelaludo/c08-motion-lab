from pathlib import Path
import json,shutil,hashlib,datetime
import os
_candidates=[Path(os.environ['MOTION_LAB_WORKSPACE'])] if os.environ.get('MOTION_LAB_WORKSPACE') else list(Path(__file__).resolve().parents)
ROOT=next((p for p in _candidates if (p/'video-mocap').is_dir() and (p/'assets').is_dir()),None)
if ROOT is None:raise RuntimeError('Set MOTION_LAB_WORKSPACE to the original local lab workspace containing video-mocap and assets; private source recoveries are not bundled.')
PUB=ROOT/'public/c08-motion-lab/docs/biped-motion';(PUB/'models').mkdir(parents=True,exist_ok=True);(PUB/'reports').mkdir(exist_ok=True)
manifest=json.loads((ROOT/'video-mocap/biped-round-2026-10-30.json').read_text(encoding='utf-8'))
ATTR=json.loads((ROOT/'public/c08-motion-lab/docs/assets/meshy-fighter-attribution.json').read_text(encoding='utf-8'))
bodies=[{'id':'c08','label':'C08 worker'},{'id':'brek43','label':'B-REK43'},{'id':'eva-k7','label':'EVA-K7'},{'id':'meshy-fighter','label':'Meshy fighter (test only)','attribution':f"{ATTR['source_title']} by {ATTR['author']}, CC BY 4.0. Experimental rig/skin by C08 Motion Lab. {ATTR['source_url']}"}]
tests=[]
for case in manifest['cases']:
 slug=case['id'];outputs=[];maxground=0
 for body in bodies:
  ident=body['id'];folder=ROOT/'video-mocap/biped-round2'/slug/ident;model=folder/'c08-mocap.glb';reportpath=folder/'retarget-report.json';qa=folder/'validation-report.json'
  if not model.exists() or not qa.exists():continue
  validation=json.loads(qa.read_text(encoding='utf-8'));assert validation['gltf_errors']==0,(slug,ident,validation['gltf_errors'])
  report=json.loads(reportpath.read_text(encoding='utf-8'));report['pipeline']='Private reference video -> GEM-X native77 SOMA -> direct original-biped rig adaptation; no MotionBricks generation'
  report['validation']=validation;report['source_sha256']=case['source_sha256'];report['source_label']=case['label'];report['limitations']=list(dict.fromkeys(case['limitations']+report['limitations']))
  dest=f'{slug}-{ident}';shutil.copy2(model,PUB/'models'/f'{dest}.glb');report['glb_sha256']=hashlib.sha256(model.read_bytes()).hexdigest();(PUB/'reports'/f'{dest}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  outputs.append({'body':ident,'model':f'models/{dest}.glb','report':f'reports/{dest}.json','sha256':report['glb_sha256']});maxground=max(maxground,report['max_abs_ground_correction_m'])
 limits=case['limitations']+['Monocular recovery estimates depth and hidden limbs; no independent ground truth for these videos.','Whole-body vertical grounding translates each target to keep its lowest skinned vertex 15 mm above the floor at authored keys. It can alter vertical motion; no support, collision or balance solve.','Original fingers remain at rest; no source finger capture.','Experimental derived takes for visual review; not automatically accepted for game use.']
 if slug=='gorilla-front':limits.insert(0,'UNRELIABLE TAIL: 55/239 frames have at least five major projected joints outside the image; 25 detections were filled. Full clip retained for diagnosis.')
 tests.append({'id':slug,'title':case['label'],'version':1,'source':{'label':case['label'],'sha256':case['source_sha256'],'recovery_reused':case.get('recovery_reused',False)},'description':'Direct recovered SOMA movement adapted independently to four original biped rigs, with synchronized playback. No MotionBricks generation and no G1 intermediate.','limitations':limits,'outputs':outputs,'metrics':{'frames':case.get('frames'),'fps':case.get('fps',30),'duration_s':case.get('duration_s'),'available_bodies':len(outputs),'max_whole_body_ground_correction_m':maxground}})
(PUB/'catalog.json').write_text(json.dumps({'version':1,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'summary':'Biped-only round: six reference motions, four bodies, 24 experimental direct adaptations. Review naturalness, floor support and transitions; finite exports do not establish motion quality.','bodies':bodies,'tests':tests},indent=2),encoding='utf-8')
print('CATALOG',len(tests),'tests',sum(len(t['outputs']) for t in tests),'models')
