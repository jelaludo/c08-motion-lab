"""Build an original proxy with one slider per reference G1 hinge for pose authoring."""
import bpy, json, math, xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'conditioning';OUT.mkdir(exist_ok=True)
library=json.loads((ROOT/'evaluation/c08-worker/round2/original-g1-poses.json').read_text())
names=library['joint_names'];neutral=library['poses']['neutral']
xml=ET.parse(ROOT/'upstream/motionbricks/assets/robots/unitree_g1/g1_29dof_rev_1_0.xml')
root_body=xml.getroot().find('worldbody').find('body')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC'
controls=bpy.data.objects.new('G1_CONTROLS',None);scene.collection.objects.link(controls)
controls.empty_display_type='CUBE';controls.empty_display_size=.06;controls.location=(0,-.5,.15)
controls['instructions']='Select this object, then Object Properties > Custom Properties. Angles drive the original G1 hinge rig. Move PELVIS_G1 for the floating root. Export with tools/export_g1_pose.py.'
for i,name in enumerate(names):
 joint=next(j for j in root_body.iter('joint') if j.get('name')==name)
 lo,hi=map(float,joint.get('range').split());controls[name]=float(neutral[7+i])
 controls.id_properties_ui(name).update(min=lo,max=hi,soft_min=lo,soft_max=hi,description='G1 hinge angle in radians; XML axis and joint limits preserved',subtype='ANGLE')
controls['joint_order_json']=json.dumps(names)
def values(text,default):return tuple(map(float,text.split())) if text else default
frames={}
def empty(name,parent=None,location=(0,0,0),quaternion=(1,0,0,0)):
 o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.parent=parent;o.location=location;o.rotation_mode='QUATERNION';o.rotation_quaternion=quaternion;o.empty_display_size=.015
 return o
def material(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
materials={'left':material('Left anatomical',(.16,.55,.85)),'right':material('Right anatomical',(.95,.55,.12)),'center':material('Center',(.5,.57,.62))}
def proxy_marker(frame,mat):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.022)
 o=bpy.context.object;o.name='PROXY_'+frame.name;o.parent=frame;o.location=(0,0,0);o.data.materials.append(mat)
def rod(parent,position,mat):
 end=Vector(position)
 if end.length<.008:return
 bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=.011,depth=end.length)
 o=bpy.context.object;o.name='PROXY_LINK';o.parent=parent;o.location=end*.5;o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(end);o.data.materials.append(mat)
def visit(body,parent=None):
 name=body.get('name');position=values(body.get('pos'),(0,0,0));rotation=values(body.get('quat'),(1,0,0,0))
 mat=materials['left' if name.startswith('left') else 'right' if name.startswith('right') else 'center']
 if parent is None:
  frame=empty('PELVIS_G1',location=neutral[:3],quaternion=(neutral[6],*neutral[3:6]))
 else:
  rest=empty('REST_'+name,parent,position,rotation)
  joint=body.find('joint')
  if joint is not None and joint.get('type')!='free':
   origin=values(joint.get('pos'),(0,0,0));axis=values(joint.get('axis'),(0,0,1))
   hinge=empty('HINGE_'+joint.get('name'),rest,origin);hinge.rotation_mode='AXIS_ANGLE';hinge.rotation_axis_angle=(0,*axis)
   driver=hinge.driver_add('rotation_axis_angle',0).driver;driver.expression='angle'
   variable=driver.variables.new();variable.name='angle';variable.type='SINGLE_PROP';variable.targets[0].id=controls;variable.targets[0].data_path='["'+joint.get('name')+'"]'
   frame=empty('BODY_'+name,hinge,tuple(-v for v in origin))
  else:frame=rest
  rod(parent,position,mat)
 frame['source_body_name']=name;frames[name]=frame;proxy_marker(frame,mat)
 for child in body.findall('body'):visit(child,frame)
visit(root_body)
# A broad, deliberately simple foot proxy makes floor penetration visible while editing.
for side in ('left','right'):
 bpy.ops.mesh.primitive_cube_add(size=1)
 o=bpy.context.object;o.name='PROXY_FOOT_'+side;o.parent=frames[side+'_ankle_roll_link'];o.location=(.07,0,-.018);o.scale=(.23,.09,.035);o.data.materials.append(materials[side])
bpy.ops.mesh.primitive_plane_add(size=6)
floor=bpy.context.object;floor.name='AUTHORING_FLOOR';floor.location.z=-.005;floor.data.materials.append(material('Floor',(.08,.1,.12)))
scene.world=bpy.data.worlds.new('World');scene.world.color=(.18,.18,.18)
text=bpy.data.texts.new('ORIGINAL_G1_POSES.json');text.write(json.dumps(library,indent=2))
apply_script='''# Choose one of the original library poses, then Run Script.
import bpy, json
pose_name = 'crouch'
library = json.loads(bpy.data.texts['ORIGINAL_G1_POSES.json'].as_string())
q = library['poses'][pose_name]
controls = bpy.data.objects['G1_CONTROLS']
for i, name in enumerate(library['joint_names']): controls[name] = q[7+i]
pelvis = bpy.data.objects['PELVIS_G1']
pelvis.location = q[:3]
pelvis.rotation_quaternion = (q[6], *q[3:6])
controls.update_tag()
bpy.context.view_layer.update()
'''
bpy.data.texts.new('Apply_Original_Pose.py').write(apply_script)
readme=bpy.data.texts.new('START_HERE.txt');readme.write('Original G1 pose authoring proxy\n\nSelect G1_CONTROLS, open Object Properties > Custom Properties and edit the 29 angle sliders.\nMove/rotate PELVIS_G1 for root placement. Units are metres/radians; G1 is Z up and +X forward.\nBlue = anatomical left; amber = right. The body frame rotations and hinge axes come from the pinned XML.\n\nThe text Apply_Original_Pose.py loads a pose from ORIGINAL_G1_POSES.json. Set pose_name then Run Script.\nSave a separate copy after editing; export numeric conditioning with tools/export_g1_pose.py.\nThis proxy contains original simple geometry, no Unitree visual meshes and no sampled NVIDIA motion.\n')
bpy.context.view_layer.update()
evidence={name:{'position':list(frame.matrix_world.translation),'quaternion_wxyz':list(frame.matrix_world.to_quaternion())} for name,frame in frames.items()}
(OUT/'authoring-reference-transforms.json').write_text(json.dumps(evidence,indent=2))
bpy.ops.object.select_all(action='DESELECT');controls.select_set(True);bpy.context.view_layer.objects.active=controls
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   region=area.spaces.active.region_3d;region.view_distance=2.5;region.view_location=Vector((0,0,.65));region.view_rotation=Quaternion((.88,.3,.15,.32)).normalized()
  elif area.type=='PROPERTIES':area.spaces.active.context='OBJECT'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'g1-pose-authoring.blend'))
print('G1_AUTHORING_PROXY_READY',OUT,flush=True)
