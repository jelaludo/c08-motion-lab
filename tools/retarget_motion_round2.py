"""Run the existing C08 adapter over the gallery in Blender; preserve source-only failures."""
from pathlib import Path
import json, os, runpy, traceback
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evaluation/c08-worker/round2'
catalog=json.loads((OUT/'catalog.json').read_text())
for case in catalog['tests']:
 if os.environ.get('MB_ONLY_TESTS') and case['id'] not in os.environ['MB_ONLY_TESTS'].split(','):continue
 if case.get('generation')!='passed':continue
 directory=OUT/case['directory'];os.environ['MB_TEST_DIRECTORY']=str(directory)
 try:
  runpy.run_path(str(ROOT/'tools/retarget_c08_test.py'),run_name='__main__')
  case['retarget']='passed'
  print('ADAPTED',case['id'],flush=True)
 except Exception as error:
  case['retarget']='failed';case['retarget_error']=str(error)
  (directory/'retarget-failure.json').write_text(json.dumps({'error':str(error),'traceback':traceback.format_exc(),'source_available':True},indent=2))
  print('ADAPTER_LIMIT',case['id'],error,flush=True)
 (OUT/'catalog.json').write_text(json.dumps(catalog,indent=2))
os.environ.pop('MB_TEST_DIRECTORY',None)
print('ROUND2_RETARGET_COMPLETE',flush=True)
