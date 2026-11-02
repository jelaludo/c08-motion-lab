"""Run one real smoke take, or the defined 15-take pilot. Requires env.ps1 first."""
from pathlib import Path
import argparse,hashlib,json,time,os
from preflight import check
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--all',action='store_true');p.add_argument('--plan',default='tests.json');p.add_argument('--round',default='pilot');p.add_argument('--resume',action='store_true');args=p.parse_args()
if not args.round.replace('-','').isalnum():raise SystemExit('Invalid round folder')
readiness=check()
if not readiness['ready_for_gpu_pilot']:
 print(json.dumps(readiness,indent=2));raise SystemExit('Not ready: complete local HF login/access and free at least 4 GiB GPU memory. No inference was attempted.')
import numpy as np,torch
from kimodo import load_model
from kimodo.tools import seed_everything
from kimodo.exports.motion_io import save_kimodo_npz
plan=json.loads((ROOT/args.plan).read_text());cases=plan['cases'] if args.all else plan['cases'][:1];seeds=plan['seeds'] if args.all else plan['seeds'][:1];default_duration=plan['duration_s'] if args.all else 2
model=load_model(plan['model'],device='cuda:0');results=[]
from kimodo.demo.embedding_cache import CachedTextEncoder
model.text_encoder=CachedTextEncoder(model.text_encoder,model_name='kimodo-soma-rp-v1.2',base_dir=str(ROOT/'cache/embeddings'))
for case in cases:
 duration=case.get('duration_s',default_duration) if args.all else 2
 for seed in seeds:
  folder=ROOT/'outputs'/(args.round if args.all else 'smoke')/f"{case['id']}-seed{seed}";folder.mkdir(parents=True,exist_ok=True)
  if (folder/'report.json').exists():
   if not args.resume:raise SystemExit(f'Refusing to overwrite completed take: {folder}')
   previous=json.loads((folder/'report.json').read_text())
   assert previous['case']==case and previous['seed']==seed and previous['motion_sha256']==hashlib.sha256((folder/'motion.npz').read_bytes()).hexdigest(),'Resume identity/hash mismatch'
   results.append(previous);print('CACHED',folder.name,flush=True);continue
  seed_everything(seed);start=time.perf_counter()
  constraint_specs=[];constraint_lst=[]
  if 'constraint_file' in case:
   from kimodo.constraints import load_constraints_lst
   constraint_specs=json.loads((ROOT/case['constraint_file']).read_text())
   constraint_path=folder/'constraints.json';constraint_path.write_text(json.dumps(constraint_specs),encoding='utf-8')
   constraint_lst=load_constraints_lst(str(constraint_path),model.skeleton)
  if 'speed_m_s' in case or 'velocity_m_s' in case:
   from kimodo.constraints import load_constraints_lst
   frames=int(duration*model.fps)
   velocity=case.get('velocity_m_s',[0.0,case.get('speed_m_s',0.0)])
   constraint_specs=[{'type':'root2d','frame_indices':list(range(frames)),'smooth_root_2d':[[velocity[0]*i/model.fps,velocity[1]*i/model.fps] for i in range(frames)]}]
   constraint_path=folder/'constraints.json';constraint_path.write_text(json.dumps(constraint_specs),encoding='utf-8')
   constraint_lst=load_constraints_lst(str(constraint_path),model.skeleton)
  with torch.inference_mode():output=model([case['prompt']],[int(duration*model.fps)],constraint_lst=constraint_lst,num_denoising_steps=100,num_samples=1,multi_prompt=True,post_processing=True,return_numpy=True)
  single={k:v[0] if hasattr(v,'shape') and len(v.shape)>0 and v.shape[0]==1 else v for k,v in output.items()}
  for key in ['posed_joints','local_rot_mats','root_positions']:
   if key not in single or not np.isfinite(single[key]).all():raise RuntimeError('Missing/nonfinite motion: '+key)
  target=folder/'motion.npz';save_kimodo_npz(str(target),single)
  report={'case':case,'seed':seed,'duration_s':duration,'model':plan['model'],'upstream_commit':readiness['upstream_commit'],'model_revision':'0e3c89024d896064b6851201373f7834784a386b','elapsed_s':time.perf_counter()-start,'postprocessing':True,'constraints':[],'motion_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'shapes':{k:list(v.shape) for k,v in single.items() if hasattr(v,'shape')},'scope':'Real text-conditioned generation; finite arrays do not establish foot contact, balance or visual quality.'}
  report['text_encoder_device']=os.environ.get('TEXT_ENCODER_DEVICE')
  report['constraints']=constraint_specs
  report['torch_version']=torch.__version__
  (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');results.append(report);print('GENERATED',folder.name,flush=True)
(ROOT/'logs'/f'{args.round}-{Path(args.plan).stem}-summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
