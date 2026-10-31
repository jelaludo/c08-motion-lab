"""Private authored C08 support cleanup. No neural generation or physical balance claims."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d,binary_closing
from scipy.optimize import lsq_linear
from scipy.sparse import eye,diags,vstack

import os

def discover_root():
 explicit=os.environ.get('MOTIONBRICKS_ROOT')
 candidates=[Path(explicit).expanduser().resolve()] if explicit else []
 candidates += list(Path(__file__).resolve().parents) + [Path.cwd().resolve()]
 for candidate in candidates:
  if (candidate/'evaluation/mocap-rebuild/exports').is_dir() or (candidate/'public/c08-motion-lab/docs/mocap-rebuild').is_dir():return candidate
 raise RuntimeError('Set MOTIONBRICKS_ROOT to the original MotionBricks workspace; private cleaned .blend inputs are needed for exact reproduction.')

ROOT=discover_root();BASE=ROOT/'evaluation/anchored-cleanup'
parser=argparse.ArgumentParser();parser.add_argument('slugs',nargs='*',default=['ukemi','sumo-stomp']);args=parser.parse_args()
g=np.load(BASE/'geometry.npz');points=g['points'];vids=g['bone_indices'];neutral=np.load(BASE/'_neutral/input.npz');names=neutral['names'].tolist();ix={n:i for i,n in enumerate(names)};parents=neutral['parents'];rest=neutral['rest'];H=rest[:,:3,3]
relative=np.einsum('nij,nj->ni',rest[vids,:3,:3],points)
neutral_q=neutral['delta_quaternions'][0];neutral_root=neutral['positions'][0,ix['MOTION']].copy();neutral_pelvis=neutral['positions'][0,ix['PELVIS']].copy()
FPS=30;SOLE=.006;CLEAR=.004;HOLD=12
def mats(q):return R.from_quat(q.reshape(-1,4)).as_matrix().reshape(*q.shape[:-1],3,3)
def fk(q,root,pelvis):
 rotations=mats(q);p=np.empty((len(names),3))
 for j,parent in enumerate(parents):
  if names[j]=='MOTION':p[j]=root
  elif names[j]=='PELVIS':p[j]=pelvis
  else:p[j]=p[parent]+rotations[parent]@(H[j]-H[parent])
 return p,rotations
def skin(p,r):return np.einsum('nij,nj->ni',r[vids],relative)+p[vids]
def foot(p,r,side):
 a=ix['ANKLE_'+side];return p[a]+r[a]@(H[ix['SOCKET_SOLE_'+side]]-H[a])
foot_vertices={side:np.flatnonzero(vids==ix['ANKLE_'+side]) for side in ['L','R']}
bindskin=np.asarray(g['bind_positions'])
sole_vertices={side:idx[np.abs(bindskin[idx,2]-bindskin[idx,2].min())<1e-5] for side,idx in foot_vertices.items()}
np0,nr0=fk(neutral_q,neutral_root,neutral_pelvis);neutral_pelvis[2]+=SOLE-min(skin(np0,nr0)[sole_vertices[s],2].min() for s in ['L','R'])
np0,nr0=fk(neutral_q,neutral_root,neutral_pelvis)
def smoothstep(u):return u*u*u*(10+u*(-15+6*u))
def qmix(a,b,u):
 rv=(R.from_quat(a).inv()*R.from_quat(b)).as_rotvec();return (R.from_quat(a)*R.from_rotvec(rv*u)).as_quat()
def transition(q0,q1,p0,p1,r0,r1,seconds,w0=None,w1=None):
 steps=round(seconds*FPS);q=[];p=[];rt=[];rv=(R.from_quat(q0).inv()*R.from_quat(q1)).as_rotvec()
 w0=np.zeros_like(rv) if w0 is None else w0;w1=np.zeros_like(rv) if w1 is None else w1
 for i in range(1,steps+1):
  u=i/steps;s=smoothstep(u);v=u-6*u**3+8*u**4-3*u**5;w=-4*u**3+7*u**4-3*u**5
  q.append((R.from_quat(q0)*R.from_rotvec(rv*s+seconds*(w0*v+w1*w))).as_quat());p.append(p0*(1-s)+p1*s);rt.append(r0*(1-s)+r1*s)
 return np.asarray(q),np.asarray(p),np.asarray(rt)
def envelope(required,holds,ceiling=None,target=None,rate=30):
 n=len(required);I=eye(n,format='csr');D1=diags([-np.ones(n-1),np.ones(n-1)],[0,1],shape=(n-1,n));D2=diags([np.ones(n-2),-2*np.ones(n-2),np.ones(n-2)],[0,1,2],shape=(n-2,n))
 scale=rate/30;A=vstack([I*.6,D1*(3*scale),D2*(24*scale*scale)],format='csr');b=np.concatenate([(required if target is None else target)*.6,np.zeros(n-1),np.zeros(n-2)])
 lower=required.copy();upper=np.full(n,np.inf) if ceiling is None else ceiling.copy();upper=np.maximum(upper,lower+1e-8);lower[holds]=-1e-10;upper[holds]=1e-10
 result=lsq_linear(A,b,bounds=(lower,upper),tol=2e-9,lsq_solver='lsmr',lsmr_tol=1e-9,max_iter=150)
 curve=result.x;curve[holds]=0
 return curve,{'solver_status':int(result.status),'optimality':float(result.optimality),'iterations':int(result.nit)}
def split_runs(mask):
 idx=np.flatnonzero(mask);return [] if not len(idx) else [a for a in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1) if len(a)]
def yaw(q):
 forward=R.from_quat(q).apply([0,-1,0]);return np.arctan2(forward[0],-forward[1])
def solve_leg(p,q,r,side,target,foot_rotation,pole,toe_rotation=None):
 hip=ix['HIP_'+side];knee=ix['KNEE_'+side];ankle=ix['ANKLE_'+side];toe=ix['TOE_'+side]
 h=p[hip];l1=np.linalg.norm(H[knee]-H[hip]);l2=np.linalg.norm(H[ankle]-H[knee]);v=target-h;dist=np.linalg.norm(v)
 if dist>l1+l2-.0005 or dist<abs(l1-l2)+.001:return False,float(dist-(l1+l2))
 direction=v/max(dist,1e-9);a=(l1*l1-l2*l2+dist*dist)/(2*dist);height=np.sqrt(max(0,l1*l1-a*a));bend=pole-direction*np.dot(pole,direction)
 if np.linalg.norm(bend)<.01:bend=np.array([0.,-1.,0.])-direction*np.dot(np.array([0.,-1.,0.]),direction)
 bend/=np.linalg.norm(bend);k=h+direction*a+bend*height
 for joint,child,desired in [(hip,knee,k-h),(knee,ankle,target-k)]:
  current=r[joint]@(H[child]-H[joint]);rot,_=R.align_vectors(desired[None]/np.linalg.norm(desired),current[None]/np.linalg.norm(current));q[joint]=(rot*R.from_quat(q[joint])).as_quat()
 q[ankle]=foot_rotation;q[toe]=foot_rotation if toe_rotation is None else toe_rotation
 return True,0.

for slug in args.slugs:
 d=np.load(BASE/slug/'input.npz');source_q=d['delta_quaternions'].copy();source_p=d['positions'];source_count=len(source_q);used=174 if slug=='gorilla-front' else source_count
 source_q=source_q[:used];root=source_p[:used,ix['MOTION']].copy();pelvis=source_p[:used,ix['PELVIS']].copy()
 # Ease horizontal root velocity at capture boundaries without retiming action samples.
 source_root=root.copy();edge=min(10,len(root)//8)
 for axis in [0,1]:
  for end in [False,True]:
   indices=np.arange(edge+1) if not end else np.arange(len(root)-edge-1,len(root));a,b=indices[0],indices[-1];u=np.linspace(0,1,len(indices));start=root[a,axis];stop=root[b,axis]
   va=0. if not end else (root[a+1,axis]-root[a,axis])*FPS;vb=0. if end else (root[b,axis]-root[b-1,axis])*FPS
   T=(b-a)/FPS;root[indices,axis]=(2*u**3-3*u*u+1)*start+(-2*u**3+3*u*u)*stop+(u**3-2*u*u+u)*T*va+(u**3-u*u)*T*vb
 pelvis[:,:2]+=root[:,:2]-source_root[:,:2]
 first_root=root[0].copy();last_root=root[-1].copy();start_pelvis=neutral_pelvis+first_root-neutral_root;end_pelvis=neutral_pelvis+last_root-neutral_root
 wfirst=(R.from_quat(source_q[0]).inv()*R.from_quat(source_q[1])).as_rotvec()*FPS;wlast=(R.from_quat(source_q[-2]).inv()*R.from_quat(source_q[-1])).as_rotvec()*FPS
 # Bounded angular tangent prevents noise at the source boundary driving a huge authored arc.
 def bounded(v):return v*np.minimum(1,3/np.maximum(1e-8,np.linalg.norm(v,axis=1)))[:,None]
 entry=transition(neutral_q,source_q[0],start_pelvis,pelvis[0],first_root,first_root,1.2,w1=bounded(wfirst));exit=transition(source_q[-1],neutral_q,pelvis[-1],end_pelvis,last_root,last_root,2.2,w0=bounded(wlast))
 # Omit coincident action endpoint in entry; source frames retain 30Hz correspondence.
 qs=np.concatenate([np.repeat(neutral_q[None],HOLD,axis=0),entry[0][:-1],source_q,exit[0],np.repeat(neutral_q[None],HOLD,axis=0)])
 ps=np.concatenate([np.repeat(start_pelvis[None],HOLD,axis=0),entry[1][:-1],pelvis,exit[1],np.repeat(end_pelvis[None],HOLD,axis=0)])
 roots=np.concatenate([np.repeat(first_root[None],HOLD,axis=0),entry[2][:-1],root,exit[2],np.repeat(last_root[None],HOLD,axis=0)])
 count=len(qs);action_start=HOLD+len(entry[0])-1;action_end=action_start+used-1
 source_index=np.full(count,-1);source_index[action_start:action_end+1]=np.arange(used);phases=np.full(count,'entry',dtype='<U24');phases[:HOLD]='neutral';phases[action_start:action_end+1]='source_action';phases[action_end+1:count-HOLD]='recovery';phases[-HOLD:]='neutral'
 holds=np.zeros(count,bool);holds[:HOLD]=True;holds[-HOLD:]=True
 raw_positions=[];required=[]
 for f in range(count):
  p,r=fk(qs[f],roots[f],ps[f]);raw_positions.append(p);required.append(CLEAR-float(skin(p,r)[:,2].min()))
 required=np.asarray(required);curve,solver=envelope(required,holds);footpos=np.empty((count,2,3));footlow=np.empty((count,2));upright=np.empty(count,bool);yaws=np.empty((count,2))
 for f in range(count):
  p,r=fk(qs[f],roots[f],ps[f]+[0,0,curve[f]]);vertices=skin(p,r);torso=p[ix['HEAD']]-p[ix['PELVIS']];upright[f]=p[ix['PELVIS'],2]>.58 and torso[2]/np.linalg.norm(torso)>.55
  for s,side in enumerate(['L','R']):footpos[f,s]=foot(p,r,side);footlow[f,s]=vertices[sole_vertices[side],2].min();yaws[f,s]=yaw(qs[f,ix['ANKLE_'+side]])
 masks=np.zeros((count,2),bool)
 for s in range(2):
  mask=upright&(footlow[:,s]<.09)&(footlow[:,s]<footlow[:,1-s]+.085)
  if slug=='ukemi':mask[(source_index>=58)&(source_index<=110)]=False
  if slug in ['ukemi','source-094553','technical-standup','gorilla-front','h3-dance']:mask[source_index>=0]=False
  if slug=='sumo-stomp':
   core=source_index>=0;mask[core]=True
   if s==1:mask[(source_index>=108)&(source_index<=166)]=False
  mask=binary_closing(mask,structure=np.ones(3));mask[:HOLD]=True;mask[-HOLD:]=True
  masks[:,s]=mask
 weights=np.zeros((count,2));anchors=np.full((count,2,3),np.nan);anchor_yaw=np.zeros((count,2));segments=np.full((count,2),-1,int);contact_rows=[];segid=0
 for s,side in enumerate(['L','R']):
  runs=split_runs(masks[:,s])
  if slug=='sumo-stomp':runs=[piece for run in runs for piece in np.split(run,[int(np.searchsorted(run,b)) for b in [action_start,action_end+1] if run[0]<b<=run[-1]]) if len(piece)]
  for run in runs:
   # Moving/pivoting feet release and replant; do not turn an entire dance into one pin.
   chunks=[];begin=0
   for j in range(1,len(run)):
    a,b=run[begin],run[j];angle=np.arctan2(np.sin(yaws[b,s]-yaws[a,s]),np.cos(yaws[b,s]-yaws[a,s]))
    if slug=='sumo-stomp' and source_index[a]>=0 and source_index[b]>=0:continue
    if (np.linalg.norm(footpos[b,s,:2]-footpos[a,s,:2])>.19 or abs(angle)>.36) and j-begin>=9:
     chunks.append(run[begin:j]);begin=j
   chunks.append(run[begin:])
   for chunk in chunks:
    if len(chunk)<7:continue
    start,end=int(chunk[0]),int(chunk[-1]);median=chunk[:min(8,len(chunk))] if slug=='sumo-stomp' and np.all(source_index[chunk]>=0) else chunk[len(chunk)//4:max(len(chunk)//4+1,3*len(chunk)//4)]
    anchor=np.median(footpos[median,s],axis=0);anchor[2]=SOLE;angle=float(np.median(np.unwrap(yaws[median,s])))
    if start==0:anchor=foot(np0,nr0,side)+first_root-neutral_root;anchor[2]=SOLE;angle=0.
    if end==count-1:anchor=foot(np0,nr0,side)+last_root-neutral_root;anchor[2]=SOLE;angle=0.
    ramp=min(5,(len(chunk)-1)//2);blend=np.ones(len(chunk));blend[:ramp]=smoothstep(np.linspace(0,1,ramp));blend[-ramp:]=smoothstep(np.linspace(1,0,ramp))
    if start==0:blend[:HOLD]=1.
    if end==count-1:blend[-HOLD:]=1.
    if slug=='sumo-stomp' and start==action_start:blend[:ramp]=1.
    if slug=='sumo-stomp' and end==action_end:blend[-ramp:]=1.
    weights[chunk,s]=blend;anchors[chunk,s]=anchor;anchor_yaw[chunk,s]=angle;segments[chunk,s]=segid
    contact_rows.append({'id':segid,'side':side,'range':[start,end],'anchor_blender':anchor.tolist(),'yaw_rad':angle,'kind':'authored_neutral' if holds[chunk].all() else 'kinematic_support','source_frame_range':[int(source_index[chunk][source_index[chunk]>=0].min()),int(source_index[chunk][source_index[chunk]>=0].max())] if np.any(source_index[chunk]>=0) else None});segid+=1
 # Authored entry/recovery use sequential foot placements with actual swing clearance.
 # One foot stays planted while the other moves; feet are not slid along a floor plane.
 ik_weights=weights.copy();ik_targets=anchors.copy();planned_q=np.full((count,2,4),np.nan);planned_toe=np.full((count,2,4),np.nan)
 swing=np.zeros((count,2),bool)
 for transition_kind,first,last in [('entry',HOLD,action_start-1),('recovery',action_end+1,count-HOLD-1)]:
  for s,side in enumerate(['L','R']):
   ankle=ix['ANKLE_'+side];toe=ix['TOE_'+side];core_frame=action_start if transition_kind=='entry' else action_end
   core_s=footpos[core_frame,s].copy();core_q=qs[core_frame,ankle].copy();core_toe=qs[core_frame,toe].copy()
   if slug=='sumo-stomp':
    core_s=anchors[core_frame,s].copy();core_q=R.from_euler('z',anchor_yaw[core_frame,s]).as_quat();core_toe=core_q.copy()
   default_s=foot(np0,nr0,side)+(first_root if transition_kind=='entry' else last_root)-neutral_root
   a,b=(default_s,core_s) if transition_kind=='entry' else (core_s,default_s)
   qa,qb=(neutral_q[ankle],core_q) if transition_kind=='entry' else (core_q,neutral_q[ankle]);ta,tb=(neutral_q[toe],core_toe) if transition_kind=='entry' else (core_toe,neutral_q[toe])
   lo,hi=([.08,.43] if s==0 else [.53,.9]) if transition_kind=='entry' else ([.23,.55] if s==0 else [.62,.94])
   for f in range(first,last+1):
    u=(f-first)/max(1,last-first);progress=smoothstep(np.clip((u-lo)/(hi-lo),0,1));point=a*(1-progress)+b*progress;point[2]+=.09*np.sin(np.pi*progress)**2
    qfoot=qmix(qa,qb,progress);qtoe=qmix(ta,tb,progress);activation=1. if transition_kind=='entry' or slug=='sumo-stomp' else smoothstep(np.clip(u/.2,0,1))
    ik_weights[f,s]=activation;ik_targets[f,s]=point;planned_q[f,s]=qfoot;planned_toe[f,s]=qtoe;swing[f,s]=lo<u<hi
    flat=R.from_quat(qfoot).apply([0,0,1])[2]>.9999;weights[f,s]=activation if not swing[f,s] and flat and point[2]<.025 else 0.;anchors[f,s]=point;anchor_yaw[f,s]=yaw(qfoot);segments[f,s]=-1
   for run in split_runs(weights[:,s]>.9999):
    run=run[(run>=first)&(run<=last)]
    if not len(run):continue
    segments[run,s]=segid;contact_rows.append({'id':segid,'side':side,'range':[int(run[0]),int(run[-1])],'anchor_blender':anchors[run[0],s].tolist(),'yaw_rad':float(anchor_yaw[run[0],s]),'kind':'authored_transition_plant','source_frame_range':None});segid+=1
 # Re-solve support and body constraints at120Hz. This is not a densified30Hz bake.
 factor=4;fps=FPS*factor;old_count=count;timeline=np.arange((old_count-1)*factor+1)/factor;sample=np.rint(timeline).astype(int)
 for f in range(old_count):
  for s,side in enumerate(['L','R']):
   if not np.isfinite(ik_targets[f,s]).all():ik_targets[f,s]=footpos[f,s]
   if not np.isfinite(planned_q[f,s]).all():planned_q[f,s]=R.from_euler('z',anchor_yaw[f,s]).as_quat() if ik_weights[f,s]>0 else qs[f,ix['ANKLE_'+side]]
   if not np.isfinite(planned_toe[f,s]).all():planned_toe[f,s]=R.from_euler('z',anchor_yaw[f,s]).as_quat() if ik_weights[f,s]>0 else qs[f,ix['TOE_'+side]]
 qs=np.stack([Slerp(np.arange(old_count),R.from_quat(qs[:,j]))(timeline).as_quat() for j in range(len(names))],axis=1)
 ps=interp1d(np.arange(old_count),ps,axis=0)(timeline);roots=interp1d(np.arange(old_count),roots,axis=0)(timeline)
 curve=np.interp(timeline,np.arange(old_count),curve);weights=interp1d(np.arange(old_count),weights,axis=0)(timeline);ik_weights=interp1d(np.arange(old_count),ik_weights,axis=0)(timeline);anchors=anchors[sample];anchor_yaw=anchor_yaw[sample];segments=segments[sample];swing=swing[sample]
 ik_targets=interp1d(np.arange(old_count),ik_targets,axis=0)(timeline);planned_q=np.stack([Slerp(np.arange(old_count),R.from_quat(planned_q[:,s]))(timeline).as_quat() for s in range(2)],axis=1);planned_toe=np.stack([Slerp(np.arange(old_count),R.from_quat(planned_toe[:,s]))(timeline).as_quat() for s in range(2)],axis=1)
 raw_positions=interp1d(np.arange(old_count),np.asarray(raw_positions),axis=0)(timeline)
 action_start*=factor;action_end*=factor;count=len(timeline);hold_count=HOLD*factor
 source_index=np.full(count,-1.,dtype=float);source_index[action_start:action_end+1]=np.arange(action_end-action_start+1)/factor
 phases=np.full(count,'entry',dtype='<U24');phases[:hold_count]='neutral';phases[action_start:action_end+1]='source_action';phases[action_end+1:count-hold_count]='recovery';phases[-hold_count:]='neutral'
 holds=np.zeros(count,bool);holds[:hold_count]=True;holds[-hold_count:]=True;qs[holds]=neutral_q;ps[:hold_count]=start_pelvis;ps[-hold_count:]=end_pelvis
 for row in contact_rows:row['range']=[int(v*factor) for v in row['range']]
 # Solve body clearance and support reach together. Old tilted feet must not force
 # the torso upward when those same feet are now solved flat by IK.
 body_required=np.empty(count);ceiling=np.full(count,np.inf);desired_curve=curve.copy();incompatible=[]
 for f in range(count):
  p,r=fk(qs[f],roots[f],ps[f]);vertices=skin(p,r);free_core=source_index[f]>=0 and slug in ['ukemi','source-094553','technical-standup','gorilla-front','h3-dance'];keep=np.ones(len(vertices),bool) if free_core else ~np.isin(vids,[ix[n+'_'+s] for n in ['ANKLE','TOE'] for s in ['L','R']])
  body_required[f]=CLEAR-float(vertices[keep,2].min())
  for s,side in enumerate(['L','R']):
   alpha=ik_weights[f,s]
   if alpha<=0:continue
   hip=ix['HIP_'+side];knee=ix['KNEE_'+side];ankle=ix['ANKLE_'+side];toe=ix['TOE_'+side];flat=R.from_euler('z',anchor_yaw[f,s]).as_quat();qf=planned_q[f,s] if np.isfinite(planned_q[f,s]).all() else flat;qt=planned_toe[f,s] if np.isfinite(planned_toe[f,s]).all() else flat;rf=R.from_quat(qmix(qs[f,ankle],qf,alpha)).as_matrix();rt=R.from_quat(qmix(qs[f,toe],qt,alpha)).as_matrix();offset=H[ix['SOCKET_SOLE_'+side]]-H[ankle];currentsole=foot(p,r,side);target=currentsole*(1-alpha)+ik_targets[f,s]*alpha-rf@offset;horizontal=np.linalg.norm(target[:2]-p[hip,:2]);length=np.linalg.norm(H[knee]-H[hip])+np.linalg.norm(H[ankle]-H[knee])-.004
   minimum=min(float((relative[vids==ankle]@rf.T)[:,2].min()),float(((relative[vids==toe]@rt.T)+(rf@(H[toe]-H[ankle])))[:,2].min()));vertical=np.sqrt(max(0,length*length-horizontal*horizontal))
   cap=max((target[2]+vertical-p[hip,2])/max(.0001,alpha),CLEAR-minimum+vertical-p[hip,2])
   desired_curve[f]=min(desired_curve[f],curve[f]*(1-alpha)+(cap-.012)*alpha)
   if alpha>.0001:ceiling[f]=min(ceiling[f],cap)
  if body_required[f]>ceiling[f]:incompatible.append(f)
 curve,stance_solver=envelope(body_required,holds,ceiling,desired_curve,rate=fps)
 final_q=qs.copy();final_p=[];actual_weights=weights.copy();releases=[];mins=[]
 # Pole hints are denoised independently; source arm/spine motion is not regenerated.
 hint=np.asarray(raw_positions);hint=gaussian_filter1d(hint,sigma=1.8*factor,axis=0,mode='nearest')
 for f in range(count):
  p,r=fk(final_q[f],roots[f],ps[f]+[0,0,curve[f]])
  free_core=source_index[f]>=0 and slug in ['ukemi','source-094553','technical-standup','gorilla-front','h3-dance']
  if not holds[f] and not free_core:
   for s,side in enumerate(['L','R']):
    alpha=ik_weights[f,s]
    ankle=ix['ANKLE_'+side];hip=ix['HIP_'+side];knee=ix['KNEE_'+side];toe=ix['TOE_'+side];flat=R.from_euler('z',anchor_yaw[f,s]).as_quat();qf=planned_q[f,s] if np.isfinite(planned_q[f,s]).all() else flat;qt=planned_toe[f,s] if np.isfinite(planned_toe[f,s]).all() else flat;footq=qmix(qs[f,ankle],qf,alpha);toeq=qmix(qs[f,toe],qt,alpha)
    currentsole=foot(p,r,side);desiredsole=currentsole if alpha<=0 else currentsole*(1-alpha)+ik_targets[f,s]*alpha;target=desiredsole-R.from_quat(footq).apply(H[ix['SOCKET_SOLE_'+side]]-H[ankle])
    rf=R.from_quat(footq).as_matrix();rt=R.from_quat(toeq).as_matrix();minimum=min(float((relative[vids==ankle]@rf.T)[:,2].min()),float(((relative[vids==toe]@rt.T)+(rf@(H[toe]-H[ankle])))[ :,2].min()))
    target[2]=max(target[2],CLEAR-minimum)
    if alpha<=0 and np.linalg.norm(target-p[ankle])<1e-6:continue
    pole=hint[f,knee]-hint[f,hip];okay,error=solve_leg(p,final_q[f],r,side,target,footq,pole,toeq)
    if not okay:
     actual_weights[f,s]=0.;releases.append({'frame':f,'side':side,'reach_excess_m':error})
     length=np.linalg.norm(H[knee]-H[hip])+np.linalg.norm(H[ankle]-H[knee])-.005;vertical=np.clip(target[2]-p[hip,2],-length+.001,length-.001);target[2]=p[hip,2]+vertical;horizontal=target[:2]-p[hip,:2];allowed=np.sqrt(max(0,length*length-vertical*vertical));norm=np.linalg.norm(horizontal)
     if norm>allowed:target[:2]=p[hip,:2]+horizontal*allowed/max(norm,1e-9)
     okay,_=solve_leg(p,final_q[f],r,side,target,footq,pole,toeq)
    p,r=fk(final_q[f],roots[f],ps[f]+[0,0,curve[f]])
  elif holds[f]:
   final_q[f]=neutral_q;p,r=fk(final_q[f],roots[f],ps[f])
  final_p.append(p);mins.append(float(skin(p,r)[:,2].min()))
 final_p=np.asarray(final_p);mins=np.asarray(mins)
 # Report contact residuals rather than silently translating planted feet again.
 report={'schema':'c08-authored-support-cleanup/1','id':slug,'method':'anchored','fps':fps,'frames':count,'duration_s':(count-1)/fps,'source_frames':source_count,'source_used_frames':used,'source_action_range':[action_start,action_end],'source_action_timing_preserved':True,'excluded_source_frame_ranges':[[used,source_count-1]] if used<source_count else [],'entry_frames':[hold_count,action_start-1],'recovery_frames':[action_end+1,count-hold_count-1],'neutral_hold_frames':hold_count,'root_motion_delta_blender':(roots[-1]-roots[0]).tolist(),'support_sole_target_m':SOLE,'floor_envelope_clearance_m':CLEAR,'floor_solver':solver,'stance_root_solver':stance_solver,'incompatible_body_floor_reach_frames':incompatible,'minimum_baked_skin_floor_m':float(mins.min()),'support_release_count':len(releases),'support_releases':releases,'contact_segments':contact_rows,'source_file_sha256':hashlib.sha256((ROOT/'evaluation/mocap-rebuild/exports'/slug/'cleaned/c08-mocap.glb').read_bytes()).hexdigest(),'provenance':'Filtered recovered C08 motion plus explicitly authored transitions, smooth constrained body-floor trajectory and kinematic support IK. No MotionBricks inference.','limitations':['Kinematic contact cleanup, not physical balance or self-collision','No hand/back pinning; roll and floor-support phases explicitly avoid foot locks','Authored pose-blend recovery is not captured stand-up motion','Core source timing retained; first/last10 horizontal root samples ease velocity without changing duration','Contact intervals are heuristic/action-specific, not sensor ground truth','Unreachable feet release instead of stretching limbs; releases reported']}
 folder=BASE/slug
 np.savez_compressed(folder/'cleanup-data.npz',bone_names=np.array(names),parents=parents,rest=rest,positions_blender=final_p,delta_quaternions=final_q,root_translation_blender=roots,pelvis_input_blender=ps,root_vertical_correction_m=curve,source_frame_index=source_index,phase=phases,support_weights=actual_weights,requested_support_weights=weights,support_anchors_blender=anchors,support_yaw_rad=anchor_yaw,contact_segment_ids=segments,swing_mask=swing,foot_ik_weights=ik_weights,foot_ik_goals_blender=ik_targets,sole_local_offsets=np.array([H[ix['SOCKET_SOLE_'+s]]-H[ix['ANKLE_'+s]] for s in ['L','R']]),skin_floor_min_m=mins,raw_source_root_blender=source_root)
 report.update(recipe_version='support-cleanup-2026-10-31-v1',neutral_hold_duration_s=HOLD/FPS,core_foot_policy='Preserve cleaned leg rotations; no foot IK or pinning in the captured action' if slug in ['ukemi','source-094553','technical-standup','gorilla-front','h3-dance'] else 'Left foot remains planted through the stomp; right releases for its lift and replants',authored_placement='Sequential left/right foot placement with9cm swing arcs during entry and recovery; one stance foot remains planted where its source/default pose is flat',root_smoothing='Quadratic body-floor/reach fit with first/second difference penalties scaled by sample rate and its square',processing_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),original_action_fps=FPS)
 (folder/'cleanup-report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
 print('CLEANUP_READY',slug,count,'minfloor',float(mins.min()),'supportframes',np.sum(actual_weights>.999),'releases',len(releases),flush=True)
