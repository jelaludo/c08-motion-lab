"""Blender: export a saved pose as native MotionBricks G1 numeric conditioning."""
import bpy, argparse, json, sys, math
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--name',default='authored_pose')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
controls=bpy.data.objects['G1_CONTROLS'];pelvis=bpy.data.objects['PELVIS_G1'];names=json.loads(controls['joint_order_json'])
position=pelvis.matrix_world.translation;quat=pelvis.matrix_world.to_quaternion().normalized()
q=[*position,quat.x,quat.y,quat.z,quat.w]+[float(controls[n]) for n in names]
assert len(q)==36
if not all(math.isfinite(value) for value in q):raise ValueError('Pose contains a nonfinite value')
if any(abs(value-1)>1e-6 for value in pelvis.matrix_world.to_scale()):raise ValueError('Move or rotate the pelvis; do not scale the authoring rig')
for name,angle in zip(names,q[7:]):
 limits=controls.id_properties_ui(name).as_dict()
 if not limits['min']-1e-6<=angle<=limits['max']+1e-6:raise ValueError(f'{name}: angle outside joint limits')
out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'name':args.name,'qpos':q,'joint_names':names,'basis':'Z up, +X forward, metres/radians, root quaternion XYZW','provenance':'Original pose authored in local G1 proxy; no bundled sample motion used'},indent=2))
print('EXPORTED_ORIGINAL_G1_POSE',out,flush=True)
