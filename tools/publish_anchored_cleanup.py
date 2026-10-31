"""Add measured support-cleanup candidates; preserve the original research artifacts."""
from pathlib import Path
import copy,datetime,hashlib,json,math,os,shutil
_roots=[Path(os.environ['MOTION_LAB_WORKSPACE'])] if os.environ.get('MOTION_LAB_WORKSPACE') else list(Path(__file__).resolve().parents)
ROOT=next((p for p in _roots if (p/'evaluation/anchored-cleanup').is_dir() and (p/'public/c08-motion-lab').is_dir()),None)
if ROOT is None:raise RuntimeError('Set MOTION_LAB_WORKSPACE to the original lab workspace.')
PUBLIC=ROOT/'public/c08-motion-lab';FOLDER=PUBLIC/'docs/mocap-rebuild';PRIVATE=ROOT/'evaluation/anchored-cleanup'
load=lambda p:json.loads(p.read_text(encoding='utf-8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=load(PRIVATE/'baseline.json');catalog=copy.deepcopy(baseline['catalog'])
catalog['version']=baseline['catalog']['version']+1;catalog['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
catalog['summary']='Compare the preferred cleaned capture with a new support-aware cleanup and authored return to the default stance. Original MotionBricks research comparisons, including the promising dance, remain available.'
catalog['methods'].append({'id':'anchored','label':'Anchored cleanup','description':'Cleaned capture with measured support-specific foot anchors, flat soles, smooth body-floor constraints and authored neutral entry/recovery. Root travel is retained. No new MotionBricks inference.'})
rows=[]
for test in catalog['tests']:
 slug=test['id'];folder=PRIVATE/slug;model=folder/'anchored.glb';generator=load(folder/'cleanup-report.json');qa=load(folder/'independent-qa.json')
 assert model.exists() and qa['structural_pass'] and qa['active_source_frames_retained_once_in_order'],slug
 assert qa['artifact_sha256']==sha(model),(slug,'Independent QA is stale')
 assert qa['sampled_floor_pass'],(slug,'floor requires another iteration')
 assert qa['seam']['root_relative_joint_position_gap_m']<.0001
 assert qa['seam']['maximum_local_orientation_gap_rad']<.0001
 clean=next(o for o in test['outputs']if o['method']=='cleaned')
 assert sha(FOLDER/clean['model'])==clean['sha256']==generator['source_file_sha256']==qa['baseline_cleaned_sha256']
 assert generator['export']['sha256']==sha(model)
 coverage=qa['support_coverage'];count=coverage['accepted_action_core_frame_sides']
 active=qa['active_jitter'];step=active.get('joint_step_rad',active.get('local_joint_step_rad',{}));accel=active.get('joint_angular_acceleration_rad_s2',{})
 metrics={'minimum_skin_floor_m':qa['whole_skin_min_floor_m'],'whole_skin_min_floor_m':qa['whole_skin_min_floor_m'],'floor_samples_below_ground':qa['skin_key_samples_below_minus_1mm'],'foot_support_speed_p95_m_s':qa['foot_support_speed_p95_m_s'],'foot_center_drift_p95_m':qa['foot_center_drift_p95_m'],'sole_tilt_p95_deg':qa['sole_tilt_p95_deg'],'sole_height_p95_m':qa['sole_height_p95_m'],'root_relative_joint_position_gap_m':qa['seam']['root_relative_joint_position_gap_m'],'root_seam_gap_m':qa['seam']['root_displacement_m'],'rotation_seam_deg':math.degrees(qa['seam']['maximum_local_orientation_gap_rad']),'start_root_speed_m_s':qa['seam']['start_max_joint_world_speed_m_s'],'end_root_speed_m_s':qa['seam']['end_max_joint_world_speed_m_s'],'action_support_frame_sides':count,'action_support_retention_fraction':coverage['action_retention_fraction'],'support_release_count':coverage['release_count'],'actual_neural_calls':0}
 if step.get('p95')is not None:metrics['local_joint_step_p95_deg']=math.degrees(step['p95'])
 if accel.get('p95')is not None:metrics['local_joint_angular_acceleration_p95_rad_s2']=accel['p95']
 validation={k:v for k,v in qa.items()if k not in ['default_pose','gltf_messages']}
 report={'id':slug,'method':'anchored','frames':generator['frames'],'fps':generator['fps'],'pipeline':generator['provenance'],'artifact_sha256':sha(model),'source_cleaned_model_sha256':clean['sha256'],'source_prepared_sha256':load(FOLDER/clean['report'])['source_prepared_sha256'],'ground_policy':'Support-specific flat sole anchors and fixed-length leg IK, coupled with smooth body-floor and reach constraints. Unsupported/roll phases release foot anchors. This is explicitly authored kinematic cleanup, not physical balance or a per-frame display grounding trick.','generator':generator,'validation':validation,'metrics':metrics,'limitations':generator['limitations'],'provenance':{'variant':'anchored','actual_neural_calls':0,'source_cleaned_model_sha256':clean['sha256'],'neutral_hold_frames':generator['neutral_hold_frames'],'source_action_range':generator['source_action_range'],'source_action_timing_preserved':generator['source_action_timing_preserved'],'root_motion_delta_blender':generator['root_motion_delta_blender']}}
 stem=slug+'-anchored';destination=FOLDER/'models'/f'{stem}.glb';shutil.copy2(model,destination)
 (FOLDER/'reports'/f'{stem}.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
 description='New authored support cleanup with neutral entry and return at the finishing root location; original capture timing retained over the declared action range.'
 if count==0:description+=' This candidate preserves the captured action leg motion; foot planting is limited to the authored neutral transitions. Action support metrics are N/A.'
 test['outputs'].append({'method':'anchored','model':f'models/{stem}.glb','report':f'reports/{stem}.json','version':1,'sha256':sha(model),'frames':generator['frames'],'duration_s':generator['duration_s'],'metrics':metrics,'description':description})
 test['limitations']=[text for text in test['limitations']if not text.startswith('All variants use a constant avatar vertical calibration')]
 test['limitations'].extend(['The original four research variants use their original constant floor calibration. Anchored cleanup is a separate, explicitly authored support/IK pass.','The anchored candidate returns to its default posture at the ending root position. Root displacement is deliberate travel, not a broken posture seam.','Foot anchors apply only to declared support phases. Hand/back support and dynamic balance are not solved.'])
 rows.append({'id':slug,'model':destination.relative_to(PUBLIC).as_posix(),'sha256':sha(model),'frames':generator['frames'],'fps':generator['fps'],'metrics':metrics,'support_coverage':coverage})
(FOLDER/'catalog.json').write_text(json.dumps(catalog,indent=2,allow_nan=False),encoding='utf-8')
summary=load(PRIVATE/'independent-summary.json');assert summary['candidates']==6 and summary['common_full_skeleton_default_pass']
assert {r['id']:r['artifact_sha256']for r in summary['results']}=={r['id']:r['sha256']for r in rows},'Aggregate QA is stale'
(PUBLIC/'research/anchored-cleanup-validation.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
release={'status':'artifact_integrity_passed_visual_review_required','candidates':6,'old_research_outputs_retained':24,'new_neural_calls':0,'scope':'Measured contact and pose integrity are distinct from visual naturalness or dynamic balance. Action-only metrics exclude authored neutral holds. Root travel is deliberate.','results':rows}
(PUBLIC/'research/anchored-cleanup-release.json').write_text(json.dumps(release,indent=2,allow_nan=False),encoding='utf-8')
print('Published6cleanupcandidates;24researchoutputsretained.')
