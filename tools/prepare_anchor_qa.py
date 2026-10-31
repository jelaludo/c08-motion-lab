"""Convert private cleanup traces for independent Three.js measurements."""
from pathlib import Path
import argparse,json,os,hashlib
import numpy as np
_roots=[Path(os.environ['MOTION_LAB_WORKSPACE'])] if os.environ.get('MOTION_LAB_WORKSPACE') else list(Path(__file__).resolve().parents)
ROOT=next((p for p in _roots if (p/'evaluation').is_dir() and (p/'assets').is_dir()),None)
if ROOT is None:raise RuntimeError('Set MOTION_LAB_WORKSPACE to the original lab workspace')
parser=argparse.ArgumentParser();parser.add_argument('slugs',nargs='+');args=parser.parse_args()
def safe(value):
 if isinstance(value,np.ndarray):return safe(value.tolist())
 if isinstance(value,list):return [safe(x) for x in value]
 if isinstance(value,dict):return {k:safe(v) for k,v in value.items()}
 if isinstance(value,float) and not np.isfinite(value):return None
 return value
for slug in args.slugs:
 assert slug and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in slug)
 folder=ROOT/'evaluation/anchored-cleanup'/slug
 data=np.load(folder/'cleanup-data.npz',allow_pickle=False)
 encoded=safe({key:data[key] for key in data.files})
 encoded['__npz_sha256']=hashlib.sha256((folder/'cleanup-data.npz').read_bytes()).hexdigest()
 (folder/'qa-input.json').write_text(json.dumps(encoded,separators=(',',':'),allow_nan=False),encoding='utf-8')
 print('ANCHOR_QA_INPUT',slug,{k:(list(data[k].shape) if hasattr(data[k],'shape') else None) for k in data.files})
