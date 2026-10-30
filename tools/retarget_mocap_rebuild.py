"""Blender: direct SOMA -> C08 motion, retaining inversion and non-foot floor support."""
from pathlib import Path
import argparse,json,math,hashlib,struct,sys
import bpy
import numpy as np
from mathutils import Matrix,Vector,Quaternion

import os
_candidates=[Path(os.environ['MOTION_LAB_WORKSPACE'])] if os.environ.get('MOTION_LAB_WORKSPACE') else list(Path(__file__).resolve().parents)
ROOT=next((p for p in _candidates if (p/'evaluation').is_dir() and (p/'video-mocap').is_dir() and (p/'assets').is_dir()),None)
if ROOT is None:raise RuntimeError('Set MOTION_LAB_WORKSPACE to the original workspace; private captures and recovered SOMA inputs are not bundled.')
parser=argparse.ArgumentParser();parser.add_argument('name');parser.add_argument('method',choices=['raw','cleaned','single','window']);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
NAME=args.name;METHOD=args.method;BODY='c08';SOURCE=ROOT/'evaluation/mocap-rebuild'/NAME/METHOD
ASSETS={'c08':'assets/c08-worker/c08_d0_lod1.glb','brek43':'assets/b-rek43/b_rek43_d0_lod1.glb','eva-k7':'assets/eva-k7/eva_k7_d0_lod1.glb','meshy-fighter':'assets/meshy-fighter/meshy-fighter-rigged.glb'}
ASSET=ROOT/ASSETS[BODY];OUT=ROOT/'evaluation/mocap-rebuild/exports'/NAME/METHOD;OUT.mkdir(parents=True,exist_ok=True)
data=np.load(SOURCE/'soma-frames.npz');metadata=json.loads((SOURCE/'source-metadata.json').read_text(encoding='utf-8'))
names=data['joint_names'].tolist();lookup={n:i for i,n in enumerate(names)}
world=data['world_transforms'];reference=data['reference_transforms'];count=len(world)
clip_name='MBR_'+NAME.replace('-','_')+'_'+METHOD
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ASSET))
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
# glTF importer creates non-renderable bone widgets; exclude them from geometry and export.
for bone in arm.pose.bones:bone.custom_shape=None
for helper in list(bpy.data.objects):
 if helper.type=='MESH' and not any(m.type=='ARMATURE' and m.object==arm for m in helper.modifiers):bpy.data.objects.remove(helper,do_unlink=True)
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
# Pilot inputs already share one raw-source ground/yaw normalization. Joint bounds
# are diagnostics, not skin bounds; do not use them as a new floor estimate.
source_ground=0.0
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
 limbmap[hand]=(prefix+'Hand',prefix+'HandMiddle1',bind_swing((H[f'FINGER_{side}2_01']-H[hand]) if f'FINGER_{side}2_01' in H else (arm.data.bones[hand].tail_local-H[hand]),prefix+'Hand',prefix+'HandMiddle1'))
# Evaluate every original skin vertex with its original normalized weights.
# The same vectorized linear-blend calculation supports rigid robot plates and
# the Meshy surface, whose vertices have up to four influences.
geometry=[];vertex_count=0;max_weight_error=0
for obj in bpy.data.objects:
 if obj.type!='MESH':continue
 mesh_to_arm=arm.matrix_world.inverted()@obj.matrix_world
 groups={g.index:g.name for g in obj.vertex_groups};bybone={};base=vertex_count
 vertex_count+=len(obj.data.vertices)
 for vertex in obj.data.vertices:
  weights=[g for g in vertex.groups if g.weight>1e-8 and groups.get(g.group) in H]
  total=sum(g.weight for g in weights);max_weight_error=max(max_weight_error,abs(total-1))
  assert abs(total-1)<1e-4,('Invalid original weight total',BODY,vertex.index,total)
  for weight in weights:
   name=groups[weight.group];point=arm.data.bones[name].matrix_local.inverted()@(mesh_to_arm@vertex.co)
   bybone.setdefault(name,[]).append((base+vertex.index,(*point,1.),weight.weight))
 for name,rows in bybone.items():geometry.append((name,np.array([r[0] for r in rows]),np.array([r[1] for r in rows],dtype=np.float64),np.array([r[2] for r in rows])))

scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=0;scene.frame_end=count-1
arm.animation_data_create();action=bpy.data.actions.new(clip_name);arm.animation_data.action=action
last_quaternion={};samples=[];ground_offsets=[];uncorrected_pelvis=[];min_after=math.inf
for frame in range(count):
 scene.frame_set(frame);pos,ori={},{}
 def put(name,p=None,q=None):
  if name not in H:return
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
 coordinates=np.zeros((vertex_count,3),dtype=np.float64)
 for name,indices,points,weights in geometry:
  m=np.array(matrices[name],dtype=float);coordinates[indices]+=(points@m.T)[:,:3]*weights[:,None]
 assert np.isfinite(coordinates).all()
 low=float(coordinates[:,2].min())
 # One constant calibration from the first target pose, then preserve every vertical motion.
 # This deliberately exposes later contact errors instead of adding per-frame vertical bobbing.
 if frame==0:
  calibration_path=ROOT/'evaluation/mocap-rebuild/exports'/NAME/'raw'/'retarget-report.json'
  if METHOD=='cleaned' and not calibration_path.exists():raise RuntimeError('Bake raw first so raw and cleaned use exactly the same calibration')
  constant_floor_offset=float(json.loads(calibration_path.read_text(encoding='utf-8'))['ground_vertical_offsets_m'][0]) if METHOD=='cleaned' else .015-low
 offset=constant_floor_offset;ground_offsets.append(offset);uncorrected_pelvis.append(list(pos['PELVIS']))
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
 samples.append({name:list(pos[name]) for name in ('PELVIS','HEAD','KNEE_L','KNEE_R','ANKLE_L','ANKLE_R','HAND_L','HAND_R','SOCKET_SOLE_L','SOCKET_SOLE_R') if name in pos})
 min_after=min(min_after,low+offset)
for curve in action.fcurves:
 for point in curve.keyframe_points:point.interpolation='LINEAR'
scene.frame_set(0);arm.show_in_front=True
arm['motion_provenance']='SOMA mocap rebuild pilot: '+METHOD+'; inspect method provenance report'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'c08-mocap.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'c08-mocap.glb'),export_format='GLB',export_animations=True,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_force_sampling=True,export_skins=True,export_yup=True,export_tangents=True)
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
for image in document.get('images',[]):
 if 'bufferView' in image:slots.append((image,'bufferView'))
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
report={**metadata,'clip':clip_name,'kind':'video_mocap','status':'experimental mocap reconstruction pilot; requires motion/contact review','fps':30,'duration_s':(count-1)/30,'source_to_target_root_scale':root_scale,'initial_heading_removed_rad':initial_yaw,'root_motion':'MOTION owns horizontal displacement only; PELVIS holds full orientation including inversion. No yaw extraction singularity during a roll. Place the entire glTF scene in an instance wrapper.','mapping':{name:{'source_joint':v[0],'source_child':v[1]} for name,v in limbmap.items()},'ground_policy':'One constant whole-avatar vertical offset places the first pose lowest skinned vertex 15 mm above the floor. No per-frame grounding, no foot locks, no limb stretching. Later penetration and hovering are retained and measured, not silently repaired.','ground_vertical_offsets_m':ground_offsets.tolist(),'max_abs_ground_correction_m':float(np.abs(ground_offsets).max()),'rms_ground_correction_m':float(np.sqrt(np.mean(ground_offsets**2))),'baked_key_minimum_floor_m':min_after,'source_pelvis_before_ground_blender':uncorrected_pelvis,'sample_positions_blender':samples,'source_asset_sha256':hashlib.sha256(ASSET.read_bytes()).hexdigest(),'limitations':metadata['limitations']+['Target proportions differ from the performer','A constant first-pose ground calibration does not establish later support: visible hovering or penetration can remain','No hand/foot pinning or armor self-collision solve','Fingers remain at original rig rest pose; source hand detail is not reproduced','MotionBricks methods are single/window; cleaned is non-neural. No G1 intermediate or physical robot control']}
(OUT/'retarget-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
report.update(body=BODY,method=METHOD,source_asset=str(ASSET.relative_to(ROOT)),vertices=vertex_count,skin_weight_max_error=max_weight_error,body_bones=len(H))
if BODY=='meshy-fighter':
 attribution=json.loads((ROOT/'assets/meshy-fighter/rig-report.json').read_text(encoding='utf-8'));report['attribution']=attribution
 document['asset']['extras']={k:attribution[k] for k in ('source_title','author','author_url','source_url','license','license_url')}
 encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+binary)
(OUT/'retarget-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(OUT/'artifact-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'c08-mocap.glb',OUT/'c08-mocap.blend',SOURCE/'soma-frames.npz')},indent=2))
print('DIRECT_SOMA_C08_READY',NAME,count,'frames','ground correction max',report['max_abs_ground_correction_m'],flush=True)
