"""Check floor-zone readout measurements against every revised speed episode."""
from pathlib import Path
import gzip,json,math
base=Path(__file__).resolve().parents[2]
site=base/'public/c08-motion-lab/docs/reactive'
if not site.exists():site=base/'docs/reactive'
catalog=json.loads((site/'catalog.json').read_text(encoding='utf8'));rows=[]
for case in catalog['cases']:
 if case['scenario']!='speedzones':continue
 ep=json.loads(gzip.decompress((site/case['episode']).read_bytes()));p=ep['played_root_path'];zones=[]
 speeds=[math.hypot(b[0]-a[0],b[1]-a[1])*ep['sample_rate'] for a,b in zip(p,p[1:])]
 for zone in ep['environment']['speed_zones']:
  samples=[v for point,v in zip(p,speeds) if zone['x_min']<=point[0]<zone['x_max']]
  assert samples,'Requested speed zone was not reached'
  zones.append({'color':zone['color'],'requested_m_s':zone['desired_speed'],'samples':len(samples),'mean_m_s':sum(samples)/len(samples),'peak_m_s':max(samples)})
 assert len(zones)==2 and zones[0]['color']=='#e69b42' and zones[1]['color']=='#d9554a'
 assert zones[0]['requested_m_s']==2.4 and zones[1]['requested_m_s']==3.3
 assert zones[1]['mean_m_s']>zones[0]['mean_m_s']+.25
 rows.append({'id':case['id'],'zones':zones})
assert len(rows)==20
report={'status':'passed','version':catalog['version'],'scope':'All20speed-zone cases: native played-root readouts, ordered orange2.4/red3.3 targets; each actual red-zone mean exceeds orange by>0.25m/s. This does not score whole-body gait realism.','cases':rows}
folder=base/'logs' if (base/'logs').exists() else base/'research';folder.mkdir(exist_ok=True)
(folder/'reactive-round4-speed-readouts.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'status':'passed','cases':len(rows),'orange_mean_range':[min(r['zones'][0]['mean_m_s'] for r in rows),max(r['zones'][0]['mean_m_s'] for r in rows)],'red_mean_range':[min(r['zones'][1]['mean_m_s'] for r in rows),max(r['zones'][1]['mean_m_s'] for r in rows)]}))
