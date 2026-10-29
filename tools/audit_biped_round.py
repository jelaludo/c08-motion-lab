"""Verify the published biped matrix and attribution without accepting motion quality."""
from pathlib import Path
import gzip, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'docs/biped-motion'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
catalog=load(FOLDER/'catalog.json')
assert {b['id'] for b in catalog['bodies']}=={'c08','brek43','eva-k7','meshy-fighter'}
assert {t['id'] for t in catalog['tests']}=={'ukemi','technical-standup','gorilla-front','sumo-stomp','source-094553','h3-dance'}
rows=[]
for test in catalog['tests']:
 assert len(test['outputs'])==4
 assert {o['body'] for o in test['outputs']}=={b['id'] for b in catalog['bodies']}
 for output in test['outputs']:
  model=FOLDER/output['model'];report=load(FOLDER/output['report'])
  digest=hashlib.sha256(model.read_bytes()).hexdigest()
  assert digest==output['sha256']==report['glb_sha256']
  qa=report['validation']
  assert qa['gltf_errors']==qa['gltf_warnings']==0
  assert qa['max_exported_joint_position_error_m']<.0001
  assert qa['max_segment_length_variation_m']<.0001
  assert qa['independent_clones'] and not qa['prohibited_animation_tracks']
  assert report['frames']==test['metrics']['frames']
  if output['body']=='meshy-fighter':
   assert report['attribution']['author']=='Tulio Portela'
   assert report['attribution']['license']=='CC-BY-4.0'
  rows.append({'id':test['id'],'body':output['body'],'path':model.relative_to(ROOT).as_posix(),'sha256':digest,'frames':report['frames'],'floor_sample_min_m':qa['skinned_geometry_min_floor_y_m'],'max_joint_export_error_m':qa['max_exported_joint_position_error_m']})
 data=json.loads(gzip.decompress((FOLDER/f"data/{test['id']}-skeleton.json.gz").read_bytes()))
 assert len(data['positions'])==data['frame_count']==test['metrics']['frames']
 assert len(data['joint_names'])==77 and data['id']==test['id']
 json.dumps(data,allow_nan=False)
for path in FOLDER.rglob('*'):
 if not path.is_file():continue
 assert path.suffix.lower() not in {'.mp4','.jpg','.png','.pt','.pth','.pkl','.onnx','.ckpt'},path
 if path.suffix.lower() in {'.json','.html','.js'}:
  text=path.read_text(encoding='utf-8')
  assert 'source_local_path' not in text and 'C:\\Users\\' not in text and 'G:\\Dev\\' not in text,path
feedback=load(ROOT/'docs/h3-motion/reports/visual-feedback-2026-10-30.json')
assert len(feedback['tests'])==13 and feedback['summary']=={'looking-good':5,'failure':7,'promising-rework':1}
recovery=load(ROOT/'research/biped-round2-recovery.json')
assert len(recovery['cases'])==6 and sum(not c['recovery_reused'] for c in recovery['cases'])==2
docs_bytes=sum(p.stat().st_size for p in (ROOT/'docs').rglob('*') if p.is_file())
assert docs_bytes<970*1024**2
result={'status':'passed','scope':'Serialization, provenance, matrix completeness and published artifact identity; not visual acceptance or physical balance','comparisons':len(rows),'raw_skeletons':6,'raw_source_media_published':False,'new_recoveries':2,'verified_cached_recoveries':4,'previous_visual_verdicts_preserved':13,'pages_artifact_mib':round(docs_bytes/1024**2,2),'results':rows}
(ROOT/'research/biped-round2-release-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
