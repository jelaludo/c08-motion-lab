"""Blender: copy cleaned C08 poses/rig geometry to a private numeric cleanup workspace."""
from pathlib import Path
import bpy,numpy as np,json,sys,hashlib
import os

def discover_root():
 explicit=os.environ.get('MOTIONBRICKS_ROOT')
 candidates=[Path(explicit).expanduser().resolve()] if explicit else []
 candidates += list(Path(__file__).resolve().parents) + [Path.cwd().resolve()]
 for candidate in candidates:
  if (candidate/'evaluation/mocap-rebuild/exports').is_dir() or (candidate/'public/c08-motion-lab/docs/mocap-rebuild').is_dir():return candidate
 raise RuntimeError('Set MOTIONBRICKS_ROOT to the original MotionBricks workspace; private cleaned .blend inputs are needed for exact reproduction.')

ROOT=discover_root();OUT=ROOT/'evaluation/anchored-cleanup';OUT.mkdir(parents=True,exist_ok=True)
slugs=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['ukemi','technical-standup','gorilla-front','sumo-stomp','source-094553','h3-dance']
for slug in ['_neutral']+slugs:
 path=ROOT/'evaluation/mocap-rebuild/exports'/('ukemi' if slug=='_neutral' else slug)/('single' if slug=='_neutral' else 'cleaned')/'c08-mocap.blend'
 bpy.ops.wm.open_mainfile(filepath=str(path));arm=next(o for o in bpy.data.objects if o.type=='ARMATURE');names=[b.name for b in arm.data.bones];index={n:i for i,n in enumerate(names)}
 rest=np.array([np.array(b.matrix_local) for b in arm.data.bones]);parents=np.array([index[b.parent.name] if b.parent else -1 for b in arm.data.bones])
 positions=[];quats=[]
 end=0 if slug=='_neutral' else bpy.context.scene.frame_end
 for f in range(end+1):
  bpy.context.scene.frame_set(f);positions.append([list(arm.pose.bones[n].matrix.translation) for n in names]);quats.append([list((arm.pose.bones[n].matrix.to_quaternion()@arm.data.bones[n].matrix_local.to_quaternion().inverted())) for n in names])
 # mathutils quaternion order WXYZ -> scipy XYZW.
 quats=np.asarray(quats)[:,:,[1,2,3,0]]
 folder=OUT/slug;folder.mkdir(exist_ok=True)
 np.savez_compressed(folder/'input.npz',names=np.array(names),parents=parents,rest=rest,positions=np.array(positions),delta_quaternions=quats)
 if not (OUT/'geometry.npz').exists():
  points=[];bones=[];bind=[]
  for obj in bpy.data.objects:
   if obj.type!='MESH' or not any(m.type=='ARMATURE' for m in obj.modifiers):continue
   matrix=arm.matrix_world.inverted()@obj.matrix_world;groups={g.index:g.name for g in obj.vertex_groups}
   for v in obj.data.vertices:
    weights=[g for g in v.groups if g.weight>1e-7];assert len(weights)==1 and abs(weights[0].weight-1)<1e-6
    name=groups[weights[0].group];world=matrix@v.co;point=arm.data.bones[name].matrix_local.inverted()@world
    points.append(list(point));bones.append(index[name]);bind.append(list(world))
  np.savez_compressed(OUT/'geometry.npz',points=points,bone_indices=bones,bind_positions=bind,names=np.array(names))
 print('EXTRACTED',slug,len(positions),flush=True)
