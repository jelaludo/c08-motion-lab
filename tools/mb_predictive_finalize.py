from pathlib import Path
import json,runpy,os,subprocess,shutil,sys
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/mb-predictive';PUBLIC=ROOT/'public/c08-motion-lab/docs/mb-predictive'
def finalize_case(folder,destination):
 folder=Path(folder);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
 for source,target in [(folder,destination),(folder/'linear',destination/'linear')]:
  if not source.exists():continue
  os.environ['MB_TEST_DIRECTORY']=str(source);runpy.run_path(str(ROOT/'tools/prepare_c08_review.py'),run_name='__main__');result=subprocess.run(['node',str(ROOT/'tools/review/validate-c08.mjs')],capture_output=True,text=True,encoding='utf8',env=os.environ)
  (source/'validation.log').write_text(result.stdout+result.stderr,encoding='utf8')
  if result.returncode:raise RuntimeError('Export validation failed: '+result.stdout+result.stderr)
  target.mkdir(exist_ok=True)
  for file in ['c08-motionbricks-test.glb','g1-motion.json','g1-preview.json','validation-report.json']:shutil.copy2(source/file,target/file)
  report=json.loads((source/'retarget-report.json').read_text());positions=report.pop('sample_positions_blender');report['root_path']=[[p['PELVIS'][0],.015,-p['PELVIS'][1]] for p in positions];(target/'retarget-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 trace=json.loads((folder/'prediction-trace.json').read_text());trace['metadata']=json.loads((folder/'g1-motion.json').read_text());report=json.loads((folder/'retarget-report.json').read_text());preview=json.loads((folder/'g1-preview.json').read_text());trace.update(body_names=preview['body_names'],parents=preview['parents'],display_scale=report['source_to_target_scale'],display_pelvis_offset=1.1-trace['skeletons_g1_zup'][0]['context'][0][preview['body_names'].index('pelvis')][2]*report['source_to_target_scale'])
 data=np.load(folder/'g1-motion.npz');idx=list(data['body_names']).index('pelvis');q=data['body_transforms'][0,idx,3:7];S=np.array([[0,1,0],[-1,0,0],[0,0,1]]);r=S@Rotation.from_quat(q).as_matrix()@S.T;forward=r@np.array([0,-1,0]);yaw=np.arctan2(forward[0],-forward[1]);A=Rotation.from_rotvec([0,0,-yaw]).as_matrix()@S;origin=A@data['body_transforms'][0,idx,:3];origin[2]=0;D=np.array([[1,0,0],[0,0,1],[0,-1,0]]);trace['display_basis']=(D@A).tolist();trace['display_origin']=(D@origin).tolist();trace['display_pelvis_offset']=float(report['sample_positions_blender'][0]['PELVIS'][2]-data['body_transforms'][0,idx,2]*report['source_to_target_scale'])
 (destination/'prediction-trace.json').write_text(json.dumps(trace,indent=2),encoding='utf8');os.environ.pop('MB_TEST_DIRECTORY',None)
 return trace
if __name__=='__main__':
 PUBLIC.mkdir(parents=True,exist_ok=True);catalog=json.loads((OUT/'catalog.json').read_text())
 for case in catalog['cases']:
  trace=finalize_case(OUT/case['id'],PUBLIC/'cases'/case['id']);case.update(inference_seconds=trace['metadata']['inference_seconds'],segment_count=len(trace['metadata']['segments']));print('VERIFIED',case['id'],flush=True)
 (PUBLIC/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf8')
