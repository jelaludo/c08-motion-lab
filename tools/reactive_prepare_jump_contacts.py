"""Contact-adapt selected takeoff/landing poses; retain source root flight arc."""
from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from harvest_fit_g1 import fk,INDEX,LOW,HIGH
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'evaluation/reactive-round4';source=np.load(folder/'jump-retimed-raw.npz');q=source['qpos'].astype(float);out=q.copy();contacts=np.zeros((len(q),4),np.float32);anchors={};errors=[];leg_names=['hip_pitch','hip_roll','hip_yaw','knee','ankle_pitch','ankle_roll'];phase_names=source['phase_names']
for f,row in enumerate(q):
 F=fk(row);phase=str(phase_names[f])
 for side,offset in [('left',0),('right',2)]:
  p,r=F[side+'_ankle_roll_link'];supported=phase not in ('flight','airborne') and p[2]<.08
  if not supported:anchors.pop(side,None);continue
  if side not in anchors:anchors[side]=p.copy();anchors[side][2]=.036
  target=anchors[side];indices=np.array([INDEX[side+'_'+n+'_joint']for n in leg_names]);base=row.copy();start=np.clip(row[indices],LOW[indices-7],HIGH[indices-7]);heading=Rotation.from_quat(row[3:7]).apply([1,0,0]);rotation=Rotation.from_euler('z',float(np.arctan2(heading[1],heading[0]))).as_matrix()
  def residual(angles):
   base[indices]=angles;now=fk(base)[side+'_ankle_roll_link'];return np.r_[(now[0]-target)*5,(now[1]-rotation).ravel()*.5,(angles-start)*.0001]
  solved=least_squares(residual,start,bounds=(LOW[indices-7],HIGH[indices-7]),max_nfev=100,ftol=1e-10,xtol=1e-10,gtol=1e-10);base[indices]=solved.x;now=fk(base)[side+'_ankle_roll_link'];error=float(np.linalg.norm(now[0]-target));angle=float(Rotation.from_matrix(now[1]@rotation.T).magnitude());correction=float(np.max(np.abs(solved.x-row[indices])));accepted=error<.001 and angle<.01 and correction<.18
  if accepted:out[f,indices]=solved.x;contacts[f,offset:offset+2]=1
  else:anchors.pop(side,None)
  errors.append({'frame':f,'side':side,'phase':phase,'accepted':bool(accepted),'position_error_m':error,'rotation_error_rad':angle,'maximum_correction_rad':correction})
for side,offset in [('left',0),('right',2)]:
 indices=np.array([INDEX[side+'_'+n+'_joint']for n in leg_names]);active=contacts[:,offset]>.5
 for f in np.where(active)[0]:
  start=f;end=f
  while start>0 and active[start-1]:start-=1
  while end<len(q)-1 and active[end+1]:end+=1
  weight=min(1.,(f-start+1)/3,(end-f+1)/3)
  out[f,indices]=q[f,indices]+(out[f,indices]-q[f,indices])*weight
  if weight<1:contacts[f,offset:offset+2]=0
report={'method':'Selected source takeoff/landing support frames receive bounded leg IK and flat soles; unreachable support requests release rather than editing the root. Flight poses unchanged. Explicit prepared-motion contact correction, not inference.','root_arc_and_quaternion_unchanged':bool(np.array_equal(q[:,:7],out[:,:7])),'accepted_support_samples':sum(r['accepted']for r in errors),'released_support_samples':sum(not r['accepted']for r in errors),'maximum_accepted_position_error_m':max((r['position_error_m']for r in errors if r['accepted']),default=0),'maximum_hinge_step_rad':float(np.max(np.abs(np.diff(out[:,7:],axis=0)))),'errors':errors}
arrays={name:source[name]for name in source.files};arrays.update(qpos=out.astype(np.float32),contacts=contacts,original_retimed_qpos=q.astype(np.float32));np.savez_compressed(folder/'jump-contact.npz',**arrays);(folder/'jump-contact.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k!='errors'}))
