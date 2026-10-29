from pathlib import Path
import json,hashlib,gzip
ROOT=Path(__file__).resolve().parents[1]
def read_json(path):
 path=Path(path)
 if not path.exists() and path.suffix=='.json':path=path.with_suffix('.json.gz')
 return json.loads(gzip.decompress(path.read_bytes()).decode('utf8') if path.suffix=='.gz' else path.read_text(encoding='utf8'))
catalog=json.loads((ROOT/'docs/motions/catalog.json').read_text())
assert len(catalog['tests'])>=36
video_count=0
for test in catalog['tests']:
 if test.get('kind')=='video_mocap':
  video_count+=1;metadata=json.loads((ROOT/'docs/motions'/test['id']/'source-metadata.json').read_text())
  assert metadata['provenance_type']=='video_mocap',test['id']
  assert not any(k in metadata for k in ('source_local_path','source_path')),test['id']
 else:
  metadata=json.loads((ROOT/'docs/motions'/test['id']/'g1-motion.json').read_text())
  assert metadata['provenance_type']=='original',test['id']
  assert 'conditioning_file' not in metadata,test['id']
 assert not test['validation']['gltf_errors'] and not test['validation']['gltf_warnings']
allowlist_path=ROOT/'research/h3-publication-allowlist.json'
allowed_videos={entry['path']:entry for entry in read_json(allowlist_path)['files']} if allowlist_path.exists() else {}
for relative,entry in allowed_videos.items():
 assert relative.startswith('docs/h3-motion/media/') and relative.endswith('.mp4'),relative
 assert entry['private_human_footage'] is False and entry['kind'] in ('creator_supplied_generated_robot_preview','own_robot_render_or_recovery_visualization'),relative
 assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==entry['sha256'],relative
for path in ROOT.rglob('*'):
 if not path.is_file() or '.git' in path.parts:continue
 assert path.suffix.lower() not in ('.pt','.pth','.ckpt','.onnx','.pkl'),path
 if path.suffix.lower()=='.mp4':assert path.relative_to(ROOT).as_posix() in allowed_videos,path
 assert path.stat().st_size<50*1024*1024,path
 if path.suffix.lower() in ('.json','.md','.html','.js','.py','.mjs','.yml') or path.name.endswith('.json.gz'):
  text=gzip.decompress(path.read_bytes()).decode('utf8') if path.name.endswith('.json.gz') else path.read_text(encoding='utf-8')
  for marker in ('ghp_','github_pat_','gho_','hf_'):
   # Match token-like strings, not function names such as hf_download.
   import re
   assert not re.search(re.escape(marker)+r'[A-Za-z0-9]{25,}',text),path
report={'status':'passed','public_motion_count':len(catalog['tests']),'video_derived_c08_count':video_count,'all_research_gallery_motionbricks_conditioning_original':True,'excluded_private_video_and_model_weights':True,'hash_allowlisted_generated_robot_render_previews':len(allowed_videos),'max_file_bytes':max(p.stat().st_size for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts),'checks':'Research gallery uses original conditioning; predictive sources are original, CC0 or user-owned; video-derived motion separately classified; generated robot previews hash-allowlisted separately; no private human source videos, inference weights or token-like credentials in publication.'}


quaternius=json.loads((ROOT/'docs/quaternius/validation-report.json').read_text(encoding='utf-8'))
assert len(quaternius['clips'])==20 and quaternius['gltf_errors']==0 and quaternius['gltf_warnings']==0
assert all(c['floor_min_m']>=-.003 and c['max_fk_error_m']<.001 and c['prohibited_tracks']==0 for c in quaternius['clips'])
print('Quaternius: 20 separately validated baseline clips; research catalog unchanged.')

# The predictive tab is a separate experiment; keep the research gallery untouched.
predictive=ROOT/'docs/mb-predictive'
cases=json.loads((predictive/'catalog.json').read_text(encoding='utf-8'))['cases']
assert len(cases)>=6
for case in cases:
 folder=predictive/'cases'/case['id']
 trace=json.loads((folder/'prediction-trace.json').read_text(encoding='utf-8'))
 provenance=trace['metadata']['provenance_type']
 harvest=trace['metadata'].get('source_harvest')
 if harvest:
  assert harvest['publishable'] and harvest['family'] in ('quaternius','own_capture','motionbricks_original')
  assert provenance in ('cc0_quaternius','user_owned_mocap','original')
 elif trace['metadata'].get('routine'):
  routine=trace['metadata']['routine'];assert provenance=='mixed_permitted_sources' and routine['move_count'] in (5,10,15)
  assert all(m['publishable'] and m['family'] in ('quaternius','own_capture','motionbricks_original') for m in routine['moves'])
 else:assert provenance=='original'
 segments=trace['metadata']['segments']
 assert all(len(s['context'])==4 and 1<=len(s['target'])<=4 for s in segments)
 for previous,current in zip(segments,segments[1:]):assert previous['last_four_generated']==current['context']
 for directory in [folder,folder/'linear']:
  v=json.loads((directory/'validation-report.json').read_text(encoding='utf-8'))
  assert v['gltf_errors']==0 and v['gltf_warnings']==0 and v['skinned_geometry_min_floor_y_m']>=-.003
  assert v['independent_clones'] and not v['prohibited_animation_tracks']
print(f'MB-Predictive: {len(cases)} permitted-source predictions and interpolation controls; exact four-pose chain links verified.')

report.update(quaternius_baseline_clips=20,predictive_neural_experiments=len(cases),predictive_interpolation_controls=len(cases),exact_generated_context_chaining=True,public_predictive_source_rights_verified=True)
(ROOT/'research/publication-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))

body=json.loads((ROOT/'docs/assets/meshy-fighter-attribution.json').read_text(encoding='utf-8'))
assert body['license']=='CC-BY-4.0' and body['author']=='Tulio Portela'
assert hashlib.sha256((ROOT/'docs/assets/meshy-fighter-rigged.glb').read_bytes()).hexdigest()==body['output_sha256']
assert 'Tulio Portela' in (ROOT/'docs/mb-predictive/index.html').read_text(encoding='utf-8')
report.update(experimental_body_attribution_verified=True,combined_sequence_move_counts=[5,10,15])
(ROOT/'research/publication-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Meshy test body: attribution and output hash verified; production exclusion documented.')

vanilla=json.loads((ROOT/'docs/vanilla/manifest.json').read_text(encoding='utf8'))
assert len(vanilla['candidates'])==15 and len({c['id'] for c in vanilla['candidates']})==15
assert all(c['source_license']=='CC0-1.0' and c['body']=='c08' for c in vanilla['candidates'])
for relative,digest in vanilla['hashes'].items():
 source_bytes=(ROOT/'docs'/relative).read_bytes()
 if relative.endswith('.js'):source_bytes=source_bytes.replace(b'\r\n',b'\n')
 assert hashlib.sha256(source_bytes).hexdigest()==digest
assert all(c['warning'] for c in vanilla['candidates'] if c['id'] in ('back_roll','get_up','lie_down','high_jump'))
report.update(vanilla_candidates=15,vanilla_source_hashes_verified=True,vanilla_review_version=vanilla['version'])
(ROOT/'research/publication-validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('Vanilla: 15 CC0-derived versioned candidates; source hashes and prototype warnings verified.')

reactive_root=ROOT/'docs/reactive'
reactive=read_json(reactive_root/'catalog.json')
paired_scenarios={'slalom','speedzones','pursuit','mixed','jump','crouch'}
expected={(scenario,seed,condition) for scenario in paired_scenarios for seed in range(1,11) for condition in ['baseline','reactive']}|{('course',seed,'reactive') for seed in range(1,4)}
assert len(reactive['cases'])==123 and {(c['scenario'],c['seed'],c['condition'])for c in reactive['cases']}==expected
source_hashes={hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'research/reactive-round4-sources').glob('*.npz')}
episodes={};genuine_neural_calls=0;prepared_source_frames=0;hybrid_takes=0
for case in reactive['cases']:
 episode=read_json(reactive_root/case['episode']);validation=read_json(reactive_root/case['validation'])
 assert episode['sample_rate']==30 and episode['duration_s']>=24
 if case['scenario']=='course':assert episode['duration_s']==80
 assert len(episode['environment']['obstacles'])>=(1 if case['scenario']=='crouch' else 2 if case['scenario']=='jump' else 6 if case['scenario']=='course' else 8)
 assert episode['environment']['bounds'][1]-episode['environment']['bounds'][0]>=30
 assert len(episode['predicted_root_path'])==len(episode['played_root_path'])==round(episode['duration_s']*30)+1
 assert case['metrics']['root_proxy_collision_frames']==0
 assert validation['gltf_errors']==validation['gltf_warnings']==0 and validation['skinned_geometry_min_floor_y_m']>=-.003
 for field in ['native_local','predictions_local']:
  artifact=(reactive_root/case[field]).resolve();assert artifact.is_file() and artifact.is_relative_to(ROOT.resolve()),artifact
 assert (reactive_root/'takes'/case['id']/'root-trajectory.csv').is_file()
 trace=read_json(reactive_root/case['trace']);segments=trace['metadata']['segments'];source_segments=[x for x in segments if x.get('segment_mode','neural')=='source_clip'];neural_segments=[x for x in segments if x.get('segment_mode','neural')=='neural']
 assert len(neural_segments)+len(source_segments)==len(segments)
 assert len(neural_segments)==case['metrics']['neural_calls']>0
 assert sum(x['frames']for x in segments)==round(episode['duration_s']*30)
 assert all(len(x['context'])==4 and 1<=len(x['target'])<=4 for x in segments)
 for previous,current in zip(segments,segments[1:]):assert previous.get('last_four_played',previous['last_four_generated'])==current['context']
 if source_segments:
  hybrid_takes+=1;assert trace['metadata']['provenance_type']=='mixed_permitted_sources'
  assert 'contact-prepared' in case['generation_method']
  for segment in source_segments:
   source=segment['source_phase'];assert source['source_sha256']in source_hashes
   assert source['source_license']in ['CC0-1.0','original authored conditioning / model-derived motion']
   assert segment['inference_seconds']==0 and segment['target_role'].startswith('Recorded source')
 else:assert trace['metadata']['provenance_type']=='original'
 genuine_neural_calls+=len(neural_segments);prepared_source_frames+=sum(x['frames']for x in source_segments)
 episodes[(case['scenario'],case['seed'],case['condition'])]=episode
assert genuine_neural_calls==reactive['neural_calls']==8340
assert prepared_source_frames==reactive['source_clip_frames']==4879 and hybrid_takes==23
for scenario in paired_scenarios:
 for seed in range(1,11):assert episodes[(scenario,seed,'baseline')]['environment']==episodes[(scenario,seed,'reactive')]['environment']
for asset in ['b-rek43','eva-k7']:
 provenance=read_json(ROOT/f'docs/assets/{asset}-provenance.json');assert hashlib.sha256((ROOT/f'docs/assets/{asset}.glb').read_bytes()).hexdigest()==provenance['source_sha256']==provenance['output_sha256']
mesh=read_json(ROOT/'research/reactive-round4-fullskin-validation.json');assert mesh['status']=='passed' and mesh['catalog_version']==reactive['version'] and mesh['take_body_combinations']==369
for body in ['c08','brek','eva']:
 assert mesh['bodies'][body]['cases']==123 and mesh['bodies'][body]['triangle_obstacle_intersections']==0
 assert len(mesh['results'][body])==123 and {r['id']for r in mesh['results'][body]}=={c['id']for c in reactive['cases']}
 for row in mesh['results'][body]:
  case=next(c for c in reactive['cases']if c['id']==row['id']);artifact=reactive_root/case['glb'if body=='c08'else'preview'];data=artifact.read_bytes();data=gzip.decompress(data)if artifact.suffix=='.gz'else data
  assert hashlib.sha256(data).hexdigest()==row['artifact_sha256'],row['id']
physics=read_json(ROOT/'research/reactive-round4-public-physics.json');assert physics['status']=='passed' and physics['cases']==123 and physics['catalog_version']==reactive['version']
for row in physics['results']:
 case=next(c for c in reactive['cases']if c['id']==row['id']);assert row['selected_input_height_quaternion_and_joints_unchanged']
 assert row['native_archive_sha256']==hashlib.sha256((reactive_root/case['native_local']).read_bytes()).hexdigest()
 assert row['selected_predictions_archive_sha256']==hashlib.sha256((reactive_root/case['predictions_local']).read_bytes()).hexdigest()
contacts=read_json(ROOT/'research/reactive-round4-viewer-footplants.json');assert contacts['status']=='passed' and {r['body']for r in contacts['results']}=={'c08','brek','eva'}
assert all(r['support_samples']>0 and r['support_speed_p95_m_s']<.005 and r['reach_release_samples']==0 for r in contacts['results'])
docs_bytes=sum(p.stat().st_size for p in (ROOT/'docs').rglob('*')if p.is_file());assert docs_bytes<970*1024*1024
report.update(reactive_recorded_takes=123,reactive_neural_only_takes=100,reactive_hybrid_takes=hybrid_takes,reactive_scenarios=sorted(paired_scenarios|{'course'}),reactive_genuine_neural_calls=genuine_neural_calls,reactive_prepared_source_frames=prepared_source_frames,reactive_continuous_courses=3,reactive_paired_environments_verified=True,reactive_exact_played_context_chaining=True,reactive_selected_input_height_quaternion_hinges_unchanged=True,reactive_displayed_take_body_combinations=369,reactive_mesh_samples=sum(b['frames']for b in mesh['bodies'].values()),reactive_final_artifact_hashes_verified=True,original_brek_eva_rigs_hash_verified=True,trusted_stance_only_footplant_validation=True,pages_artifact_mib=round(docs_bytes/1024**2,2))
(ROOT/'research/publication-validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(f'Reactive:123 recordings, {genuine_neural_calls} genuine neural calls plus {prepared_source_frames} explicitly classified prepared-source frames; all369 displayed body/take combinations validated.')

bakes=list((ROOT/'docs/vanilla/takes').glob('*.glb'))
assert len(bakes)==30
for bake in bakes:
 metadata=json.loads(bake.with_suffix('.json').read_text(encoding='utf8'))
 assert metadata['recipe_version']==vanilla['version']
 assert metadata['sha256']==hashlib.sha256(bake.read_bytes()).hexdigest()
 assert metadata['gltf_errors']==metadata['gltf_warnings']==0
report.update(vanilla_game_bakes=30,vanilla_bake_version_hashes_verified=True)
(ROOT/'research/publication-validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('Vanilla game exports: 30 bakes, exact recipe versions, hashes and glTF validation verified.')
