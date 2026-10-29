"""Compare independently computed full skins with reimported GLB skins, allowing vertex reordering."""
import argparse,json,numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
ap=argparse.ArgumentParser();ap.add_argument('--expected',required=True);ap.add_argument('--actual',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();x=np.load(a.expected);y=np.load(a.actual)
assert np.array_equal(x['skin_sample_indices'],y['skin_sample_indices'])
errors=[]
for p,q in zip(x['world_skin_samples'],y['world_skin_samples']):errors.append(float(max(cKDTree(p).query(q)[0].max(),cKDTree(q).query(p)[0].max())))
r={'method':'Bidirectional nearest-vertex distances after full skin evaluation; allows export material/vertex reordering. No spatial alignment.','sample_frames':x['skin_sample_indices'].tolist(),'expected_vertices_per_frame':x['world_skin_samples'].shape[1],'actual_vertices_per_frame':y['world_skin_samples'].shape[1],'maximum_bidirectional_full_skin_distance_m':max(errors),'per_sample_m':errors};assert max(errors)<2e-5,r;Path(a.out).write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
