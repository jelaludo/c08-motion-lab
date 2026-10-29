"""Paired closed-loop MotionBricks trials. Environment planning is outside the model."""
from pathlib import Path
import argparse,json,time,hashlib,math,sys
import numpy as np
from scipy.spatial.transform import Rotation
import warp as wp
from mb_predictive_generate import Predictor,LIB
from motionbricks.model.config import MotionBricksInferenceConfig
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/reactive-round4';FPS=30;CHUNK=15
DURATIONS={'slalom':24,'speedzones':40,'pursuit':40,'mixed':40,'jump':32,'crouch':32,'course':80}
SCENARIOS=list(DURATIONS)
SOURCES={'walk':ROOT/'evaluation/c08-worker/round3/fresh_brisk_walk/g1-motion.npz','run':ROOT/'evaluation/c08-worker/round2/own_run/g1-motion.npz','jump':ROOT/'evaluation/c08-worker/round2/own_jump_over/g1-motion.npz','crouch':ROOT/'evaluation/c08-worker/round2/own_deep_crouch/g1-motion.npz','crouch_walk':ROOT/'evaluation/c08-worker/round3/fresh_crouch_forward/g1-motion.npz'}
GAITS={name:np.load(p)['qpos'] for name,p in SOURCES.items()}
for p in SOURCES.values():assert json.loads(p.with_suffix('.json').read_text())['provenance_type']=='original'
def clearance(p,env,radius):
 return min([np.linalg.norm(p-np.array(ob['center']))-ob['radius']-radius for ob in env['obstacles']]+[p[0]-env['bounds'][0]-radius,env['bounds'][1]-p[0]-radius,p[1]-env['bounds'][2]-radius,env['bounds'][3]-p[1]-radius])
def sweep_slide(start,end,env,radius):
 """Continuous swept-circle collision/slide. This is external kinematic control."""
 position=np.array(start,dtype=float);remaining=np.array(end,dtype=float)-position;hits=[]
 for iteration in range(5):
  if np.linalg.norm(remaining)<1e-8:break
  hit_time=1.;normal=None;which=None
  for index,ob in enumerate(env['obstacles']):
   offset=position-np.array(ob['center']);r=ob['radius']+radius+1e-4;a=remaining@remaining;b=2*(offset@remaining);c=offset@offset-r*r;disc=b*b-4*a*c
   if disc<0:continue
   t=(-b-math.sqrt(max(0.,disc)))/(2*a)
   if -1e-7<=t<hit_time:
    candidate_normal=position+remaining*max(0,t)-np.array(ob['center']);candidate_normal/=max(np.linalg.norm(candidate_normal),1e-8)
    if remaining@candidate_normal<0:hit_time=max(0,t);normal=candidate_normal;which=index
  bounds=env['bounds']
  for axis,lo,hi in [(0,bounds[0]+radius+1e-4,bounds[1]-radius-1e-4),(1,bounds[2]+radius+1e-4,bounds[3]-radius-1e-4)]:
   if abs(remaining[axis])<1e-9:continue
   value=(lo-position[axis])/remaining[axis] if remaining[axis]<0 else (hi-position[axis])/remaining[axis]
   if 0<=value<hit_time:
    hit_time=value;normal=np.zeros(2);normal[axis]=1 if remaining[axis]<0 else -1;which=-1-axis
  if normal is None:position+=remaining;break
  position+=remaining*max(0.,hit_time-1e-6);remaining*=1-hit_time;remaining-=normal*min(0.,remaining@normal);position+=normal*1e-5;hits.append(which)
 return position,hits
def route(start,end,env,radius):
 """A* on half-metre navigation cells with swept-clear edges."""
 import heapq
 start=np.array(start,float);end=np.array(end,float)
 direct,hits=sweep_slide(start,end,env,radius+.2)
 if not hits and np.linalg.norm(direct-end)<.01:return [start,end]
 step=.5;bounds=env['bounds'];origin=np.array(bounds[:1]+bounds[2:3]);shape=np.array([round((bounds[1]-bounds[0])/step),round((bounds[3]-bounds[2])/step)])
 cache=env.setdefault('_navigation_cache',{});key=str(round(radius,3))
 if key not in cache:
  xx,yy=np.meshgrid(origin[0]+np.arange(shape[0]+1)*step,origin[1]+np.arange(shape[1]+1)*step,indexing='ij');valid=(xx>bounds[0]+radius+.15)&(xx<bounds[1]-radius-.15)&(yy>bounds[2]+radius+.15)&(yy<bounds[3]-radius-.15)
  for ob in env['obstacles']:valid&=(xx-ob['center'][0])**2+(yy-ob['center'][1])**2>(ob['radius']+radius+.15)**2
  cache[key]=valid
 valid=cache[key]
 index=lambda p:tuple(np.round((p-origin)/step).astype(int));point=lambda i:origin+np.array(i)*step
 s=index(start);goal=index(end);queue=[(0.,s)];cost={s:0.};previous={};found=None
 while queue:
  _,node=heapq.heappop(queue)
  if node==goal or np.linalg.norm(point(node)-end)<.6:found=node;break
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   nxt=(node[0]+dx,node[1]+dy)
   if min(nxt)<0 or nxt[0]>shape[0] or nxt[1]>shape[1]:continue
   q=point(nxt)
   if not valid[nxt]:continue
   trial=cost[node]+math.hypot(dx,dy)
   if trial<cost.get(nxt,float('inf')):cost[nxt]=trial;previous[nxt]=node;heapq.heappush(queue,(trial+np.linalg.norm(q-end)/step,nxt))
 if found is None:return [start,end]
 nodes=[found]
 while nodes[-1]!=s:nodes.append(previous[nodes[-1]])
 result=[start]+[point(i) for i in reversed(nodes[:-1])]
 if clearance(end,env,radius+.05)>0:result.append(end)
 return result
def scene(seed,scenario):
 rng=np.random.default_rng(seed);pillars=[]
 # Thirty-metre courses: broad staggered field, rather than scaled-up avatar geometry.
 for i,x in enumerate([4.,7.5,11.,14.5,18.,21.5,25.,28.5]):
  y=(1.25 if i%2==0 else -1.25)+rng.uniform(-.2,.2)
  if scenario=='speedzones':y=(3.3 if i%2==0 else -3.3)
  pillars.append({'center':[x,float(y)],'radius':float(rng.uniform(.45,.65)),'height':float(rng.uniform(1.4,2.1))})
 pillars.extend([{'center':[9.,5.5],'radius':.7,'height':1.8},{'center':[22.,-5.5],'radius':.65,'height':1.9}])
 if scenario in ['jump','crouch']:
  pillars=[{'center':[x,0.],'radius':2.05,'shape':'box','kind':'hurdle' if scenario=='jump' else 'overhead','width':4.,'depth':.35 if scenario=='jump' else .5,'height':.18 if scenario=='jump' else .2,'base_z':0. if scenario=='jump' else 1.65,'display_by_body':{} if scenario=='jump' else {'brek':{'base_z':1.15},'eva':{'base_z':1.35}}} for x in ([10.,22.] if scenario=='jump' else [5.])]
 env={'bounds':[-2.,34.,-7.,7.],'arena_bounds':{'x_min':-2.,'x_max':34.,'y_min':-7.,'y_max':7.},'obstacles':pillars,'speed_zones':[{'x_min':5.,'x_max':15.,'desired_speed':2.4,'color':'#e69b42','label':'Orange / run','order':1},{'x_min':15.,'x_max':24.,'desired_speed':3.3,'color':'#d9554a','label':'Red / sprint','order':2}],'goal':[30.,0.] if scenario!='crouch' else [10.,0.],'root_radius_m':1.05,'cat_radius_m':.28,'seed':seed,'duration_s':DURATIONS[scenario]}
 if scenario=='course':
  env.update(bounds=[-2.,58.,-8.,8.],arena_bounds={'x_min':-2.,'x_max':58.,'y_min':-8.,'y_max':8.},goal=[54.,0.])
  env['obstacles']=[{'center':[x,y],'radius':.6,'height':1.8} for x,y in [(24,1.4),(28,-1.4),(48,4.5),(53,-4.5)]]
  env['obstacles'] += [{'center':[34.,0.],'radius':2.05,'shape':'box','kind':'overhead','width':4.,'depth':.5,'height':.2,'base_z':1.65,'display_by_body':{'brek':{'base_z':1.15},'eva':{'base_z':1.35}}},{'center':[44.,0.],'radius':2.05,'shape':'box','kind':'hurdle','width':4.,'depth':.35,'height':.18,'base_z':0.}]
  env['speed_zones'][0].update(x_min=4.,x_max=12.);env['speed_zones'][1].update(x_min=12.,x_max=22.)
 waypoints=[np.array([2.0,2.5])]+[np.array(p)+rng.uniform(-.3,.3,2) for p in [[8,-2.4],[13,2.6],[18,-2.1],[24,2.8],[29,-2.8],[26,3.5]]]
 if scenario=='course':waypoints=[np.array([45.,3.])]+[np.array(p)+rng.uniform(-.4,.4,2) for p in [[51,-3],[54,3],[47,-3],[55,-2],[48,4],[54,-3],[47,2],[54,3],[48,-3],[55,1]]]
 path=[waypoints[0]]
 for a,b in zip(waypoints,waypoints[1:]):path.extend(route(a,b,env,env['cat_radius_m'])[1:])
 cat=[path[0].copy()];edge=1
 for f in range(DURATIONS[scenario]*FPS):
  speed=.95+.25*math.sin(f/FPS*.45+seed);distance=speed/FPS;position=cat[-1].copy()
  while distance>1e-8 and edge<len(path):
   delta=path[edge]-position;length=np.linalg.norm(delta)
   if length<=distance:position=path[edge].copy();distance-=length;edge+=1
   else:position+=delta/length*distance;distance=0
  safe,_=sweep_slide(cat[-1],position,env,env['cat_radius_m']);cat.append(safe)
 env['cat_path']=np.array(cat).tolist();env['cat_route_waypoints']=[p.tolist() for p in waypoints];return env
def control(scenario,reactive,env,p,velocity,t,previous_speed):
 frame=min(len(env['cat_path'])-1,round(t*FPS));cat=np.array(env['cat_path'][frame]);pursuit=scenario in ['pursuit','mixed'] or scenario=='course' and p[0]>46.
 if pursuit:
  target=cat.copy()
  if reactive:
   future=np.array(env['cat_path'][min(len(env['cat_path'])-1,frame+21)]);target=future
  if scenario=='mixed' and not reactive:target=np.array(env['cat_path'][0])
 else:target=np.array(env['goal'])
 delta=target-p;distance=np.linalg.norm(delta);direction=delta/max(distance,1e-6)
 desired=1.2
 if scenario=='slalom':desired=1.35
 if scenario=='jump':desired=2.2
 if scenario=='crouch':desired=1.0
 if pursuit:desired=min(2.0,max(1.0,distance*.65))
 if scenario in ['speedzones','mixed','course']:
  for zone in env['speed_zones']:
   if zone['x_min']<p[0]<zone['x_max']:desired=zone['desired_speed']
 if pursuit and distance<2.6:desired=max(0.,(distance-1.65)*1.2)
 if not pursuit and distance<1.:desired=min(desired,distance)
 if reactive and scenario not in ['jump','crouch']:
  nav_env={**env,'obstacles':[ob for ob in env['obstacles'] if not ob.get('kind')]} if scenario=='course' else env
  planned=route(p,target,nav_env,env['root_radius_m']+.2);waypoint=planned[-1]
  for candidate in planned[1:]:
   waypoint=candidate
   if np.linalg.norm(candidate-p)>1.4:break
  direction=(waypoint-p)/max(np.linalg.norm(waypoint-p),1e-6)
  speed=previous_speed+np.clip(desired-previous_speed,-.3,.3)
 else:speed=desired
 return direction,float(speed),target

BANKS={}
def action_bank(kind):
 if kind not in BANKS:
  file=OUT/('cc0-crouch-contact.npz' if kind=='crouch' else 'jump-contact.npz');data=np.load(file);BANKS[kind]={'qpos':data['qpos'],'contacts':data['contacts'],'phase_names':data['phase_names'].tolist() if 'phase_names' in data.files else ['crouch walk']*len(data['qpos']),'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
 return BANKS[kind]
def action_window(scenario,env,position,frame,state):
 """Neural entry/exit around openly labelled, contact-prepared recorded motion."""
 if state.get('active') is None:
  for index,ob in enumerate(env['obstacles']):
   if not ob.get('kind'):continue
   kind='jump' if ob['kind']=='hurdle' else 'crouch';lead=4.2 if kind=='jump' else 3.1
   if index not in state['completed'] and 0<ob['center'][0]-position[0]<lead:
    state['active']={'index':index,'start':frame,'phase':0,'kind':kind,'cursor':0};break
 if state.get('active') is None:return None,None
 active=state['active'];kind=active['kind'];bank=action_bank(kind);qbank=bank['qpos'];ob=env['obstacles'][active['index']];x=ob['center'][0]
 if active['phase']>=3:
  state['completed'].append(active['index']);state['active']=None;return None,None
 event={'kind':kind,'obstacle':active['index'],'phase':active['phase'],'elapsed':(frame-active['start'])/FPS,'source_sha256':bank['sha256'],'source_license':'CC0-1.0' if kind=='crouch' else 'original authored conditioning / model-derived motion','source_reference':'Quaternius UAL1 Standard RM Crouch_Fwd_Loop plus explicit contact preparation' if kind=='crouch' else 'Original-conditioned own_jump_over, phase-retimed with stance contact preparation'}
 if active['phase']==0:
  q=np.repeat(qbank[:1],4,axis=0) if kind=='crouch' else qbank[:4].copy();q[:,:2]-=qbank[0,:2];q[:,:2]+=np.array([x-(2.02 if kind=='jump' else 1.6),ob['center'][1]]);event['phase_name']='run to plant' if kind=='jump' else 'crouch entry';return q,event
 if active['phase']==1:
  if kind=='jump' and active['cursor']>=len(qbank)-1 or kind=='crouch' and position[0]>x+1.65:active['phase']=2
  else:
   if 'anchor' not in active:active['anchor']=position.copy()
   event.update(source_replay=True,moving_target=True,phase_name='recorded '+kind+' motion');return qbank[:4].copy(),event
 if kind=='jump':q=target_window(position,np.array([1.,0.]),2.2,frame)
 else:
  q=np.repeat(np.array(LIB['poses']['neutral'],np.float32)[None,:],4,axis=0);q[:,:2]=[position[0]+.6,position[1]]
 event.update(phase=2,phase_name='running recovery' if kind=='jump' else 'stand and recover');return q,event

def replay_chunk(state):
 active=state['active'];kind=active['kind'];bank=action_bank(kind);source=bank['qpos'];period=len(source)-1;n=CHUNK if kind=='crouch' else min(CHUNK,period-active['cursor']);frames=[];contacts=[];names=[]
 for _ in range(n):
  active['cursor']+=2 if kind=='crouch' else 1;cursor=active['cursor'];index=cursor%period if kind=='crouch' else cursor;cycle=cursor//period if kind=='crouch' else 0;q=source[index].copy();q[:2]-=source[0,:2];q[:2]+=active['anchor']+cycle*(source[-1,:2]-source[0,:2]);frames.append(q);contacts.append(bank['contacts'][index]);names.append(bank['phase_names'][index] if kind=='jump' else 'crouch walk')
 return np.array(frames,np.float32),np.array(contacts,np.float32),names

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
 FRAMES=DURATIONS[scenario]*FPS
 id=f'{scenario}_{condition}_{seed}';folder=OUT/id;folder.mkdir(parents=True,exist_ok=True);env=scene(seed,scenario);reactive=condition=='reactive';initial=np.array(LIB['poses']['neutral'],np.float32);initial[1]=np.random.default_rng(seed+100).uniform(-.06,.06);recent=np.repeat(initial[None,:],4,axis=0);shown=[initial];unmodified=[initial.copy()];full_predictions=[];prediction_offsets=[];controller_contacts=[[]];controller_corrections=[0.];contacts=[np.zeros(4,np.float32)];trace=[];commands=[];speed=0.;start=time.perf_counter();action_state={'active':None,'completed':[]};action_events=[];phase_names=['idle'];segment_modes=[];contact_ik_mask=[0]
 with wp.ScopedStream(predictor.engine.stream):
  while len(shown)<=FRAMES:
   frame=len(shown)-1;now=shown[-1];position=now[:2].copy();velocity=(shown[-1][:2]-shown[-2][:2])*FPS if len(shown)>1 else np.zeros(2);direction,speed,target=control(scenario,reactive,env,position,velocity,frame/FPS,speed);g=target_window(position,direction,speed,frame);action_event=None
   if reactive and scenario in ['jump','crouch','course']:
    action_target,action_event=action_window(scenario,env,position,frame,action_state)
    if action_target is not None:g=action_target;action_events.append({'frame':frame,**action_event})
   before=recent.copy()
   replay=bool(action_event and action_event.get('source_replay'));segment_mode='source_clip' if replay else 'neural';segment_modes.append(segment_mode)
   if replay:
    raw,c,raw_phases=replay_chunk(action_state);g=raw[-4:].copy();elapsed=0.;offset=0;n=len(raw)
   else:
    predictor.context.update_from_poses(wp.array(recent,dtype=wp.float32),stream=predictor.engine.stream);predictor.target.update_from_poses(wp.array(g,dtype=wp.float32),stream=predictor.engine.stream);tick=time.perf_counter();predictor.engine.generate_animation(predictor.context,predictor.target,predictor.output,config=MotionBricksInferenceConfig());predictor.engine.synchronize();elapsed=time.perf_counter()-tick
    raw=predictor.output.poses[:predictor.output.num_frames].numpy().copy();c=predictor.output.foot_contacts[:predictor.output.num_frames].numpy().copy();offset=int(np.allclose(raw[0],now,atol=1e-4));n=len(raw)-offset if action_event else CHUNK;raw_phases=[action_event['phase_name'] if action_event else ('pursuit' if scenario in ['pursuit','mixed'] or scenario=='course' and position[0]>46 else 'run' if speed>1.5 else 'walk')]*len(raw)
   prediction_offsets.append([sum(len(p) for p in full_predictions),len(raw)]);full_predictions.append(raw.copy());n=min(n,FRAMES+1-len(shown),len(raw)-offset);played=raw[offset:offset+n].copy();played_c=c[offset:offset+n];assert n>0 and np.isfinite(played).all();phase_names.extend(raw_phases[offset:offset+n]);contact_ik_mask.extend([int(replay)]*n)
   chunk_origin_delta=np.zeros(2)
   for j,row in enumerate(played):
    unmodified.append(row.copy());candidate=row[:2]+chunk_origin_delta
    if scenario in ['jump','crouch','course']:
     from reactive_behavior_collision import resolve_pose
     candidate_q=row.copy();candidate_q[:2]=candidate;resolved=resolve_pose(shown[-1],candidate_q,env,predictor);safe,hits=resolved[:2]
    else:safe,hits=sweep_slide(shown[-1][:2],candidate,env,env['root_radius_m'])
    correction=safe-candidate;chunk_origin_delta+=correction;row[:2]=safe;shown.append(row.copy());controller_contacts.append(hits);controller_corrections.append(float(np.linalg.norm(correction)))
   contacts.extend(played_c)
   if action_event and not replay:action_state['active']['phase']+=1
   recent=np.array(shown[-4:],np.float32)
   if len(recent)<4:recent=np.concatenate([before,recent])[-4:]
   trace.append({'segment_mode':segment_mode,'source_phase':action_event,'index':len(trace),'start_frame':frame+1,'frames':n,'raw_frames':len(raw),'unused_future_frames':len(raw)-offset-n,'inference_seconds':elapsed,'context':before.tolist(),'target':g.tolist(),'last_four_generated':recent.tolist(),'last_four_played':recent.tolist(),'context_from_previous_prediction':bool(trace),'context_is_last_displayed_not_unused_future':True,'context_includes_native_collision_response':True,'shared_endpoint_removed':bool(offset),'endpoint_root_error_m':float(np.linalg.norm(shown[-1][:2]-g[0,:2]))})
   commands.append({'frame':frame,'position':position.tolist(),'desired_speed':speed,'direction':direction.tolist(),'external_goal':target.tolist(),'action':action_event,'segment_mode':segment_mode})
 q=np.array(shown,np.float32);c=np.array(contacts,np.float32);vel=np.diff(q[:,:2],axis=0)*FPS;acc=np.diff(vel,axis=0)*FPS;jerk=np.diff(acc,axis=0)*FPS;clear=[];collisions=np.zeros(len(q),bool)
 body=predictor.transforms(q);ankles=[predictor.names.index(n) for n in ['left_ankle_roll_link','right_ankle_roll_link']];sole=body[:,ankles,2].min(axis=1)-.17;top=body[:,:,2].max(axis=1)+.86;obstacle_overlaps=[[] for _ in q];passages=[]
 for index,ob in enumerate(env['obstacles']):
  delta=np.abs(q[:,:2]-np.array(ob['center']))
  if ob.get('shape')=='box':planar=np.maximum(delta[:,0]-ob['depth']/2-env['root_radius_m'],delta[:,1]-ob['width']/2-env['root_radius_m'])
  else:planar=np.linalg.norm(delta,axis=1)-ob['radius']-env['root_radius_m']
  vertical=np.maximum(ob.get('base_z',0.)-top,sole-ob.get('base_z',0.)-ob['height']);dist=np.maximum(planar,vertical);inside=dist< -1e-5;clear.extend(dist);collisions|=inside
  for i in np.where(inside)[0]:obstacle_overlaps[i].append(index)
  if ob.get('kind'):
   crossed=bool(q[:,0].max()>ob['center'][0]+ob['depth']/2+env['root_radius_m'])
   passages.append({'obstacle':index,'kind':ob['kind'],'crossed':crossed,'proxy_collision_frames':int(inside.sum()),'success':crossed and not bool(inside.any())})
 zone_metrics=[]
 for zone in env['speed_zones']:
  selected=(q[:-1,0]>=zone['x_min'])&(q[:-1,0]<zone['x_max']);speeds=np.linalg.norm(vel,axis=1);zone_metrics.append({'label':zone.get('label'),'order':zone.get('order'),'command_m_s':zone['desired_speed'],'mean_actual_speed_m_s':float(speeds[selected].mean()) if selected.any() else None,'time_s':float(selected.sum()/FPS)})
 metrics={'zone_metrics':zone_metrics,'root_proxy_collision_frames':int(collisions.sum()),'attempted_contact_frames':sum(bool(c) for c in controller_contacts),'controller_correction_total_m':float(sum(controller_corrections)),'cat_minimum_proxy_clearance_m':float(min(clearance(np.array(p),env,env['cat_radius_m']) for p in env['cat_path'])),'minimum_root_proxy_clearance_m':float(min(clear)) if clear else None,'mean_speed_m_s':float(np.linalg.norm(vel,axis=1).mean()),'max_speed_m_s':float(np.linalg.norm(vel,axis=1).max()),'root_acceleration_p95_m_s2':float(np.percentile(np.linalg.norm(acc,axis=1),95)),'root_jerk_p95_m_s3':float(np.percentile(np.linalg.norm(jerk,axis=1),95)),'final_goal_distance_m':float(np.linalg.norm(q[-1,:2]-(np.array(env['cat_path'][-1]) if scenario in ['pursuit','mixed'] else np.array(env['goal'])))),'jump_peak_sole_proxy_m':float(sole.max()),'crouch_min_top_proxy_m':float(top.min()),'behavior_crossed_obstacles':sum(p['crossed'] for p in passages),'behavior_successful_passages':sum(p['success'] for p in passages),'height_active_proxy_collision_frames':int(collisions.sum()),'neural_calls':sum(mode=='neural' for mode in segment_modes),'source_clip_frames':sum(seg['frames'] for seg in trace if seg.get('segment_mode')=='source_clip'),'discarded_future_frames':sum(s['unused_future_frames'] for s in trace)}
 meta={'id':id,'label':f'{scenario} / {condition} / seed {seed}','clip':'REACTIVE_'+id,'purpose':'Closed-loop recorded take: neural locomotion/entry/exit, with explicitly classified contact-prepared source playback for hybrid actions. Planner selects targets; model does not receive scene geometry.','provenance_type':'mixed_permitted_sources' if scenario in ['jump','crouch','course'] and reactive else 'original','model':'MotionBricks-G1-RP-v1','precision':'FP32','sample_rate':FPS,'frames':len(q),'duration_s':(len(q)-1)/FPS,'inputs':[{'context':s['context'],'target':s['target']} for s in trace],'segments':trace,'inference_seconds':sum(s['inference_seconds'] for s in trace),'total_seconds':time.perf_counter()-start,'source_metrics':{'maximum_joint_key_step_rad':float(np.abs(np.diff(q[:,7:],axis=0)).max())},'body_names':predictor.names,'routine':{'type':'reactive_closed_loop','move_count':len(trace)},'sources':{n:hashlib.sha256(path.read_bytes()).hexdigest() for n,path in SOURCES.items()},'generation_method':'neural entry/exit plus contact-prepared recorded source action' if any(mode=='source_clip' for mode in segment_modes) else 'neural generation','reactive':{'scenario':scenario,'condition':condition,'seed':seed,'metrics':metrics},'limitations':['Kinematic generation plus an external swept root-circle stop/slide controller; not a dynamic or limb collision solver.','Collision metrics use a conservative root proxy, not whole-body shape clearance.','Locomotion and action entry/exit are neural generations. Labelled contact-prepared recorded action segments are replayed, then fed into subsequent neural context. Unused locomotion futures are discarded.','Root radius 1.05 m is a conservative native-space broad-armor navigation envelope; full articulated collision is not solved.','Pursuit keeps a larger arrival standoff; mutual dynamic cat/actor collision is not solved.','C08/BREK grounding is a separate displayed retarget correction; raw G1 is retained.']}
 predictor.save(folder,q,c,meta)
 with np.load(folder/'g1-motion.npz') as data:arrays={k:data[k].copy() for k in data.files}
 np.savez(folder/'g1-motion.npz',**arrays,contact_ik_mask=np.array(contact_ik_mask,np.uint8))
 np.savez_compressed(folder/'unmodified-predictions.npz',selected_unmodified_qpos=np.array(unmodified,np.float32),all_predicted_future_qpos=np.concatenate(full_predictions),prediction_offsets=np.array(prediction_offsets),segment_modes=np.array(segment_modes),played_corrected_qpos=q); (folder/'prediction-trace.json').write_text(json.dumps({'metadata':meta,'skeletons_g1_zup':[{'context':predictor.transforms(np.array(s['context'],np.float32))[:,:,:3].tolist(),'target':predictor.transforms(np.array(s['target'],np.float32))[:,:,:3].tolist()} for s in trace]},indent=2),encoding='utf8');episode={'generation_method':meta['generation_method'],'action_provenance':list({e['kind']:{k:e[k] for k in ['kind','source_reference','source_sha256','source_license']} for e in action_events}.values()),'contact_ik_mask':contact_ik_mask,'id':id,'scenario':scenario,'condition':condition,'seed':seed,'environment':{k:v for k,v in env.items() if not k.startswith('_')},'commands':commands,'metrics':metrics,'raw_root_path':q[:,:3].tolist(),'played_root_path':q[:,:3].tolist(),'predicted_root_path':np.array(unmodified)[:,:3].tolist(),'phase_names':phase_names,'action_events':action_events,'behavior_passages':passages,'obstacle_overlaps':obstacle_overlaps,'controller_contacts':controller_contacts,'controller_corrections_m':controller_corrections,'collision_events':[{'frame':i,'obstacle_indices':hits,'correction_m':controller_corrections[i]} for i,hits in enumerate(controller_contacts) if hits],'collision_contacts':[{'frame':i,'obstacles':hits,'correction_m':controller_corrections[i]} for i,hits in enumerate(controller_contacts) if hits],'sample_rate':FPS,'duration_s':meta['duration_s'],'limitations':meta['limitations']};(folder/'episode.json').write_text(json.dumps(episode,indent=2),encoding='utf8');return {'id':id,'label':meta['label'],'scenario':scenario,'condition':condition,'seed':seed,'duration_s':meta['duration_s'],'metrics':metrics}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--seeds',type=int,default=10);parser.add_argument('--scenario',default='all');parser.add_argument('--append',action='store_true');parser.add_argument('--conditions',default='baseline,reactive');parser.add_argument('--start-seed',type=int,default=1);parser.add_argument('--skip-existing',action='store_true');args=parser.parse_args();OUT.mkdir(exist_ok=True);predictor=Predictor();catalog=json.loads((OUT/'catalog.json').read_text())['cases'] if args.append and (OUT/'catalog.json').exists() else []
 for scenario in SCENARIOS if args.scenario=='all' else args.scenario.split(','):
  for seed in range(args.start_seed,args.seeds+1):
   for condition in args.conditions.split(','):
    if args.skip_existing and (OUT/f'{scenario}_{condition}_{seed}'/'episode.json').exists():continue
    record=run(predictor,scenario,condition,seed);catalog=[r for r in catalog if r['id']!=record['id']];catalog.append(record);(OUT/'catalog.json').write_text(json.dumps({'version':'reactive-round4-motion-quality','cases':catalog},indent=2),encoding='utf8');print('REACTIVE_GENERATED',record['id'],record['metrics'],flush=True)
