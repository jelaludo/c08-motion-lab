"""Four additional real 6 m/s sprint predictions, using the exact cached prompt."""
from pathlib import Path
import hashlib,json,time,os
import numpy as np
import torch
from kimodo import load_model
from kimodo.constraints import load_constraints_lst
from kimodo.tools import seed_everything
from kimodo.exports.motion_io import save_kimodo_npz
R=Path(os.environ['KIMODO_WORKSPACE'])
base=json.loads((R/'outputs/game/game-sprint-forward-seed411/report.json').read_text())
case=base['case'];prompt=case['prompt']
key=hashlib.sha256(('kimodo-soma-rp-v1.2|LLM2VecEncoder|'+prompt).encode()).hexdigest()
embedding=np.load(R/'cache/embeddings/kimodo-soma-rp-v1.2'/f'{key}.npy')
class CachedOnlyEncoder:
 def __call__(self,texts):
  assert all(t==prompt for t in texts)
  return torch.tensor(np.stack([embedding for _ in texts])),[len(embedding)]*len(texts)
 def to(self,*args,**kwargs):return self
free,total=torch.cuda.mem_get_info();assert free>5*2**30
torch.cuda.set_per_process_memory_fraction(min(4*2**30,free-2*2**30)/total)
model=load_model('Kimodo-SOMA-RP-v1.2',device='cuda:0',text_encoder=CachedOnlyEncoder())
folder=R/'outputs/game-variants';folder.mkdir(exist_ok=True)
constraint=folder/'sprint-root2d.json';constraint.write_text(json.dumps(base['constraints']),encoding='utf-8')
constraints=load_constraints_lst(str(constraint),model.skeleton)
for seed in [1233,1644,2055,2466]:
 out=folder/f'game-sprint-forward-seed{seed}';out.mkdir(exist_ok=True)
 if (out/'report.json').exists():print('CACHED',out.name,flush=True);continue
 seed_everything(seed);start=time.perf_counter()
 with torch.inference_mode():output=model([prompt],[180],constraint_lst=constraints,num_denoising_steps=100,num_samples=1,multi_prompt=True,post_processing=True,return_numpy=True,progress_bar=lambda x,**kw:x)
 single={k:v[0] if hasattr(v,'shape') and len(v.shape)>0 and v.shape[0]==1 else v for k,v in output.items()}
 assert all(np.isfinite(single[k]).all() for k in ['posed_joints','root_positions','local_rot_mats'])
 save_kimodo_npz(str(out/'motion.npz'),single)
 report={**{k:base[k] for k in ['case','model','model_revision','upstream_commit','constraints']},'seed':seed,'duration_s':6,'elapsed_s':time.perf_counter()-start,'motion_sha256':hashlib.sha256((out/'motion.npz').read_bytes()).hexdigest(),'postprocessing':True,'cached_prompt_embedding':True,'peak_gpu_allocated_gib':torch.cuda.max_memory_allocated()/2**30,'scope':'New 6 m/s text/root-conditioned sprint candidate; visual foot slip and style acceptance remains necessary.'}
 (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8',newline='\n');print('GENERATED',out.name,flush=True)
