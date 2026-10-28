"""Generate from sampled midpoint/end poses with separately classified input rights."""
from pathlib import Path
import json,hashlib,csv,traceback
import numpy as np
from scipy.spatial.transform import Rotation as R
from mb_predictive_generate import Predictor
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/pose-harvest';LIB=json.loads((ROOT/'evaluation/c08-worker/round2/original-g1-poses.json').read_text());cases=[]
for c in json.loads((OUT/'converted-poses.json').read_text())['cases']:
 q=np.array(c.pop('qpos'),np.float32);c.pop('reference_transforms',None);c.pop('world_transforms',None);c['category']='Harvest / Quaternius CC0' if c['family']=='quaternius' else 'Harvest / own video capture';cases.append({**c,'context':q[:4],'goals':[q[4:5],q[5:6]],'provenance_type':'cc0_quaternius' if c['family']=='quaternius' else 'user_owned_mocap'})
for id,folder in [('mb_run','evaluation/c08-worker/round2/own_run'),('mb_jump','evaluation/c08-worker/round2/own_jump_over'),('mb_dance','evaluation/c08-worker/round3/fresh_dance'),('mb_crouch','evaluation/c08-worker/round2/own_deep_crouch')]:
 p=ROOT/folder/'g1-motion.npz';d=np.load(p);q=d['qpos'];meta=json.loads(p.with_suffix('.json').read_text());assert meta['provenance_type']=='original';idx=[0,1,2,3,round((len(q)-1)/2),len(q)-1];cases.append({'id':id,'label':'MotionBricks original / '+id[3:],'family':'motionbricks_original','license':'Original authored conditioning; MotionBricks model terms','publishable':True,'category':'Harvest / our MotionBricks outputs','source_clip':meta['clip'],'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'duration_s':(len(q)-1)/30,'sample_times_s':[i/30 for i in idx],'context':q[:4],'goals':[q[idx[4]:idx[4]+1],q[-1:]],'provenance_type':'original'})
for id,pattern in [('sample_walk','Neutral_walk_forward_002__A057.csv'),('sample_skip','skipping_R_002__A360.csv')]:
 p=next((ROOT/'upstream/assets/motions/unitree_g1').rglob(pattern));a=np.loadtxt(p,delimiter=',',skiprows=1);header=next(csv.reader(p.open()));assert header[7:]==LIB['joint_names'];q=np.column_stack([a[:,1:4]*.01,R.from_euler('xyz',a[:,4:7],degrees=True).as_quat(),np.deg2rad(a[:,7:])]).astype(np.float32);idx=[0,4,8,12,round((len(q)-1)/2),len(q)-1]
 cases.append({'id':id,'label':'LOCAL evaluation / '+id[7:],'family':'bundled_sample','license':'NVIDIA Sample Data Evaluation License; internal evaluation only','publishable':False,'category':'LOCAL / bundled sample evaluation','source_clip':pattern,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'duration_s':(len(q)-1)/120,'sample_times_s':[i/120 for i in idx],'context':q[idx[:4]],'goals':[q[idx[4]:idx[4]+1],q[-1:]],'provenance_type':'bundled_sample'})
predictor=Predictor();catalog=[]
for c in cases:
 record={k:v for k,v in c.items() if k not in ('context','goals')};folder=OUT/'generated'/c['id'];record['directory']=str(folder.relative_to(ROOT)).replace('\\','/')
 try:
  provenance={k:v for k,v in record.items() if k!='directory'};provenance.update(sample_policy='Four initial source poses at 30 Hz; a midpoint and final pose become two sequential one-pose target requests. The generated duration is not the source duration.',conversion_limitations='G1 fitting preserves normalized limb directions with bounded hinges; fingers, object contact and human proportions are not preserved.')
  case={'id':c['id'],'label':c['label'],'context':c['context'],'goals':c['goals'],'source_harvest':provenance,'provenance_type':c['provenance_type'],'purpose':'Pose-harvest conditioning from '+c['label']+'. '+c['license']+'. Sparse source poses, not manual substitute targets.'}
  meta=predictor.generate(case,folder);record.update(generation='passed',frames=meta['frames'],generated_duration_s=meta['duration_s'],inference_seconds=meta['inference_seconds']);print('HARVEST_GENERATED',c['id'],meta['frames'],flush=True)
 except Exception as e:record.update(generation='failed',error=str(e));traceback.print_exc()
 catalog.append(record);(OUT/'catalog.json').write_text(json.dumps({'cases':catalog},indent=2),encoding='utf8')
