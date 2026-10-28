from pathlib import Path
import bpy,json,os
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/c08-worker/round3'
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
for case in catalog['tests']:
    if os.environ.get('MB_ONLY_TESTS') and case['id'] not in os.environ['MB_ONLY_TESTS'].split(','):continue
    folder=OUT/case['directory']
    if not (folder/'c08-motionbricks-test.blend').exists():continue
    bpy.ops.wm.open_mainfile(filepath=str(folder/'c08-motionbricks-test.blend'))
    scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE_NEXT';scene.render.resolution_x=600;scene.render.resolution_y=600;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('ReviewWorld');scene.world.color=(.18,.18,.18)
    arm=next(o for o in scene.objects if o.type=='ARMATURE')
    bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;mat=bpy.data.materials.new('ReviewFloor');mat.diffuse_color=(.09,.11,.13,1);floor.data.materials.append(mat)
    d=bpy.data.cameras.new('ReviewCamera');camera=bpy.data.objects.new('ReviewCamera',d);scene.collection.objects.link(camera);scene.camera=camera;d.type='ORTHO';d.ortho_scale=3.2
    lights=[]
    for name,offset,power,size in [('Key',(3,-4,6),1300,5),('Fill',(-4,-1,3),900,4),('Rim',(1,4,5),1500,3)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);lights.append((obj,Vector(offset)))
    frame=round(scene.frame_end*.5);scene.frame_set(frame);bpy.context.view_layer.update()
    pelvis=arm.matrix_world@arm.pose.bones['PELVIS'].matrix.translation;target=Vector((pelvis.x,pelvis.y,1.15))
    camera.location=target+Vector((3,-5,2));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    for light,offset in lights:light.location=target+offset;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(folder/'preview.png');bpy.ops.render.render(write_still=True)
    print('FRESH_PREVIEW',case['id'],frame,flush=True)
