from pathlib import Path
import argparse,hashlib,json,numpy as np
from kimodo.skeleton import SOMASkeleton77
ROOT=Path(__file__).resolve().parents[1]
s=SOMASkeleton77();names=s.bone_order_names;rest=s.neutral_joints.numpy().copy();height=-rest[:,1].min();rest[:,1]+=height
reference=np.tile(np.eye(4),(77,1,1));reference[:,:3,3]=rest
p=argparse.ArgumentParser();p.add_argument('--round',choices=['pilot','round2','combat','game','game-directionfix','game-jumpfix','game-jumpanchors']);args=p.parse_args()
sources=[p for rnd in ([args.round] if args.round else ['pilot','round2','combat']) for p in sorted((ROOT/'outputs'/rnd).glob('*/motion.npz'))]
for source in sources:
 report=json.loads((source.parent/'report.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==report['motion_sha256']
 data=np.load(source);points=data['posed_joints'];world=np.tile(np.eye(4),(len(points),77,1,1));world[:,:,:3,3]=points;world[:,:,:3,:3]=data['global_rot_mats']
 out=ROOT/'retarget-source'/source.parent.name;out.mkdir(parents=True,exist_ok=True)
 bounds=np.stack([points.min(axis=1),points.max(axis=1)],axis=1)
 np.savez_compressed(out/'soma-frames.npz',joint_names=names,parent_indices=s.joint_parents.numpy(),world_transforms=world,reference_transforms=reference,surface_bounds_world=bounds,reference_surface_bounds=np.stack([rest.min(axis=0),rest.max(axis=0)]),foot_contacts=data['foot_contacts'])
 metadata={'pipeline':'Kimodo SOMA-RP-v1.2 text generation -> direct original-biped anatomical retarget','frames':len(points),'source_kind':'kimodo_text_motion','prompt':report['case']['prompt'],'seed':report['seed'],'generation':report,'source_motion_sha256':report['motion_sha256'],'limitations':['New target-proportion adaptations need fresh visual review.','Original Kimodo motion is preserved; only a constant target bind-floor calibration is applied.','No target contact IK, obstacle collision or balance solver in this baseline.','No new MotionBricks inference.']}
 (out/'source-metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
print(f'Prepared{len(sources)} immutable Kimodo SOMA inputs')
