from pathlib import Path
import json,numpy as np,hashlib
from scipy.spatial.transform import Rotation,Slerp
from scipy.interpolate import PchipInterpolator
r=Path(__file__).resolve().parents[1];src=r/'evaluation/c08-worker/round2/own_jump_over/g1-motion.npz';d=np.load(src);q=d['qpos'];schedule=[('recoil',28,58,18),('extend',58,62,6),('flight',62,117,23),('land',117,127,9),('recovery',127,135,12)];indices=[28.];phases=['recoil']
for name,a,b,n in schedule:
 for value in np.linspace(a,b,n+1)[1:]:indices.append(value);phases.append(name)
knots=np.cumsum([0]+[row[3]/30 for row in schedule]);source_knots=[28]+[row[2] for row in schedule];x=PchipInterpolator(knots,source_knots)(np.arange(len(indices))/30);out=np.array([np.interp(x,np.arange(len(q)),q[:,i]) for i in range(36)]).T;out[:,3:7]=Slerp(np.arange(len(q)),Rotation.from_quat(q[:,3:7]))(x).as_quat();origin=out[0,:2].copy();out[:,:2]-=origin;out[:,:2]*=2.04;c=np.array([np.interp(x,np.arange(len(q)),d['contacts'][:,i]) for i in range(4)]).T;dest=r/'evaluation/reactive-round4';dest.mkdir(exist_ok=True);np.savez_compressed(dest/'jump-retimed-raw.npz',qpos=out.astype(np.float32),contacts=c.astype(np.float32),phase_names=np.array(phases),source_indices=x)
meta={'source':'Original-conditioned MotionBricks own_jump_over','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'method':'Contiguous recorded pose trajectory retimed by semantic phases; horizontal displacement scaled2.04; source root-height samples and joints interpolated without a new vertical arc. Stance contact preparation is separate.','phases':schedule,'fps':30,'frames':len(out),'duration_s':(len(out)-1)/30,'forward_distance_m':float(out[-1,0]-out[0,0])};(dest/'jump-retimed-raw.json').write_text(json.dumps(meta,indent=2),encoding='utf8');print(meta)
