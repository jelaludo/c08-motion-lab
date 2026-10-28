from pathlib import Path
import json,os,runpy,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/c08-worker/round3'
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
for case in catalog['tests']:
    if os.environ.get('MB_ONLY_TESTS') and case['id'] not in os.environ['MB_ONLY_TESTS'].split(','):continue
    if case.get('generation')!='passed':continue
    folder=OUT/case['directory'];os.environ['MB_TEST_DIRECTORY']=str(folder)
    runpy.run_path(str(ROOT/'tools/prepare_c08_review.py'),run_name='__main__')
    meta=json.loads((folder/'g1-motion.json').read_text(encoding='utf-8'));case['joint_limit_violations']=meta['joint_limit_audit']['violations']
    if case.get('retarget')=='passed':
        result=subprocess.run(['node',str(ROOT/'tools/review/validate-c08.mjs')],capture_output=True,text=True,env=os.environ);(folder/'validation.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        case['technical_validation']='passed' if result.returncode==0 else 'failed'
        if (folder/'validation-report.json').exists():
            v=json.loads((folder/'validation-report.json').read_text());r=json.loads((folder/'retarget-report.json').read_text());case['validation']=v;case['adaptation']={k:r[k] for k in ('max_pelvis_reach_correction_m','max_foot_floor_lift_m')}
            flags=[]
            if v['skinned_geometry_min_floor_y_m']<-.002:flags.append('C08 geometry penetrates the floor')
            if r['max_foot_floor_lift_m']>.1:flags.append('Large C08 foot-clearance correction')
            if r['max_pelvis_reach_correction_m']>.1:flags.append('Large C08 pelvis reach correction')
            if case['source_metrics']['maximum_joint_key_step_rad']>.8:flags.append('Abrupt source joint change')
            if case['joint_limit_violations']:flags.append('Generated G1 joint-limit violations')
            case['review_flags']=flags
    print('FRESH_CHECKED',case['id'],case.get('technical_validation','source only'),case.get('review_flags',[]),flush=True)
    (OUT/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
summary={'total':len(catalog['tests']),'generated':sum(c.get('generation')=='passed' for c in catalog['tests']),'adapted':sum(c.get('retarget')=='passed' for c in catalog['tests']),'technical_passes':sum(c.get('technical_validation')=='passed' for c in catalog['tests']),'flagged_for_review':sum(bool(c.get('review_flags')) for c in catalog['tests']),'purpose':'Fresh original numerical replacements, not republication or alteration of sample-driven outputs.'}
catalog['summary']=summary;(OUT/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8');(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
