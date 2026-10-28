"""Experimental manual-landmark humanoid rig and automatic skinning for CC-BY Meshy test asset."""
from pathlib import Path
import bpy,json,hashlib,math,struct
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/meshy-fighter';OUT.mkdir(parents=True,exist_ok=True);SOURCE=Path('G:/L_Download2026/bjj_jiu-jitsu_woman_girl_fighter_free.glb')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(SOURCE));meshes=[o for o in bpy.data.objects if o.type=='MESH'];points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices];low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)));factor=1.7/(high.z-low.z);centre=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
for o in meshes:
 world=o.matrix_world.copy()
 for v in o.data.vertices:v.co=(world@v.co-centre)*factor
 o.parent=None;o.matrix_world=Matrix.Identity(4)
 bpy.context.view_layer.objects.active=o;o.select_set(True)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name='Meshy_Fighter_Surface'
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.000025);bpy.ops.object.mode_set(mode='OBJECT');before=len(mesh.data.polygons)
mod=mesh.modifiers.new('Lab web mesh reduction','DECIMATE');mod.ratio=.35;bpy.ops.object.modifier_apply(modifier=mod.name)
# Only the primary UV set is referenced by the imported materials; preserve that set and textures.
while len(mesh.data.uv_layers)>1:mesh.data.uv_layers.remove(mesh.data.uv_layers[-1])
for material in mesh.data.materials:
 if material and material.use_nodes:
  for node in material.node_tree.nodes:
   if node.type=='UVMAP':node.uv_map=mesh.data.uv_layers[0].name
heads={'MOTION':(0,0,0),'PELVIS':(0,0,.89),'WAIST':(0,.005,1.02),'CHEST':(0,.012,1.24),'NECK':(0,0,1.405),'HEAD':(0,0,1.50)};parents={'MOTION':None,'PELVIS':'MOTION','WAIST':'PELVIS','CHEST':'WAIST','NECK':'CHEST','HEAD':'NECK'};tails={'MOTION':(0,0,.15),'HEAD':(0,0,1.67)}
for side,sign in [('L',1),('R',-1)]:
 for n,p,parent in [('HIP',(.12,0,.87),'PELVIS'),('KNEE',(.17,0,.47),'HIP_'+side),('ANKLE',(.22,0,.09),'KNEE_'+side),('TOE',(.245,-.10,.035),'ANKLE_'+side),('SHOULDER',(.10,0,1.32),'CHEST'),('UPPER_ARM',(.19,0,1.32),'SHOULDER_'+side),('FOREARM',(.29,-.005,1.10),'UPPER_ARM_'+side),('HAND',(.35,-.015,.92),'FOREARM_'+side)]:heads[n+'_'+side]=(p[0]*sign,p[1],p[2]);parents[n+'_'+side]=parent
 tails['TOE_'+side]=(.28*sign,-.13,.03);tails['HAND_'+side]=(.37*sign,-.025,.83)
for n in heads:
 if n not in tails:
  children=[c for c,p in parents.items() if p==n];tails[n]=heads[children[0]] if children else Vector(heads[n])+Vector((0,0,.08))
data=bpy.data.armatures.new('Meshy_Fighter_Lab_Rig');arm=bpy.data.objects.new('Meshy_Fighter_Lab_Rig',data);bpy.context.collection.objects.link(arm);bpy.context.view_layer.objects.active=arm;bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for n,p in heads.items():
 bone=data.edit_bones.new(n);bone.head=p;bone.tail=tails[n];bone.use_deform=n!='MOTION';bone.parent=data.edit_bones.get(parents[n]) if parents[n] else None
bpy.ops.object.mode_set(mode='OBJECT');bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=arm
try:bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except RuntimeError as e:print('HEAT_NOTE',str(e),flush=True)
if not any(m.type=='ARMATURE' for m in mesh.modifiers):m=mesh.modifiers.new('Armature','ARMATURE');m.object=arm
mesh.parent=arm
# Inspect weights, normalize, and provide a bounded distance fallback only for missing heat weights.
deform=[b for b in data.bones if b.use_deform];groups={b.name:mesh.vertex_groups.get(b.name) or mesh.vertex_groups.new(name=b.name) for b in deform};fallback=0
for v in mesh.data.vertices:
 weights=[(mesh.vertex_groups[g.group].name,g.weight) for g in v.groups if g.weight>1e-8 and mesh.vertex_groups[g.group].name in groups]
 if not weights:
  distances=[]
  for b in deform:
   a=b.head_local;ab=b.tail_local-a;t=max(0,min(1,(v.co-a).dot(ab)/ab.length_squared));distances.append(((v.co-a-ab*t).length,b.name))
  nearest=sorted(distances)[:4];weights=[(n,math.exp(-((d-nearest[0][0])/.055)**2)) for d,n in nearest];fallback+=1
 weights=sorted(weights,key=lambda x:x[1],reverse=True)[:4];total=sum(w for _,w in weights)
 for g in list(v.groups):mesh.vertex_groups[g.group].remove([v.index])
 for n,w in weights:groups[n].add([v.index],w/total,'REPLACE')
mesh['asset_role']='Attribution-required test-only Meshy asset; not production';arm['rigging_method']='Manual anatomical landmarks, Blender heat weights with normalized four-weight cleanup'
scene=bpy.context.scene;scene.frame_start=0;scene.frame_end=1;scene.render.fps=30
bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'meshy-fighter-rigged.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'meshy-fighter-rigged.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_yup=True,export_tangents=True)
report={'source_title':'BJJ Jiu-Jitsu Woman Girl Fighter Free','author':'Tulio Portela','author_url':'https://sketchfab.com/TulioPortela','source_url':'https://sketchfab.com/3d-models/bjj-jiu-jitsu-woman-girl-fighter-free-8077cada67a14af18249b6af687fcc3c','license':'CC-BY-4.0','license_url':'https://creativecommons.org/licenses/by/4.0/','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'source_generator':'Meshy AI, per creator description; downloaded through Sketchfab','changes':['Normalized copied geometry to 1.70 m height','Joined surface partitions and reduced triangles for the lab','Added an original manual-landmark humanoid rig','Blender heat skin weights, limited and normalized to four influences','Original textures preserved; no finger articulation or cloth simulation'],'triangles_before':before,'triangles_after':len(mesh.data.polygons),'vertices':len(mesh.data.vertices),'bones':len(heads),'heat_weight_fallback_vertices':fallback,'role':'Experiment-only secondary body; excluded from production asset pipeline','bind_heads_blender':{n:list(p) for n,p in heads.items()}}
(OUT/'rig-report.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('RIGGED',json.dumps(report),flush=True)

# Keep attribution with the standalone GLB and put the skinned surface beside its skeleton.
p=OUT/'meshy-fighter-rigged.glb';payload=p.read_bytes();size=struct.unpack_from('<I',payload,12)[0];document=json.loads(payload[20:20+size]);binary=payload[20+size:]
document['asset']['extras']={'author':report['author'],'author_url':report['author_url'],'source':report['source_url'],'license':'CC-BY-4.0','license_url':report['license_url'],'title':report['source_title'],'modifications':'Normalized size, geometry reduction, experimental humanoid rig and skinning by C08 Motion Lab. Original Meshy textures preserved. Test-only, excluded from production.'}
for i,node in enumerate(document['nodes']):
 if 'skin' not in node:continue
 assert not any(k in node for k in ('matrix','translation','rotation','scale'))
 for parent in document['nodes']:
  if i in parent.get('children',[]):parent['children'].remove(i)
 for scene in document['scenes']:
  if i not in scene['nodes']:scene['nodes'].append(i)
encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);p.write_bytes(struct.pack('<III',0x46546c67,2,20+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+binary)
report['output_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(OUT/'rig-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
