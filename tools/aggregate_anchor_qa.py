"""Aggregate independent candidate measurements without turning them into visual approval."""
from pathlib import Path
import argparse,json,math,os
_roots=[Path(os.environ['MOTION_LAB_WORKSPACE'])] if os.environ.get('MOTION_LAB_WORKSPACE') else list(Path(__file__).resolve().parents)
ROOT=next((p for p in _roots if (p/'evaluation').is_dir() and (p/'assets').is_dir()),None)
if ROOT is None:raise RuntimeError('Set MOTION_LAB_WORKSPACE')
parser=argparse.ArgumentParser();parser.add_argument('slugs',nargs='*',default=['ukemi','technical-standup','gorilla-front','sumo-stomp','source-094553','h3-dance']);args=parser.parse_args()
rows=[];reference=None;default_rows=[]
for slug in args.slugs:
 report=json.loads((ROOT/'evaluation/anchored-cleanup'/slug/'independent-qa.json').read_text(encoding='utf-8'))
 assert report['structural_pass'],slug
 default=report['default_pose'];reference=reference or default
 position=0.;angle=0.
 for name,bone in default.items():
  position=max(position,math.dist(bone['root_relative_position'],reference[name]['root_relative_position']))
  q=bone['local_quaternion'];r=reference[name]['local_quaternion'];cosine=abs(sum(a*b for a,b in zip(q,r)))/math.sqrt(sum(a*a for a in q)*sum(b*b for b in r));angle=max(angle,2*math.acos(min(1,cosine)))
 default_rows.append({'id':slug,'maximum_common_default_position_difference_m':position,'maximum_common_default_rotation_difference_rad':angle})
 rows.append({k:v for k,v in report.items() if k not in ['default_pose','gltf_messages']})
common=all(r['maximum_common_default_position_difference_m']<1e-5 and r['maximum_common_default_rotation_difference_rad']<1e-5 for r in default_rows)
summary={'status':'artifact_integrity_passed_visual_review_required','candidates':len(rows),'gltf_errors':sum(r['gltf_errors'] for r in rows),'gltf_warnings':sum(r['gltf_warnings'] for r in rows),'max_exported_joint_position_error_m':max(r['max_exported_joint_position_error_m'] for r in rows),'common_full_skeleton_default_pass':common,'common_default_comparison':default_rows,'root_displacement_is_not_a_loop_failure':True,'scope':'Original source timing retained over declared used ranges; root displacement is deliberate. Foot support is measured only in trusted core intervals. No sensor ground truth, physical balance or visual acceptance is claimed.','results':rows}
dest=ROOT/'evaluation/anchored-cleanup/independent-summary.json';dest.write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ['results','common_default_comparison']},indent=2))
if not common:raise SystemExit('Shared default pose mismatch')
