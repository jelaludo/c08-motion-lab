"""Combine independent mesh audits only after matching every final public artifact."""
from pathlib import Path
import argparse,json,gzip,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--c08',nargs='+',required=True);parser.add_argument('--brek',nargs='+',required=True);parser.add_argument('--public',type=Path,default=ROOT/'public/c08-motion-lab/docs/reactive');parser.add_argument('--report',type=Path,default=ROOT/'public/c08-motion-lab/research/reactive-round3-fullskin-validation.json');args=parser.parse_args()
catalog=json.loads((args.public/'catalog.json').read_text(encoding='utf8'));expected={c['id']for c in catalog['cases']};assert len(expected)==120
all_results={};body_stats={}
for body,files in [('c08',args.c08),('brek',args.brek)]:
 results=[]
 for filename in files:
  report=json.loads(Path(filename).read_text(encoding='utf8'));assert report['status']=='passed',filename;assert report.get('body',body)==body
  results.extend(report['results'])
 assert len(results)==120 and {r['id']for r in results}==expected,(body,'incomplete or duplicate case coverage')
 for row in results:
  assert row['triangle_obstacle_intersections']==0,row['id']
  assert row['sampling_hz']==(120 if body=='c08' else 30),row['id']
  case=next(c for c in catalog['cases']if c['id']==row['id']);path=args.public/case['glb' if body=='c08' else 'preview'];data=path.read_bytes();data=gzip.decompress(data)if path.suffix=='.gz'else data
  assert hashlib.sha256(data).hexdigest()==row['artifact_sha256'],(body,row['id'],'audited input differs from published artifact')
 crossings=[p for r in results for p in r['interaction_clearance']if p['root_crossed']]
 assert len(crossings)==30 and sum(p['kind']=='hurdle'for p in crossings)==20 and sum(p['kind']=='overhead'for p in crossings)==10
 assert all(p['mesh_over_footprint_frames']>0 and p['minimum_actual_mesh_vertical_clearance_native_m']>=0 for p in crossings)
 all_results[body]=results
 body_stats[body]={'cases':len(results),'sampling_hz':120 if body=='c08'else 30,'frames':sum(r['frames']for r in results),'triangle_obstacle_intersections':0,'hurdle_crossings':20,'crouch_bar_crossings':10,'minimum_hurdle_clearance_native_m':min(p['minimum_actual_mesh_vertical_clearance_native_m']for p in crossings if p['kind']=='hurdle'),'minimum_crouch_clearance_native_m':min(p['minimum_actual_mesh_vertical_clearance_native_m']for p in crossings if p['kind']=='overhead')}
report={'status':'passed','catalog_version':catalog['version'],'generated_utc':datetime.now(timezone.utc).isoformat(),'take_body_combinations':240,'bodies':body_stats,'checks':['Every final C08 GLB and decoded B-REK preview matches its independently audited SHA-256','Every displayed C08 pose at 120 Hz and B-REK43 pose at 30 Hz','Exact triangles versus height-clipped pillar cylinders or native oriented interaction boxes','Full rigid-skin bone bounds screen distant obstacles','Actual mesh footprint overlaps each crossed hurdle/bar and records vertical clearance','20 hurdle and 10 crouch-bar crossings per body; controls remain before the interaction obstacles'],'limitations':['Sampled mesh validation, not continuous articulated dynamics','Root/cat continuous swept proxies are audited separately','Armor self-collision, dynamic balance and actor/cat mutual collision are not solved','Crouch bar geometry is calibrated separately for each body'],'runtime_brek_adapter_sha256':hashlib.sha256((args.public/'brek.js').read_bytes()).hexdigest(),'mesh_validator_sha256':hashlib.sha256((ROOT/'tools/review/validate-reactive-armor.mjs').read_bytes()).hexdigest(),'results':all_results}
args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({'status':'passed','bodies':body_stats}))
