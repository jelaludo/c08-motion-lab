from pathlib import Path
import json,os,runpy,traceback
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/c08-worker/round3'
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
for case in catalog['tests']:
    if os.environ.get('MB_ONLY_TESTS') and case['id'] not in os.environ['MB_ONLY_TESTS'].split(','):continue
    if case.get('generation')!='passed':continue
    folder=OUT/case['directory'];os.environ['MB_TEST_DIRECTORY']=str(folder)
    try:
        runpy.run_path(str(ROOT/'tools/retarget_c08_test.py'),run_name='__main__');case['retarget']='passed';print('FRESH_ADAPTED',case['id'],flush=True)
    except Exception as error:
        case['retarget']='failed';case['retarget_error']=str(error);(folder/'retarget-failure.json').write_text(json.dumps({'error':str(error),'traceback':traceback.format_exc()},indent=2),encoding='utf-8');print('FRESH_ADAPTER_LIMIT',case['id'],error,flush=True)
    (OUT/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
os.environ.pop('MB_TEST_DIRECTORY',None)
