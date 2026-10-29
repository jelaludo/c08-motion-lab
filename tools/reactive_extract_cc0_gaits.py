from pathlib import Path
import bpy,json,hashlib
r=Path('G:/Dev/MotionBricks');source=next((r/'assets/quaternius/standard').rglob('UAL1_Standard_RM.glb'));bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(source));arm=next(o for o in bpy.data.objects if o.type=='ARMATURE');names=[b.name for b in arm.data.bones];cases=[]
for label in ['Crouch_Fwd_Loop','Jump_Start','Jump_Loop','Jump_Land','Sprint_Loop']:
 action=bpy.data.actions[label];arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0];start,end=map(float,action.frame_range);frames=[];times=[]
 for index in range(round(end-start)+1):
  frame=start+index;bpy.context.scene.frame_set(int(frame),subframe=frame%1);frames.append([[list(row) for row in arm.pose.bones[n].matrix] for n in names]);times.append(index/30)
 case={'id':'cc0_'+label.lower(),'label':'Quaternius CC0 / '+label,'family':'quaternius','license':'CC0-1.0','publishable':True,'source_clip':label,'duration_s':times[-1],'sample_times_s':times,'joint_names':names,'reference_transforms':[[list(row) for row in arm.data.bones[n].matrix_local] for n in names],'world_transforms':frames,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'basis':'blender'};cases.append(case);i=names.index('pelvis');positions=[f[i][j][3] for f in frames for j in []];print(label,len(frames),'pelvis first',arm.data.bones['pelvis'].head_local[:],'worldfirst',frames[0][i][0][3],frames[0][i][1][3],frames[0][i][2][3],'worldlast',frames[-1][i][0][3],frames[-1][i][1][3],frames[-1][i][2][3],flush=True)
out=r/'evaluation/reactive-round4';out.mkdir(exist_ok=True);(out/'cc0-gaits-full.json').write_text(json.dumps({'cases':cases}),encoding='utf8')
