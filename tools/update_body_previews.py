from pathlib import Path
import json,runpy,os,shutil
ROOT=Path(__file__).resolve().parents[1];site=ROOT/'public/c08-motion-lab/docs/mb-predictive';cases=json.loads((site/'catalog.json').read_text())['cases'];harvest=json.loads((ROOT/'evaluation/pose-harvest/catalog.json').read_text())['cases'];byid={c['id']:c for c in harvest}
for c in cases:
 source=ROOT/byid[c['id']]['directory'] if c.get('harvested') else ROOT/('evaluation/predictive-sequences' if c.get('routine') else 'evaluation/mb-predictive')/c['id']
 for branch in ['', 'linear']:
  folder=source/branch;os.environ['MB_TEST_DIRECTORY']=str(folder);runpy.run_path(str(ROOT/'tools/prepare_c08_review.py'),run_name='__main__');shutil.copy2(folder/'g1-preview.json',site/'cases'/c['id']/branch/'g1-preview.json')
for c in harvest:
 if c['publishable']:continue
 for branch in ['', 'linear']:
  folder=ROOT/c['directory']/branch;os.environ['MB_TEST_DIRECTORY']=str(folder);runpy.run_path(str(ROOT/'tools/prepare_c08_review.py'),run_name='__main__');shutil.copy2(folder/'g1-preview.json',ROOT/'evaluation/pose-harvest/local-view'/c['id']/branch/'g1-preview.json')
os.environ.pop('MB_TEST_DIRECTORY',None);print('UPDATED_BODY_PREVIEWS',len(cases),flush=True)
