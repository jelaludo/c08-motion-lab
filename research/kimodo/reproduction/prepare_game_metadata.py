"""Immutable source diagnostics used when deriving game-specific clips."""
from pathlib import Path
import hashlib,json,numpy as np
from kimodo.skeleton import SOMASkeleton77
R=Path(__file__).resolve().parents[1]
s=SOMASkeleton77();names=s.bone_order_names
out=R/'game-derived';out.mkdir(exist_ok=True)
records={}
for p in [p for rnd in ['game','game-directionfix','game-jumpfix','game-jumpanchors'] for p in sorted((R/'outputs'/rnd).glob('*/report.json'))]:
 r=json.loads(p.read_text());raw=p.parent/'motion.npz'
 assert hashlib.sha256(raw.read_bytes()).hexdigest()==r['motion_sha256']
 d=np.load(raw);xyz=d['posed_joints'];root=d['root_positions'];n=len(root)
 feet=[xyz[:,names.index(side+'Foot'),1] for side in ['Left','Right']]
 sole=np.minimum(*feet);ground=float(np.quantile(sole,.05))
 airborne=sole>ground+.09;peak=int(np.argmax(sole));a=peak;b=peak
 while a>0 and airborne[a-1]:a-=1
 while b<n-1 and airborne[b+1]:b+=1
 phases=None
 if r['case']['kind']=='jump':
  valid=bool(airborne[peak] and b-a>=5)
  if not valid:a=max(5,peak-10);b=min(n-6,peak+10)
  start=max(0,a-11);end=min(n-1,b+22)
  phases=dict(valid_airborne_detection=valid,source_start_frame=start,source_end_frame=end,
    takeoff_s=(a-start)/30,apex_s=(peak-start)/30,landing_s=(b-start)/30,
    source_airtime_s=(b-a)/30,source_height_rise_m=float(root[peak,1]-min(root[a,1],root[b,1])))
 records[p.parent.name]=dict(case=r['case'],seed=r['seed'],source_sha256=r['motion_sha256'],
  frames=n,source_net_speed_m_s=float(np.linalg.norm(root[-1,[0,2]]-root[0,[0,2]])/((n-1)/30)),
  source_contacts=d['foot_contacts'].astype(float).round(3).tolist(),jump=phases,source_round=p.parent.parent.name)
(out/'source-metadata.json').write_text(json.dumps(records),encoding='utf-8')
print('Prepared source diagnostics:',len(records))
