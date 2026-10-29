"""Validate round-three neural takes and publish compact game/review artifacts."""
from pathlib import Path
import json,shutil,csv,time,gzip,hashlib,concurrent.futures,numpy as np
from mb_predictive_finalize import finalize_case
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/reactive-round4';PUBLIC=ROOT/'public/c08-motion-lab/docs/reactive'
catalog=json.loads((OUT/'catalog.json').read_text())
old_catalog=json.loads((ROOT/'evaluation/reactive-round3/catalog.json').read_text())
new_ids={c['id'] for c in catalog['cases']}
catalog['cases']=[c for c in old_catalog['cases'] if c['id'] not in new_ids]+catalog['cases']
def gzjson(path,value):
 path=Path(path)
 with gzip.GzipFile(filename=str(path)+'.gz',mode='wb',compresslevel=9,mtime=0) as f:f.write(json.dumps(value,separators=(',',':'),allow_nan=False).encode())
 if path.exists():path.unlink()
def paths(case):
 case.update(native=f'https://raw.githubusercontent.com/jelaludo/c08-motion-lab/main/research/reactive-native/{case["id"]}/native-g1-motion.npz',predictions=f'https://raw.githubusercontent.com/jelaludo/c08-motion-lab/main/research/reactive-native/{case["id"]}/unmodified-predictions.npz',native_local=f'../../research/reactive-native/{case["id"]}/native-g1-motion.npz',predictions_local=f'../../research/reactive-native/{case["id"]}/unmodified-predictions.npz',glb=f'takes/{case["id"]}/c08-motionbricks-test.glb',episode=f'takes/{case["id"]}/episode.json.gz',preview=f'takes/{case["id"]}/g1-preview.json.gz',trace=f'takes/{case["id"]}/prediction-trace.json.gz',metadata=f'takes/{case["id"]}/g1-motion.json.gz',validation=f'takes/{case["id"]}/validation-report.json')
 return case
def is_complete(folder,dest):
 try:
  for name in ['episode.json.gz','g1-preview.json.gz','prediction-trace.json.gz','g1-motion.json.gz','root-trajectory.csv','retarget-report.json','validation-report.json']:
   if not (dest/name).exists():return False
  archive=ROOT/'public/c08-motion-lab/research/reactive-native'/folder.name
  if not (archive/'native-g1-motion.npz').exists() or not (archive/'unmodified-predictions.npz').exists():return False
  if (archive/'native-g1-motion.npz').stat().st_mtime_ns<(folder/'g1-motion.npz').stat().st_mtime_ns:return False
  if (dest/'g1-motion.json.gz').stat().st_mtime_ns<(folder/'g1-motion.json').stat().st_mtime_ns:return False
  with gzip.open(dest/'episode.json.gz','rt',encoding='utf8') as f:episode=json.load(f)
  if 'archive_scope' not in episode:return False
  for name in ['g1-preview.json.gz','prediction-trace.json.gz','g1-motion.json.gz']:
   with gzip.open(dest/name,'rt',encoding='utf8') as f:json.load(f)
  return hashlib.sha256((dest/'c08-motionbricks-test.glb').read_bytes()).digest()==hashlib.sha256((folder/'c08-motionbricks-test.glb').read_bytes()).digest()
 except Exception:return False
def finalize_record(case):
 folder=OUT/case['id']
 if not folder.exists():folder=ROOT/'evaluation/reactive-round3'/case['id']
 deadline=time.monotonic()+14400
 while not (folder/'retarget-report.json').exists() or (folder/'retarget-report.json').stat().st_mtime_ns<(folder/'g1-motion.npz').stat().st_mtime_ns:
  if time.monotonic()>deadline:raise RuntimeError('Timed out waiting for retarget '+str(folder))
  time.sleep(.5)
 dest=PUBLIC/'takes'/case['id']
 if is_complete(folder,dest):
  with gzip.open(dest/'episode.json.gz','rt',encoding='utf8') as f:cached_episode=json.load(f)
  case.update(generation_method=cached_episode.get('generation_method','neural generation'),action_provenance=cached_episode.get('action_provenance',[]))
  print('REACTIVE_CACHED',case['id'],flush=True);return paths(case)
 trace=finalize_case(folder,dest);episode=json.loads((folder/'episode.json').read_text());episode['display']={k:trace[k] for k in ['display_scale','display_basis','display_origin','display_pelvis_offset']}
 episode['archive_scope']='Public native G1 archive retains all exact played poses and FK. Public unmodified archive retains exact selected untouched neural/source candidates and corrected played poses. Full unused future predictions and segment offsets are retained locally in the research workspace.'
 gzjson(dest/'episode.json',episode)
 archive=ROOT/'public/c08-motion-lab/research/reactive-native'/case['id'];archive.mkdir(parents=True,exist_ok=True)
 source=np.load(folder/'g1-motion.npz');np.savez_compressed(archive/'native-g1-motion.npz',**{k:source[k] for k in source.files})
 source=np.load(folder/'unmodified-predictions.npz');np.savez_compressed(archive/'unmodified-predictions.npz',selected_unmodified_qpos=source['selected_unmodified_qpos'],played_corrected_qpos=source['played_corrected_qpos'],**({'segment_modes':source['segment_modes']} if 'segment_modes' in source.files else {}))
 with (dest/'root-trajectory.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow(['time_s','g1_x_m','g1_y_m','g1_z_m','cat_x_m','cat_y_m']);w.writerows([i/30,*p,*episode['environment']['cat_path'][i]] for i,p in enumerate(episode['raw_root_path']))
 preview=json.loads((dest/'g1-preview.json').read_text());
 for key in ['positions','rotation_deltas','reference_positions']:
  if key in preview:preview[key]=np.round(np.array(preview[key]),6).tolist()
 preview['display_precision']='Positions/rotations rounded to six decimal places for display only; exact FP32 data retained in native NPZ.';gzjson(dest/'g1-preview.json',preview)
 trace.pop('skeletons_g1_zup',None);trace['metadata'].pop('inputs',None);trace['archive_note']='Full world-space input skeletons are omitted from this compact trace; exact four-pose context and targets remain in metadata.segments. Full research trace remains local.';gzjson(dest/'prediction-trace.json',trace)
 meta=json.loads((dest/'g1-motion.json').read_text());meta.pop('inputs',None);meta.pop('segments',None);meta['trace']='prediction-trace.json.gz';gzjson(dest/'g1-motion.json',meta)
 for name in ['retarget-report.json','validation-report.json']:
  path=dest/name;value=json.loads(path.read_text());path.write_text(json.dumps(value,separators=(',',':')),encoding='utf8')
 for stale in ['native-g1-motion.npz','unmodified-predictions.npz']:
  path=dest/stale
  if path.exists():path.unlink()
 case.update(generation_method=episode.get('generation_method','neural generation'),action_provenance=episode.get('action_provenance',[]));paths(case);print('REACTIVE_VALIDATED',case['id'],flush=True)
 return case
if __name__=='__main__':
 with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:
  catalog['cases']=list(pool.map(finalize_record,catalog['cases']))
 catalog['default_take']='course_reactive_1' if any(c['scenario']=='course' for c in catalog['cases']) else 'jump_reactive_1'
 catalog.update(description='Recorded paired research takes and continuous courses. Locomotion and action entry/exit use MotionBricks. Revised jump/crouch actions replay explicitly labelled contact-prepared original/CC0 motion; their actual displayed poses feed subsequent neural context. Orange-to-red running commands progress from 2.4 to 3.3 native m/s, with played speeds measured separately.',sample_rate=30,neural_calls=sum(c['metrics']['neural_calls'] for c in catalog['cases']),source_clip_frames=sum(c['metrics'].get('source_clip_frames',0) for c in catalog['cases']),summaries=[])
 for scenario in ['slalom','speedzones','pursuit','mixed','jump','crouch','course']:
  for condition in ['baseline','reactive']:
   rows=[c['metrics'] for c in catalog['cases'] if c['scenario']==scenario and c['condition']==condition]
   if not rows:continue
   catalog['summaries'].append({'scenario':scenario,'condition':condition,'runs':len(rows),'mean_collision_frames':float(np.mean([r['root_proxy_collision_frames'] for r in rows])),'mean_attempted_contact_frames':float(np.mean([r['attempted_contact_frames'] for r in rows])),'mean_controller_correction_total_m':float(np.mean([r['controller_correction_total_m'] for r in rows])),'mean_speed_m_s':float(np.mean([r['mean_speed_m_s'] for r in rows])),'max_speed_m_s':float(max(r['max_speed_m_s'] for r in rows)),'mean_jerk_p95_m_s3':float(np.mean([r['root_jerk_p95_m_s3'] for r in rows])),'mean_goal_distance_m':float(np.mean([r['final_goal_distance_m'] for r in rows])),'behavior_successful_passages':sum(r.get('behavior_successful_passages',0) for r in rows)})
 (PUBLIC/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf8');(ROOT/'public/c08-motion-lab/research/reactive-round4-results.json').write_text(json.dumps(catalog,indent=2),encoding='utf8');print('REACTIVE_FINALIZED',len(catalog['cases']),catalog['neural_calls'],flush=True)
