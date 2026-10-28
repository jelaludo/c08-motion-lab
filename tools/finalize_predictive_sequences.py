from pathlib import Path
import json,os,runpy
from mb_predictive_finalize import finalize_case
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'evaluation/predictive-sequences';site=ROOT/'public/c08-motion-lab/docs/mb-predictive';catalog=json.loads((site/'catalog.json').read_text());entries={c['id']:c for c in catalog['cases']}
for c in json.loads((out/'catalog.json').read_text())['cases']:
 trace=finalize_case(out/c['id'],site/'cases'/c['id']);v=json.loads((site/'cases'/c['id']/'validation-report.json').read_text());assert v['gltf_errors']==0 and v['gltf_warnings']==0 and v['skinned_geometry_min_floor_y_m']>=-.003;c.update(inference_seconds=trace['metadata']['inference_seconds'],segment_count=len(trace['metadata']['segments']));entries[c['id']]=c;print('SEQUENCE_VALIDATED',c['id'],flush=True)
catalog['cases']=list(entries.values());catalog['summary']['combined_neural_sequences']=3;(site/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf8')
