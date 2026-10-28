"""Blender: direct SOMA -> C08 motion, retaining inversion and non-foot floor support."""
from pathlib import Path
import argparse,json,math,hashlib,struct,sys
import bpy
import numpy as np
from mathutils import Matrix,Vector,Quaternion

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('name',nargs='?',default='ukemi');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
NAME=args.name;OUT=ROOT/'video-mocap/c08-retarget'/NAME
data=np.load(OUT/'soma-frames.npz');metadata=json.loads((OUT/'source-metadata.json').read_text(encoding='utf-8'))
names=data['joint_names'].tolist();lookup={n:i for i,n in enumerate(names)}
world=data['world_transforms'];reference=data['reference_transforms'];count=len(world)
clip_name='VC_'+NAME.replace('-','_')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/c08-worker/c08_d0_lod1.glb'))
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for obj in bpy.data.objects:
 if obj.animation_data:obj.animation_data_clear()
for bone in arm.pose.bones:bone.matrix_basis=Matrix.Identity(4)
H={b.name:b.head_local.copy() for b in arm.data.bones};parents={b.name:b.parent.name if b.parent else None for b in arm.data.bones}
# Source SOMA is Y up / +Z forward. Blender is Z up / -Y forward.
S=Matrix(((1,0,0),(0,0,-1),(0,1,0)));qs=S.to_quaternion()
def source_rotation(frame,name):return Matrix(world[frame,lookup[name],:3,:3].tolist()).to_quaternion().normalized()
def ref_rotation(name):return Matrix(reference[lookup[name],:3,:3].tolist()).to_quaternion().normalized()
initial=qs@(source_rotation(0,'Hips')@ref_rotation('Hips').inverted())@qs.inverted()
forward=initial@Vector((0,-1,0));initial_yaw=math.atan2(forward.x,-forward.y)
align=Quaternion((0,0,1),-initial_yaw);A=align.to_matrix()@S
source_ground=float(data['surface_bounds_world'][:,0,1].min())
ref_height=float(reference[0,1,3]-data['reference_surface_bounds'][0,1])
root_scale=H['PELVIS'].z/ref_height
origin=A@Vector(world[0,lookup['Hips'],:3,3]);origin.z=0
def src(frame,name):return A@Vector(world[frame,lookup[name],:3,3])
def delta(frame,name):return align@qs@(source_rotation(frame,name)@ref_rotation(name).inverted())@qs.inverted()
def bind_swing(target_vector,parent,child):
 direction=S@Vector(reference[lookup[child],:3,3]-reference[lookup[parent],:3,3])
 return Vector(target_vector).rotation_difference(direction)
limbmap={}
for side,prefix in [('L','Left'),('R','Right')]:
 for target,child,source,source_child in [('HIP','KNEE','Leg','Shin'),('KNEE','ANKLE','Shin','Foot'),('UPPER_ARM','FOREARM','Arm','ForeArm'),('FOREARM','HAND','ForeArm','Hand')]:
  n=target+'_'+side;limbmap[n]=(prefix+source,prefix+source_child,bind_swing(H[child+'_'+side]-H[n],prefix+source,prefix+source_child))
 hand='HAND_'+side
 limbmap[hand]=(prefix+'Hand',prefix+'HandMiddle1',bind_swing(H[f'FINGER_{side}2_01']-H[hand],prefix+'Hand',prefix+'HandMiddle1'))
# Each rigid armor plate has one bone influence. Evaluate its true vertices from the bind matrix.
geometry=[]
for obj in bpy.data.objects:
 if obj.type!='MESH':continue
 mesh_to_arm=arm.matrix_world.inverted()@obj.matrix_world
 groups={g.index:g.name for g in obj.vertex_groups}
 bybone={}
 for vertex in obj.data.vertices:
  weights=[g for g in vertex.groups if g.weight>1e-7]
  if not weights:continue
  total=sum(g.weight for g in weights)
  assert abs(total-1)<1e-5 and len(weights)==1,'C08 plate must stay rigid'
  name=groups[weights[0].group];point=arm.data.bones[name].matrix_local.inverted()@(mesh_to_arm@vertex.co)
  bybone.setdefault(name,[]).append((*point,1.))
 for name,points in bybone.items():geometry.append((name,np.array(points,dtype=np.float64)))

scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=0;scene.frame_end=count-1
arm.animation_data_create();action=bpy.data.actions.new(clip_name);arm.animation_data.action=action
last_quaternion={};samples=[];ground_offsets=[];uncorrected_pelvis=[];min_after=math.inf
for frame in range(count):
 scene.frame_set(frame);pos,ori={},{}
 def put(name,p=None,q=None):
  parent=parents[name]
  pos[name]=Vector(p) if p is not None else (pos[parent]+ori[parent]@(H[name]-H[parent]) if parent else H[name].copy())
  ori[name]=q.copy() if q is not None else (ori[parent].copy() if parent else Quaternion())
 hips=src(frame,'Hips');rootxy=(hips-origin)*root_scale;rootxy.z=0
 put('MOTION',rootxy,Quaternion())
 pelvis=rootxy+Vector((0,0,(float(world[frame,lookup['Hips'],1,3])-source_ground)*root_scale))
 put('PELVIS',pelvis,delta(frame,'Hips'))
 put('WAIST',q=delta(frame,'Spine2'));put('CHEST',q=delta(frame,'Chest'))
 put('NECK',q=delta(frame,'Neck2'));put('HEAD',q=delta(frame,'Head'));put('SENSOR_YAW')
 for side,prefix in [('L','Left'),('R','Right')]:
  for target in ('HIP','KNEE','ANKLE','TOE'):
   name=target+'_'+side
   if name in limbmap:put(name,q=delta(frame,limbmap[name][0])@limbmap[name][2])
   elif target=='ANKLE':put(name,q=delta(frame,prefix+'Foot'))
   else:put(name,q=delta(frame,prefix+'ToeBase'))
  put('SHOULDER_'+side,q=delta(frame,prefix+'Shoulder'))
  for target in ('UPPER_ARM','FOREARM','HAND'):
   name=target+'_'+side;put(name,q=delta(frame,limbmap[name][0])@limbmap[name][2])
 for name in H:
  if name not in pos:put(name)
 matrices={name:Matrix.Translation(pos[name])@ori[name].to_matrix().to_4x4()@arm.data.bones[name].matrix_local.to_3x3().to_4x4() for name in H}
 low=math.inf
 for name,points in geometry:
  m=np.array(matrices[name],dtype=float);coordinates=points@m.T;low=min(low,float(coordinates[:,2].min()))
 # All source exercises have body support. Translate the complete avatar, not feet/limbs individually.
 # This preserves intentional shoulder/back/hand contacts and inversion; it is not an IK/contact solve.
 offset=.015-low;ground_offsets.append(offset);uncorrected_pelvis.append(list(pos['PELVIS']))
 for name in H:
  if name=='MOTION':continue
  pos[name].z+=offset
 matrices={}
 for name in H:
  b=arm.data.bones[name];parent=parents[name]
  m=Matrix.Translation(pos[name])@ori[name].to_matrix().to_4x4()@b.matrix_local.to_3x3().to_4x4();matrices[name]=m
  kwargs={'parent_matrix':matrices[parent],'parent_matrix_local':arm.data.bones[parent].matrix_local} if parent else {}
  pb=arm.pose.bones[name];pb.rotation_mode='QUATERNION';pb.matrix_basis=b.convert_local_to_pose(m,b.matrix_local,invert=True,**kwargs)
  if name.startswith(('SOCKET_','FINGER_','THUMB_')) or name=='SENSOR_YAW':continue
  q=pb.rotation_quaternion.copy()
  if name in last_quaternion and q.dot(last_quaternion[name])<0:q.negate();pb.rotation_quaternion=q
  last_quaternion[name]=q.copy()
  pb.keyframe_insert(data_path='location',frame=frame);pb.keyframe_insert(data_path='rotation_quaternion',frame=frame)
 samples.append({name:list(pos[name]) for name in ('PELVIS','HEAD','KNEE_L','KNEE_R','ANKLE_L','ANKLE_R','HAND_L','HAND_R','SOCKET_SOLE_L','SOCKET_SOLE_R')})
 min_after=min(min_after,low+offset)
for curve in action.fcurves:
 for point in curve.keyframe_points:point.interpolation='LINEAR'
scene.frame_set(0);arm.show_in_front=True
arm['motion_provenance']='Direct GEM-X recovered SOMA to C08 retarget of user-provided video; not MotionBricks-generated'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'c08-mocap.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'c08-mocap.glb'),export_format='GLB',export_animations=True,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_force_sampling=True,export_skins=True,export_yup=True)
# Keep game-owned controls and sockets free of animation channels.
path=OUT/'c08-mocap.glb';payload=path.read_bytes();size=struct.unpack_from('<I',payload,12)[0];document=json.loads(payload[20:20+size]);binary=payload[20+size:]
for i,node in enumerate(document['nodes']):
 if 'skin' not in node:continue
 assert not any(k in node for k in ('matrix','translation','rotation','scale'))
 for parent in document['nodes']:
  if i in parent.get('children',[]):parent['children'].remove(i)
 for s in document['scenes']:
  if i not in s['nodes']:s['nodes'].append(i)
for animation in document['animations']:
 animation['name']=clip_name
 animation['channels']=[c for c in animation['channels'] if c['target']['path']!='scale' and not document['nodes'][c['target']['node']].get('name','').startswith(('SOCKET_','FINGER_','THUMB_')) and document['nodes'][c['target']['node']].get('name') not in ('ROOT','SENSOR_YAW')]
 used=sorted({c['sampler'] for c in animation['channels']});mapping={a:b for b,a in enumerate(used)};animation['samplers']=[animation['samplers'][i] for i in used]
 for c in animation['channels']:c['sampler']=mapping[c['sampler']]
slots=[]
for mesh in document.get('meshes',[]):
 for primitive in mesh['primitives']:
  slots.extend((primitive['attributes'],k) for k in primitive['attributes'])
  if 'indices' in primitive:slots.append((primitive,'indices'))
for skin in document.get('skins',[]):
 if 'inverseBindMatrices' in skin:slots.append((skin,'inverseBindMatrices'))
for animation in document['animations']:
 for sampler in animation['samplers']:slots.extend(((sampler,'input'),(sampler,'output')))
used=sorted({d[k] for d,k in slots});mapping={a:b for b,a in enumerate(used)};document['accessors']=[document['accessors'][i] for i in used]
for d,k in slots:d[k]=mapping[d[k]]
slots=[]
for accessor in document['accessors']:
 if 'bufferView' in accessor:slots.append((accessor,'bufferView'))
 if 'sparse' in accessor:slots.extend(((accessor['sparse']['indices'],'bufferView'),(accessor['sparse']['values'],'bufferView')))
used=sorted({d[k] for d,k in slots});mapping={a:b for b,a in enumerate(used)};document['bufferViews']=[document['bufferViews'][i] for i in used]
for d,k in slots:d[k]=mapping[d[k]]
encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+binary)
# A source-skeleton overlay in the same review basis, but at its true source scale.
source_points=np.empty((count,len(names),3))
for frame in range(count):
 for i in range(len(names)):
  p=A@Vector(world[frame,i,:3,3]);p-=origin;p.z-=source_ground;source_points[frame,i]=[p.x,p.z,-p.y]
preview={'fps':30,'frames':count,'body_names':names,'parents':{name:(names[int(data['parent_indices'][i])] if int(data['parent_indices'][i])>=0 else None) for i,name in enumerate(names)},'positions':source_points.tolist(),'contacts':[[0,0,0,0]]*count,'note':'Raw recovered human SOMA skeleton; not a G1 robot; fixed source-ground/heading display conversion only'}
(OUT/'source-preview.json').write_text(json.dumps(preview,separators=(',',':')),encoding='utf-8')
ground_offsets=np.array(ground_offsets)
report={**metadata,'clip':clip_name,'kind':'video_mocap','status':'experimental direct C08 retarget; requires motion/contact review','fps':30,'duration_s':(count-1)/30,'source_to_target_root_scale':root_scale,'initial_heading_removed_rad':initial_yaw,'root_motion':'MOTION owns horizontal displacement only; PELVIS holds full orientation including inversion. No yaw extraction singularity during a roll. Place the entire glTF scene in an instance wrapper.','mapping':{name:{'source_joint':v[0],'source_child':v[1]} for name,v in limbmap.items()},'ground_policy':'Complete avatar is translated vertically each frame so its lowest rigid armor vertex is 15 mm above a flat floor. No foot locks, no standing pose constraint, no limb stretching; this is a measured presentation correction, not physical contact IK.','ground_vertical_offsets_m':ground_offsets.tolist(),'max_abs_ground_correction_m':float(np.abs(ground_offsets).max()),'rms_ground_correction_m':float(np.sqrt(np.mean(ground_offsets**2))),'baked_key_minimum_floor_m':min_after,'source_pelvis_before_ground_blender':uncorrected_pelvis,'sample_positions_blender':samples,'source_asset_sha256':hashlib.sha256((ROOT/'assets/c08-worker/c08_d0_lod1.glb').read_bytes()).hexdigest(),'limitations':metadata['limitations']+['C08 has much broader armor and different proportions from the performer','Whole-avatar grounding changes vertical root motion, especially during inversion; offsets are reported','No hand/foot pinning or armor self-collision solve','Finger curls remain at C08 rest pose; source hand detail is not reproduced','Not a MotionBricks-generated clip, not a G1 CSV, not physical robot control']}
(OUT/'retarget-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(OUT/'artifact-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'c08-mocap.glb',OUT/'c08-mocap.blend',OUT/'soma-frames.npz')},indent=2))
print('DIRECT_SOMA_C08_READY',NAME,count,'frames','ground correction max',report['max_abs_ground_correction_m'],flush=True)

