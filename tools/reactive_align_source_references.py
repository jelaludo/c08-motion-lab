from pathlib import Path
import json,numpy as np
from harvest_fit_g1 import fk
root=Path(__file__).resolve().parents[1]/'evaluation/reactive-round4'
for folder in root.iterdir():
 if not (folder/'episode.json').exists():continue
 meta=json.loads((folder/'g1-motion.json').read_text())
 if not any(s.get('segment_mode')=='source_clip' for s in meta['segments']):continue
 archive=np.load(folder/'unmodified-predictions.npz')
 trace=json.loads((folder/'prediction-trace.json').read_text())
 for i,s in enumerate(meta['segments']):
  if s.get('segment_mode')!='source_clip':continue
  start,length=archive['prediction_offsets'][i]
  q=archive['all_predicted_future_qpos'][start:start+length][-4:]
  s['target']=q.tolist()
  s['target_role']='Recorded source reference poses, not a neural target request'
  last=np.array(s['last_four_played'][-1])
  s['endpoint_root_error_m']=float(np.linalg.norm(last[:2]-q[-1,:2]))
  trace['skeletons_g1_zup'][i]['target']=[[fk(row)[n][0].tolist()for n in meta['body_names']]for row in q]
 meta['inputs']=[{'context':s['context'],'target':s['target'],'segment_mode':s.get('segment_mode','neural')}for s in meta['segments']]
 trace['metadata']=meta
 (folder/'g1-motion.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
 (folder/'prediction-trace.json').write_text(json.dumps(trace,indent=2),encoding='utf8')
 print('SOURCE_REFERENCE_ALIGNED',folder.name,flush=True)
