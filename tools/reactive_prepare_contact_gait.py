"""Prepare the explicitly authored/contact-adapted CC0 crouch cycle for replay."""
from pathlib import Path
import numpy as np,json,hashlib
from reactive_contact_gait import contact_gait
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'evaluation/reactive-round4';source=folder/'cc0-crouch-fitted.npz';original=np.load(source)['qpos'];q,contacts,report=contact_gait(original)
assert report['maximum_ankle_target_error_m']<.001,report['maximum_ankle_target_error_m']
assert report['maximum_foot_rotation_error_rad']<.001
report.update(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),provenance_type='cc0_quaternius_contact_adapted',source_license='CC0-1.0',neural_calls=0,frames=len(q),sample_rate=30,root_height_preserved=bool(np.array_equal(original[:,2],q[:,2])),loop_hinge_seam_max_rad=float(np.max(np.abs(q[-1,7:]-q[0,7:]))),maximum_hinge_step_rad=float(np.max(np.abs(np.diff(q[:,7:],axis=0)))))
np.savez_compressed(folder/'cc0-crouch-contact.npz',qpos=q,contacts=contacts,original_fitted_qpos=original)
(folder/'cc0-crouch-contact.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k!='errors'}))
