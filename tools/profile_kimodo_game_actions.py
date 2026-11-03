"""Locate useful source windows; keep all original motion files untouched."""
from pathlib import Path
import argparse
import hashlib,json,numpy as np
from kimodo.skeleton import SOMASkeleton77
parser=argparse.ArgumentParser();parser.add_argument('--kimodo-root',type=Path,required=True);R=parser.parse_args().kimodo_root;names=SOMASkeleton77().bone_order_names
meta=json.loads((R/'game-derived/source-metadata.json').read_text());profiles={}
durations={'game-jab':.32,'game-cross':.38,'game-kick':.48,'game-block':.30,'game-vault':.85,'game-mantle':1.18,'game-pickup':.65,'game-putdown':.60,'game-panel':.45,'game-sit':.55,'game-stand-seat':.45}
for take,m in meta.items():
 id=m['case']['id']
 if id.startswith('game-dodge-'):duration=.32
 elif id in durations:duration=durations[id]
 else:continue
 d=np.load(R/'outputs'/m['source_round']/take/'motion.npz');xyz=d['posed_joints'];root=d['root_positions'];n=len(xyz)
 hips=xyz[:,names.index('Hips')];chest=xyz[:,names.index('Chest')]
 if id in ['game-jab','game-cross','game-block']:
  hand=xyz[:,names.index('LeftHand' if id=='game-jab' else 'RightHand')]-chest
  signal=hand[:,2] if id!='game-block' else hand[:,1]
 elif id=='game-kick':signal=np.maximum(xyz[:,names.index('LeftFoot'),2]-hips[:,2],xyz[:,names.index('RightFoot'),2]-hips[:,2])
 elif id.startswith('game-dodge-'):signal=np.r_[0,np.linalg.norm(np.diff(root[:,[0,2]],axis=0),axis=1)]
 elif id in ['game-pickup','game-putdown','game-sit']:signal=-root[:,1]
 elif id=='game-stand-seat':signal=np.r_[0,np.diff(root[:,1])]
 elif id=='game-panel':signal=(xyz[:,names.index('RightHand')]-chest)[:,2]
 else:signal=root[:,1]
 lo=3;hi=n-4;peak=int(np.argmax(signal[lo:hi])+lo)
 if id in ['game-jab','game-cross','game-kick']:
  threshold=float(np.quantile(signal[lo:hi],.92));candidates=[i for i in range(lo+1,hi-1) if signal[i]>=threshold and signal[i]>=signal[i-1] and signal[i]>=signal[i+1]]
  if candidates:peak=candidates[0]
 before,after=(8,12) if id.startswith('game-dodge-') or id in ['game-jab','game-cross'] else (18,24)
 start=max(0,peak-before);end=min(n-1,peak+after)
 if id=='game-mantle':
  rising=np.flatnonzero(root[:peak,1]>root[0,1]+.12)
  start=max(0,int(rising[0])-12) if len(rising) else max(0,peak-60)
  end=min(n-1,peak+10)
 for body in ['c08','brek43']:
  file=R/'web/kimodo-game/clips'/f'{take}-{body}.json'
  profiles[f'{take}:{body}']={'start':start/30,'end':end/30,'peak':peak/30,'duration':duration,'clip_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
out={'schema':'responsive-action-windows/1','recipe':1,'scope':'Source motion is unchanged. Controller samples these diagnostic active windows at authored game durations. These windows are candidates, not combat-technique or physical-contact certification.','profiles':profiles}
(R/'tools/game/action-profiles.json').write_text(json.dumps(out,indent=2),encoding='utf-8',newline='\n')
print('Profiled',len(profiles),'body/take windows')
for k,v in profiles.items():
 if k.endswith('seed411:c08'):print(k,{x:v[x] for x in ['start','peak','end','duration']})
