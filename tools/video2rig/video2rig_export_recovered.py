"""Blender: recovered quaternion stream -> original skinned body GLB, with independent FK parity."""
import bpy,json,sys,runpy,math
from pathlib import Path
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

ap=__import__('argparse').ArgumentParser();ap.add_argument('--project',required=True);ap.add_argument('--motion',required=True);ap.add_argument('--tag',required=True);ap.add_argument('--metrics',default='')
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);R=find_workspace();P=Path(a.project).resolve();motion=Path(a.motion).resolve();out=P/'recovered';out.mkdir(exist_ok=True);sc=bpy.context.scene
d=np.load(motion);fps=int(round(1/np.median(np.diff(d['times']))));sc.frame_start=0;sc.render.fps=fps;sc.render.fps_base=1
for arm in [o for o in sc.objects if o.type=='ARMATURE']:
 if arm.animation_data:
  arm.animation_data.action=None
  for tr in arm.animation_data.nla_tracks:tr.mute=True
argv=sys.argv;sys.argv=['import_motion.py','--','--motion',str(motion),'--action',a.tag];runpy.run_path(str(R/'experiments/video2rig/upstream/blender/import_motion.py'),run_name='__main__');sys.argv=argv
arm=next(o for o in sc.objects if o.type=='ARMATURE');names=[str(n) for n in d['bones']];duration=float(d['times'][-1]+np.median(np.diff(d['times'])));end=int(round(duration*fps));last=float(d['times'][-1])*fps
sc.frame_set(math.floor(last),subframe=last-math.floor(last));bpy.context.preferences.edit.keyframe_new_interpolation_type='LINEAR'
for pb in arm.pose.bones:
 pb.keyframe_insert('rotation_quaternion',frame=end)
 if pb.name==str(d['root']):pb.keyframe_insert('location',frame=end)
sc.frame_end=end
world=[]
for t in d['times']:
 f=float(t)*fps;sc.frame_set(math.floor(f),subframe=f-math.floor(f));world.append([list(arm.matrix_world@arm.pose.bones[n].head) for n in names])
world=np.array(world);report={'motion':motion.name,'tag':a.tag,'frames':len(world),'bones':len(names),'nominal_duration_s':duration,'export_frame_end':end,'finite':bool(np.isfinite(world).all()),'body':'Original source skinned body and authored rig; recovered root/rotations only. No world alignment/floor lift added.'}
if a.metrics:
 ref=np.load(Path(a.metrics).with_suffix('.npz'));inds=[list(ref['bones']).index(n) for n in names];e=np.linalg.norm(world-ref['world_heads'][:,inds],axis=-1);report['max_numpy_vs_blender_world_error_m']=float(e.max());assert e.max()<1e-5,report
assert report['finite'];sc.frame_set(0)
# Root skinned nodes avoid ambiguous glTF parent transforms; keep world matrix and skin modifier intact.
for ob in sc.objects:
 if ob.type=='MESH' and any(m.type=='ARMATURE' and m.object==arm for m in ob.modifiers):
  world_matrix=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=world_matrix
bpy.ops.wm.save_as_mainfile(filepath=str(out/(a.tag+'.blend')))
bpy.ops.export_scene.gltf(filepath=str(out/(a.tag+'.glb')),export_format='GLB',export_animations=True,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_force_sampling=True,export_skins=True,export_yup=True)
np.savez_compressed(out/(a.tag+'-heads.npz'),times=d['times'],bones=np.array(names),world_heads=world)
(out/(a.tag+'-export.json')).write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
