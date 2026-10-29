"""Verify the native control GLB against independently sampled original joint positions."""
import bpy,json,sys,argparse
import numpy as np

def find_workspace():
    """Find the local experiment workspace without embedding any user's filesystem path."""
    import os
    explicit = os.environ.get('MOTION_LAB_WORKSPACE')
    candidates = [Path(explicit)] if explicit else list(Path(__file__).resolve().parents)
    for candidate in candidates:
        if (candidate / 'assets').is_dir() and (candidate / 'experiments/video2rig/upstream').is_dir():
            return candidate.resolve()
    raise RuntimeError('Set MOTION_LAB_WORKSPACE to a MotionBricks workspace containing assets/ and experiments/video2rig/upstream/.')

from pathlib import Path
R=find_workspace();ap=argparse.ArgumentParser();ap.add_argument('--project',default='experiments/video2rig/k0-control');ap.add_argument('--glb',default='native-control-4s.glb');ap.add_argument('--reference',default='ground-truth-native.npz');ap.add_argument('--out',default='native-glb-validation.json');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);P=R/a.project
d=np.load(P/a.reference);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(P/a.glb))
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');sc=bpy.context.scene
for tr in arm.animation_data.nla_tracks:tr.mute=True
errs=[]
skin_samples=[]
truth=d['world_heads'] if 'world_heads' in d.files else d['heads']@d['armature_world'][:3,:3].T+d['armature_world'][:3,3]
for i,(t,H) in enumerate(zip(d['times'],truth)):
 f=float(t)*30;sc.frame_set(int(f),subframe=f-int(f))
 heads=np.array([list(arm.matrix_world@arm.pose.bones[str(n)].head) for n in d['bones']]);errs.append(np.linalg.norm(heads-H,axis=-1))
 if 'skin_sample_indices' in d.files and i in d['skin_sample_indices']:
  pieces=[]
  for ob in sc.objects:
   if ob.type=='MESH' and any(m.type=='ARMATURE' for m in ob.modifiers):
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());v=np.empty(len(ev.data.vertices)*3);ev.data.vertices.foreach_get('co',v);v=v.reshape(-1,3);M=np.array(ev.matrix_world);pieces.append(v@M[:3,:3].T+M[:3,3])
  skin_samples.append(np.vstack(pieces))
e=np.array(errs);report={'source':Path(a.glb).name,'original_reference':Path(a.reference).name,'samples':len(e),'bones':len(d['bones']),'maximum_joint_world_error_m':float(e.max()),'mean_joint_world_error_m':float(e.mean()),'animation_duration_s':float(arm.animation_data.action.frame_range[1]/30),'finite':bool(np.isfinite(e).all())};expected=float(d['times'][-1]+np.median(np.diff(d['times'])))
assert report['finite'] and e.max()<1e-5 and abs(report['animation_duration_s']-expected)<1e-5,report
(P/a.out).write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
if skin_samples:np.savez_compressed((P/a.out).with_suffix('.npz'),skin_sample_indices=d['skin_sample_indices'],world_skin_samples=np.array(skin_samples))
