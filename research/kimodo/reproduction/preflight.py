"""Read-only readiness check. Never prints credentials or accepts gated terms."""
from pathlib import Path
import importlib,json,shutil,subprocess,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[1]
def check():
 import torch
 from huggingface_hub import get_token,snapshot_download
 report={'python':__import__('sys').version,'torch':torch.__version__,'cuda_available':torch.cuda.is_available(),'disk_free_gib':round(shutil.disk_usage(ROOT).free/2**30,2),'imports':{},'gated_model':'meta-llama/Meta-Llama-3-8B-Instruct'}
 for name in ['kimodo','motion_correction','transformers','peft']:
  try:importlib.import_module(name);report['imports'][name]='passed'
  except Exception as e:report['imports'][name]=type(e).__name__+': '+str(e)
 if torch.cuda.is_available():
  report['cuda_arithmetic_pass']=float((torch.ones(8,device='cuda')*2).sum())==16
  report['gpu']=torch.cuda.get_device_name();report['gpu_free_gib']=round(torch.cuda.mem_get_info()[0]/2**30,2)
 token=get_token();report['token_configured']=bool(token)
 request=urllib.request.Request('https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/resolve/main/config.json',headers={'Authorization':'Bearer '+token} if token else {})
 try:
  with urllib.request.urlopen(request,timeout=20) as r:report['llama_access_http']=r.status
 except urllib.error.HTTPError as e:report['llama_access_http']=e.code
 except Exception as e:report['llama_access_http']=type(e).__name__
 try:
  report['kimodo_snapshot']=snapshot_download('nvidia/Kimodo-SOMA-RP-v1.2',local_files_only=True)
  assert Path(report['kimodo_snapshot']).name=='0e3c89024d896064b6851201373f7834784a386b','Cached checkpoint revision changed'
 except Exception:report['kimodo_snapshot']=None
 report['upstream_commit']=subprocess.check_output(['git','-C',str(ROOT/'upstream'),'rev-parse','HEAD'],text=True).strip()
 report['ready_for_gpu_pilot']=all(v=='passed' for v in report['imports'].values()) and report.get('cuda_arithmetic_pass',False) and report['llama_access_http']==200 and report.get('gpu_free_gib',0)>=4 and bool(report['kimodo_snapshot'])
 return report
if __name__=='__main__':
 report=check();(ROOT/'logs').mkdir(exist_ok=True);(ROOT/'logs/preflight.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
 raise SystemExit(0 if report['ready_for_gpu_pilot'] else 2)
