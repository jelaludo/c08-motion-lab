"""Separate true anchor releases from unanchored reach projections in frozen cleanup reports."""
from pathlib import Path
import hashlib,json,numpy as np
import os

def discover_root():
 explicit=os.environ.get('MOTIONBRICKS_ROOT')
 candidates=[Path(explicit).expanduser().resolve()] if explicit else []
 candidates += list(Path(__file__).resolve().parents) + [Path.cwd().resolve()]
 for candidate in candidates:
  if (candidate/'evaluation/mocap-rebuild/exports').is_dir() or (candidate/'public/c08-motion-lab/docs/mocap-rebuild').is_dir():return candidate
 raise RuntimeError('Set MOTIONBRICKS_ROOT to the original MotionBricks workspace; private cleaned .blend inputs are needed for exact reproduction.')

ROOT=discover_root();BASE=ROOT/'evaluation/anchored-cleanup'
for slug in ['ukemi','technical-standup','gorilla-front','sumo-stomp','source-094553','h3-dance']:
 folder=BASE/slug;path=folder/'cleanup-report.json';report=json.loads(path.read_text(encoding='utf-8'));data=np.load(folder/'cleanup-data.npz')
 events=report.get('ik_reach_events',report['support_releases'])
 for event in events:
  f=event['frame'];s=0 if event['side']=='L' else 1;requested=float(data['requested_support_weights'][f,s]);event.update(requested_support_weight=requested,phase=str(data['phase'][f]),kind='support_anchor_release' if requested>.001 else 'unanchored_reach_projection')
 report['ik_reach_events']=events;report['support_releases']=[e for e in events if e['kind']=='support_anchor_release'];report['support_release_count']=len(report['support_releases']);report['unanchored_reach_projection_count']=sum(e['kind']=='unanchored_reach_projection' for e in events)
 core=data['source_frame_index']>=0
 report['action_foot_anchoring_applicable']=bool(np.any(data['requested_support_weights'][core]>.999))
 report['action_support_coverage']={side:{'full_support_keys':int(np.sum(data['support_weights'][core,s]>.999)),'action_keys':int(np.sum(core)),'fraction':float(np.mean(data['support_weights'][core,s]>.999))} for s,side in enumerate(['L','R'])}
 report['metadata_annotation_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 path.write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(slug,'anchor_releases',report['support_release_count'],'unanchored_projections',report['unanchored_reach_projection_count'])
