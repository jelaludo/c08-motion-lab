"""Check the published six authored candidates against independent measurements."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
catalog=read(ROOT/'docs/mocap-rebuild/catalog.json')
summary=read(ROOT/'research/anchored-cleanup-validation.json')
baseline=read(ROOT/'research/anchored-cleanup-baseline-validation.json')
assert baseline['status']=='passed' and baseline['original_artifacts_unchanged']==66
assert summary['candidates']==6 and summary['common_full_skeleton_default_pass']
rows=[]
for test in catalog['tests']:
    assert len(test['outputs'])==5
    out=next(o for o in test['outputs'] if o['method']=='anchored')
    report=read(ROOT/'docs/mocap-rebuild'/out['report'])
    digest=hashlib.sha256((ROOT/'docs/mocap-rebuild'/out['model']).read_bytes()).hexdigest()
    qa=report['validation']
    assert digest==out['sha256']==report['artifact_sha256']==qa['artifact_sha256']
    assert qa['structural_pass'] and qa['sampled_floor_pass']
    assert qa['active_source_frames_retained_once_in_order']
    assert qa['seam']['root_relative_joint_position_gap_m']<.0001
    assert qa['seam']['maximum_local_orientation_gap_rad']<.0001
    assert qa['support_coverage']['release_count']==0
    assert report['provenance']['actual_neural_calls']==0
    if test['id']!='sumo-stomp':
        assert qa['support_coverage']['accepted_action_core_frame_sides']==0
    rows.append({'id':test['id'],'sha256':digest})
assert len(rows)==6
result={'status':'artifact_integrity_passed_visual_review_required','candidates':6,'new_neural_calls':0,'results':rows,'scope':'Checks integrity and reported kinematic measurements; does not certify naturalness, balance or self-collision.'}
(ROOT/'research/anchored-cleanup-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
