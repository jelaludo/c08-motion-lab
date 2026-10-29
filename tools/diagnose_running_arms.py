"""Measure local bone rotations and write an isolated upper-body cleanup proposal.

Requires local evaluation inputs and the separately obtained CC0 Quaternius asset;
these working inputs are not bundled with this public checkout. Example:
  python tools/diagnose_running_arms.py --workspace G:/Dev/MotionBricks
  python tools/diagnose_running_arms.py --workspace /path/to/workspace --output /tmp/arms

Default output: this public repository's research directory. See
research/running-arms-reproduction.md for source requirements and dependencies.
"""
from pathlib import Path
import argparse,json,struct,hashlib

SCRIPT_ROOT=Path(__file__).resolve().parents[1]
REPO=SCRIPT_ROOT if (SCRIPT_ROOT/'docs').is_dir() else SCRIPT_ROOT/'public/c08-motion-lab'
parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--workspace',type=Path,help='Local MotionBricks workspace containing evaluation/ and assets/. Auto-detected from enclosing directories when omitted.')
parser.add_argument('--output',type=Path,default=REPO/'research',help='Destination for report and proposed GLB (default: repository research/). Existing same-named outputs are overwritten.')
args=parser.parse_args()
if args.workspace is not None:
 ROOT=args.workspace.expanduser().resolve()
else:
 ROOT=next((p for p in [Path.cwd(),*Path.cwd().parents,SCRIPT_ROOT,*SCRIPT_ROOT.parents] if (p/'evaluation').is_dir() and (p/'assets').is_dir()),None)
 if ROOT is None:parser.error('No local MotionBricks workspace found. Pass --workspace PATH containing evaluation/ and assets/. The public checkout alone does not contain the required working inputs.')
required=[ROOT/'evaluation/reactive-round4/speedzones_reactive_1'/name for name in ['c08-motionbricks-test.glb','g1-motion.npz','prediction-trace.json']]
missing=[str(p) for p in required if not p.is_file()]
references=list((ROOT/'assets/quaternius').rglob('UAL1_Standard_RM.glb')) if (ROOT/'assets/quaternius').is_dir() else []
if not references:missing.append(str(ROOT/'assets/quaternius/**/UAL1_Standard_RM.glb'))
if missing:parser.error('Required local source inputs are missing:\n  '+'\n  '.join(missing)+'\nSee research/running-arms-reproduction.md; no outputs were written.')
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scipy.ndimage import gaussian_filter1d
OUT=args.output.expanduser().resolve();OUT.mkdir(parents=True,exist_ok=True)
MB=required[0]
CC0=sorted(references)[0]
TYPE={'SCALAR':1,'VEC3':3,'VEC4':4};DT={5126:'<f4',5123:'<u2',5125:'<u4'}
def read(path):
 raw=bytearray(path.read_bytes());n=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+n]);base=28+n
 def array(i):
  a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']];count=a['count'];dim=TYPE[a['type']];dt=np.dtype(DT[a['componentType']]);stride=v.get('byteStride',dim*dt.itemsize)
  return np.ndarray((count,dim),dtype=dt,buffer=raw,offset=base+v.get('byteOffset',0)+a.get('byteOffset',0),strides=(stride,dt.itemsize))
 return raw,doc,array
raw,doc,A=read(MB);cr,cd,C=read(CC0)
clip=doc['animations'][0];ref=next(a for a in cd['animations']if a['name']=='Sprint_Loop')
JOINTS={'CHEST':'spine_03','SHOULDER_L':None,'UPPER_ARM_L':'upperarm_l','FOREARM_L':'lowerarm_l','HAND_L':'hand_l','SHOULDER_R':None,'UPPER_ARM_R':'upperarm_r','FOREARM_R':'lowerarm_r','HAND_R':'hand_r'}
def channels(d,clip,access):
 result={}
 for channel in clip['channels']:
  if channel['target']['path']!='rotation':continue
  sampler=clip['samplers'][channel['sampler']];name=d['nodes'][channel['target']['node']]['name']
  assert sampler.get('interpolation','LINEAR')=='LINEAR'
  result[name]=(access(sampler['input']).ravel().astype(float),access(sampler['output']).astype(float),sampler['output'])
 return result
mb=channels(doc,clip,A);cc=channels(cd,ref,C)
trace=json.loads((MB.parent/'prediction-trace.json').read_text())['metadata']['segments'];joins=np.array([s['start_frame']/30 for s in trace[1:]])
q=np.load(MB.parent/'g1-motion.npz')['qpos'];ground_speed=np.r_[np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1)*30,0]
def stats(x):
 if len(x)==0:return None
 return {'samples':len(x),'median':float(np.median(x)),'p95':float(np.percentile(x,95)),'max':float(np.max(x)),'mean':float(np.mean(x))}
def diagnostic(source,fps,is_mb):
 rows={}
 for name,(times,quats,idx)in source.items():
  if is_mb and name not in JOINTS or not is_mb and name not in JOINTS.values():continue
  t=np.arange(0,times[-1]+1e-8,1/fps);r=Slerp(times,Rotation.from_quat(quats))(t)
  omega=(r[1:]*r[:-1].inv()).as_rotvec()*fps;speed=np.linalg.norm(omega,axis=1);acc=np.linalg.norm(np.diff(omega,axis=0)*fps,axis=1)
  row={'angular_speed_rad_s':stats(speed),'angular_acceleration_rad_s2':stats(acc)}
  if is_mb:
   mid=(t[1:]+t[:-1])/2;acc_t=t[1:-1];active=np.interp(mid,np.arange(len(q))/30,ground_speed)>1.5;active_a=np.interp(acc_t,np.arange(len(q))/30,ground_speed)>1.5
   near=np.min(np.abs(mid[:,None]-joins),axis=1)<=1/fps;near_a=np.min(np.abs(acc_t[:,None]-joins),axis=1)<=1/fps
   row.update(moving_speed=stats(speed[active]),moving_acceleration=stats(acc[active_a]),moving_join_speed=stats(speed[active&near]),moving_within_segment_speed=stats(speed[active&~near]),moving_join_acceleration=stats(acc[active_a&near_a]),moving_within_segment_acceleration=stats(acc[active_a&~near_a]))
  rows[name]=row
 return rows
before={str(fps):diagnostic(mb,fps,True)for fps in [30,60]};reference={str(fps):diagnostic(cc,fps,False)for fps in [30,60]}
# Smooth only named upper-body rotation accessors; root/legs/positions/binary layout untouched.
original=bytes(raw);changed=[]
for name,(times,quat,index)in mb.items():
 if name not in JOINTS:continue
 adjusted=quat.copy()
 for i in range(1,len(adjusted)):
  if np.dot(adjusted[i],adjusted[i-1])<0:adjusted[i]*=-1
 hz=1/float(np.median(np.diff(times)));smoothed=gaussian_filter1d(adjusted,sigma=.04*hz,axis=0,mode='nearest');smoothed/=np.linalg.norm(smoothed,axis=1)[:,None];A(index)[:]=smoothed.astype(np.float32);changed.append({'bone':name,'accessor':index,'keys':len(times),'sample_rate':hz})
pilot=OUT/'running-arms-upperbody-filter-proposal.glb';pilot.write_bytes(raw)
after={str(fps):diagnostic(channels(doc,clip,A),fps,True)for fps in [30,60]}
# Verify every unselected animation output accessor remains byte-identical.
_,old_doc,old_A=read(MB);changed_ids={x['accessor']for x in changed};untouched=[]
for anim in doc['animations']:
 for sampler in anim['samplers']:
  index=sampler['output']
  if index in changed_ids:continue
  assert A(index).tobytes()==old_A(index).tobytes();untouched.append(index)
report={'method':'Sample local bone rotations through glTF LINEAR quaternion interpolation at30/60Hz. Parent-coordinate angular velocity=log(q_next*q_current^-1)/dt, angular acceleration=finite difference of that vector. Moving samples require native ground speed>1.5m/s. Join windows are within one diagnostic sample of recorded neural segment start; other moving samples are within-segment.','sources':{'motionbricks_glb':str(MB.relative_to(ROOT)),'motionbricks_sha256':hashlib.sha256(original).hexdigest(),'native_npz_sha256':hashlib.sha256((MB.parent/'g1-motion.npz').read_bytes()).hexdigest(),'quaternius_glb':str(CC0.relative_to(ROOT)),'quaternius_sha256':hashlib.sha256(cr).hexdigest(),'quaternius_clip':'Sprint_Loop','quaternius_license':'CC0'},'bone_reference_mapping':JOINTS,'before':before,'cc0_reference':reference,'proposal':{'artifact':pilot.name,'sha256':hashlib.sha256(raw).hexdigest(),'method':'Hemisphere-unwrapped quaternion component Gaussian smoothing with40ms sigma, then unit normalization; only named upper-body local rotation accessor values change. Not neural generation.','modified_channels':changed,'unmodified_animation_output_accessors':len(set(untouched)),'root_legs_position_accessors_byte_identical':True,'native_npz_contacts_unmodified':True,'requires_visual_review':True,'balance_or_center_of_mass_correction':False,'after':after},'limits':['Local rotation derivatives locate rapid changes; they do not prove their cause or establish perceptual quality.','Reference and robot differ in rig, degrees of freedom, running speed, style and clip duration. Scalar derivatives are descriptive rather than an equivalent quality benchmark.','Retargeted C08 includes a120Hz export bake; diagnostics cannot separate neural source, retargeting and interpolation effects without additional controlled runs.','Smoothing may erase purposeful arm action or alter hand placement; only a separate proposal artifact is created.','Center of mass requires mass distribution plus support geometry and dynamics; these joint-rotation diagnostics cannot certify crouch balance.','Raw G1 source, all published123takes and review storage are unchanged.']}
(OUT/'running-arms-diagnostic.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('REPORT',str(OUT/'running-arms-diagnostic.json'))
for name in ['UPPER_ARM_L','FOREARM_L','UPPER_ARM_R','FOREARM_R']:
 b=before['60'][name];a=after['60'][name];print(name,'acc_p95',b['moving_acceleration']['p95'],'filtered',a['moving_acceleration']['p95'],'join',b['moving_join_acceleration']['p95'],'within',b['moving_within_segment_acceleration']['p95'])
