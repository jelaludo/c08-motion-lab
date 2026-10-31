"""Blender: bake the authored support cleanup onto the unchanged original C08 rig."""
from pathlib import Path
import argparse,hashlib,json,struct,sys
import bpy,numpy as np
from mathutils import Matrix,Quaternion
import os

def discover_root():
 explicit=os.environ.get('MOTIONBRICKS_ROOT')
 candidates=[Path(explicit).expanduser().resolve()] if explicit else []
 candidates += list(Path(__file__).resolve().parents) + [Path.cwd().resolve()]
 for candidate in candidates:
  if (candidate/'evaluation/mocap-rebuild/exports').is_dir() or (candidate/'public/c08-motion-lab/docs/mocap-rebuild').is_dir():return candidate
 raise RuntimeError('Set MOTIONBRICKS_ROOT to the original MotionBricks workspace; private cleaned .blend inputs are needed for exact reproduction.')

ROOT=discover_root();BASE=ROOT/'evaluation/anchored-cleanup'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['ukemi','sumo-stomp']
for slug in args:
 folder=BASE/slug;data=np.load(folder/'cleanup-data.npz');report=json.loads((folder/'cleanup-report.json').read_text(encoding='utf-8'))
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'evaluation/mocap-rebuild/exports'/slug/'cleaned/c08-mocap.blend'))
 arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
 for bone in arm.pose.bones:bone.custom_shape=None
 for obj in list(bpy.data.objects):
  if obj.type=='MESH' and not any(m.type=='ARMATURE' and m.object==arm for m in obj.modifiers):bpy.data.objects.remove(obj,do_unlink=True)
 for obj in bpy.data.objects:
  if obj.animation_data:obj.animation_data_clear()
 for action in list(bpy.data.actions):bpy.data.actions.remove(action)
 names=data['bone_names'].tolist();parents=data['parents'];p=data['positions_blender'];q=data['delta_quaternions'];rest=data['rest'];count=len(p);fps=report['fps']
 scene=bpy.context.scene;scene.render.fps=fps;scene.frame_start=0;scene.frame_end=count-1
 arm.animation_data_create();action=bpy.data.actions.new('CLEAN_'+slug.replace('-','_')+'_anchored');arm.animation_data.action=action;last={}
 for f in range(count):
  scene.frame_set(f);matrices={}
  for j,name in enumerate(names):
   bone=arm.data.bones[name];quat=Quaternion((q[f,j,3],*q[f,j,:3]));m=Matrix.Translation(p[f,j])@quat.to_matrix().to_4x4()@bone.matrix_local.to_3x3().to_4x4();matrices[name]=m
   kwargs={'parent_matrix':matrices[names[parents[j]]],'parent_matrix_local':arm.data.bones[names[parents[j]]].matrix_local} if parents[j]>=0 else {}
   pb=arm.pose.bones[name];pb.rotation_mode='QUATERNION';pb.matrix_basis=bone.convert_local_to_pose(m,bone.matrix_local,invert=True,**kwargs)
   if name.startswith(('SOCKET_','FINGER_','THUMB_')) or name=='SENSOR_YAW':continue
   rotation=pb.rotation_quaternion.copy()
   if name in last and rotation.dot(last[name])<0:rotation.negate();pb.rotation_quaternion=rotation
   last[name]=rotation.copy();pb.keyframe_insert(data_path='location',frame=f);pb.keyframe_insert(data_path='rotation_quaternion',frame=f)
 for pb in arm.pose.bones:
  if pb.name.startswith(('SOCKET_','FINGER_','THUMB_')) or pb.name=='SENSOR_YAW':pb.matrix_basis=Matrix.Identity(4)
 for curve in action.fcurves:
  for point in curve.keyframe_points:point.interpolation='LINEAR'
 scene.frame_set(0);arm['motion_provenance']='User-owned cleaned capture + authored recovery and contact-aware kinematic support; no neural calls'
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/'anchored.blend'))
 target=folder/'anchored.glb';bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',export_animations=True,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_force_sampling=True,export_skins=True,export_yup=True,export_tangents=True)
 payload=target.read_bytes();length=struct.unpack_from('<I',payload,12)[0];document=json.loads(payload[20:20+length]);binary=payload[20+length:]
 for i,node in enumerate(document['nodes']):
  if 'skin' not in node:continue
  assert not any(k in node for k in ('matrix','translation','rotation','scale'))
  for parent in document['nodes']:
   if i in parent.get('children',[]):parent['children'].remove(i)
  for s in document['scenes']:
   if i not in s['nodes']:s['nodes'].append(i)
 for animation in document['animations']:
  animation['name']=action.name;animation['channels']=[c for c in animation['channels'] if c['target']['path']!='scale' and not document['nodes'][c['target']['node']].get('name','').startswith(('SOCKET_','FINGER_','THUMB_')) and document['nodes'][c['target']['node']].get('name') not in ('ROOT','SENSOR_YAW')]
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
 for image in document.get('images',[]):
  if 'bufferView' in image:slots.append((image,'bufferView'))
 used=sorted({d[k] for d,k in slots});mapping={a:b for b,a in enumerate(used)};document['bufferViews']=[document['bufferViews'][i] for i in used]
 for d,k in slots:d[k]=mapping[d[k]]
 encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);target.write_bytes(struct.pack('<III',0x46546c67,2,20+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+binary)
 assert len(document['animations'])==1
 report['export']={'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'animated_clip':action.name,'animations':1,'bones':len(names),'mesh_nodes':sum('mesh' in n for n in document['nodes']),'unskinned_mesh_nodes':sum('mesh'in n and 'skin' not in n for n in document['nodes']),'geometry_unchanged':True,'bone_widgets_removed':True,'fps':fps}
 (folder/'cleanup-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('ANCHORED_EXPORT_READY',slug,count,'fps',fps,'bytes',target.stat().st_size,flush=True)
