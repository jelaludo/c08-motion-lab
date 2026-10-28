from pathlib import Path
import os,runpy,json,traceback
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/pose-harvest';catalog=json.loads((OUT/'catalog.json').read_text())
for case in catalog['cases']:
 if case.get('generation')!='passed':continue
 folder=ROOT/case['directory'];errors=[]
 for source in [folder,folder/'linear']:
  os.environ['MB_TEST_DIRECTORY']=str(source)
  try:runpy.run_path(str(ROOT/'tools/retarget_c08_test.py'),run_name='__main__')
  except Exception as e:errors.append(str(e));(source/'adapter-failure.json').write_text(json.dumps({'error':str(e),'traceback':traceback.format_exc()},indent=2));print('ADAPTER_LIMIT',case['id'],source.name,str(e),flush=True)
 case.update(retarget='failed' if errors else 'passed',retarget_errors=errors);(OUT/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf8')
