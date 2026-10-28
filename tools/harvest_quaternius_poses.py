"""Sample original Quaternius skeletal poses at selected source times, in Blender space."""
from pathlib import Path
import bpy,json,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/pose-harvest';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=next((ROOT/'assets/quaternius/standard').rglob('UAL1_Standard.glb'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(SOURCE));arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
clips=['Walk_Loop','Dance_Loop','Interact','Jump_Start','Crouch_Fwd_Loop'];names=[b.name for b in arm.data.bones];reference=[list(b.matrix_local) for b in arm.data.bones];cases=[]
for label in clips:
 action=bpy.data.actions[label];arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0];start,end=map(float,action.frame_range);duration=(end-start)/30;times=[0,1/30,2/30,3/30,duration*.5,duration];frames=[]
 for t in times:
  frame=start+t*30;bpy.context.scene.frame_set(int(frame),subframe=frame%1);frames.append([[list(row) for row in arm.pose.bones[n].matrix] for n in names])
 cases.append({'id':'quat_'+label.lower(),'label':'Quaternius / '+label.replace('_',' '),'family':'quaternius','license':'CC0-1.0','publishable':True,'source_clip':label,'duration_s':duration,'sample_times_s':times,'joint_names':names,'reference_transforms':[[list(row) for row in arm.data.bones[n].matrix_local] for n in names],'world_transforms':frames,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'basis':'blender'})
(OUT/'quaternius-poses.json').write_text(json.dumps({'cases':cases}),encoding='utf8');print('HARVESTED',len(cases),'Quaternius clips',flush=True)
