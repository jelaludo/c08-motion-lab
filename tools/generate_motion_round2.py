"""Explore G1 generation with original numeric poses and separate sample-driven cases."""
from pathlib import Path
import hashlib, json, math, subprocess, time, traceback, argparse
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares
import warp as wp
import newton
from motionbricks.io.utils import get_unitree_g1_model
from motionbricks.model.unitree_g1.contract import UNITREE_G1_N1_CONTRACT, UNITREE_G1_N1_FP32_ONNX_PATH
from motionbricks.model.unitree_g1.engine import MotionBricksUnitreeG1Engine
from motionbricks.model.config import MotionBricksInferenceConfig

ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'upstream';OUT=ROOT/'evaluation/c08-worker/round2'
OUT.mkdir(parents=True,exist_ok=True)
joint_names=list(UNITREE_G1_N1_CONTRACT.joint_names)
index={n:i+7 for i,n in enumerate(joint_names)}
xml=ET.parse(UP/'motionbricks/assets/robots/unitree_g1/g1_29dof_rev_1_0.xml')
tree=xml.getroot().find('worldbody').find('body')
def vector(text,default):return np.array([float(v) for v in text.split()]) if text else np.array(default,dtype=float)
def quat(text):
 q=vector(text,[1,0,0,0]);return R.from_quat(q[[1,2,3,0]]).as_matrix()
limits={j.get('name'):list(map(float,j.get('range').split())) for j in tree.iter('joint') if j.get('range')}
def fk(q):
 result={}
 def visit(b,parent=None):
  if parent is None:p=q[:3];r=R.from_quat(q[3:7]).as_matrix()
  else:
   pp,pr=result[parent];p=pp+pr@vector(b.get('pos'),[0,0,0]);r=pr@quat(b.get('quat'))
   for j in b.findall('joint'):
    if j.get('type')=='free':continue
    axis=vector(j.get('axis'),[0,0,1]);origin=vector(j.get('pos'),[0,0,0]);turn=R.from_rotvec(axis*q[index[j.get('name')]]).as_matrix()
    p=p+r@(origin-turn@origin);r=r@turn
  result[b.get('name')]=(p,r)
  for child in b.findall('body'):visit(child,b.get('name'))
 visit(tree);return result
neutral=np.zeros(36,dtype=np.float32);neutral[2]=.793;neutral[6]=1
for side,sign in [('left',1),('right',-1)]:
 neutral[index[f'{side}_elbow_joint']]=1.05
 neutral[index[f'{side}_shoulder_roll_joint']]=sign*.12
rest=fk(neutral)
def crouch(height):
 q=neutral.astype(np.float64);q[2]=height
 keys=[f'{s}_{j}_joint' for s in ('left','right') for j in ('hip_pitch','knee','ankle_pitch')]
 ids=[index[k] for k in keys]
 def residual(x):
  q[ids]=x[:6];q[0]=x[6];transforms=fk(q);values=[]
  for s in ('left','right'):
   p,r=transforms[s+'_ankle_roll_link'];rp,rr=rest[s+'_ankle_roll_link']
   values.extend(p-rp);values.extend(R.from_matrix(r@rr.T).as_rotvec()*.2)
  values.append(x[6]*.001)
  return np.array(values)
 solved=least_squares(residual,[-.6,1.2,-.6]*2+[0],bounds=([limits[k][0] for k in keys]+[-.35],[limits[k][1] for k in keys]+[.35]),max_nfev=200)
 assert np.linalg.norm(solved.fun)<.003,('authored crouch IK',height,solved.fun)
 q[ids]=solved.x[:6];q[0]=solved.x[6];return q.astype(np.float32)
poses={'neutral':neutral,'crouch':crouch(.58),'deep_crouch':crouch(.43)}
for name,sides,angle in [('reach_right',('right',),-1.1),('reach_both',('left','right'),-1.0),('hands_high',('left','right'),-2.0)]:
 p=neutral.copy()
 for side in sides:p[index[f'{side}_shoulder_pitch_joint']]=angle;p[index[f'{side}_elbow_joint']]=.4
 poses[name]=p
original={'provenance':'Original poses authored numerically in this workspace; no NVIDIA sample motion used. C08 geometry and original authored animations are user-owned.','basis':'G1 Z up, +X forward, metres/radians, XYZW root quaternion','joint_names':joint_names,'poses':{k:v.tolist() for k,v in poses.items()},'method':'Neutral posture and arm angles authored directly; crouch leg angles solved against the reference ankle transforms and joint limits.'}
(OUT/'original-g1-poses.json').write_text(json.dumps(original,indent=2))

def place(p,x=0,y=0,yaw=0,velocity=None):
 q=p.copy();turn=R.from_euler('z',yaw);q[:3]=turn.apply(q[:3]);q[:2]+=[x,y];q[3:7]=(turn*R.from_quat(q[3:7])).as_quat()
 if velocity is None:return q[None,:]
 window=np.repeat(q[None,:],4,axis=0)
 for i in range(4):window[i,:2]+=np.array(velocity)*i/30
 return window
cases=[]
def own(id,label,targets,category='Original poses',tokens=tuple(range(8,15)),start=None):
 cases.append({'id':id,'label':label,'category':category,'provenance_type':'original','purpose':original['provenance'],'context':np.repeat((neutral if start is None else start)[None,:],4,axis=0),'targets':targets,'tokens':tokens})
N=poses['neutral'];C=poses['crouch'];D=poses['deep_crouch']
own('own_idle','Original · neutral idle',[place(N)]*3)
own('own_crouch_down','Original · crouch down',[place(C)])
own('own_crouch_hold','Original · crouch hold',[place(C)]*2,start=C)
own('own_stand_up','Original · stand up',[place(N)],start=C)
own('own_deep_crouch','Original · deep crouch and return',[place(D),place(D),place(N)],'Original stress tests')
own('own_reach_right','Original · reach right and return',[place(poses['reach_right']),place(poses['reach_right']),place(N)])
own('own_reach_both','Original · reach both hands',[place(poses['reach_both']),place(N)])
own('own_hands_high','Original · hands overhead',[place(poses['hands_high']),place(N)],'Original stress tests')
own('own_turn_left90','Original · turn left 90°',[place(N,yaw=math.pi/2)]*2)
own('own_turn_right90','Original · turn right 90°',[place(N,yaw=-math.pi/2)]*2)
own('own_turn180','Original · turn around',[place(N,yaw=math.pi)],'Original stress tests')
own('own_forward_steps','Original · forward targets',[place(N,x=.7,velocity=(.5,0)),place(N,x=1.4,velocity=(.5,0)),place(N,x=1.8)])
own('own_backward_steps','Original · backward targets',[place(N,x=-.4,velocity=(-.3,0)),place(N,x=-.8)])
own('own_left_steps','Original · sidestep left',[place(N,y=.4,velocity=(0,.3)),place(N,y=.8)])
own('own_right_steps','Original · sidestep right',[place(N,y=-.4,velocity=(0,-.3)),place(N,y=-.8)])
own('own_fast_long_step','Original · 3 m rapid arrival',[place(N,x=3)],'Original stress tests',tokens=(6,7,8))

# Original moving targets and an explicitly airborne target for the public diorama.
def running_window(t):
 rows=[]
 for i in range(4):
  tick=t+i/30;phase=tick*math.tau/0.78;q=N.copy();q[0]=1.35*tick;q[2]=.765+.018*math.cos(phase*2)
  for side,offset in [('left',0),('right',math.pi)]:
   swing=math.sin(phase+offset)
   q[index[side+'_hip_pitch_joint']]=-.44*swing
   q[index[side+'_knee_joint']]=.27+.48*max(0,-swing)
   q[index[side+'_ankle_pitch_joint']]=-.18-.16*swing
   q[index[side+'_shoulder_pitch_joint']]=.30*swing
  rows.append(q)
 return np.array(rows)
cases.append({'id':'own_run','label':'Original · playful run','category':'Original diorama actions','provenance_type':'original','purpose':'Original procedural running target windows authored here; no bundled motion samples.','context':running_window(0),'targets':[running_window(t) for t in (1.,2.,3.)],'tokens':tuple(range(8,15))})
air=C.copy();air[2]=1.22
for side in ('left','right'):air[index[side+'_shoulder_pitch_joint']]=-.45
own('own_jump_over','Original · jump over K0-Tech',[place(C,x=.1),place(air,x=1.05),place(N,x=2.1)],'Original diorama actions')

base=UP/'assets/motions/unitree_g1'
def find(token):
 matches=[p for p in base.rglob('*.csv') if token in p.stem]
 exact=[p for p in matches if p.stem==token]
 if exact:matches=exact
 assert len(matches)==1,(token,matches)
 return matches[0]
def read_motion(p):
 raw=np.loadtxt(p,delimiter=',',skiprows=1)
 q=np.zeros((len(raw),36),np.float32);q[:,:3]=raw[:,1:4]*.01;q[:,3:7]=R.from_euler('xyz',raw[:,4:7],degrees=True).as_quat();q[:,7:]=np.deg2rad(raw[:,7:])
 # Align the first sampled heading and ground origin without changing the articulation.
 first=min(48,len(q)-1);r=R.from_quat(q[first,3:7]);f=r.apply([1,0,0]);turn=R.from_euler('z',-math.atan2(f[1],f[0]));origin=q[first,:3].copy();origin[2]=0
 q[:,:3]=turn.apply(q[:,:3]-origin);q[:,3:7]=(turn*R.from_quat(q[:,3:7])).as_quat()
 return q
def window(q,t):
 ids=np.clip(np.rint((t+np.arange(4)/30)*120).astype(int),0,len(q)-1)
 return q[ids].copy()
def sampled(id,label,token,category='Sample-driven locomotion',travel_scale=1):
 p=find(token);q=read_motion(p);q[:,:2]*=travel_scale;duration=(len(q)-1)/120
 start=.3;end=min(duration-.12,4.5)
 target_times=np.linspace(start+.4,end,3)
 if id in ('jump_small','vault'):
  peak=float(np.argmax(q[:,2])/120)
  target_times=np.array([max(start+.2,peak-.5),peak,min(duration-.12,peak+.5),duration-.12])
 cases.append({'id':id,'label':label,'category':category,'provenance_type':'bundled_sample','purpose':'Internal evaluation only: bundled NVIDIA/Bones motion conditioning; C08 geometry remains user-owned.','conditioning_file':str(p.relative_to(UP)),'conditioning_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'conditioning_target_times_s':target_times.tolist(),'context':window(q,start-.1),'targets':[window(q,t) for t in target_times],'tokens':tuple(range(8,15))})
sampled('slow_walk','Slow walk','neutral_walk_ff_180_R_002')
sampled('brisk_walk','Brisk walk / swagger','Neutral_walk_forward_002')
sampled('jog','Jog','neutral_jog_ff_180')
sampled('run','Run · high speed','run_loop_180_R_003__A326','Sample-driven stress tests')
sampled('strafe_left','Strafe left','jog_ff_loop_270_R_very_fast_002__A455_M',travel_scale=.45)
sampled('strafe_right','Strafe right','jog_ff_loop_270_R_very_fast_002__A455',travel_scale=.45)
sampled('backward','Backward locomotion','jog_ff_loop_360_R_very_fast',travel_scale=.4)
sampled('crouch_forward','Crouched forward movement','crouch_ff_loop_180_R_001')
sampled('crouch_left','Crouched left movement','crouch_ff_loop_270_R_002__A196_M')
sampled('crouch_right','Crouched right movement','crouch_ff_loop_270_R_002__A196')
sampled('look_around','Look-around body motion','neutral_looking_around')
sampled('duck_under','Duck under an obstacle','neutral_avoid_obstacle_bend_down_walk','Sample-driven interactions')
sampled('sit_down','Sit down','sit_on_chair_start','Sample-driven interactions')
sampled('sit_hold','Seated hold','sit_on_chair_loop','Sample-driven interactions')
sampled('stand_from_chair','Stand from chair','sit_on_chair_stop','Sample-driven interactions')
sampled('jump_small','Jump over small obstacle','jump_over_obstacle_0_5m_R_001','Sample-driven stress tests')
sampled('vault','Vault · hand contact challenge','jump_over_obstacle_0_75m_R_102','Sample-driven stress tests')
sampled('limp','Injured-leg limp','injured_L_leg_grab_walk','Sample-driven styles')
sampled('guarded','Guarded quick steps','combat_quickstep_ff_idle_180','Sample-driven styles')
sampled('zombie','Zombie walk','zombie_walk','Sample-driven styles')
sampled('skip','Skipping','skipping_R','Sample-driven styles')
sampled('dance','Dance / articulation stress','dance_vouge_vogue','Sample-driven styles')
# Start and stop combine original neutral poses with sampled gait targets.
p=find('neutral_walk_ff_180_R_002');walk=read_motion(p)
for id,label,start,targets in [('walk_start','Walk start',np.repeat(N[None,:],4,axis=0),[window(walk,1.2),window(walk,2.2)]),('walk_stop','Walk stop',window(walk,.5),[place(N,x=.7),place(N,x=.7)])]:
 cases.append({'id':id,'label':label,'category':'Sample-driven transitions','provenance_type':'bundled_sample','purpose':'Internal evaluation only: sampled gait plus original neutral target.','context':start,'targets':targets,'tokens':tuple(range(8,15)),'conditioning_file':str(p.relative_to(UP)),'conditioning_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})

parser=argparse.ArgumentParser();parser.add_argument('--only',nargs='+');args=parser.parse_args()
if args.only:cases=[c for c in cases if c['id'] in args.only]
wp.init();wp.set_device('cuda:0')
model=get_unitree_g1_model(load_visuals=False)
assert [s.rsplit('/',1)[-1] for s in model.joint_label][1:]==joint_names
state=model.state();names=[s.rsplit('/',1)[-1] for s in model.body_label]
newton.eval_fk(model,model.joint_q,model.joint_qd,state);refbody=state.body_q.numpy().copy();refq=model.joint_q.numpy().copy()
# Verify the independent FK used to author the poses against Newton before inference.
for name,q in poses.items():
 newton.eval_fk(model,wp.array(q,dtype=wp.float32),model.joint_qd,state);actual=state.body_q.numpy();expected=fk(q)
 assert max(np.linalg.norm(actual[i,:3]-expected[n][0]) for i,n in enumerate(names))<1e-5,('FK authoring mismatch',name)
catalog=json.loads((OUT/'catalog.json').read_text())['tests'] if args.only and (OUT/'catalog.json').exists() else []
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=UP,text=True).strip()
with MotionBricksUnitreeG1Engine(UNITREE_G1_N1_FP32_ONNX_PATH) as engine, wp.ScopedStream(engine.stream):
 context,target,output=engine.create_input(),engine.create_input(),engine.create_output()
 for case in cases:
  directory=OUT/case['id'];directory.mkdir(exist_ok=True)
  entry={k:case[k] for k in ('id','label','category','provenance_type','purpose')};entry['directory']=case['id'];entry['clip']='MB_'+case['id']
  try:
   segments=[];confidence=[];boundaries=[];inputs=[];recent=case['context'].copy();start=time.perf_counter()
   for goal in case['targets']:
    assert np.isfinite(recent).all() and np.isfinite(goal).all()
    context.update_from_poses(wp.array(recent,dtype=wp.float32),stream=engine.stream)
    target.update_from_poses(wp.array(goal,dtype=wp.float32),stream=engine.stream)
    inputs.append({'context':recent.tolist(),'target':goal.tolist()})
    tick=time.perf_counter();engine.generate_animation(context,target,output,config=MotionBricksInferenceConfig(allowed_token_counts=case['tokens']));engine.synchronize()
    q=output.poses[:output.num_frames].numpy().copy();c=output.foot_contacts[:output.num_frames].numpy().copy()
    assert np.isfinite(q).all() and np.allclose(np.linalg.norm(q[:,3:7],axis=1),1,atol=1e-4)
    duplicate=bool(segments and np.allclose(segments[-1][-1],q[0],atol=1e-5))
    if duplicate:q=q[1:];c=c[1:]
    boundaries.append({'frame':sum(len(s) for s in segments),'num_frames':len(q),'shared_endpoint_removed':duplicate,'generation_seconds':time.perf_counter()-tick})
    segments.append(q);confidence.append(c);recent=np.concatenate(segments)[-4:].copy()
   q=np.concatenate(segments);transforms=[]
   for row in q:
    newton.eval_fk(model,wp.array(row,dtype=wp.float32),model.joint_qd,state);transforms.append(state.body_q.numpy().copy())
   np.savez(directory/'g1-motion.npz',qpos=q,timestamps=np.arange(len(q))/30,contacts=np.concatenate(confidence),body_transforms=np.array(transforms),body_names=np.array(names),reference_qpos=refq,reference_bodies=refbody)
   metrics={'root_horizontal_travel_m':float(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1).sum()),'pelvis_height_min_m':float(q[:,2].min()),'pelvis_height_max_m':float(q[:,2].max()),'maximum_joint_key_step_rad':float(np.abs(np.diff(q[:,7:],axis=0)).max()),'root_endpoint_error_m':float(np.linalg.norm(q[-1,:3]-case['targets'][-1][0,:3]))}
   meta={**entry,'upstream_commit':commit,'model':'MotionBricks-G1-RP-v1','precision':'FP32','sample_rate':30,'frames':len(q),'duration_s':(len(q)-1)/30,'segments':boundaries,'inputs':inputs,'allowed_token_counts':case['tokens'],'body_names':names,'source_metrics':metrics,'total_seconds':time.perf_counter()-start,'basis':'Z up, +X forward; quaternion XYZW'}
   for k in ('conditioning_file','conditioning_sha256','conditioning_target_times_s'):
    if k in case:meta[k]=case[k]
   (directory/'g1-motion.json').write_text(json.dumps(meta,indent=2));entry.update(frames=len(q),duration_s=(len(q)-1)/30,generation='passed',source_metrics=metrics)
   print('GENERATED',case['id'],len(q),'frames',round(time.perf_counter()-start,2),'s',flush=True)
  except Exception as error:
   entry.update(generation='failed',error=str(error));traceback.print_exc()
  existing=next((i for i,c in enumerate(catalog) if c['id']==entry['id']),None)
  if existing is None:catalog.append(entry)
  else:catalog[existing]=entry
  (OUT/'catalog.json').write_text(json.dumps({'label':'C08 MotionBricks — round 2','tests':catalog},indent=2))
print('ROUND2_GENERATION_COMPLETE',len(catalog),'cases',flush=True)
