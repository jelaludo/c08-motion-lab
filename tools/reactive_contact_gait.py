"""Explicit authored contact paths + bounded G1 leg IK over a permitted gait.

This is external animation preparation, not MotionBricks inference. Permitted
source upper-body motion and squat height are retained; travel is shortened and
lateral pelvis roll is removed. Feet alternate support and minimum-jerk swing.
"""
from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from harvest_fit_g1 import fk,INDEX,LOW,HIGH

def contact_gait(qpos,fps=30,duty=.64,lift=.075,pace_scale=.3,root_lift=0.,foot_forward=.4):
 original=np.asarray(qpos,float);q=original.copy();period=len(q)-1;duration=period/fps
 travel=q[-1,:2]-q[0,:2];yaw=np.arctan2(travel[1],travel[0]);align=Rotation.from_euler('z',-yaw)
 q[:,:3]=align.apply(q[:,:3]);q[:,:2]*=pace_scale;q[:,2]+=root_lift
 # Retain forward squat lean; remove lateral pelvis rolling for support.
 pitch=np.array([Rotation.from_quat(row[3:7]).as_euler('xyz')[1]for row in original])
 q[:,3:7]=np.c_[np.zeros(len(q)),np.sin(pitch/2),np.zeros(len(q)),np.cos(pitch/2)]
 stride=q[-1,:3]-q[0,:3];stride[2]=0
 F=[fk(row)for row in q];offsets={'left':0.,'right':.5};leg_names=['hip_pitch','hip_roll','hip_yaw','knee','ankle_pitch','ankle_roll'];seeds={};anchors={}
 for side,phase in offsets.items():
  frame=round(phase*period);anchors[side]=q[frame,:3].copy();anchors[side][0]+=foot_forward;anchors[side][1]+=.11 if side=='left'else -.11;anchors[side][2]=.036
  seeds[side]=q[0,[INDEX[side+'_'+n+'_joint']for n in leg_names]].copy()
 corrected=q.copy();contacts=np.zeros((len(q),4),np.float32);errors=[]
 for frame,row in enumerate(q):
  phase=frame/period
  # Source yaw is retained, but support soles remain flat rather than rolling
  # through a drifting fitted ankle trajectory.
  forward=Rotation.from_quat(row[3:7]).apply([1,0,0]);yaw=np.arctan2(forward[1],forward[0]);foot_rotation=Rotation.from_euler('z',yaw).as_matrix()
  for side,offset in offsets.items():
   absolute=phase-offset;cycle=np.floor(absolute);local=absolute-cycle;anchor=anchors[side]+cycle*stride
   supported=local<duty
   if supported:target=anchor.copy()
   else:
    u=(local-duty)/(1-duty);smooth=u*u*u*(10+u*(-15+6*u));target=anchor+stride*smooth;target[2]+=(np.sin(np.pi*u)**2)*lift
   indices=np.array([INDEX[side+'_'+n+'_joint']for n in leg_names]);start=np.clip(row[indices],LOW[indices-7],HIGH[indices-7]);base=row.copy()
   def residual(angles):
    base[indices]=angles;p,r=fk(base)[side+'_ankle_roll_link'];return np.r_[(p-target)*5,(r-foot_rotation).ravel()*.5,(angles-start)*.0001]
   solved=least_squares(residual,start,bounds=(LOW[indices-7],HIGH[indices-7]),max_nfev=100,ftol=1e-10,xtol=1e-10,gtol=1e-10)
   corrected[frame,indices]=solved.x;seeds[side]=solved.x;now=fk(corrected[frame])[side+'_ankle_roll_link'];errors.append({'frame':frame,'side':side,'support':bool(supported),'position_error_m':float(np.linalg.norm(now[0]-target)),'orientation_error_rad':float(Rotation.from_matrix(now[1]@foot_rotation.T).magnitude()),'target':target.tolist()})
   if supported:
    if side=='left':contacts[frame,:2]=1
    else:contacts[frame,2:]=1
 report={'method':'Explicit alternating flat support / minimum-jerk swing, bounded 6-DOF leg IK over CC0 upper-body style. Canonical forward travel, shortened stride, forward squat lean and no lateral pelvis roll. Not neural inference.','period_s':duration,'duty_factor':duty,'swing_lift_m':lift,'native_stride_m':stride.tolist(),'root_lift_m':root_lift,'pace_scale':pace_scale,'foot_forward_from_pelvis_m':foot_forward,'prepared_root_preserved_during_leg_ik':bool(np.array_equal(q[:,:7],corrected[:,:7])),'maximum_ankle_target_error_m':max(e['position_error_m']for e in errors),'maximum_foot_rotation_error_rad':max(e['orientation_error_rad']for e in errors),'hinge_change_max_rad':float(np.max(np.abs(corrected[:,7:]-q[:,7:]))),'errors':errors}
 return corrected.astype(np.float32),contacts,report

if __name__=='__main__':
 root=Path(__file__).resolve().parents[1];folder=root/'evaluation/reactive-round4';source=folder/'cc0-crouch-fitted.npz';q=np.load(source)['qpos'];fixed,contacts,report=contact_gait(q);np.savez_compressed(folder/'cc0-crouch-contact-ik.npz',qpos=fixed,contacts=contacts);(folder/'cc0-crouch-contact-ik.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k!='errors'}))
