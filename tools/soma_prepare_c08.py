"""Evaluate exact public SOMA transforms for direct C08 retargeting, without standing IK."""
from pathlib import Path
import argparse, json, os, hashlib
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('names',nargs='*',default=['ukemi']);args=parser.parse_args()
os.environ['WARP_CACHE_PATH']=str(ROOT/'video-mocap/cache/warp')
from gem.motion.geometry import MotionGeometry
geometry=MotionGeometry(ROOT/'video-mocap/gem-x/assets/soma',device='cpu',chunk_size=16,apply_correctives=False)
for name in args.names:
 source=ROOT/'video-mocap'/name
 if not (source/'soma-motion.npz').exists():print('NOT_READY',name,flush=True);continue
 data=np.load(source/'soma-motion.npz');out=ROOT/'video-mocap/c08-retarget'/name;out.mkdir(parents=True,exist_ok=True)
 transforms=[]
 with torch.inference_mode():
  for start in range(0,len(data['timestamps']),16):
   stop=start+16
   values={key:torch.from_numpy(data[field][start:stop].copy()).float() for key,field in [('body_pose','body_pose_axis_angle'),('global_orient','root_axis_angle'),('transl','root_translation'),('identity_coeffs','identity_coeffs'),('scale_params','scale_params')]}
   output=geometry.body_model(**values,pose2rot=True,apply_correctives=False,return_joints_only=True,repose_to_bind_pose=True)
   transforms.append(output['transforms'].cpu().numpy())
  reference_output=geometry.body_model(body_pose=torch.zeros((1,228)),global_orient=torch.zeros((1,3)),transl=torch.zeros((1,3)),identity_coeffs=torch.from_numpy(np.median(data['identity_coeffs'],axis=0)[None].copy()).float(),scale_params=torch.from_numpy(np.median(data['scale_params'],axis=0)[None].copy()).float(),pose2rot=True,apply_correctives=False,return_joints_only=False,repose_to_bind_pose=True)
  ref=reference_output['transforms'].cpu().numpy()[0]
  refvertices=reference_output['vertices'].cpu().numpy()[0]
 runtime=geometry.body_model.runtime;names=list(runtime.public_joint_names);parents=runtime.public_joint_parent_ids.cpu().numpy().astype(int)
 world=np.concatenate(transforms)
 if names[0]=='Root':world=world[:,1:];ref=ref[1:];names=names[1:];parents=parents[1:]-1
 assert names==data['joint_names'].tolist()
 error=float(np.linalg.norm(world[:,:,:3,3]-data['joints_world'],axis=-1).max())
 assert error<2e-4,('SOMA transform/joint mismatch',error)
 np.savez_compressed(out/'soma-frames.npz',world_transforms=world,reference_transforms=ref,reference_surface_bounds=np.stack([refvertices.min(axis=0),refvertices.max(axis=0)]),joint_names=np.array(names),parent_indices=parents,timestamps=data['timestamps'],surface_bounds_world=data['surface_bounds_world'])
 meta={'id':'mocap_'+name.replace('-','_'),'source_motion_sha256':hashlib.sha256((source/'soma-motion.npz').read_bytes()).hexdigest(),'provenance_type':'video_mocap','pipeline':'User-provided reference video -> GEM-X native SOMA recovery -> direct C08 retarget; no MotionBricks generation','source_space':'SOMA world, +Y up, metres; source translation applied exactly once','frames':len(world),'sample_rate':30,'duration_s':float(data['timestamps'][-1]),'source_joint_count':len(names),'transform_to_saved_joint_max_error_m':error,'source_file_id':name,'reference_note':'Median recovered identity/scale, zero public rotations and zero translation; exact matching SOMA 0.3.3 runtime with procedural conventions','limitations':['Monocular recovery estimates occluded limbs and depth','Direct experimental adaptation; not a physical/contact solve','Original video and source frames remain local']}
 (out/'source-metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
 print('SOMA_FRAMES_READY',name,len(world),'error',error,'hips ref',ref[0,:3,3],'ground',data['surface_bounds_world'][:,0,1].min(),'hips0',world[0,0,:3,3],flush=True)
