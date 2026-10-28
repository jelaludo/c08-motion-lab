"""Retarget the official CC0 Quaternius Standard library to the existing rigid C08 rig."""
from pathlib import Path
import bpy,math,json,hashlib,sys
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/vanilla-base';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=next((ROOT/'assets/quaternius/standard').rglob('UAL1_Standard.glb'))
CLIPS=['Death01']
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(SOURCE));src=next(o for o in bpy.data.objects if o.type=='ARMATURE');source_actions={a.name:a for a in bpy.data.actions};source_objects=list(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/c08-worker/c08_d0_lod1.glb'));arm=next(o for o in bpy.data.objects if o.type=='ARMATURE' and o!=src);targets=[o for o in bpy.data.objects if o not in source_objects]
for o in targets:
 if o.animation_data:o.animation_data_clear()
H={b.name:b.head_local.copy() for b in arm.data.bones};parents={b.name:b.parent.name if b.parent else None for b in arm.data.bones}
R={b.name:b.matrix_local.to_quaternion() for b in src.data.bones};SH={b.name:b.head_local.copy() for b in src.data.bones};scale=H['PELVIS'].z/SH['pelvis'].z
mapping={'PELVIS':'pelvis','WAIST':'spine_01','CHEST':'spine_03','NECK':'neck_01','HEAD':'Head'}
limbs={}
for side in ['L','R']:
 s=side.lower()
 for t,c,f,g in [('HIP','KNEE','thigh','calf'),('KNEE','ANKLE','calf','foot'),('UPPER_ARM','FOREARM','upperarm','lowerarm'),('FOREARM','HAND','lowerarm','hand')]:
  n=t+'_'+side;source=f+'_'+s;mapping[n]=source;limbs[n]=(H[c+'_'+side]-H[n]).rotation_difference(SH[g+'_'+s]-SH[source])
 for t,f in [('ANKLE','foot'),('TOE','ball'),('SHOULDER','clavicle'),('HAND','hand')]:mapping[t+'_'+side]=f+'_'+s
geometry=[]
for o in targets:
 if o.type!='MESH':continue
 groups={g.index:g.name for g in o.vertex_groups};m=arm.matrix_world.inverted()@o.matrix_world
 for v in o.data.vertices:
  ws=[g for g in v.groups if g.weight>1e-7]
  if not ws:continue
  assert len(ws)==1 and abs(ws[0].weight-1)<1e-5
  n=groups[ws[0].group];geometry.append((n,arm.data.bones[n].matrix_local.inverted()@(m@v.co)))
reports=[];actions=[]
for label in CLIPS:
 sa=source_actions[label];src.animation_data_create();src.animation_data.action=sa;src.animation_data.action_slot=sa.slots[0]
 length=float(sa.frame_range[1]-sa.frame_range[0]);count=round(length*4)+1
 action=bpy.data.actions.new('Q_'+label);action.use_fake_user=True;arm.animation_data_create();arm.animation_data.action=action;last={};samples=[];corrections=[];base=None
 for f in range(count):
  scene.frame_set(0,subframe=0);scene.frame_set(int(f*length/(count-1)),subframe=(f*length/(count-1))%1)
  pos={};ori={}
  def put(n,p=None,q=None):
   parent=parents[n];pos[n]=Vector(p) if p is not None else (pos[parent]+ori[parent]@(H[n]-H[parent]) if parent else H[n].copy());ori[n]=q.copy() if q is not None else (ori[parent].copy() if parent else Quaternion())
  put('MOTION',Vector((0,0,0)),Quaternion());p=src.pose.bones['pelvis'].head*scale;p.x=0;p.y=0;put('PELVIS',p,src.pose.bones['pelvis'].matrix.to_quaternion()@R['pelvis'].inverted())
  for n in H:
   if n in pos:continue
   sn=mapping.get(n);q=(src.pose.bones[sn].matrix.to_quaternion()@R[sn].inverted()) if sn else None
   if n in limbs:q=q@limbs[n]
   put(n,q=q)
  matrices={n:Matrix.Translation(pos[n])@ori[n].to_matrix().to_4x4()@arm.data.bones[n].matrix_local.to_3x3().to_4x4() for n in H}
  low=min((matrices[n]@v).z for n,v in geometry)
  if base is None:base=.012-low
  correction=max(base,.012-low) if label.startswith('Jump_') else .012-low
  corrections.append(correction)
  for n in H:
   if n!='MOTION':pos[n].z+=correction
  matrices={}
  for n in H:
   b=arm.data.bones[n];parent=parents[n];m=Matrix.Translation(pos[n])@ori[n].to_matrix().to_4x4()@b.matrix_local.to_3x3().to_4x4();matrices[n]=m
   kw={'parent_matrix':matrices[parent],'parent_matrix_local':arm.data.bones[parent].matrix_local} if parent else {}
   pb=arm.pose.bones[n];pb.rotation_mode='QUATERNION';pb.matrix_basis=b.convert_local_to_pose(m,b.matrix_local,invert=True,**kw)
   if n.startswith(('SOCKET_','FINGER_','THUMB_')) or n=='SENSOR_YAW':continue
   q=pb.rotation_quaternion.copy()
   if n in last and q.dot(last[n])<0:q.negate();pb.rotation_quaternion=q
   last[n]=q.copy();pb.keyframe_insert(data_path='location',frame=f);pb.keyframe_insert(data_path='rotation_quaternion',frame=f)
  samples.append({n:list(pos[n]) for n in ('PELVIS','HEAD','ANKLE_L','ANKLE_R','HAND_L','HAND_R')})
 for curve in action.fcurves:
  for k in curve.keyframe_points:k.interpolation='LINEAR'
 actions.append(action);reports.append({'name':action.name,'source_clip':label,'duration_s':(count-1)/120,'frames':count,'fps':120,'loop':label.endswith('_Loop'),'ground_correction_min_m':min(corrections),'ground_correction_max_m':max(corrections),'sample_positions_blender':samples})
 print('RETARGETED',label,count,flush=True)
for o in source_objects:bpy.data.objects.remove(o,do_unlink=True)
for a in list(bpy.data.actions):
 if a not in actions:bpy.data.actions.remove(a)
scene.render.fps=120;arm.animation_data.action=actions[0];scene.frame_start=0;scene.frame_end=max(x['frames'] for x in reports)-1;scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for o in targets:o.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'c08-quaternius.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'c08-quaternius.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_skins=True,export_yup=True)
(OUT/'retarget-report.json').write_text(json.dumps({'source':'Quaternius Universal Animation Library 1 Standard','license':'CC0-1.0','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'target_sha256':hashlib.sha256((ROOT/'assets/c08-worker/c08_d0_lod1.glb').read_bytes()).hexdigest(),'scale':scale,'clips':reports,'limitations':['Direct anatomical retarget with fixed C08 segment lengths','Whole-avatar ground placement; no foot/hand contact IK','Broad armor may overlap; motion quality requires visual review','In-place clips; source root travel excluded']},indent=2),encoding='utf8')
