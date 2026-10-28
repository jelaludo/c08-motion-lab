"""MotionBricks predictive experiments with explicit per-case input provenance."""
from pathlib import Path
import json,time,subprocess,sys,os,xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
import warp as wp,newton
from motionbricks.io.utils import get_unitree_g1_model
from motionbricks.model.unitree_g1.contract import UNITREE_G1_N1_FP32_ONNX_PATH
from motionbricks.model.unitree_g1.engine import MotionBricksUnitreeG1Engine
from motionbricks.model.config import MotionBricksInferenceConfig
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/mb-predictive'
LIB=json.loads((ROOT/'evaluation/c08-worker/round2/original-g1-poses.json').read_text(encoding='utf8'))
PURPOSE='Original authored numeric G1 poses; no bundled sample motion, sample-conditioned output or Quaternius pose is used.'
def goal(pose='neutral',x=.7,y=0,yaw=0):
 q=np.array(LIB['poses'][pose],np.float32);r=Rotation.from_euler('z',yaw,degrees=True);q[:3]=r.apply(q[:3]);q[0]+=x;q[1]+=y;q[3:7]=(r*Rotation.from_quat(q[3:7])).as_quat();return q[None,:]
def default_cases():
 return [dict(id='near',label='01 / A short arrival',goals=[goal(x=.65)]),dict(id='far',label='02 / Same stance, farther target',goals=[goal(x=1.3)]),dict(id='turn',label='03 / Arrive with a new heading',goals=[goal(x=.8,y=.3,yaw=45)]),dict(id='crouch',label='04 / Approach a crouched target',goals=[goal('crouch',x=.65)]),dict(id='reach',label='05 / Approach and reach',goals=[goal('reach_right',x=.65)]),dict(id='chain',label='06 / Chain three predictions',goals=[goal(x=.6),goal('crouch',x=.85,y=.15),goal(x=1.15,y=.1,yaw=25)])]
class Predictor:
 def __init__(self):
  wp.init();wp.set_device('cuda:0');self.model=get_unitree_g1_model(load_visuals=False);self.state=self.model.state();newton.eval_fk(self.model,self.model.joint_q,self.model.joint_qd,self.state)
  self.refbody=self.state.body_q.numpy().copy();self.refq=self.model.joint_q.numpy().copy();self.names=[n.rsplit('/',1)[-1] for n in self.model.body_label]
  self.engine=MotionBricksUnitreeG1Engine(UNITREE_G1_N1_FP32_ONNX_PATH);self.context=self.engine.create_input();self.target=self.engine.create_input();self.output=self.engine.create_output()
 def transforms(self,q):
  rows=[]
  for row in q:
   newton.eval_fk(self.model,wp.array(row,dtype=wp.float32),self.model.joint_qd,self.state);rows.append(self.state.body_q.numpy().copy())
  return np.array(rows)
 def save(self,folder,q,contacts,meta):
  folder.mkdir(parents=True,exist_ok=True);np.savez(folder/'g1-motion.npz',qpos=q,timestamps=np.arange(len(q))/30,contacts=contacts,body_transforms=self.transforms(q),body_names=np.array(self.names),reference_qpos=self.refq,reference_bodies=self.refbody)
  (folder/'g1-motion.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
 def generate(self,case,folder,baseline=True):
  recent=np.array(case.get('context',np.repeat(np.array(LIB['poses']['neutral'],np.float32)[None,:],4,axis=0)),np.float32);assert recent.shape==(4,36);purpose=case.get('purpose',PURPOSE);segments=[];contacts=[];trace=[];linear=[];linear_recent=recent[-1].copy();start=time.perf_counter()
  with wp.ScopedStream(self.engine.stream):
   for i,g in enumerate(case['goals']):
    before=recent.copy();self.context.update_from_poses(wp.array(recent,dtype=wp.float32),stream=self.engine.stream);self.target.update_from_poses(wp.array(g,dtype=wp.float32),stream=self.engine.stream);tick=time.perf_counter()
    self.engine.generate_animation(self.context,self.target,self.output,config=MotionBricksInferenceConfig());self.engine.synchronize();seconds=time.perf_counter()-tick
    raw=self.output.poses[:self.output.num_frames].numpy().copy();c=self.output.foot_contacts[:self.output.num_frames].numpy().copy();assert np.isfinite(raw).all() and np.allclose(np.linalg.norm(raw[:,3:7],axis=1),1,atol=1e-4)
    q=raw.copy();duplicate=bool(segments and np.allclose(segments[-1][-1],q[0],atol=1e-5))
    if duplicate:q=q[1:];c=c[1:]
    boundary=sum(len(s) for s in segments);segments.append(q);contacts.append(c);recent=np.concatenate(segments)[-4:].copy()
    # Identical endpoints and segment duration; ordinary interpolation has no learned stepping.
    u=np.linspace(0,1,len(raw));b=linear_recent[None,:]*(1-u[:,None])+g[0][None,:]*u[:,None];b[:,3:7]=Slerp([0,1],Rotation.from_quat(np.stack([linear_recent[3:7],g[0,3:7]])))(u).as_quat();b=b.astype(np.float32)
    if duplicate:b=b[1:]
    linear.append(b);linear_recent=g[0].copy()
    trace.append({'index':i,'start_frame':boundary,'frames':len(q),'raw_frames':len(raw),'inference_seconds':seconds,'context':before.tolist(),'target':g.tolist(),'last_four_generated':recent.tolist(),'context_from_previous_prediction':i>0,'shared_endpoint_removed':duplicate,'endpoint_root_error_m':float(np.linalg.norm(q[-1,:3]-g[0,:3]))})
  q=np.concatenate(segments);c=np.concatenate(contacts)
  meta={'id':case['id'],'label':case['label'],'clip':'MBP_'+case['id'],'purpose':purpose,'provenance_type':case.get('provenance_type','original'),'model':'MotionBricks-G1-RP-v1','precision':'FP32','sample_rate':30,'frames':len(q),'duration_s':(len(q)-1)/30,'inputs':[{'context':s['context'],'target':s['target']} for s in trace],'segments':trace,'inference_seconds':sum(s['inference_seconds'] for s in trace),'total_seconds':time.perf_counter()-start,'upstream_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/'upstream',text=True).strip(),'endpoint_correction':True,'allowed_token_counts':list(range(8,15)),'body_names':self.names,'source_metrics':{'maximum_joint_key_step_rad':float(np.abs(np.diff(q[:,7:],axis=0)).max())}}
  if 'source_harvest' in case:meta['source_harvest']=case['source_harvest']
  self.save(folder,q,c,meta)
  if baseline:
   b=np.concatenate(linear);bm={**meta,'clip':'LINEAR_'+case['id'],'kind':'linear_baseline','model':None,'purpose':purpose+' Non-neural joint interpolation with matched endpoints/duration.','segments':[]};self.save(folder/'linear',b,np.zeros_like(c),bm)
  # Explicit G1 context/target skeletons, on the same source basis as g1-preview.json.
  skeletons=[{'context':self.transforms(np.array(s['context'],np.float32))[:,:,:3].tolist(),'target':self.transforms(np.array(s['target'],np.float32))[:,:,:3].tolist()} for s in trace]
  (folder/'prediction-trace.json').write_text(json.dumps({'metadata':meta,'skeletons_g1_zup':skeletons},indent=2),encoding='utf8')
  return meta
if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True);p=Predictor();catalog=[]
 for case in default_cases():
  meta=p.generate(case,OUT/case['id']);catalog.append({'id':case['id'],'label':case['label'],'duration_s':meta['duration_s']});print('PREDICTED',case['id'],meta['frames'],meta['inference_seconds'],flush=True)
 (OUT/'catalog.json').write_text(json.dumps({'cases':catalog},indent=2),encoding='utf8')
