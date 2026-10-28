"""Blender batch adapter for predictive outputs and matched non-neural baselines."""
from pathlib import Path
import os,runpy,json,sys
ROOT=Path(__file__).resolve().parents[1]
folders=[Path(p) for p in sys.argv[sys.argv.index('--')+1:]] if '--' in sys.argv else [ROOT/'evaluation/mb-predictive'/c['id'] for c in json.loads((ROOT/'evaluation/mb-predictive/catalog.json').read_text())['cases']]
for folder in folders:
 for p in [folder,folder/'linear']:
  if not (p/'g1-motion.npz').exists():continue
  os.environ['MB_TEST_DIRECTORY']=str(p);runpy.run_path(str(ROOT/'tools/retarget_c08_test.py'),run_name='__main__')
