"""Prepare source previews, validate exported motion, and collect measurable limits."""
from pathlib import Path
import json, os, runpy, subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/c08-worker/round2'
catalog=json.loads((OUT/'catalog.json').read_text())
for case in catalog['tests']:
 if os.environ.get('MB_ONLY_TESTS') and case['id'] not in os.environ['MB_ONLY_TESTS'].split(','):continue
 if case.get('generation')!='passed':continue
 directory=OUT/case['directory'];os.environ['MB_TEST_DIRECTORY']=str(directory)
 runpy.run_path(str(ROOT/'tools/prepare_c08_review.py'),run_name='__main__')
 meta=json.loads((directory/'g1-motion.json').read_text())
 case['joint_limit_violations']=meta['joint_limit_audit']['violations']
 case['source_metrics']=meta['source_metrics']
 if case.get('retarget')=='passed':
  result=subprocess.run(['node',str(ROOT/'tools/review/validate-c08.mjs')],capture_output=True,text=True,env=os.environ)
  (directory/'validation.log').write_text(result.stdout+result.stderr)
  case['technical_validation']='passed' if result.returncode==0 else 'failed'
  if (directory/'validation-report.json').exists():
   validation=json.loads((directory/'validation-report.json').read_text());case['validation']=validation
   retarget=json.loads((directory/'retarget-report.json').read_text());case['adaptation']={k:retarget[k] for k in ('max_pelvis_reach_correction_m','max_foot_floor_lift_m')}
   flags=[]
   if validation['skinned_geometry_min_floor_y_m']<-.002:flags.append('C08 geometry penetrates the floor')
   if retarget['max_foot_floor_lift_m']>.1:flags.append('Large C08 foot-clearance correction')
   if retarget['max_pelvis_reach_correction_m']>.1:flags.append('Large C08 pelvis reach correction')
   if case['source_metrics']['maximum_joint_key_step_rad']>.8:flags.append('Abrupt source joint change')
   if case['joint_limit_violations']:flags.append('Generated G1 joint-limit violations')
   case['review_flags']=flags
 print('CHECKED',case['id'],case.get('technical_validation','source only'),'flags',case.get('review_flags',[]),flush=True)
 (OUT/'catalog.json').write_text(json.dumps(catalog,indent=2))
os.environ.pop('MB_TEST_DIRECTORY',None)
summary={'total':len(catalog['tests']),'original_conditioning':sum(c['provenance_type']=='original' for c in catalog['tests']),'generated':sum(c.get('generation')=='passed' for c in catalog['tests']),'adapted':sum(c.get('retarget')=='passed' for c in catalog['tests']),'technical_passes':sum(c.get('technical_validation')=='passed' for c in catalog['tests']),'flagged_for_review':sum(bool(c.get('review_flags')) for c in catalog['tests']),'adapter_failures':[{'id':c['id'],'error':c.get('retarget_error')} for c in catalog['tests'] if c.get('retarget')=='failed'],'all_motion_quality':'Pending visual and contact review; technical validity does not imply a good motion'}
catalog['summary']=summary;(OUT/'catalog.json').write_text(json.dumps(catalog,indent=2));(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
