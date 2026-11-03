"""Generate lateral judo/skate-style breakfalls, three seeds for each side."""
from pathlib import Path
import hashlib,json,time,os,gc
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from kimodo import load_model
from kimodo.constraints import load_constraints_lst
from kimodo.demo.embedding_cache import CachedTextEncoder
from kimodo.tools import seed_everything
from kimodo.exports.motion_io import save_kimodo_npz
R=Path(os.environ['KIMODO_WORKSPACE'])
os.environ['TEXT_ENCODER_DEVICE']='cpu'
free,total=torch.cuda.mem_get_info();assert free>5*2**30
torch.cuda.set_per_process_memory_fraction(min(4*2**30,free-2*2**30)/total)
torch.set_num_threads(min(12,os.cpu_count() or 4))
print('Loading Kimodo with CPU text encoder; existing processes left running.',flush=True)
model=load_model('Kimodo-SOMA-RP-v1.2',device='cuda:0')
model.text_encoder=CachedTextEncoder(model.text_encoder,model_name='kimodo-soma-rp-v1.2',base_dir=str(R/'cache/embeddings'))
idle=np.load(R/'outputs/game/game-idle-seed411/motion.npz');neutral=idle['local_rot_mats'][0];height=float(idle['root_positions'][0,1]);rot=Rotation.from_matrix(neutral).as_rotvec().tolist()
for side,sign in [('left',1),('right',-1)]:
 for seed,style in [(4411,'judo'),(5522,'judo'),(6633,'skateboard')]:
  prompt=(f'A person standing upright loses balance and falls sideways to the {side}. They tuck their chin, bend their knees, land softly on their {side} side and shoulder, roll smoothly across their upper back in a judo side breakfall, then get back up to a relaxed standing posture.' if style=='judo' else f'A person trips sideways to the {side} like a skateboarder falling off a board. They crouch and tuck, fall onto their {side} shoulder and side, curl into a sideways shoulder roll across their back to absorb the fall, then smoothly stand up again.')
  case=dict(id='game-ukemi-side-'+side,label='Ukemi / side '+side,group='ground',kind='action',duration_s=5,prompt=prompt,style=style)
  folder=R/'outputs/game-side-ukemi'/f"{case['id']}-seed{seed}";folder.mkdir(parents=True,exist_ok=True)
  if (folder/'report.json').exists():print('CACHED',folder.name,flush=True);continue
  spec=[dict(type='fullbody',frame_indices=[0,137,149],local_joints_rot=[rot,rot,rot],root_positions=[[0,height,0],[sign*1.8,height,0],[sign*1.8,height,0]])]
  constraints=folder/'constraints.json';constraints.write_text(json.dumps(spec),encoding='utf-8',newline='\n');lst=load_constraints_lst(str(constraints),model.skeleton)
  seed_everything(seed);start=time.perf_counter()
  with torch.inference_mode():output=model([prompt],[150],constraint_lst=lst,num_denoising_steps=100,num_samples=1,multi_prompt=True,post_processing=True,return_numpy=True)
  single={k:v[0] if hasattr(v,'shape') and len(v.shape)>0 and v.shape[0]==1 else v for k,v in output.items()}
  assert all(np.isfinite(single[k]).all() for k in ['posed_joints','root_positions','local_rot_mats'])
  save_kimodo_npz(str(folder/'motion.npz'),single)
  root=single['root_positions'];names=model.output_skeleton.bone_order_names;xyz=single['posed_joints'];head=xyz[:,names.index('Head')];rotation=single['global_rot_mats'][:,0];up=rotation[:,:,1]
  report=dict(case=case,seed=seed,duration_s=5,model='Kimodo-SOMA-RP-v1.2',model_revision='0e3c89024d896064b6851201373f7834784a386b',upstream_commit='e1c219c99b4b94ba48be1fb6a1cbc64ecee4c954',motion_sha256=hashlib.sha256((folder/'motion.npz').read_bytes()).hexdigest(),elapsed_s=time.perf_counter()-start,conditioning=dict(kind='Text-conditioned lateral breakfall with native idle start/end keyframes',frame_indices=[0,137,149],lateral_destination_m=sign*1.8,constraint_sha256=hashlib.sha256(constraints.read_bytes()).hexdigest()),diagnostics=dict(min_hip_y_m=float(root[:,1].min()),min_head_y_m=float(head[:,1].min()),max_lateral_tilt=float(np.abs(up[:,0]).max()),min_up_y=float(up[:,1].min()),lateral_displacement_m=float(root[-1,0]-root[0,0]),peak_torch_gpu_allocated_gib=torch.cuda.max_memory_allocated()/2**30),scope='New Kimodo-generated lateral judo/skate-style candidate. Endpoint constraints do not establish side-fall technique, ground contact or final visual acceptance.')
  (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8',newline='\n');print('GENERATED',folder.name,json.dumps(report['diagnostics']),flush=True)
