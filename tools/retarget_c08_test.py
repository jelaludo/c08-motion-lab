"""Bake an explicitly experimental G1 -> C08 retarget without altering originals."""
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from pathlib import Path
import json, math, hashlib, struct, os

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('MB_TEST_DIRECTORY',ROOT/'evaluation/c08-worker'))
metadata=json.loads((OUT/'g1-motion.json').read_text())
CLIP_NAME=metadata.get('clip','MB_G1_Walk_Test')
data=np.load(OUT/'g1-motion.npz')
names=list(data['body_names'])
source=data['body_transforms']
reference=data['reference_bodies']
contacts=data['contacts']
contact_ik_mask=data['contact_ik_mask'] if 'contact_ik_mask' in data.files else None
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/c08-worker/c08_d0_lod1.glb'))
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
arm.animation_data_clear()
for obj in bpy.data.objects:
 if obj.animation_data:obj.animation_data_clear()
for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
H={b.name:b.head_local.copy() for b in arm.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in arm.data.bones}
S=Matrix(((0,1,0),(-1,0,0),(0,0,1)))
qs=S.to_quaternion()
def sq(v):return Quaternion((float(v[6]),float(v[3]),float(v[4]),float(v[5])))
firstq=qs@sq(source[0,names.index('pelvis')])@qs.inverted()
forward=firstq@Vector((0,-1,0))
initial_yaw=math.atan2(forward.x,-forward.y)
align=Quaternion((0,0,1),-initial_yaw)
A=align.to_matrix()@S
origin=A@Vector(source[0,names.index('pelvis'),:3]);origin.z=0
def refpos(n):return S@Vector(reference[names.index(n),:3])
scale=(H['PELVIS'].z-H['ANKLE_L'].z)/(refpos('pelvis').z-refpos('left_ankle_roll_link').z)
def point(frame,n):return A@Vector(source[frame,names.index(n),:3])
def rotation(frame,n):return align@qs@sq(source[frame,names.index(n)])@qs.inverted()
def yawq(q):
 f=q@Vector((0,-1,0));return Quaternion((0,0,1),math.atan2(f.x,-f.y))
def delta_rotation(frame,n):
 return align@qs@(sq(source[frame,names.index(n)])@sq(reference[names.index(n)]).inverted())@qs.inverted()

arm.animation_data_create()
action=bpy.data.actions.new(CLIP_NAME)
arm.animation_data.action=action
fps=30
scene=bpy.context.scene
scene.render.fps=fps
scene.frame_start=0
scene.frame_end=len(source)-1
locks={'L':None,'R':None}
last_quat={}
max_reach_correction=0.
reactive_lock_releases=0;max_reactive_ankle_reach_adjustment=0.
floor_corrections=[]
samples=[]
# Sparse human targets can include inverted/non-foot support. Retain the raw source;
# report any whole-avatar grounding correction on this experimental adaptation.
whole_body_ground=bool(metadata.get('source_harvest') or metadata.get('routine'));ground_geometry=[];body_ground_offsets=[];dense_ground_offsets=[]
if whole_body_ground:
 for obj in bpy.data.objects:
  if obj.type!='MESH':continue
  bybone={};groups={g.index:g.name for g in obj.vertex_groups};mesh_to_arm=arm.matrix_world.inverted()@obj.matrix_world
  for vertex in obj.data.vertices:
   weights=[g for g in vertex.groups if g.weight>1e-7]
   if not weights:continue
   assert len(weights)==1 and abs(weights[0].weight-1)<1e-5
   n=groups[weights[0].group];p=arm.data.bones[n].matrix_local.inverted()@(mesh_to_arm@vertex.co);bybone.setdefault(n,[]).append((*p,1.))
  ground_geometry.extend((n,np.array(points)) for n,points in bybone.items())
for frame in range(len(source)):
 scene.frame_set(frame)
 pos,ori={},{}
 def put(n,p=None,q=None):
  parent=parents[n]
  pos[n]=Vector(p) if p is not None else (pos[parent]+ori[parent]@(H[n]-H[parent]) if parent else H[n].copy())
  ori[n]=q.copy() if q is not None else (ori[parent].copy() if parent else Quaternion())
 pelvis=point(frame,'pelvis')
 rootq=rotation(frame,'pelvis');heading=yawq(rootq)
 rootxy=(pelvis-origin)*scale;rootxy.z=0
 put('MOTION',rootxy,heading)
 p=rootxy+Vector((0,0,H['PELVIS'].z+(pelvis.z-refpos('pelvis').z)*scale))
 put('PELVIS',p,rootq)
 put('WAIST',q=delta_rotation(frame,'waist_roll_link'))
 put('CHEST',q=delta_rotation(frame,'torso_link'))
 for n in ('NECK','HEAD','SENSOR_YAW'):put(n)
 # Source foot trajectories are scaled, then widened to C08's standing stance.
 feet={}
 for side,prefix,ci in [('L','left',0),('R','right',2)]:
  ankle='ANKLE_'+side;src=prefix+'_ankle_roll_link'
  q=delta_rotation(frame,src)
  bias=H[ankle]-refpos(src)*scale;bias.z=0
  p=(point(frame,src)-origin)*scale+heading@bias
  p.z=H[ankle].z+(point(frame,src).z-refpos(src).z)*scale
  sole=H['SOCKET_SOLE_'+side]-H[ankle]
  supported=bool(max(contacts[frame,ci:ci+2])>=.65)
  if contact_ik_mask is not None:
   # Only externally prepared contact phases are trusted. Genuine neural
   # entry/exit frames keep their original, unreviewed contact predictions.
   supported=supported and bool(contact_ik_mask[frame])
  elif metadata.get('reactive',{}).get('scenario')=='crouch':
   # These squat-shuffle predictions retain unreliable high contact labels during
   # root travel. Follow the predicted feet instead of pinning both soles until
   # the short C08 legs collapse or stretch. This adaptation does not claim IK contact repair.
   supported=False
  if supported:
   if locks[side] is None:locks[side]=(p+q@sole).copy()
   support=p+q@sole
   p.x+=locks[side].x-support.x;p.y+=locks[side].y-support.y
  else:locks[side]=None
  # C08 has much broader feet. Lift the ankle enough to keep its rigid sole above the plane.
  corners=[Vector((x,y,-.194)) for x in (-.15,.15) for y in (-.31,.14)]
  minimum=min((p+q@v).z for v in corners)
  # Two extra millimetres cover the actual beveled sole below the socket proxy.
  lift=max(0,.008-minimum)
  p.z+=lift;floor_corrections.append(lift)
  feet[side]=(p,q)
 # Lower the pelvis only when target leg reach requires it; never stretch limbs.
 correction=0.
 for side in ('L','R'):
  hip=pos['PELVIS']+rootq@(H['HIP_'+side]-H['PELVIS'])
  foot=feet[side][0]
  a=(H['KNEE_'+side]-H['HIP_'+side]).length;b=(H['ANKLE_'+side]-H['KNEE_'+side]).length
  horizontal=(Vector((foot.x,foot.y,0))-Vector((hip.x,hip.y,0))).length
  allowed=math.sqrt(max(.001,(a+b-.002)**2-horizontal**2))
  correction=max(correction,max(0,hip.z-foot.z-allowed))
 max_reach_correction=max(max_reach_correction,correction)
 if correction:
  for n in ('PELVIS','WAIST','CHEST','NECK','HEAD','SENSOR_YAW'):pos[n].z-=correction
 for side,prefix in [('L','left'),('R','right')]:
  hipname,kneename,anklename=('HIP_'+side,'KNEE_'+side,'ANKLE_'+side)
  hip=pos['PELVIS']+rootq@(H[hipname]-H['PELVIS'])
  foot,footq=feet[side]
  a=(H[kneename]-H[hipname]).length;b=(H[anklename]-H[kneename]).length
  d=foot-hip;length=d.length
  if metadata.get('reactive') and length>=a+b:
   # A predicted planted-contact interval can outlast the retargeted leg's reach.
   # Release that display-only lock and keep rigid segment lengths; raw G1 stays intact.
   corrected=hip+d.normalized()*(a+b-.002)
   max_reactive_ankle_reach_adjustment=max(max_reactive_ankle_reach_adjustment,(corrected-foot).length)
   reactive_lock_releases+=1;locks[side]=None;foot=corrected;d=foot-hip;length=d.length
  if not abs(a-b)<length<a+b:raise ValueError(('unreachable leg',frame,side,length,a+b))
  direction=d.normalized()
  sh=point(frame,prefix+'_hip_pitch_link');sk=point(frame,prefix+'_knee_link');sa=point(frame,prefix+'_ankle_roll_link')
  axis=(sa-sh).normalized();pole=sk-sh-axis*(sk-sh).dot(axis)
  pole-=direction*pole.dot(direction)
  if pole.length<1e-5:pole=heading@Vector((0,-1,0));pole-=direction*pole.dot(direction)
  pole.normalize()
  along=(a*a-b*b+length*length)/(2*length)
  knee=hip+direction*along+pole*math.sqrt(max(0,a*a-along*along))
  put(hipname,hip,(H[kneename]-H[hipname]).rotation_difference(knee-hip))
  put(kneename,knee,(H[anklename]-H[kneename]).rotation_difference(foot-knee))
  put(anklename,foot,footq);put('TOE_'+side)
  put('SHOULDER_'+side)
  upper,lower,hand='UPPER_ARM_'+side,'FOREARM_'+side,'HAND_'+side
  updir=point(frame,prefix+'_elbow_link')-point(frame,prefix+'_shoulder_roll_link')
  lodir=point(frame,prefix+'_wrist_yaw_link')-point(frame,prefix+'_elbow_link')
  uq=(H[lower]-H[upper]).rotation_difference(updir)
  lq=(H[hand]-H[lower]).rotation_difference(lodir)
  put(upper,q=uq);put(lower,q=lq)
  # Carry source wrist articulation relative to the forearm; fingers remain at their own rest pose.
  wrist=rotation(frame,prefix+'_wrist_yaw_link')
  elbow=rotation(frame,prefix+'_elbow_link')
  put(hand,q=(wrist@elbow.inverted())@lq)
 # Unmapped fingers and sockets inherit the adapted parent; none receives an animation channel.
 for n in H:
  if n not in pos:put(n)
 if whole_body_ground:
  low=min(float((points@np.array(Matrix.Translation(pos[n])@ori[n].to_matrix().to_4x4()@arm.data.bones[n].matrix_local.to_3x3().to_4x4())[2,:]).min()) for n,points in ground_geometry)
  body_lift=max(0,.012-low);body_ground_offsets.append(body_lift)
  for n in H:
   if n!='MOTION':pos[n].z+=body_lift
 matrices={}
 for n in H:
  b=arm.data.bones[n];parent=parents[n]
  m=Matrix.Translation(pos[n])@ori[n].to_matrix().to_4x4()@b.matrix_local.to_3x3().to_4x4()
  matrices[n]=m
  args=dict(parent_matrix=matrices[parent],parent_matrix_local=arm.data.bones[parent].matrix_local) if parent else {}
  pb=arm.pose.bones[n];pb.rotation_mode='QUATERNION'
  pb.matrix_basis=b.convert_local_to_pose(m,b.matrix_local,invert=True,**args)
  if n.startswith(('SOCKET_','FINGER_','THUMB_')) or n=='SENSOR_YAW':continue
  q=pb.rotation_quaternion.copy()
  if n in last_quat and q.dot(last_quat[n])<0:q.negate();pb.rotation_quaternion=q
  last_quat[n]=q.copy()
  pb.keyframe_insert(data_path='location',frame=frame)
  pb.keyframe_insert(data_path='rotation_quaternion',frame=frame)
 samples.append({n:list(pos[n]) for n in ('PELVIS','KNEE_L','KNEE_R','ANKLE_L','ANKLE_R','SOCKET_SOLE_L','SOCKET_SOLE_R')})
for fc in action.fcurves:
 for key in fc.keyframe_points:key.interpolation='LINEAR'
if whole_body_ground:
 # Preserve source timing while sampling the geometric clearance at 120 Hz.
 for fc in action.fcurves:
  for key in fc.keyframe_points:
   key.co.x*=4;key.handle_left.x*=4;key.handle_right.x*=4
 scene.render.fps=120;scene.frame_end=(len(source)-1)*4;dense_locations=[]
 for frame in range(scene.frame_end+1):
  scene.frame_set(frame);bpy.context.view_layer.update()
  low=min(float((points@np.array(arm.pose.bones[n].matrix)[2,:]).min()) for n,points in ground_geometry);lift=max(0,.012-low);dense_ground_offsets.append(lift)
  pb=arm.pose.bones['PELVIS'];b=arm.data.bones['PELVIS'];m=pb.matrix.copy();m.translation.z+=lift
  local=b.convert_local_to_pose(m,b.matrix_local,parent_matrix=pb.parent.matrix,parent_matrix_local=b.parent.matrix_local,invert=True);dense_locations.append(local.translation.copy())
 for frame,location in enumerate(dense_locations):
  arm.pose.bones['PELVIS'].location=location;arm.pose.bones['PELVIS'].keyframe_insert(data_path='location',frame=frame)
 for fc in action.fcurves:
  for key in fc.keyframe_points:key.interpolation='LINEAR'
scene.frame_set(0)
arm.show_in_front=True
arm['motion_provenance']=metadata['purpose']+'; MotionBricks G1 FP32; experimental retarget'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'c08-motionbricks-test.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'c08-motionbricks-test.glb'),export_format='GLB',export_animations=True,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_force_sampling=True,export_skins=True,export_all_influences=False,export_yup=True)
# Blender samples every joint, including constant game-owned controls. Strip those channels.
glb_path=OUT/'c08-motionbricks-test.glb'
payload=glb_path.read_bytes();json_size=struct.unpack_from('<I',payload,12)[0]
document=json.loads(payload[20:20+json_size]);rest=payload[20+json_size:]
# Export the skin beside the skeleton, preserving the identity transforms, so whole-scene placement is explicit.
for index,node in enumerate(document['nodes']):
 if 'skin' not in node:continue
 assert not any(k in node for k in ('matrix','translation','rotation','scale'))
 for parent in document['nodes']:
  if index in parent.get('children',[]):
   assert not any(k in parent for k in ('matrix','translation','rotation','scale'))
   parent['children'].remove(index)
 for gltf_scene in document['scenes']:
  if index not in gltf_scene['nodes']:gltf_scene['nodes'].append(index)
for animation in document['animations']:
 animation['name']=CLIP_NAME
 animation['channels']=[c for c in animation['channels'] if c['target']['path']!='scale' and not document['nodes'][c['target']['node']].get('name','').startswith(('SOCKET_','FINGER_','THUMB_')) and document['nodes'][c['target']['node']].get('name') not in ('SENSOR_YAW','ROOT')]
 # Remove orphaned samplers and remap references after filtering.
 used=sorted({c['sampler'] for c in animation['channels']});indices={old:new for new,old in enumerate(used)}
 animation['samplers']=[animation['samplers'][i] for i in used]
 for c in animation['channels']:c['sampler']=indices[c['sampler']]
# Compact references to removed animation data. Binary offsets stay unchanged.
slots=[]
for mesh in document.get('meshes',[]):
 for primitive in mesh['primitives']:
  slots.extend((primitive['attributes'],k) for k in primitive['attributes'])
  if 'indices' in primitive:slots.append((primitive,'indices'))
  for target in primitive.get('targets',[]):slots.extend((target,k) for k in target)
for skin in document.get('skins',[]):
 if 'inverseBindMatrices' in skin:slots.append((skin,'inverseBindMatrices'))
for animation in document['animations']:
 for sampler in animation['samplers']:slots.extend(((sampler,'input'),(sampler,'output')))
used=sorted({d[k] for d,k in slots});indices={old:new for new,old in enumerate(used)}
document['accessors']=[document['accessors'][i] for i in used]
for d,k in slots:d[k]=indices[d[k]]
slots=[]
for accessor in document['accessors']:
 if 'bufferView' in accessor:slots.append((accessor,'bufferView'))
 if 'sparse' in accessor:
  slots.extend(((accessor['sparse']['indices'],'bufferView'),(accessor['sparse']['values'],'bufferView')))
for image in document.get('images',[]):
 if 'bufferView' in image:slots.append((image,'bufferView'))
used=sorted({d[k] for d,k in slots});indices={old:new for new,old in enumerate(used)}
document['bufferViews']=[document['bufferViews'][i] for i in used]
for d,k in slots:d[k]=indices[d[k]]
encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
glb_path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(encoded)+len(rest))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+rest)
report={'status':'experimental prototype; not game accepted','conditioning_provenance':metadata['purpose'],'source_asset_sha256':hashlib.sha256((ROOT/'assets/c08-worker/c08_d0_lod1.glb').read_bytes()).hexdigest(),'clip':CLIP_NAME,'frames':len(source),'fps':fps,'duration_s':(len(source)-1)/fps,'source_to_target_scale':scale,'initial_heading_removed_rad':initial_yaw,'max_pelvis_reach_correction_m':max_reach_correction,'reactive_foot_lock_releases':reactive_lock_releases,'max_reactive_ankle_reach_adjustment_m':max_reactive_ankle_reach_adjustment,'max_foot_floor_lift_m':max(floor_corrections),'root_motion':'MOTION owns scaled horizontal travel and heading; PELVIS residual; do not add navigation travel','trusted_contact_mask_frames':int(np.sum(contact_ik_mask)) if contact_ik_mask is not None else 0,'contact_policy':('Authored prepared-contact mask plus phase contacts enable sole XY locking; raw NN entry/exit contacts are not pinned. Broad-sole floor correction retained.' if contact_ik_mask is not None else 'Predicted foot positions with sole XY locking disabled for reactive squat-shuffles; source contact labels retained unreviewed; broad-sole floor correction.' if metadata.get('reactive',{}).get('scenario')=='crouch' else '>=0.65 maximum source heel/toe confidence; heuristic sole-center XY locking, broad-sole floor correction; unreviewed contacts'),'limitations':['G1 and C08 proportions/rigs differ; this is measured adaptation, not reference-rig equivalence','Fingers/toes/head remain inherited rest controls','No self-collision or physical balance guarantee'],'sample_positions_blender':samples}
report.update(export_bake_hz=120 if whole_body_ground else 30,max_whole_body_ground_lift_m=max(body_ground_offsets,default=0.),max_dense_ground_lift_m=max(dense_ground_offsets,default=0.),whole_avatar_ground_policy='Complete-avatar lift only, including non-foot armor support; no balance/contact solve' if whole_body_ground else 'Original standing foot adapter')
(OUT/'retarget-report.json').write_text(json.dumps(report,indent=2))
print('RETARGET_COMPLETE',len(source),'frames','scale',scale,'pelvis correction',max_reach_correction,'foot lift',max(floor_corrections),flush=True)
