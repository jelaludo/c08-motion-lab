from pathlib import Path
import argparse,json,subprocess,time
import os
_candidates=[Path(os.environ['MOTION_LAB_WORKSPACE'])] if os.environ.get('MOTION_LAB_WORKSPACE') else list(Path(__file__).resolve().parents)
ROOT=next((p for p in _candidates if (p/'evaluation').is_dir() and (p/'video-mocap').is_dir() and (p/'assets').is_dir()),None)
if ROOT is None:raise RuntimeError('Set MOTION_LAB_WORKSPACE to the original workspace; private captures and recovered SOMA inputs are not bundled.')
parser=argparse.ArgumentParser();parser.add_argument('methods',nargs='*',default=['raw','cleaned','single','window']);args=parser.parse_args()
slugs=['ukemi','technical-standup','gorilla-front','sumo-stomp','source-094553','h3-dance']
blender=ROOT/'tools/blender-4.5.15-windows-x64/blender.exe'
records=[]
for name in slugs:
 for method in args.methods:
  source=ROOT/'evaluation/mocap-rebuild'/name/method/'soma-frames.npz'
  if not source.exists():print('WAITING',name,method,flush=True);continue
  out=ROOT/'evaluation/mocap-rebuild/exports'/name/method
  log=ROOT/'logs'/f'rebuild-{name}-{method}-export.log'
  with log.open('w',encoding='utf-8') as stream:
   code=subprocess.run([str(blender),'--background','--python',str(ROOT/'tools/retarget_mocap_rebuild.py'),'--',name,method],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT).returncode
  if code:raise RuntimeError((name,method,'Blender failed',code))
  print('EXPORTED',name,method,flush=True)
  code=subprocess.run(['node',str(ROOT/'tools/validate_mocap_rebuild.mjs'),name+':'+method],cwd=ROOT).returncode
  if code:raise RuntimeError((name,method,'Validation failed',code))
  records.append({'id':name,'method':method,'status':'ready'})
  (ROOT/'evaluation/mocap-rebuild/export-state.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('EXPORT_BATCH_COMPLETE',len(records),flush=True)
