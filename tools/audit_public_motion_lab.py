from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]/'public/c08-motion-lab'
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
for path in ROOT.rglob('*'):
 if not path.is_file() or '.git' in path.parts:continue
 assert path.suffix.lower() not in ('.mp4','.pt','.pth','.ckpt','.onnx','.pkl'),path
 assert path.stat().st_size<50*1024*1024,path
 if path.suffix.lower() in ('.json','.md','.html','.js','.py','.mjs','.yml'):
  text=path.read_text(encoding='utf-8')
  for marker in ('ghp_','github_pat_','gho_','hf_'):
   # Match token-like strings, not function names such as hf_download.
   import re
   assert not re.search(re.escape(marker)+r'[A-Za-z0-9]{25,}',text),path
report={'status':'passed','public_motion_count':len(catalog['tests']),'video_derived_c08_count':video_count,'all_research_gallery_motionbricks_conditioning_original':True,'excluded_private_video_and_model_weights':True,'max_file_bytes':max(p.stat().st_size for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts),'checks':'Research gallery uses original conditioning; predictive sources are original, CC0 or user-owned; video-derived motion separately classified; no raw videos, source-local paths, inference weights or token-like credentials in publication.'}


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
reactive=json.loads((reactive_root/'catalog.json').read_text(encoding='utf8'))
assert len(reactive['cases'])==40
assert {c['scenario'] for c in reactive['cases']}=={'slalom','speedzones','pursuit','mixed'}
episodes={}
for case in reactive['cases']:
 episode=json.loads((reactive_root/case['episode']).read_text(encoding='utf8'))
 validation=json.loads((reactive_root/case['validation']).read_text(encoding='utf8'))
 assert case['metrics']['neural_calls']==16 and episode['sample_rate']==30
 assert validation['gltf_errors']==0 and validation['gltf_warnings']==0
 assert validation['skinned_geometry_min_floor_y_m']>=-.003
 for name in ['prediction-trace.json','native-g1-motion.npz','root-trajectory.csv']:
  assert (reactive_root/'takes'/case['id']/name).is_file()
 episodes[(case['scenario'],case['seed'],case['condition'])]=episode
for scenario in ['slalom','speedzones','pursuit','mixed']:
 for seed in range(1,6):
  assert episodes[(scenario,seed,'baseline')]['environment']==episodes[(scenario,seed,'reactive')]['environment']
brek=json.loads((ROOT/'docs/assets/b-rek43-provenance.json').read_text(encoding='utf8'))
assert hashlib.sha256((ROOT/'docs/assets/b-rek43.glb').read_bytes()).hexdigest()==brek['source_sha256']==brek['output_sha256']
report.update(reactive_neural_takes=40,reactive_neural_calls=640,reactive_paired_environments_verified=True,brek43_original_rig_hash_verified=True)
(ROOT/'research/publication-validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('Reactive: 40 real neural rollouts / 640 calls; paired environments, derived exports and B-REK43 hash verified.')

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
