"""Fresh, original numerical conditioning for publicly shareable G1 experiments.

No sample BVH/CSV files or sample-conditioned outputs are read by this script.
"""
from pathlib import Path
import json, math, subprocess, time, traceback, argparse, shutil
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation
import warp as wp
import newton
from motionbricks.io.utils import get_unitree_g1_model
from motionbricks.model.unitree_g1.contract import UNITREE_G1_N1_CONTRACT, UNITREE_G1_N1_FP32_ONNX_PATH
from motionbricks.model.unitree_g1.engine import MotionBricksUnitreeG1Engine
from motionbricks.model.config import MotionBricksInferenceConfig

ROOT=Path(__file__).resolve().parents[1];UP=ROOT/'upstream';OUT=ROOT/'evaluation/c08-worker/round3'
OUT.mkdir(parents=True,exist_ok=True)
library_path=ROOT/'evaluation/c08-worker/round2/original-g1-poses.json'
library=json.loads(library_path.read_text(encoding='utf-8'))
joint_names=list(UNITREE_G1_N1_CONTRACT.joint_names);index={n:i+7 for i,n in enumerate(joint_names)}
assert library['joint_names']==joint_names
poses={name:np.array(q,np.float32) for name,q in library['poses'].items()}
N,C,D=poses['neutral'],poses['crouch'],poses['deep_crouch']
xml=ET.parse(UP/'motionbricks/assets/robots/unitree_g1/g1_29dof_rev_1_0.xml')
limits={j.get('name'):tuple(map(float,j.get('range').split())) for j in xml.getroot().iter('joint') if j.get('range')}

def authored(q):
    q=q.copy()
    # These bounds are part of authoring the inputs, never post-hoc output clamping.
    for name,i in index.items():
        low,high=limits[name];q[i]=np.clip(q[i],low+1e-4,high-1e-4)
    assert np.isfinite(q).all() and np.linalg.norm(q[3:7])>.9
    return q

def place(p,x=0,y=0,yaw=0):
    q=p.copy();r=Rotation.from_euler('z',yaw);q[:3]=r.apply(q[:3]);q[:2]+=(x,y);q[3:7]=(r*Rotation.from_quat(q[3:7])).as_quat()
    return authored(q)[None,:]

def gait(t,*,speed=.55,period=1.1,amplitude=.25,direction=(1,0),crouched=False,style='neutral'):
    rows=[]
    for i in range(4):
        tick=t+i/30;phase=tick*math.tau/period;q=(C if crouched else N).copy()
        q[:2]+=np.array(direction)*speed*tick
        q[2]+=(.008 if crouched else -.025)+.012*math.cos(phase*2)
        for side,offset,sign in [('left',0,1),('right',math.pi,-1)]:
            swing=math.sin(phase+offset)
            scale=.55 if style=='limp' and side=='left' else 1
            hip=-amplitude*swing*scale
            knee=(.12 if crouched else .22)*max(0,-swing)*scale
            if abs(direction[1])>.5:
                q[index[side+'_hip_roll_joint']]+=-amplitude*.35*swing
            else:q[index[side+'_hip_pitch_joint']]+=hip
            q[index[side+'_knee_joint']]+=knee
            q[index[side+'_ankle_pitch_joint']]+=-hip*.5-knee*.45
            q[index[side+'_shoulder_pitch_joint']]=amplitude*.7*swing
        if style=='guarded':
            q[index['waist_yaw_joint']]=.08*math.sin(phase)
            for side in ('left','right'):
                q[index[side+'_shoulder_pitch_joint']]=-.6+.05*math.sin(phase)
                q[index[side+'_elbow_joint']]=1.45
        elif style=='limp':
            q[index['waist_roll_joint']]=.06+.04*math.sin(phase)
            q[2]-=.025*max(0,math.sin(phase))
        elif style=='zombie':
            for side in ('left','right'):
                q[index[side+'_shoulder_pitch_joint']]=-1.15
                q[index[side+'_elbow_joint']]=.22
            q[index['waist_pitch_joint']]=.08
        elif style=='skip':
            q[2]+=.075*max(0,math.sin(phase*2))**2
            q[index['left_shoulder_pitch_joint']]=-.45*math.sin(phase)
            q[index['right_shoulder_pitch_joint']]=.45*math.sin(phase)
        rows.append(authored(q))
    return np.array(rows)

cases=[]
purpose='Original numerical poses and target trajectories authored in this workspace; no NVIDIA/Bones sample motion or sample-conditioned generated clip used.'
def add(id,label,context,targets,category='Fresh original motion',note=''):
    cases.append(dict(id='fresh_'+id,label=label,context=context,targets=targets,category=category,provenance_type='original',purpose=purpose,authoring_note=note))
def moving(id,label,**settings):
    add(id,label,gait(0,**settings),[gait(t,**settings) for t in (1.,2.,3.)],note='New procedural four-pose gait windows, with authored root velocity and hinge oscillation; requested style is a test hypothesis, not guaranteed model output.')
moving('slow_walk','Original · deliberate slow walk',speed=.3,period=1.5,amplitude=.17)
moving('brisk_walk','Original · brisk walk',speed=.8,period=.95,amplitude=.3)
moving('jog','Original · light jog',speed=1.1,period=.75,amplitude=.38)
add('walk_start','Original · walk start',np.repeat(N[None,:],4,axis=0),[gait(1,speed=.5),gait(2,speed=.5)])
add('walk_stop','Original · walk stop',gait(0,speed=.5),[place(N,x=.65),place(N,x=.65)])
for id,label,direction in [('crouch_forward','forward',(1,0)),('crouch_backward','backward',(-1,0)),('crouch_left','left',(0,1)),('crouch_right','right',(0,-1))]:
    moving(id,'Original · crouched '+label,speed=.25,period=1.4,amplitude=.13,direction=direction,crouched=True)
duck=D.copy();duck[index['waist_pitch_joint']]=.20
add('duck_under','Original · duck through low space',np.repeat(N[None,:],4,axis=0),[place(C,x=.15),place(duck,x=.3),place(C,x=.45),place(N,x=.55)],'Fresh original interactions','Original lowered torso targets; no obstacle geometry or hand/contact constraint is supplied to the neural model. Travel is deliberately compact to stay within the C08 adapter reach envelope.')
seat=N.copy();seat[0]=-.18;seat[2]=.46
for side in ('left','right'):
    seat[index[side+'_hip_pitch_joint']]=-.95
    seat[index[side+'_knee_joint']]=1.5
    seat[index[side+'_ankle_pitch_joint']]=-.55
seat=authored(seat)
add('sit_down','Original · seated lowering',np.repeat(N[None,:],4,axis=0),[place(seat),place(seat)],'Fresh original interactions','Original chair-like target posture; no chair/support surface is inferred or supplied.')
add('sit_hold','Original · seated hold',np.repeat(seat[None,:],4,axis=0),[place(seat)]*2,'Fresh original interactions','Original static seated target, not a force-balanced pose or accepted chair interaction.')
add('stand_from_seat','Original · stand from seated pose',np.repeat(seat[None,:],4,axis=0),[place(C),place(N)],'Fresh original interactions')
moving('guarded_steps','Original · guarded side steps',speed=.45,period=.8,amplitude=.22,direction=(0,1),style='guarded')
moving('limp','Original · asymmetric limp experiment',speed=.35,period=1.4,amplitude=.24,style='limp')
moving('zombie_walk','Original · arms-forward walk',speed=.35,period=1.5,amplitude=.22,style='zombie')
moving('skip','Original · skipping experiment',speed=.6,period=1.05,amplitude=.34,style='skip')
dance_targets=[]
for tick in range(4):
    q=N.copy();q[1]=.10*math.sin(tick*math.pi*.75);q[2]-=.04*(tick%2)
    q[index['waist_yaw_joint']]=.35*math.sin(tick*math.pi*.75)
    q[index['waist_roll_joint']]=.10*math.cos(tick*math.pi*.75)
    for side,sign in [('left',1),('right',-1)]:
        q[index[side+'_shoulder_pitch_joint']]=-.9-.45*math.sin(tick*math.pi*.75+sign)
        q[index[side+'_shoulder_roll_joint']]=sign*(.4+.2*math.cos(tick*math.pi*.75))
        q[index[side+'_elbow_joint']]=.8+.4*math.cos(tick*math.pi*.75+sign)
    dance_targets.append(authored(q)[None,:])
add('dance','Original · playful torso and arm sequence',np.repeat(N[None,:],4,axis=0),dance_targets+[place(N)],'Fresh original styles','Original alternating arm/torso targets, not a sampled dance performance.')

(OUT/'authored-inputs.json').write_text(json.dumps({'purpose':purpose,'source_library':'Our previously authored original-g1-poses.json; numerical inputs only','joint_names':joint_names,'seat_pose':seat.tolist(),'cases':[{'id':c['id'],'context':c['context'].tolist(),'targets':[q.tolist() for q in c['targets']],'authoring_note':c['authoring_note']} for c in cases]},indent=2),encoding='utf-8')
parser=argparse.ArgumentParser();parser.add_argument('--only',nargs='+');args=parser.parse_args()
if args.only:cases=[c for c in cases if c['id'] in args.only]
wp.init();wp.set_device('cuda:0');model=get_unitree_g1_model(load_visuals=False)
assert [name.rsplit('/',1)[-1] for name in model.joint_label][1:]==joint_names
state=model.state();names=[name.rsplit('/',1)[-1] for name in model.body_label]
newton.eval_fk(model,model.joint_q,model.joint_qd,state);refbody=state.body_q.numpy().copy();refq=model.joint_q.numpy().copy()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=UP,text=True).strip();catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))['tests'] if args.only and (OUT/'catalog.json').exists() else []
with MotionBricksUnitreeG1Engine(UNITREE_G1_N1_FP32_ONNX_PATH) as engine,wp.ScopedStream(engine.stream):
    context,target,output=engine.create_input(),engine.create_input(),engine.create_output()
    for case in cases:
        folder=OUT/case['id'];folder.mkdir(exist_ok=True)
        if (folder/'retarget-failure.json').exists() and not (folder/'attempt-1').exists():
            (folder/'attempt-1').mkdir()
            for name in ('g1-motion.npz','g1-motion.json','retarget-failure.json'):shutil.copy2(folder/name,folder/'attempt-1'/name)
        entry={key:case[key] for key in ('id','label','category','provenance_type','purpose','authoring_note')};entry['directory']=case['id'];entry['clip']='MB_'+case['id']
        try:
            segments=[];contacts=[];boundaries=[];inputs=[];recent=case['context'].copy();started=time.perf_counter()
            for goal in case['targets']:
                context.update_from_poses(wp.array(recent,dtype=wp.float32),stream=engine.stream);target.update_from_poses(wp.array(goal,dtype=wp.float32),stream=engine.stream)
                inputs.append({'context':recent.tolist(),'target':goal.tolist()});tick=time.perf_counter()
                engine.generate_animation(context,target,output,config=MotionBricksInferenceConfig());engine.synchronize()
                q=output.poses[:output.num_frames].numpy().copy();c=output.foot_contacts[:output.num_frames].numpy().copy()
                assert np.isfinite(q).all() and np.allclose(np.linalg.norm(q[:,3:7],axis=1),1,atol=1e-4)
                duplicate=bool(segments and np.allclose(segments[-1][-1],q[0],atol=1e-5))
                if duplicate:q=q[1:];c=c[1:]
                boundaries.append({'frame':sum(len(s) for s in segments),'num_frames':len(q),'shared_endpoint_removed':duplicate,'generation_seconds':time.perf_counter()-tick})
                segments.append(q);contacts.append(c);recent=np.concatenate(segments)[-4:].copy()
            q=np.concatenate(segments);transforms=[]
            for row in q:
                newton.eval_fk(model,wp.array(row,dtype=wp.float32),model.joint_qd,state);transforms.append(state.body_q.numpy().copy())
            np.savez(folder/'g1-motion.npz',qpos=q,timestamps=np.arange(len(q))/30,contacts=np.concatenate(contacts),body_transforms=np.array(transforms),body_names=np.array(names),reference_qpos=refq,reference_bodies=refbody)
            metrics={'root_horizontal_travel_m':float(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1).sum()),'pelvis_height_min_m':float(q[:,2].min()),'pelvis_height_max_m':float(q[:,2].max()),'maximum_joint_key_step_rad':float(np.abs(np.diff(q[:,7:],axis=0)).max()),'root_endpoint_error_m':float(np.linalg.norm(q[-1,:3]-case['targets'][-1][0,:3]))}
            meta={**entry,'upstream_commit':commit,'model':'MotionBricks-G1-RP-v1','precision':'FP32','sample_rate':30,'frames':len(q),'duration_s':(len(q)-1)/30,'segments':boundaries,'inputs':inputs,'allowed_token_counts':list(range(8,15)),'body_names':names,'source_metrics':metrics,'total_seconds':time.perf_counter()-started,'basis':'Z up, +X forward; quaternion XYZW','public_conditioning_audit':'No source sample motion or earlier sample-conditioned output read.'}
            (folder/'g1-motion.json').write_text(json.dumps(meta,indent=2),encoding='utf-8');entry.update(frames=len(q),duration_s=(len(q)-1)/30,generation='passed',source_metrics=metrics)
            print('FRESH_GENERATED',case['id'],len(q),flush=True)
        except Exception as error:entry.update(generation='failed',error=str(error));traceback.print_exc()
        old=next((i for i,c in enumerate(catalog) if c['id']==entry['id']),None)
        if old is None:catalog.append(entry)
        else:catalog[old]=entry
        (OUT/'catalog.json').write_text(json.dumps({'label':'Fresh original conditioning experiments','tests':catalog},indent=2),encoding='utf-8')
print('FRESH_GENERATION_COMPLETE',len(catalog),flush=True)
