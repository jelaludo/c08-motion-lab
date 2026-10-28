"""Publish only explicitly permitted harvested-pose outputs; sample-conditioned results stay local."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/pose-harvest';SITE=ROOT/'public/c08-motion-lab/docs/mb-predictive';source=json.loads((OUT/'catalog.json').read_text());catalog=json.loads((SITE/'catalog.json').read_text());entries={c['id']:c for c in catalog['cases'] if not c.get('harvested')};private=[];results=[]
for c in source['cases']:
 if c.get('validation')!='passed' or c.get('minimum_floor_m',-1)<-.003:raise RuntimeError('Unaccepted export: '+c['id'])
 review=OUT/'review'/c['id'];trace=json.loads((review/'prediction-trace.json').read_text());h=trace['metadata']['source_harvest'];native=c['family'] in ('motionbricks_original','bundled_sample');h['conversion_limitations']='Native G1 source coordinates sampled directly; no joint clamping or human skeleton fitting.' if native else 'Bounded direction/foot/torso IK onto G1; fingers, contact and human proportions are not preserved.'
 if c['family']=='own_capture':
  notes={'capture_ukemi':'Occluded roll poses and floor support are uncertain; sparse targets cannot encode the full Ukemi contact sequence.','capture_gorilla_front':'The source ends in a face close-up; the missing full body at the endpoint is inferred.','capture_gorilla_side':'Late source cropping and occluded fists make support/hand detail uncertain.','capture_technical_standup':'Feet leave the source image and planted-hand placement is approximate.','capture_deadlift':'The source recovery contains body motion only, without a bar, load or grip contacts.','capture_sumo_stomp':'Monocular depth and foot-support estimates remain uncertain.'}
  h['source_quality_notes']=[notes[c['id']]]
 elif c['family']=='motionbricks_original':h['source_quality_notes']=['This source was itself generated from original conditioning: the result is a second-generation prediction.']
 for directory in [review,review/'linear',ROOT/c['directory'],ROOT/c['directory']/'linear']:
  p=directory/'g1-motion.json';d=json.loads(p.read_text());d['source_harvest']=h;p.write_text(json.dumps(d,indent=2),encoding='utf8')
 (review/'prediction-trace.json').write_text(json.dumps(trace,indent=2),encoding='utf8')
 if c['publishable']:
  assert h['publishable'] and c['family']!='bundled_sample' and trace['metadata']['provenance_type'] in ('original','cc0_quaternius','user_owned_mocap')
  target=SITE/'cases'/c['id'];shutil.copytree(review,target,dirs_exist_ok=True)
 else:
  target=OUT/'local-view'/c['id'];shutil.copytree(review,target,dirs_exist_ok=True)
 record={'id':c['id'],'label':c['label'],'category':c['category'],'family':c['family'],'harvested':True,'source_duration_s':c['duration_s'],'duration_s':c['generated_duration_s'],'inference_seconds':c['inference_seconds'],'segment_count':2,'source_sample_times_s':c['sample_times_s'],'publishable':c['publishable']}
 if c['publishable']:entries[c['id']]=record
 else:private.append({**record,'base':'/mb-predictive/evaluation/'+c['id']+'/'})
 r=json.loads((review/'retarget-report.json').read_text());results.append({**record,'minimum_floor_m':c['minimum_floor_m'],'maximum_pose_fit_error_deg':max((p['bone_direction_max_error_deg'] for p in c.get('pose_fit',[])),default=0),'max_whole_body_ground_lift_m':r.get('max_whole_body_ground_lift_m',0)})
catalog['cases']=list(entries.values());catalog['summary']={'authored_original':6,'harvested_public':sum(c['publishable'] for c in source['cases']),'restricted_sample_results_in_public':False};(SITE/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf8');(OUT/'private-catalog.json').write_text(json.dumps({'cases':private},indent=2),encoding='utf8')
(OUT/'results.json').write_text(json.dumps({'cases':results},indent=2),encoding='utf8');public_results=[r for r in results if r['publishable']];(ROOT/'public/c08-motion-lab/research/pose-harvest-results.json').write_text(json.dumps({'public_cases':public_results,'public_count':len(public_results),'local_sample_count':len(private),'note':'No restricted source poses, arrays or generated animations included in public results.'},indent=2),encoding='utf8');print(json.dumps({'public_total':len(entries),'public_harvested':len(public_results),'private_sample_cases':len(private)},indent=2))
