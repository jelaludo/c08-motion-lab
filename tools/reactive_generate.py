"""Paired closed-loop MotionBricks trials. Environment planning is outside the model."""
from pathlib import Path
import argparse,json,time,hashlib,math,sys
import numpy as np
from scipy.spatial.transform import Rotation
import warp as wp
from mb_predictive_generate import Predictor,LIB
from motionbricks.model.config import MotionBricksInferenceConfig
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/reactive';FPS=30;FRAMES=240;CHUNK=15
SCENARIOS=['slalom','speedzones','pursuit','mixed']
SOURCES={'walk':ROOT/'evaluation/c08-worker/round3/fresh_brisk_walk/g1-motion.npz','run':ROOT/'evaluation/c08-worker/round2/own_run/g1-motion.npz'}
GAITS={name:np.load(p)['qpos'] for name,p in SOURCES.items()}
for p in SOURCES.values():assert json.loads(p.with_suffix('.json').read_text())['provenance_type']=='original'
def scene(seed,scenario):
 rng=np.random.default_rng(seed);pillars=[] if scenario=='speedzones' else [[1.4,float(rng.uniform(-.1,.1)),.35],[2.9,float(rng.uniform(-.2,.1)),.35],[4.4,float(rng.uniform(-.1,.1)),.4]]
 if scenario=='pursuit':pillars=[[2.7,.2,.45]]
 # The same prerecorded seeded cat path supplies the external moving goal to both conditions.
 points=np.array([[2.2,1.1],[3.6,-1.2],[5.4,.9],[4.0,1.8],[2.5,-1.0]],float)+rng.uniform(-.2,.2,(5,2))
 cat=[]
 for f in range(FRAMES+1):
  u=f/FPS/2;i=min(int(u),3);v=min(1,u-i);v=v*v*(3-2*v);cat.append((points[i]*(1-v)+points[i+1]*v).tolist())
 return {'obstacles':[{'center':[x,y],'radius':r,'height':1.6} for x,y,r in pillars],'speed_zones':[{'x_min':1.4,'x_max':4.3,'desired_speed':1.35}],'cat_path':cat,'goal':[6.,0.],'root_radius_m':.3,'seed':seed}
def control(scenario,reactive,env,p,velocity,t,previous_speed):
 frame=min(FRAMES,round(t*FPS));cat=np.array(env['cat_path'][frame]);pursuit=scenario in ['pursuit','mixed']
 if pursuit:
  target=cat.copy()
  if reactive:
   future=np.array(env['cat_path'][min(FRAMES,frame+15)]);target=future
  if scenario=='mixed' and not reactive:target=np.array(env['cat_path'][0])
 else:target=np.array(env['goal'])
 delta=target-p;distance=np.linalg.norm(delta);direction=delta/max(distance,1e-6)
 desired=1.35 if (scenario in ['speedzones','mixed'] and 1.4<p[0]<4.3) or pursuit else .8
 if pursuit and distance<1.:desired=max(0.,(distance-.6)*1.2)
 if not pursuit and distance<1.:desired=min(desired,distance)
 if reactive:
  # Deterministic local obstacle planner. The network never sees pillar geometry.
  for ob in env['obstacles']:
   centre=np.array(ob['center']);offset=centre-p;along=np.dot(offset,direction);cross=offset-direction*along;clearance=ob['radius']+env['root_radius_m']+.3
   if 0<along<1.7 and np.linalg.norm(cross)<clearance:
    side=1. if centre[1]<=.1 else -1.;waypoint=centre+np.array([-.1,side*(clearance+.3)]);direction=(waypoint-p)/max(np.linalg.norm(waypoint-p),1e-6);desired=min(desired,.9)
  speed=previous_speed+np.clip(desired-previous_speed,-.3,.3)
 else:speed=desired
 return direction,float(speed),target
def target_window(p,direction,speed,frame):
 if speed<.08:
  q=np.repeat(np.array(LIB['poses']['neutral'],np.float32)[None,:],4,axis=0)
 else:
  source=GAITS['run' if speed>1.05 else 'walk'];index=min(len(source)-5,max(4,len(source)//3+(frame//CHUNK*3)%max(1,len(source)//3)));q=source[index:index+4].copy()
 # Preserve four-frame gait motion and scale its root velocity to desired travel speed.
 source_forward=Rotation.from_quat(q[0,3:7]).apply([1,0,0]);source_yaw=math.atan2(source_forward[1],source_forward[0]);yaw=math.atan2(direction[1],direction[0]);r=Rotation.from_euler('z',yaw-source_yaw)
 relative=r.apply(q[:,:3]-q[0,:3]);native=np.linalg.norm(relative[-1,:2])*FPS/3
 if native>.001:relative[:,:2]*=speed/native
 q[:,:3]=relative+np.array([p[0]+direction[0]*speed*.9,p[1]+direction[1]*speed*.9,q[0,2]])
 q[:,3:7]=(r*Rotation.from_quat(q[:,3:7])).as_quat();return q.astype(np.float32)
def run(predictor,scenario,condition,seed):
 id=f'{scenario}_{condition}_{seed}';folder=OUT/id;folder.mkdir(parents=True,exist_ok=True);env=scene(seed,scenario);reactive=condition=='reactive';initial=np.array(LIB['poses']['neutral'],np.float32);initial[1]=np.random.default_rng(seed+100).uniform(-.06,.06);recent=np.repeat(initial[None,:],4,axis=0);shown=[initial];contacts=[np.zeros(4,np.float32)];trace=[];commands=[];speed=0.;start=time.perf_counter()
 with wp.ScopedStream(predictor.engine.stream):
  while len(shown)<=FRAMES:
   frame=len(shown)-1;now=shown[-1];position=now[:2].copy();velocity=(shown[-1][:2]-shown[-2][:2])*FPS if len(shown)>1 else np.zeros(2);direction,speed,target=control(scenario,reactive,env,position,velocity,frame/FPS,speed);g=target_window(position,direction,speed,frame);before=recent.copy()
   predictor.context.update_from_poses(wp.array(recent,dtype=wp.float32),stream=predictor.engine.stream);predictor.target.update_from_poses(wp.array(g,dtype=wp.float32),stream=predictor.engine.stream);tick=time.perf_counter();predictor.engine.generate_animation(predictor.context,predictor.target,predictor.output,config=MotionBricksInferenceConfig());predictor.engine.synchronize();elapsed=time.perf_counter()-tick
   raw=predictor.output.poses[:predictor.output.num_frames].numpy().copy();c=predictor.output.foot_contacts[:predictor.output.num_frames].numpy().copy();offset=int(np.allclose(raw[0],now,atol=1e-4));n=min(CHUNK,FRAMES+1-len(shown),len(raw)-offset);played=raw[offset:offset+n];played_c=c[offset:offset+n];assert n>0 and np.isfinite(played).all();shown.extend(played);contacts.extend(played_c);recent=np.array(shown[-4:],np.float32)
   if len(recent)<4:recent=np.concatenate([before,recent])[-4:]
   trace.append({'index':len(trace),'start_frame':frame+1,'frames':n,'raw_frames':len(raw),'unused_future_frames':len(raw)-offset-n,'inference_seconds':elapsed,'context':before.tolist(),'target':g.tolist(),'last_four_generated':recent.tolist(),'context_from_previous_prediction':bool(trace),'context_is_last_displayed_not_unused_future':True,'shared_endpoint_removed':bool(offset),'endpoint_root_error_m':float(np.linalg.norm(played[-1,:2]-g[0,:2]))})
   commands.append({'frame':frame,'position':position.tolist(),'desired_speed':speed,'direction':direction.tolist(),'external_goal':target.tolist()})
 q=np.array(shown,np.float32);c=np.array(contacts,np.float32);vel=np.diff(q[:,:2],axis=0)*FPS;acc=np.diff(vel,axis=0)*FPS;jerk=np.diff(acc,axis=0)*FPS;clear=[];collisions=np.zeros(len(q),bool)
 for ob in env['obstacles']:
  dist=np.linalg.norm(q[:,:2]-np.array(ob['center']),axis=1)-ob['radius']-env['root_radius_m'];clear.extend(dist);collisions|=dist<0
 metrics={'root_proxy_collision_frames':int(collisions.sum()),'minimum_root_proxy_clearance_m':float(min(clear)) if clear else None,'mean_speed_m_s':float(np.linalg.norm(vel,axis=1).mean()),'max_speed_m_s':float(np.linalg.norm(vel,axis=1).max()),'root_acceleration_p95_m_s2':float(np.percentile(np.linalg.norm(acc,axis=1),95)),'root_jerk_p95_m_s3':float(np.percentile(np.linalg.norm(jerk,axis=1),95)),'final_goal_distance_m':float(np.linalg.norm(q[-1,:2]-(np.array(env['cat_path'][-1]) if scenario in ['pursuit','mixed'] else np.array(env['goal'])))),'neural_calls':len(trace),'discarded_future_frames':sum(s['unused_future_frames'] for s in trace)}
 meta={'id':id,'label':f'{scenario} / {condition} / seed {seed}','clip':'REACTIVE_'+id,'purpose':'Actual closed-loop neural rollout from original-conditioned gait windows. Planner selects targets; model does not receive scene geometry.','provenance_type':'original','model':'MotionBricks-G1-RP-v1','precision':'FP32','sample_rate':FPS,'frames':len(q),'duration_s':(len(q)-1)/FPS,'inputs':[{'context':s['context'],'target':s['target']} for s in trace],'segments':trace,'inference_seconds':sum(s['inference_seconds'] for s in trace),'total_seconds':time.perf_counter()-start,'source_metrics':{'maximum_joint_key_step_rad':float(np.abs(np.diff(q[:,7:],axis=0)).max())},'body_names':predictor.names,'routine':{'type':'reactive_closed_loop','move_count':len(trace)},'sources':{n:hashlib.sha256(path.read_bytes()).hexdigest() for n,path in SOURCES.items()},'reactive':{'scenario':scenario,'condition':condition,'seed':seed,'metrics':metrics},'limitations':['Kinematic generation; no dynamics or collision solver.','Collision metrics use a conservative root proxy, not whole-body shape clearance.','A target is replanned every 0.5 seconds, and unused predicted futures are discarded.','C08/BREK grounding is a separate displayed retarget correction; raw G1 is retained.']}
 predictor.save(folder,q,c,meta);(folder/'prediction-trace.json').write_text(json.dumps({'metadata':meta,'skeletons_g1_zup':[{'context':predictor.transforms(np.array(s['context'],np.float32))[:,:,:3].tolist(),'target':predictor.transforms(np.array(s['target'],np.float32))[:,:,:3].tolist()} for s in trace]},indent=2),encoding='utf8');episode={'id':id,'scenario':scenario,'condition':condition,'seed':seed,'environment':env,'commands':commands,'metrics':metrics,'raw_root_path':q[:,:3].tolist(),'sample_rate':FPS,'duration_s':meta['duration_s'],'limitations':meta['limitations']};(folder/'episode.json').write_text(json.dumps(episode,indent=2),encoding='utf8');return {'id':id,'label':meta['label'],'scenario':scenario,'condition':condition,'seed':seed,'duration_s':meta['duration_s'],'metrics':metrics}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--seeds',type=int,default=5);parser.add_argument('--scenario',default='all');args=parser.parse_args();OUT.mkdir(exist_ok=True);predictor=Predictor();catalog=[]
 for scenario in SCENARIOS if args.scenario=='all' else [args.scenario]:
  for seed in range(1,args.seeds+1):
   for condition in ['baseline','reactive']:
    record=run(predictor,scenario,condition,seed);catalog.append(record);(OUT/'catalog.json').write_text(json.dumps({'version':'reactive-round1','cases':catalog},indent=2),encoding='utf8');print('REACTIVE_GENERATED',record['id'],record['metrics'],flush=True)
