"""Sparse source-pose -> bounded G1 fitting, with measured loss and no sample-data mixing."""
from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET,time
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/pose-harvest';OUT.mkdir(parents=True,exist_ok=True)
LIB=json.loads((ROOT/'evaluation/c08-worker/round2/original-g1-poses.json').read_text(encoding='utf8'));NEUTRAL=np.array(LIB['poses']['neutral'],float);INDEX={n:i+7 for i,n in enumerate(LIB['joint_names'])}
XML=ET.parse(ROOT/'upstream/motionbricks/assets/robots/unitree_g1/g1_29dof_rev_1_0.xml');nodes=[];limits={}
def vec(s,default):return np.array(list(map(float,s.split())) if s else default,float)
def visit(body,parent=-1):
 i=len(nodes);quat=vec(body.get('quat'),[1,0,0,0]);rotation=R.from_quat(quat[[1,2,3,0]]).as_matrix();joints=[]
 for j in body.findall('joint'):
  if j.get('type')=='free':continue
  axis=vec(j.get('axis'),[0,0,1]);x,y,z=axis;K=np.array([[0,-z,y],[z,0,-x],[-y,x,0]]);joints.append((INDEX[j.get('name')],K,K@K,vec(j.get('pos'),[0,0,0])));limits[j.get('name')]=tuple(map(float,j.get('range').split()))
 nodes.append((body.get('name'),parent,vec(body.get('pos'),[0,0,0]),rotation,joints))
 for child in body.findall('body'):visit(child,i)
visit(XML.getroot().find('worldbody').find('body'))
LOW=np.array([limits[n][0]+1e-5 for n in LIB['joint_names']]);HIGH=np.array([limits[n][1]-1e-5 for n in LIB['joint_names']])
def fk(q):
 result={};world=[]
 for name,parent,p,r,joints in nodes:
  if parent<0:p=q[:3].copy();r=R.from_quat(q[3:7]).as_matrix()
  else:
   pp,pr=world[parent];p=pp+pr@p;r=pr@r
   for index,K,K2,origin in joints:
    angle=q[index];turn=np.eye(3)+np.sin(angle)*K+(1-np.cos(angle))*K2;p=p+r@(origin-turn@origin);r=r@turn
  world.append((p,r));result[name]=(p,r)
 return result
REST=fk(NEUTRAL)
def unit(v):return v/max(1e-9,np.linalg.norm(v))
def source_cases():
 cases=json.loads((OUT/'quaternius-poses.json').read_text())['cases']
 for name in ['deadlift','sumo-stomp','technical-standup','ukemi','gorilla-side','gorilla-front']:
  folder=ROOT/'video-mocap/c08-retarget'/name;d=np.load(folder/'soma-frames.npz');count=len(d['timestamps']);idx=[0,1,2,3,round((count-1)*.5),count-1]
  cases.append({'id':'capture_'+name.replace('-','_'),'label':'Own capture / '+name.replace('-',' '),'family':'own_capture','license':'user-owned reference','publishable':True,'source_clip':name,'source_sha256':hashlib.sha256((folder/'soma-frames.npz').read_bytes()).hexdigest(),'duration_s':float(d['timestamps'][-1]),'sample_times_s':d['timestamps'][idx].tolist(),'joint_names':d['joint_names'].tolist(),'reference_transforms':d['reference_transforms'].tolist(),'world_transforms':d['world_transforms'][idx].tolist(),'basis':'soma','ground':float(d['surface_bounds_world'][:,0,1].min()),'reference_ground':float(d['reference_surface_bounds'][0,1])})
 return cases

def fit_case(case):
 names=case['joint_names'];lookup={n:i for i,n in enumerate(names)};world=np.array(case['world_transforms']);reference=np.array(case['reference_transforms']);soma=case['basis']=='soma';basis=np.array([[0,0,1],[1,0,0],[0,1,0]]) if soma else np.array([[0,-1,0],[1,0,0],[0,0,1]])
 hip='Hips' if soma else 'pelvis';chest='Chest' if soma else 'spine_03';root_ref=reference[lookup[hip]];delta0=basis@world[0,lookup[hip],:3,:3]@root_ref[:3,:3].T@basis.T;heading=delta0@np.array([1,0,0]);yaw=np.arctan2(heading[1],heading[0]);align=R.from_euler('z',-yaw).as_matrix();A=align@basis;origin=A@world[0,lookup[hip],:3,3];origin[2]=0
 ground=case.get('ground',0);reference_ground=case.get('reference_ground',0);height=(basis@root_ref[:3,3])[2]-reference_ground;scale=NEUTRAL[2]/height
 mapping=[]
 for side,prefix in [('left','Left'),('right','Right')]:
  s=side[0]
  hipn=prefix+'Leg' if soma else 'thigh_'+s;knee=prefix+'Shin' if soma else 'calf_'+s;foot=prefix+'Foot' if soma else 'foot_'+s;arm=prefix+'Arm' if soma else 'upperarm_'+s;elbow=prefix+'ForeArm' if soma else 'lowerarm_'+s;hand=prefix+'Hand' if soma else 'hand_'+s
  mapping.extend([(side+'_hip_pitch_link',side+'_knee_link',hipn,knee),(side+'_knee_link',side+'_ankle_roll_link',knee,foot),(side+'_shoulder_pitch_link',side+'_elbow_link',arm,elbow),(side+'_elbow_link',side+'_wrist_yaw_link',elbow,hand)])
 qlist=[];reports=[];seed=np.clip(NEUTRAL[7:],LOW,HIGH);started=time.perf_counter()
 for f in range(len(world)):
  W=world[f]
  def pos(n):return A@W[lookup[n],:3,3]
  def delta(n):return align@basis@W[lookup[n],:3,:3]@reference[lookup[n],:3,:3].T@basis.T
  q=NEUTRAL.copy();q[:3]=(pos(hip)-origin)*scale;q[2]-=ground*scale;q[3:7]=R.from_matrix(delta(hip)).as_quat();directions=[unit(pos(b)-pos(a)) for _,_,a,b in mapping]
  orientation=[('torso_link',delta(chest)@REST['torso_link'][1],.25)]
  for side,prefix in [('left','Left'),('right','Right')]:
   foot=prefix+'Foot' if soma else 'foot_'+side[0];orientation.append((side+'_ankle_roll_link',delta(foot)@REST[side+'_ankle_roll_link'][1],.12))
  def residual(hinges):
   q[7:]=hinges;F=fk(q);parts=[unit(F[b][0]-F[a][0])-d for (a,b,_,_),d in zip(mapping,directions)]
   parts.extend(((F[n][1]-r)*weight).ravel() for n,r,weight in orientation);parts.append(.012*(hinges-NEUTRAL[7:]));return np.concatenate(parts)
  solved=least_squares(residual,seed,bounds=(LOW,HIGH),max_nfev=70,ftol=1e-5,xtol=1e-5,gtol=1e-5);seed=solved.x;q[7:]=seed;F=fk(q)
  angles=[np.degrees(np.arccos(np.clip(np.dot(unit(F[b][0]-F[a][0]),d),-1,1))) for (a,b,_,_),d in zip(mapping,directions)];reports.append({'source_time_s':case['sample_times_s'][f],'bone_direction_mean_error_deg':float(np.mean(angles)),'bone_direction_max_error_deg':float(max(angles)),'function_evaluations':int(solved.nfev),'converged':bool(solved.success),'root_height_m':float(q[2])});qlist.append(q.copy())
 result={k:v for k,v in case.items() if k not in ('world_transforms','reference_transforms','joint_names')};result.update(qpos=np.array(qlist,np.float32).tolist(),pose_fit=reports,source_to_g1_height_scale=scale,conversion='Bounded direction/foot/torso IK onto native 29-hinge G1. Root orientation including inversion retained; not a faithful lossless skeleton conversion.',fit_seconds=time.perf_counter()-started)
 return result
if __name__=='__main__':
 # Verify the independent XML FK against an already exported Newton source sample.
 data=np.load(ROOT/'evaluation/mb-predictive/near/g1-motion.npz');F=fk(data['qpos'][0]);error=max(np.linalg.norm(F[str(n)][0]-data['body_transforms'][0,i,:3]) for i,n in enumerate(data['body_names']) if str(n) in F);assert error<2e-5,error
 output=[]
 for case in source_cases():
  converted=fit_case(case);output.append(converted);(OUT/'converted-poses.json').write_text(json.dumps({'fk_crosscheck_error_m':float(error),'cases':output},indent=2),encoding='utf8');print('FITTED',case['id'],'max direction error',max(r['bone_direction_max_error_deg'] for r in converted['pose_fit']),'seconds',converted['fit_seconds'],flush=True)
