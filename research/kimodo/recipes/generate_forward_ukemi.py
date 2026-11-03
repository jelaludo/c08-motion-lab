"""Generate new forward-roll candidates from the creator's own capture anchors.

Reuses an exact, already cached prompt embedding. No second Llama encoder is
loaded, no video is uploaded and existing generated/retargeted takes are untouched.
"""
from pathlib import Path
import hashlib,json,os,time
import numpy as np
from scipy.spatial.transform import Rotation as Rotation
import torch
from kimodo import load_model
from kimodo.constraints import load_constraints_lst
from kimodo.tools import seed_everything
from kimodo.exports.motion_io import save_kimodo_npz

ROOT=Path(os.environ['KIMODO_WORKSPACE'])
source=Path(os.environ['OWNED_UKEMI_SOMA_NPZ'])
prompt=next(c['prompt'] for c in json.loads((ROOT/'tests-round2.json').read_text())['cases'] if c['id']=='r2-ukemi-forward')
key=hashlib.sha256(('kimodo-soma-rp-v1.2|LLM2VecEncoder|'+prompt).encode()).hexdigest()
cached=ROOT/'cache/embeddings/kimodo-soma-rp-v1.2'/f'{key}.npy'
assert cached.exists(),'Required exact prompt embedding is not cached'
embedding=np.load(cached)
class CachedOnlyEncoder:
 def __call__(self,texts):
  assert all(t==prompt for t in texts),'Refusing to substitute a different prompt embedding'
  return torch.tensor(np.stack([embedding for _ in texts])),[len(embedding)]*len(texts)
 def to(self,*args,**kwargs):return self

free,total=torch.cuda.mem_get_info();assert free>5*2**30,'Wait for more free GPU memory; no other processes are stopped'
torch.cuda.set_per_process_memory_fraction(min(4*2**30,free-2*2**30)/total)
model=load_model('Kimodo-SOMA-RP-v1.2',device='cuda:0',text_encoder=CachedOnlyEncoder())
d=np.load(source);names=d['joint_names'].tolist();parents=d['parent_indices'];world=d['world_transforms'];ref=d['reference_transforms']
assert names==model.output_skeleton.bone_order_names
# GEM-X's neutral bone frames differ from Kimodo's identity global rotations.
# Remove each reference frame before converting global deltas to local rotations.
global_delta=world[:,:,:3,:3]@np.swapaxes(ref[None,:,:3,:3],-1,-2)
local=global_delta.copy()
for j,p in enumerate(parents):
 if p>=0:local[:,j]=np.swapaxes(global_delta[:,p],-1,-2)@global_delta[:,j]
idle=np.load(ROOT/'outputs/game/game-idle-seed411/motion.npz')
source_frames=[0,34,54,62,70,78,86,94,110]
target_frames=[0,12,28,38,48,58,68,78,95]
rots=[];roots=[];origin=world[0,0,:3,3]
for i,f in enumerate(source_frames):
 r=local[f].copy();root=world[f,0,:3,3].copy();root[[0,2]]-=origin[[0,2]];root[0]=0
 # Forward progression comes from the owned forward recording, not reversal
 # of the earlier backward take. Lower the conditioning supports to joint floor.
 root[1]+=max(-.30,min(.10,.045-float(world[f,:,1,3].min())))
 if i==0:r=idle['local_rot_mats'][0].copy();root=np.array([0,float(idle['root_positions'][0,1]),0])
 rots.append(Rotation.from_matrix(r).as_rotvec().tolist());roots.append(root.tolist())
for f in [119,134]:
 target_frames.append(f);rots.append(Rotation.from_matrix(idle['local_rot_mats'][0]).as_rotvec().tolist());roots.append([0,float(idle['root_positions'][0,1]),float(roots[-1][2])])
spec=[dict(type='fullbody',frame_indices=target_frames,local_joints_rot=rots,root_positions=roots)]
constraint_dir=ROOT/'game-derived/ukemi-constraints';constraint_dir.mkdir(exist_ok=True)
constraint_path=constraint_dir/'forward-owned-capture.json';constraint_path.write_text(json.dumps(spec),encoding='utf-8',newline='\n')
constraints=load_constraints_lst(str(constraint_path),model.skeleton)
case=dict(id='game-ukemi-forward',label='Ukemi / forward',group='ground',kind='action',duration_s=4.5,prompt=prompt)
for seed in [1101,2202,3303]:
 folder=ROOT/'outputs/game-ukemi'/f'game-ukemi-forward-seed{seed}';folder.mkdir(parents=True,exist_ok=True)
 if (folder/'report.json').exists():print('CACHED',folder.name,flush=True);continue
 seed_everything(seed);started=time.perf_counter()
 with torch.inference_mode():output=model([prompt],[135],constraint_lst=constraints,num_denoising_steps=100,num_samples=1,multi_prompt=True,post_processing=True,return_numpy=True,progress_bar=lambda x,**kw:x)
 single={k:v[0] if hasattr(v,'shape') and len(v.shape)>0 and v.shape[0]==1 else v for k,v in output.items()}
 assert all(np.isfinite(single[k]).all() for k in ['posed_joints','root_positions','local_rot_mats'])
 save_kimodo_npz(str(folder/'motion.npz'),single)
 xyz=single['posed_joints'];root=single['root_positions'];head=names.index('Head')
 report=dict(case=case,seed=seed,duration_s=4.5,model='Kimodo-SOMA-RP-v1.2',model_revision='0e3c89024d896064b6851201373f7834784a386b',upstream_commit='e1c219c99b4b94ba48be1fb6a1cbc64ecee4c954',elapsed_s=time.perf_counter()-started,motion_sha256=hashlib.sha256((folder/'motion.npz').read_bytes()).hexdigest(),conditioning=dict(kind='creator-owned forward ukemi landmarks',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_frames=source_frames,target_frames=target_frames,private_constraint_sha256=hashlib.sha256(constraint_path.read_bytes()).hexdigest(),cached_prompt_embedding=True),diagnostics=dict(forward_displacement_m=float(root[-1,2]-root[0,2]),min_head_minus_hip_m=float((xyz[:,head,1]-root[:,1]).min()),peak_gpu_allocated_gib=torch.cuda.max_memory_allocated()/2**30),scope='New Kimodo prediction from creator-owned capture anchors. Numeric direction/inversion are diagnostics, not martial-arts technique or physical contact certification.')
 (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8',newline='\n');print('GENERATED',folder.name,json.dumps(report['diagnostics']),flush=True)
