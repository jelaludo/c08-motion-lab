"""Validate paired neural rollouts, publish derived takes and summarize measured outcomes."""
from pathlib import Path
import json,shutil,csv,time,numpy as np
from mb_predictive_finalize import finalize_case
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/reactive-round2';PUBLIC=ROOT/'public/c08-motion-lab/docs/reactive';catalog=json.loads((OUT/'catalog.json').read_text())
ordered=sorted(catalog['cases'],key=lambda c:(not (OUT/c['id']/'retarget-report.json').exists(),c['id']))
for case in ordered:
 folder=OUT/case['id']
 deadline=time.monotonic()+7200
 while not (folder/'retarget-report.json').exists():
  if time.monotonic()>deadline:raise RuntimeError('Timed out waiting for completed retarget: '+str(folder))
  time.sleep(.5)
 dest=PUBLIC/'takes'/case['id'];trace=finalize_case(folder,dest);episode=json.loads((folder/'episode.json').read_text());episode['display']={k:trace[k] for k in ['display_scale','display_basis','display_origin','display_pelvis_offset']};(dest/'episode.json').write_text(json.dumps(episode,separators=(',',':')),encoding='utf8');shutil.copy2(folder/'g1-motion.npz',dest/'native-g1-motion.npz');shutil.copy2(folder/'unmodified-predictions.npz',dest/'unmodified-predictions.npz')
 with (dest/'root-trajectory.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow(['time_s','g1_x_m','g1_y_m','g1_z_m','cat_x_m','cat_y_m']);w.writerows([i/30,*p,*episode['environment']['cat_path'][i]] for i,p in enumerate(episode['raw_root_path']))
 for name in ['prediction-trace.json','g1-motion.json']:
  path=dest/name;value=json.loads(path.read_text(encoding='utf8'));path.write_text(json.dumps(value,separators=(',',':'),allow_nan=False),encoding='utf8')
 case.update(glb=f'takes/{case["id"]}/c08-motionbricks-test.glb',episode=f'takes/{case["id"]}/episode.json',preview=f'takes/{case["id"]}/g1-preview.json',validation=f'takes/{case["id"]}/validation-report.json');print('REACTIVE_VALIDATED',case['id'],flush=True)
catalog.update(description='40 expanded actual closed-loop neural rollouts, 24-40 seconds each, in a 36 by 14 metre course with ten obstacles. Both conditions use an external continuous swept root-circle collision/slide controller; reactive conditions also plan routes and update moving targets. Corrected displayed history feeds subsequent predictions. Full-avatar limb collision/dynamics are not solved.',sample_rate=30,neural_calls=sum(c['metrics']['neural_calls'] for c in catalog['cases']),summaries=[])
for scenario in ['slalom','speedzones','pursuit','mixed']:
 for condition in ['baseline','reactive']:
  rows=[c['metrics'] for c in catalog['cases'] if c['scenario']==scenario and c['condition']==condition];catalog['summaries'].append({'scenario':scenario,'condition':condition,'runs':len(rows),'mean_collision_frames':float(np.mean([r['root_proxy_collision_frames'] for r in rows])),'mean_attempted_contact_frames':float(np.mean([r['attempted_contact_frames'] for r in rows])),'mean_controller_correction_total_m':float(np.mean([r['controller_correction_total_m'] for r in rows])),'mean_speed_m_s':float(np.mean([r['mean_speed_m_s'] for r in rows])),'mean_jerk_p95_m_s3':float(np.mean([r['root_jerk_p95_m_s3'] for r in rows])),'mean_goal_distance_m':float(np.mean([r['final_goal_distance_m'] for r in rows]))})
(PUBLIC/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf8');(ROOT/'public/c08-motion-lab/research/reactive-round2-results.json').write_text(json.dumps(catalog,indent=2),encoding='utf8');print('REACTIVE_FINALIZED',len(catalog['cases']),catalog['neural_calls'],flush=True)
