from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,subprocess,json,time
ROOT=Path(__file__).resolve().parents[1];BLENDER='G:/Dev/MotionBricks/tools/blender-4.5.15-windows-x64/blender.exe'
p=argparse.ArgumentParser();p.add_argument('--prefix',default='');p.add_argument('--bodies',nargs='+',default=['c08','brek43','eva-k7','meshy-fighter']);args=p.parse_args()
jobs=[(p.name,b) for p in sorted((ROOT/'retarget-source').iterdir()) if p.is_dir() and p.name.startswith(args.prefix) for b in args.bodies]
def run(job):
 name,body=job;folder=ROOT/'retarget'/name/body
 if (folder/'retarget-report.json').exists() and (folder/'c08-mocap.glb').exists():
  previous=json.loads((folder/'retarget-report.json').read_text());source=json.loads((ROOT/'retarget-source'/name/'source-metadata.json').read_text())
  if previous.get('retarget_recipe')==2 and previous.get('source_motion_sha256')==source['source_motion_sha256']:return {'take':name,'body':body,'status':'cached'}
 start=time.perf_counter()
 with (ROOT/'logs'/f'bake-{name}-{body}.log').open('w',encoding='utf-8') as log:
  result=subprocess.run([BLENDER,'--background','--python-exit-code','1','--python',str(ROOT/'tools/retarget_bipeds.py'),'--',name,'--body',body],stdout=log,stderr=subprocess.STDOUT)
 if result.returncode or not (folder/'retarget-report.json').exists():raise RuntimeError('Bake failed: '+name+'/'+body)
 print('BAKED',name,body,flush=True);return {'take':name,'body':body,'status':'baked','elapsed_s':time.perf_counter()-start}
with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,jobs))
(ROOT/'logs'/('game-bakes.json' if args.prefix.startswith('game') else 'biped-bakes.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')
print(f'All{len(jobs)} biped bakes complete',flush=True)
