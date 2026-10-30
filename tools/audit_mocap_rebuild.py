"""Audit published pilot identity and loops; retain measured motion-quality failures."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];FOLDER=ROOT/'docs/mocap-rebuild'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
catalog=load(FOLDER/'catalog.json');methods={'raw','cleaned','single','window'}
assert {m['id'] for m in catalog['methods']}==methods and catalog['body']=='c08'
assert len(catalog['tests'])==6
calls=0;rows=[];findings=[]
for test in catalog['tests']:
 assert len(test['outputs'])==4 and {o['method'] for o in test['outputs']}==methods
 reports={}
 for output in test['outputs']:
  model=FOLDER/output['model'];report=load(FOLDER/output['report']);qa=report['validation'];method=output['method']
  assert hashlib.sha256(model.read_bytes()).hexdigest()==output['sha256']==report['artifact_sha256']
  assert qa['gltf_errors']==qa['gltf_warnings']==0
  assert qa['independent_clones'] and not qa['prohibited_animation_tracks']
  assert qa['max_exported_joint_position_error_m']<.0001
  assert qa['max_segment_length_variation_m']<.0001
  assert report['frames']==output['frames']==qa['frames']
  assert 'constant' in report['ground_policy'].lower()
  if method in {'single','window'}:
   trace=load(FOLDER/output['trace']);assert trace['method']==method and trace['id']==test['id']
   assert trace['actual_neural_calls']==len(trace['segments'])==8
   assert all(s['target_window_frames']==(1 if method=='single' else 4) for s in trace['segments'])
   assert all(s['raw_frames']-s['frames']==s['used_start_index']==1 for s in trace['segments'])
   assert [s['source_key_index'] for s in trace['segments'][:-1]]==[k['frame'] for k in test['keyframes']]
   seam=qa['seam']
   assert output['metrics']['root_seam_gap_m']<1e-6
   assert output['metrics']['maximum_joint_seam_gap_m']<1e-6
   assert output['metrics']['rotation_seam_deg']<1e-5
   assert output['metrics']['start_root_speed_m_s']<1e-6 and output['metrics']['end_root_speed_m_s']<1e-6
   assert report['provenance']['neutral_hold_frames']==12
   assert qa['active_frame_range'][0]==12 and qa['active_frame_range'][1]==qa['frames']-13
   calls+=8
  else:assert output['metrics']['actual_neural_calls']==0
  reports[method]=report
  rows.append({'id':test['id'],'method':method,'path':model.relative_to(ROOT).as_posix(),'sha256':output['sha256'],'frames':qa['frames'],'metrics':output['metrics']})
 assert reports['raw']['constant_ground_offset_m']==reports['cleaned']['constant_ground_offset_m']
 assert reports['raw']['frames']==reports['cleaned']['frames']
 findings.append({'id':test['id'],'methods':{m:{'duration_s':reports[m]['validation']['duration_s'],'floor_minimum_m':reports[m]['metrics']['minimum_skin_floor_m'],'active_angular_acceleration_p95_rad_s2':reports[m]['metrics']['local_joint_angular_acceleration_p95_rad_s2']} for m in ['raw','cleaned','single','window']}})
assert calls==96
generation=load(ROOT/'research/mocap-rebuild-generation-validation.json')
assert generation['status']=='passed' and generation['actual_neural_calls']==96 and generation['neural_variants']==12
guard=load(ROOT/'research/mocap-rebuild-source-guard.json');assert guard['status']=='passed' and guard['immutable_files']==56
for path in FOLDER.rglob('*'):
 if not path.is_file():continue
 assert path.suffix.lower() not in {'.mp4','.jpg','.png','.pt','.pth','.pkl','.onnx','.ckpt','.npz'},path
 if path.suffix in {'.json','.js','.html'}:
  text=path.read_text(encoding='utf-8')
  assert 'source_local_path' not in text and 'C:\\Users\\' not in text and 'G:\\Dev\\' not in text,path
size=sum(p.stat().st_size for p in (ROOT/'docs').rglob('*') if p.is_file());assert size<970*1024**2
result={'status':'artifact_integrity_passed_visual_review_required','performances':6,'comparisons':24,'neural_variants':12,'actual_neural_calls':96,'closed_neutral_loops':12,'previous_source_artifacts_unchanged':56,'pages_artifact_mib':round(size/1024**2,2),'scope':'Matching endpoints and valid exports do not establish natural motion, contacts or balance. Measured penetrations remain visible. Authored holds are excluded from active jitter metrics.','results':rows,'findings':findings}
(ROOT/'research/mocap-rebuild-release-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in {'results','findings'}},indent=2))
