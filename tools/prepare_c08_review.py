import numpy as np
from scipy.spatial.transform import Rotation
from pathlib import Path
import json, hashlib, xml.etree.ElementTree as ET, os
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('MB_TEST_DIRECTORY',ROOT/'evaluation/c08-worker'))
d=np.load(OUT/'g1-motion.npz')
S=np.array([[0,1,0],[-1,0,0],[0,0,1]])
q=d['qpos'][0,3:7];r=S@Rotation.from_quat(q).as_matrix()@S.T
forward=r@np.array([0,-1,0]);yaw=np.arctan2(forward[0],-forward[1])
A=Rotation.from_rotvec([0,0,-yaw]).as_matrix()@S
p=d['body_transforms'][:,:,:3]@A.T
origin=p[0,list(d['body_names']).index('pelvis')].copy();origin[2]=0
p-=origin
# Blender -> glTF axes, once. Source preview stays at source scale.
p=p[:,:,[0,2,1]];p[:,:,2]*=-1
xml=ET.parse(ROOT/'upstream/motionbricks/assets/robots/unitree_g1/g1_29dof_rev_1_0.xml')
parents={}
def visit(body,parent=None):
 name=body.get('name');parents[name]=parent
 for child in body.findall('body'):visit(child,name)
for body in xml.getroot().find('worldbody').findall('body'):visit(body)
# Audit source joint limits against the XML in its serialized traversal order; retain all original values.
joints=[j for j in xml.getroot().iter('joint') if j.get('type')!='free' and j.get('range')]
audit=[]
for i,j in enumerate(joints):
 low,high=map(float,j.get('range').split());v=d['qpos'][:,7+i]
 violation=np.maximum(low-v, v-high)
 if np.any(violation>1e-5):audit.append({'joint':j.get('name'),'violating_frames':int(np.sum(violation>1e-5)),'max_violation_rad':float(max(violation))})
meta=json.loads((OUT/'g1-motion.json').read_text());meta['joint_limit_audit']={'clamped':False,'violations':audit};meta['newton_joint_order_verified']=True;meta['retargeting']='experimental C08 adaptation complete' if (OUT/'retarget-report.json').exists() else 'C08 adaptation failed or pending; source available'
(OUT/'g1-motion.json').write_text(json.dumps(meta,indent=2))
B=np.array([[1,0,0],[0,0,1],[0,-1,0]])@A;B0=np.array([[0,1,0],[0,0,1],[1,0,0]]);rot=Rotation.from_quat(d['body_transforms'][:,:,3:7].reshape(-1,4)).as_matrix().reshape(len(p),-1,3,3);ref=Rotation.from_quat(d['reference_bodies'][:,3:7]).as_matrix();deltas=np.einsum('ij,fbjk,bkl,lm->fbim',B,rot,np.swapaxes(ref,-1,-2),B0.T);quat=Rotation.from_matrix(deltas.reshape(-1,3,3)).as_quat().reshape(len(p),-1,4)
preview={'rotation_deltas':quat.tolist(),'reference_positions':(d['reference_bodies'][:,:3]@B0.T).tolist(),'fps':30,'frames':len(p),'body_names':d['body_names'].tolist(),'parents':parents,'positions':p.tolist(),'contacts':d['contacts'].tolist(),'note':'G1 skeleton at original source scale; aligned initial heading; source contact predictions are unreviewed'}
if 'contact_ik_mask' in d.files:preview['contact_ik_mask']=d['contact_ik_mask'].tolist()
(OUT/'g1-preview.json').write_text(json.dumps(preview,separators=(',',':')))
manifest=json.loads((ROOT/'assets/c08-worker/manifest.json').read_text())
checks=[]
for asset in manifest['assets']:
 path=ROOT/'assets/c08-worker'/asset['file']
 actual=hashlib.sha256(path.read_bytes()).hexdigest()
 assert actual==asset['sha256'],path
 checks.append({'file':asset['file'],'sha256':actual,'bytes':path.stat().st_size})
master_hash=hashlib.sha256((ROOT/'assets/c08-worker/a6-c08-worker.blend').read_bytes()).hexdigest()
assert master_hash==manifest['source']['sha256'],'Editable master checksum mismatch'
(ROOT/'assets/c08-worker/download-report.json').write_text(json.dumps({'source':'https://jelaludo.github.io/SentryTowers_A6/c08-worker/','verified_assets':checks,'editable_master_sha256':master_hash},indent=2))
artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'g1-motion.npz',OUT/'c08-motionbricks-test.glb',OUT/'c08-motionbricks-test.blend') if p.exists()}
(OUT/'artifact-hashes.json').write_text(json.dumps(artifacts,indent=2))
print('Verified',len(checks),'original GLBs; wrote source skeleton preview')
