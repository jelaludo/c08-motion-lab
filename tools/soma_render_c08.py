"""Render representative direct-retarget poses without including reference video."""
from pathlib import Path
import argparse,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('name',nargs='?',default='ukemi');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=ROOT/'video-mocap/c08-retarget'/args.name
bpy.ops.wm.open_mainfile(filepath=str(OUT/'c08-mocap.blend'))
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE_NEXT';scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('ReviewWorld');scene.world.color=(.18,.18,.18)
arm=next(o for o in scene.objects if o.type=='ARMATURE')
robot=[o for o in scene.objects if o.type=='MESH']
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0));floor=bpy.context.object;floor.name='ReviewFloor'
mat=bpy.data.materials.new('ReviewFloorMaterial');mat.diffuse_color=(.09,.11,.13,1);floor.data.materials.append(mat)
camera_data=bpy.data.cameras.new('ReviewCamera');camera=bpy.data.objects.new('ReviewCamera',camera_data);scene.collection.objects.link(camera);scene.camera=camera
camera_data.type='ORTHO';camera_data.ortho_scale=3.3
lights=[]
for name,offset,power,size in [('Key',(3,-4,6),1300,5),('Fill',(-4,-1,3),900,4),('Rim',(1,4,5),1500,3)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);lights.append((o,Vector(offset)))
frames=sorted(set([0,round(scene.frame_end*.25),round(scene.frame_end*.5),round(scene.frame_end*.6),round(scene.frame_end*.75),scene.frame_end]))
if args.name=='ukemi':frames=sorted(set(frames+[66,70,80]))
for frame in frames:
 scene.frame_set(frame);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
 points=[obj.matrix_world@Vector(v) for obj in robot for v in obj.evaluated_get(deps).bound_box]
 lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)));target=(lo+hi)*.5
 camera.location=target+Vector((3,-5,2.4));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
 for light,offset in lights:light.location=target+offset;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(OUT/f'preview-{frame:04d}.png');bpy.ops.render.render(write_still=True)
print('SOMA_C08_RENDERS_READY',args.name,frames,flush=True)
