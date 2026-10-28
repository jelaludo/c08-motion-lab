"""Attach sanitized recovery findings and measured contact-drift proxies to C08 artifacts."""
from pathlib import Path
import json, math
ROOT=Path(__file__).resolve().parents[1]
for out in (ROOT/'video-mocap/c08-retarget').iterdir():
 if not (out/'retarget-report.json').exists(): continue
 report=json.loads((out/'retarget-report.json').read_text())
 provenance=json.loads((ROOT/'video-mocap'/out.name/'derived-motion-provenance.json').read_text())
 report['recovery_provenance']=provenance
 report['limitations']=list(dict.fromkeys(report['limitations']+provenance['limitations']))
 report['ground_contact_drift_proxy']={'definition':'Horizontal displacement between adjacent 30Hz samples when the same sole socket/hand joint is below 15cm at both samples. This is an unverified near-ground proxy, not labelled contact truth or a physical error metric. Robot armor may touch before the measured joint.'}
 for joint in ['SOCKET_SOLE_L','SOCKET_SOLE_R','HAND_L','HAND_R']:
  points=[f[joint] for f in report['sample_positions_blender']]
  steps=[math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:]) if a[2]<.15 and b[2]<.15]
  report['ground_contact_drift_proxy'][joint]={'candidate_steps':len(steps),'maximum_step_m':max(steps,default=None),'rms_step_m':math.sqrt(sum(v*v for v in steps)/len(steps)) if steps else None}
 (out/'retarget-report.json').write_text(json.dumps(report,indent=2))
 validation=json.loads((out/'validation-report.json').read_text());validation['limitations']=report['limitations']
 (out/'validation-report.json').write_text(json.dumps(validation,indent=2))
 print(out.name,'finalized')
