from pathlib import Path
import json,numpy as np,random
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
POOL=['quat_walk_loop','quat_dance_loop','quat_interact','quat_crouch_fwd_loop','capture_deadlift','capture_sumo_stomp','mb_crouch','mb_dance','mb_run']
def sequence_case(count,seed=0,context=None):
 if count not in (5,10,15):raise ValueError('Choose 5, 10 or 15 source moves')
 rng=random.Random(seed);lib=json.loads((ROOT/'evaluation/c08-worker/round2/original-g1-poses.json').read_text());neutral=np.array(lib['poses']['neutral'],np.float32);goals=[];moves=[];bag=[]
 for i in range(count):
  if not bag:bag=list(POOL);rng.shuffle(bag)
  source=bag.pop();meta=json.loads((ROOT/'evaluation/pose-harvest/generated'/source/'g1-motion.json').read_text());h=meta['source_harvest'];assert h['publishable'] and h['family']!='bundled_sample'
  angle=(i+1)*.45;x=.7+.5*np.sin(angle);y=.45*np.sin(angle*.8);yaw=20*np.sin(angle)
  for j,item in enumerate(meta['inputs']):
   q=np.array(item['target'][0],np.float32);q[:2]=[x-(.12 if j==0 else 0),y];forward=Rotation.from_quat(q[3:7]).apply([1,0,0]);old=np.arctan2(forward[1],forward[0]);q[3:7]=(Rotation.from_euler('z',np.deg2rad(yaw)-old)*Rotation.from_quat(q[3:7])).as_quat();goals.append(q[None,:])
  moves.append({'source_id':source,'label':h['label'],'family':h['family'],'license':h['license'],'publishable':True,'first_segment':2*i,'source_times_s':h['sample_times_s'][4:6]})
 end=neutral.copy();end[:2]=goals[-1][0,:2];goals.append(end[None,:]);return {'id':'routine_'+str(count),'label':str(count)+' moves / neural chain','context':np.repeat(neutral[None,:],4,axis=0) if context is None else context,'goals':goals,'purpose':'Chained predictions through sampled midpoint/end poses from explicitly permitted sources; final neutral recovery. No bundled samples.','provenance_type':'mixed_permitted_sources','routine':{'move_count':count,'seed':seed,'moves':moves,'target_count':len(goals),'final_recovery_segment':len(goals)-1,'generation':'Each request uses the actual preceding prediction last four poses; not a playback montage.'}}
if __name__=='__main__':
 from mb_predictive_generate import Predictor
 out=ROOT/'evaluation/predictive-sequences';out.mkdir(exist_ok=True);p=Predictor();records=[]
 for count in (5,10,15):
  case=sequence_case(count,20261028+count);meta=p.generate(case,out/case['id']);records.append({'id':case['id'],'label':case['label'],'duration_s':meta['duration_s'],'move_count':count,'category':'Combined / neural sequences','routine':True});print('NEURAL_SEQUENCE',count,meta['frames'],flush=True)
 (out/'catalog.json').write_text(json.dumps({'cases':records},indent=2),encoding='utf8')
