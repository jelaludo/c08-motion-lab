from pathlib import Path
import json,numpy as np
from harvest_fit_g1 import fit_case
r=Path(__file__).resolve().parents[1];out=r/'evaluation/reactive-round4';source=json.loads((out/'cc0-gaits-full.json').read_text())['cases'][0];fit=fit_case(source);(out/'cc0-crouch-fitted.json').write_text(json.dumps(fit),encoding='utf8');np.savez_compressed(out/'cc0-crouch-fitted.npz',qpos=np.array(fit['qpos'],np.float32));print('FITTED_CC0_CROUCH',len(fit['qpos']),fit['fit_seconds'],flush=True)
