"""Local six-performance SOMA in-betweening pilot; original captures stay unchanged."""
from pathlib import Path
import argparse, hashlib, json, os, time, traceback
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R

_roots=[Path(os.environ['MOTION_LAB_WORKSPACE'])] if os.environ.get('MOTION_LAB_WORKSPACE') else list(Path(__file__).resolve().parents)
ROOT=next((p for p in _roots if (p/'video-mocap').is_dir() and (p/'upstream/motionbricks').is_dir()),None)
if ROOT is None:raise RuntimeError('Set MOTION_LAB_WORKSPACE to the existing local lab containing video-mocap and upstream; private captures and model weights are not included.')
os.environ['WARP_CACHE_PATH']=str(ROOT/'evaluation/mocap-rebuild/cache/warp')
os.environ['CUDA_CACHE_PATH']=str(ROOT/'evaluation/mocap-rebuild/cache/cuda')
import warp as wp
from motionbricks.animation.skeleton import Skeleton
from motionbricks.model.soma.engine import MotionBricksSOMAEngine
from motionbricks.model.soma.contract import SOMA_N1_FP32_ONNX_PATH
from motionbricks.model.config import MotionBricksInferenceConfig

SLUGS=['ukemi','technical-standup','gorilla-front','sumo-stomp','source-094553','h3-dance']
parser=argparse.ArgumentParser();parser.add_argument('slugs',nargs='*',default=SLUGS);parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--reassemble-cached',action='store_true');args=parser.parse_args()
OUT=ROOT/'evaluation/mocap-rebuild';OUT.mkdir(parents=True,exist_ok=True)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
def mat_to_pq(m):
 shape=m.shape[:-2];q=R.from_matrix(m[...,:3,:3].reshape(-1,3,3)).as_quat().reshape(*shape,4)
 return np.concatenate([m[...,:3,3],q],axis=-1)
def pq_to_mat(pq):
 shape=pq.shape[:-1];m=np.broadcast_to(np.eye(4),(*shape,4,4)).copy();m[...,:3,:3]=R.from_quat(pq[...,3:].reshape(-1,4)).as_matrix().reshape(*shape,3,3);m[...,:3,3]=pq[...,:3];return m
def local_from_world(world,parents):
 local=world.copy()
 for j,p in enumerate(parents):
  if p>=0:local[:,j]=np.linalg.inv(world[:,p])@world[:,j]
 return mat_to_pq(local)
def world_from_local(local,parents):
 matrices=pq_to_mat(local);world=matrices.copy()
 for j,p in enumerate(parents):
  if p>=0:world[:,j]=world[:,p]@matrices[:,j]
 return world
def continuous(quats):
 q=quats.copy()
 for f in range(1,len(q)):
  reverse=np.sum(q[f-1]*q[f],axis=-1)<0;q[f,reverse]*=-1
 return q
def neutral_pose(reference,parents,names,reference_bounds):
 local=local_from_world(reference[None],parents)[0];local[0,:3]=[0,-float(reference_bounds[0,1])-.006,0]
 matrices=pq_to_mat(local);world=[]
 for j,p in enumerate(parents):
  m=matrices[j].copy();base=(world[p]@m) if p>=0 else m
  name=names[j]
  angle=None;axis='z'
  if name=='LeftArm':angle=-75
  elif name=='RightArm':angle=75
  elif name in ('LeftLeg','RightLeg'):angle=-4;axis='x'
  elif name in ('LeftShin','RightShin'):angle=4;axis='x'
  elif name in ('LeftFoot','RightFoot'):angle=0;axis='x'
  if angle is not None:
   base[:3,:3]=R.from_euler(axis,angle,degrees=True).as_matrix()@reference[j,:3,:3]
   m=np.linalg.inv(world[p])@base if p>=0 else base
  world.append(base);matrices[j]=m
 return mat_to_pq(matrices)
def pick_keys(world,names,limit):
 """Pose-curve simplification + explicit floor/limb extremes, bounded temporal spacing."""
 n=limit;lookup={name:i for i,name in enumerate(names)}
 idx=[lookup[name] for name in ['Hips','Head','LeftHand','RightHand','LeftFoot','RightFoot','LeftShin','RightShin']]
 pos=world[:n,idx,:3,3];scale=max(.2,np.linalg.norm(pos[0,1]-pos[0,0]));features=pos.reshape(n,-1)/scale
 keys=[0,n-4]
 # Greedy largest deviation from piecewise-linear body trajectory.
 while len(keys)<7:
  best=(-1,None)
  for a,b in zip(sorted(keys)[:-1],sorted(keys)[1:]):
   if b-a<18:continue
   ids=np.arange(a+8,b-7);u=(ids-a)/(b-a)
   residual=np.linalg.norm(features[ids]-(features[a][None]*(1-u[:,None])+features[b][None]*u[:,None]),axis=1)
   k=int(np.argmax(residual))
   if float(residual[k])>best[0]:best=(float(residual[k]),int(ids[k]))
  if best[1] is None:break
  keys.append(best[1])
 return sorted(set(keys))
def metrics(local):
 q=continuous(local[:,:,3:]);relative=(R.from_quat(q[:-1].reshape(-1,4)).inv()*R.from_quat(q[1:].reshape(-1,4))).as_rotvec().reshape(len(q)-1,-1,3)
 speed=np.linalg.norm(relative,axis=-1)*30
 acceleration=np.linalg.norm(np.diff(relative,axis=0),axis=-1)*900
 return {'angular_speed_p95_rad_s':float(np.quantile(speed,.95)),'angular_acceleration_p95_rad_s2':float(np.quantile(acceleration,.95)),'maximum_local_rotation_step_deg':float(np.degrees(speed.max()/30))}
def save_variant(slug,variant,local,source,metadata,contacts=None):
 folder=OUT/slug/variant;folder.mkdir(parents=True,exist_ok=True);world=world_from_local(local,source['parent_indices']);positions=world[:,:,:3,3]
 np.savez_compressed(folder/'soma-frames.npz',world_transforms=world,reference_transforms=source['reference_transforms'],reference_surface_bounds=source['reference_surface_bounds'],joint_names=source['joint_names'],parent_indices=source['parent_indices'],timestamps=np.arange(len(world))/30,surface_bounds_world=np.stack([positions.min(axis=1),positions.max(axis=1)],axis=1),local_transforms=local,foot_contacts=np.asarray(contacts) if contacts is not None else np.zeros((len(world),4)))
 base={'id':f'rebuild_{slug}_{variant}','source_file_id':slug,'variant':variant,'provenance_type':'user_owned_mocap' if slug!='h3-dance' else 'creator_supplied_generated_biped_reference','pipeline':'Own reference -> GEM-X SOMA77 -> MotionBricks SOMA' if variant in ('single','window') else 'Own reference -> GEM-X SOMA77 control; no MotionBricks inference','frames':len(world),'sample_rate':30,'duration_s':(len(world)-1)/30,'source_joint_count':len(source['joint_names']),'source_space':'Y up, metres; source first heading removed and origin/floor translated once','source_motion_sha256':digest(ROOT/'video-mocap'/slug/'soma-motion.npz'),'source_prepared_sha256':digest(ROOT/'video-mocap/c08-retarget'/slug/'soma-frames.npz'),'surface_bounds_note':'Joint-coordinate bounds only, not recovered or target skinned geometry. Do not use as full-skin ground proof.','limitations':['Monocular depth and hidden joints remain estimates','No physical contact/balance/self-collision solve','No source video, source frames or model weights published','Non-model fingers stay at reference during neural output; source finger articulation is not regenerated'],**metadata}
 base['motion_metrics_full_clip']=metrics(local)
 active=base.get('active_frame_range',[0,len(local)-1]);active_local=local[active[0]:active[1]+1]
 if len(active_local)>2:base['motion_metrics_active']=metrics(active_local)
 write(folder/'source-metadata.json',base);write(folder/'artifact-hashes.json',{'soma-frames.npz':digest(folder/'soma-frames.npz')})
 print('VARIANT_READY',slug,variant,len(world),flush=True);return base
def prepare(slug):
 sourcepath=ROOT/'video-mocap/c08-retarget'/slug/'soma-frames.npz';data=np.load(sourcepath);source={key:data[key].copy() for key in data.files}
 names=source['joint_names'].tolist();parents=source['parent_indices'];world=source['world_transforms'].copy();ref=source['reference_transforms'];bounds=source['reference_surface_bounds']
 # Initial horizontal origin, heading and a single recovered-surface ground translation.
 left=names.index('LeftLeg');right=names.index('RightLeg');across=world[0,right,:3,3]-world[0,left,:3,3];forward=np.cross([0,1,0],across);heading=float(np.arctan2(forward[0],forward[2]));rotation=R.from_euler('y',-heading).as_matrix()
 offset=world[0,0,:3,3].copy();offset[1]=float(source['surface_bounds_world'][:,0,1].min());world[:,:,:3,3]=(world[:,:,:3,3]-offset)@rotation.T;world[:,:,:3,:3]=rotation[None,None]@world[:,:,:3,:3]
 raw=local_from_world(world,parents);clean=raw.copy();clean[:,:,3:]=continuous(raw[:,:,3:]);clean[:,:,3:]=gaussian_filter1d(clean[:,:,3:],sigma=1.15,axis=0,mode='nearest');clean[:,:,3:]/=np.linalg.norm(clean[:,:,3:],axis=-1,keepdims=True)
 clean[:,0,:3]=gaussian_filter1d(clean[:,0,:3],sigma=1.15,axis=0,mode='nearest')
 # Stable source lengths from median local translations; no limb or root-floor lock.
 clean[:,1:,:3]=np.median(raw[:,1:,:3],axis=0)[None]
 neutral=neutral_pose(ref,parents,names,bounds)
 limit=len(world);excluded=[]
 if slug=='gorilla-front':
  coverage=json.loads((ROOT/'video-mocap'/slug/'recovery-validation.json').read_text(encoding='utf-8'))['input_visibility_diagnostics'];bad=coverage['frames_with_at_least_five_major_joints_outside_image']
  if bad:limit=max(30,int(bad[0]));excluded=[[limit,len(world)-1]]
 keys=pick_keys(world_from_local(clean,parents),names,limit)
 plan={'source_id':slug,'source_prepared_sha256':digest(sourcepath),'original_frames':len(world),'used_source_frame_range':[0,limit-1],'excluded_source_frame_ranges':excluded,'exclusion_note':'Gorilla uses the explicitly reported reliable prefix before >=5 major projected joints leave image; original raw/cleaned controls remain full length. Coverage is not accuracy.','source_key_indices':keys,'source_key_times_s':[i/30 for i in keys],'key_policy':'Greedy largest body-trajectory deviation from piecewise linear paths, seven landmarks with >=8-frame spacing, using head/hands/feet/shins/root; corrected by modest smoothing, no authored source poses.','cleaning':{'quaternion_filter':'Sign-continuous local quaternion normalized Gaussian average','sigma_frames':1.15,'root_position_filter':'Gaussian sigma1.15 frames','child_translation_policy':'Constant median local bone translations','foot_or_hand_ik':False,'per_frame_floor_translation':False},'initial_heading_removed_rad':heading,'single_constant_input_translation':offset.tolist(),'default_stance':'Authored relaxed T-bind delta: upper arms ±75deg worldZ, thighs -4deg/shins +4deg worldX, feet reference orientation; reference-proportioned hips height. Not recovered performance or neural generation.','neutral_hold_frames':12}
 write(OUT/slug/'key-plan.json',plan)
 save_variant(slug,'raw',raw,source,{'active_frame_range':[0,len(raw)-1],'neutral_hold_frames':0,'actual_neural_calls':0,'generated_segment_boundaries':[],'loop_policy':'Original full source motion; not closed','basis':plan})
 save_variant(slug,'cleaned',clean,source,{'active_frame_range':[0,len(clean)-1],'neutral_hold_frames':0,'actual_neural_calls':0,'generated_segment_boundaries':[],'loop_policy':'Original full source motion after modest filtering; not closed','basis':plan})
 return source,raw,clean,neutral,plan

if args.reassemble_cached:
 # Deduplicating a coincident first sample does not change a segment's last four
 # poses, so the recorded inference requests remain valid without new model calls.
 summary=json.loads((OUT/'generation-summary.json').read_text(encoding='utf-8'));checks=[]
 for slug in args.slugs:
  for variant in ('single','window'):
   folder=OUT/slug/variant
   meta=json.loads((folder/'source-metadata.json').read_text(encoding='utf-8'))
   with np.load(folder/'soma-frames.npz') as saved:source={key:saved[key].copy() for key in saved.files}
   with np.load(folder/'inference-arrays.npz') as saved:arrays={key:saved[key].copy() for key in saved.files}
   neutral=source['local_transforms'][0].copy();parts=[np.repeat(neutral[None],12,axis=0)];contacts=[np.ones((12,4),np.float32)];boundaries=[];trace=[]
   for old in meta['segments']:
    i=old['segment'];actual_context=arrays[f'context_{i}'].astype(np.float32);actual_target=arrays[f'target_{i}'].astype(np.float32);output=arrays[f'output_{i}'];foot=arrays[f'contacts_{i}']
    assert np.array_equal(actual_context,np.concatenate(parts)[-4:].astype(np.float32)),('Context mismatch',slug,variant,i)
    gap=float(np.max(np.abs(pq_to_mat(output[0])-pq_to_mat(parts[-1][-1]))));shared=gap<1e-5;used=int(shared);start=sum(len(part) for part in parts)
    parts.append(output[used:]);contacts.append(foot[used:]);boundaries.append(start)
    arrays[f'context_{i}']=actual_context;arrays[f'target_{i}']=actual_target
    trace.append({**old,'output_frame_start':start,'frames':len(output)-used,'raw_frames':len(output),'played_frames':len(output)-used,'used_start_index':used,'shared_endpoint_removed':shared,'shared_endpoint_matrix_gap':gap,'input_storage_dtype':'float32','context_chain_comparison':'Exact after float32 engine-upload conversion','context_sha256':hashlib.sha256(actual_context.tobytes()).hexdigest(),'target_sha256':hashlib.sha256(actual_target.tobytes()).hexdigest()})
   motion=np.concatenate(parts);foot=np.concatenate(contacts);active_end=len(motion)-1;motion[-1]=neutral;motion=np.concatenate([motion,np.repeat(neutral[None],12,axis=0)]);foot=np.concatenate([foot,np.ones((12,4),np.float32)])
   meta.update(frames=len(motion),duration_s=(len(motion)-1)/30,active_frame_range=[12,active_end],generated_segment_boundaries=boundaries,final_hold_start_frame=active_end+1,segments=trace,shared_endpoint_deduplication='One coincident start sample removed at each segment; complete raw NN arrays retained. No pose interpolation or output smoothing added.',contacts_note='Native neural predicted values within generated segments; authored neutral holds use ones as an explicit display label, not a measured contact solve.')
   np.savez_compressed(folder/'inference-arrays.npz',**arrays);newmeta=save_variant(slug,variant,motion,source,meta,foot)
   write(folder/'generation-trace.json',{'metadata':newmeta,'array_file':'inference-arrays.npz','all_generated_poses_retained_in_arrays':True,'coincident_output_start_removed_from_playback':True,'source_video_included':False})
   for row in summary['results']:
    if row['source']==slug and row['variant']==variant:row['frames']=len(motion)
   checks.append({'source':slug,'variant':variant,'calls':len(trace),'exact_float32_context_chain':True,'shared_starts_removed':sum(t['used_start_index'] for t in trace),'raw_frames':sum(t['raw_frames'] for t in trace),'played_neural_frames':sum(t['played_frames'] for t in trace)})
 summary['cached_deduplication']={'status':'passed','additional_neural_calls':0,'results':checks};write(OUT/'generation-summary.json',summary);raise SystemExit(0)

wp.init();wp.set_device('cuda:0')
prepared={}
for slug in args.slugs:
 (OUT/slug).mkdir(parents=True,exist_ok=True);prepared[slug]=prepare(slug)
if args.prepare_only:raise SystemExit(0)
modelhash=digest(Path(SOMA_N1_FP32_ONNX_PATH));started=time.perf_counter();results=[]
with MotionBricksSOMAEngine(SOMA_N1_FP32_ONNX_PATH,cache_dir=str(ROOT/'upstream/.trt-cache'),logger_severity='WARNING') as engine:
 for slug,(source,raw,clean,neutral,plan) in prepared.items():
  skeleton=Skeleton(source['joint_names'].tolist(),source['parent_indices'],local_from_world(source['reference_transforms'][None],source['parent_indices'])[0]);skeleton.up_axis=wp.vec3(0,1,0);skeleton.forward_axis=wp.vec3(0,0,1)
  context=engine.create_input(skeleton);target=engine.create_input(skeleton);output=engine.create_output(skeleton)
  for variant in ['single','window']:
   folder=OUT/slug/variant;folder.mkdir(parents=True,exist_ok=True);parts=[np.repeat(neutral[None],12,axis=0)];contacts=[np.ones((12,4),np.float32)];recent=parts[0][-4:].copy();traces=[];buffers={};boundaries=[]
   # Identical phase landmarks for both variants; final default is always a stop.
   goals=[(int(key),clean[key:key+(4 if variant=='window' else 1)].copy()) for key in plan['source_key_indices']]
   goals.append((None,np.repeat(neutral[None],4 if variant=='window' else 1,axis=0)))
   with wp.ScopedStream(engine.stream):
    for segment,(key,goal) in enumerate(goals):
     before=recent.copy();context.update_from_poses(wp.array(before.astype(np.float32),dtype=wp.transform),stream=engine.stream);target.update_from_poses(wp.array(goal.astype(np.float32),dtype=wp.transform),stream=engine.stream)
     tick=time.perf_counter();engine.generate_animation(context,target,output,config=MotionBricksInferenceConfig(allowed_token_counts=tuple(range(6,17))));engine.synchronize();seconds=time.perf_counter()-tick
     generated=output.poses[:output.num_frames].numpy().astype(np.float64);pred_contacts=output.foot_contacts[:output.num_frames].numpy();assert len(generated)>=4 and np.isfinite(generated).all()
     endpoint_error=float(np.max(np.abs(pq_to_mat(generated[-1])-pq_to_mat(goal[0]))))
     start=sum(len(part) for part in parts);boundaries.append(start)
     shared=bool(np.max(np.abs(pq_to_mat(generated[0])-pq_to_mat(parts[-1][-1])))<1e-5);used_start=int(shared)
     parts.append(generated[used_start:]);contacts.append(pred_contacts[used_start:]);recent=np.concatenate(parts)[-4:].copy()
     actual_context=before.astype(np.float32);actual_target=goal.astype(np.float32)
     buffers[f'context_{segment}']=actual_context;buffers[f'target_{segment}']=actual_target;buffers[f'output_{segment}']=generated;buffers[f'contacts_{segment}']=pred_contacts
     traces.append({'segment':segment,'output_frame_start':start,'frames':len(generated)-used_start,'raw_frames':len(generated),'played_frames':len(generated)-used_start,'used_start_index':used_start,'shared_endpoint_removed':shared,'source_key_index':key,'target_window_frames':len(goal),'inference_seconds':seconds,'endpoint_matrix_max_error':endpoint_error,'context_sha256':hashlib.sha256(actual_context.tobytes()).hexdigest(),'target_sha256':hashlib.sha256(actual_target.tobytes()).hexdigest(),'output_sha256':hashlib.sha256(generated.tobytes()).hexdigest(),'input_storage_dtype':'float32','context_chain_comparison':'Exact after float32 engine-upload conversion','context_is_last_four_actual_played_poses':True,'kind':'neural_return_to_default' if key is None else 'neural_between_source_landmarks'})
     print('NN_SEGMENT',slug,variant,segment,len(generated),seconds,flush=True)
   motion=np.concatenate(parts);foot=np.concatenate(contacts);active_end=len(motion)-1
   # Engine endpoint correction is floating-point approximate. Report residual before
   # snapping that endpoint to its requested neutral, then hold it for a clean seam.
   neutral_residual=float(np.max(np.abs(pq_to_mat(motion[-1])-pq_to_mat(neutral))))
   motion[-1]=neutral;motion=np.concatenate([motion,np.repeat(neutral[None],12,axis=0)]);foot=np.concatenate([foot,np.ones((12,4),np.float32)])
   np.savez_compressed(folder/'inference-arrays.npz',**buffers)
   meta=save_variant(slug,variant,motion,source,{'basis':plan,'active_frame_range':[12,active_end],'neutral_hold_frames':12,'generated_segment_boundaries':boundaries,'source_key_indices':plan['source_key_indices'],'actual_neural_calls':len(traces),'model':'MotionBricks-SOMA-RP-v1','model_precision':'FP32','model_sha256':modelhash,'model_sample_rate':30,'source_to_model_skeleton':'Original native77 hierarchy passed to official engine; required30joint subset used by model; noG1intermediate','loop_policy':'Authored12frame neutral hold -> genuine neural phase targets -> genuine neural return to exactsame neutral -> authored12frame neutral hold; model durations freely reinterpreted','final_endpoint_numeric_snap_max_matrix_error':neutral_residual,'loop_endpoint_world_matrix_max_error':float(np.max(np.abs(world_from_local(motion[:1],source['parent_indices'])-world_from_local(motion[-1:],source['parent_indices'])))),'final_hold_start_frame':active_end+1,'generated_duration_not_original_timing':True,'segments':traces},foot)
   write(folder/'generation-trace.json',{'metadata':meta,'array_file':'inference-arrays.npz','all_generated_poses_retained_in_arrays':True,'coincident_output_start_removed_from_playback':True,'source_video_included':False});results.append({'source':slug,'variant':variant,'frames':len(motion),'actual_neural_calls':len(traces),'loop_endpoint_world_matrix_max_error':meta['loop_endpoint_world_matrix_max_error']})
   write(OUT/'generation-summary.json',{'status':'running','model_sha256':modelhash,'results':results})
write(OUT/'generation-summary.json',{'status':'complete','model_sha256':modelhash,'precision':'FP32','wall_seconds':time.perf_counter()-started,'actual_neural_calls':sum(r['actual_neural_calls'] for r in results),'results':results})
print('MOCAP_REBUILD_COMPLETE',len(results),'neural variants',flush=True)
