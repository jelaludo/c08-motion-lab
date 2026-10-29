"""Height-aware external root navigation; never edits a neural pose's Z or joints.

Coordinates are native G1 metres, Z up. The anatomical envelope is calibrated
against the actual C08 skin (see reactive-behavior-calibration.json); this is a
conservative navigation proxy, not articulated mesh collision. Publication QA
must separately test both displayed bodies against the obstacle geometry.
"""
import math
import numpy as np

EPSILON=1e-4
HEAD_MARGIN_M=.86
SOLE_MARGIN_M=.17

def pose_vertical_bounds(q,predictor):
    """Conservative C08-native sole/head envelope from the untouched G1 FK."""
    b=predictor.transforms(np.asarray(q,dtype=np.float32)[None,:])[0]
    names={name:i for i,name in enumerate(predictor.names)}
    ankles=[names[n] for n in ('left_ankle_roll_link','right_ankle_roll_link')]
    return float(b[ankles,2].min()-SOLE_MARGIN_M),float(b[:,2].max()+HEAD_MARGIN_M)

def vertically_overlaps(a,b,ob):
    """Union of endpoint envelopes conservatively covers each 1/30s step."""
    bottom=min(a[0],b[0]);top=max(a[1],b[1])
    base=float(ob.get('base_z',0.));ceiling=base+float(ob['height'])
    return bottom<ceiling+EPSILON and top>base-EPSILON

def _circle_hit(position,delta,center,radius):
    offset=position-center;a=float(delta@delta)
    if a<1e-18:return None
    c=float(offset@offset-radius*radius)
    if c< -EPSILON:
        # Existing penetration is surfaced; no silent teleport/depenetration.
        normal=offset/max(np.linalg.norm(offset),1e-9)
        return (0.,normal) if delta@normal<0 else None
    b=2*float(offset@delta);disc=b*b-4*a*c
    if disc<0:return None
    t=(-b-math.sqrt(max(0.,disc)))/(2*a)
    if -1e-7<=t<=1:
        normal=offset+delta*max(0.,t);normal/=max(np.linalg.norm(normal),1e-9)
        if delta@normal<0:return max(0.,t),normal
    return None

def _box_hit(position,delta,ob,radius):
    center=np.asarray(ob['center'],float)
    half=np.array([float(ob['depth'])/2,float(ob['width'])/2])+radius+EPSILON
    lo=center-half;hi=center+half;enter=-np.inf;leave=np.inf;normal=None
    inside=bool(np.all(position>lo+EPSILON)&np.all(position<hi-EPSILON))
    if inside:
        # A newly lowered pose while over the obstacle is a failed passage.
        # Freeze inward travel and report contact; never lift it over the bar.
        axis=int(np.argmin(np.minimum(position-lo,hi-position)))
        n=np.zeros(2);n[axis]=-1 if position[axis]-lo[axis]<hi[axis]-position[axis] else 1
        return (0.,n) if delta@n<=0 else None
    for axis in (0,1):
        if abs(delta[axis])<1e-12:
            if position[axis]<lo[axis] or position[axis]>hi[axis]:return None
            continue
        t0=(lo[axis]-position[axis])/delta[axis];t1=(hi[axis]-position[axis])/delta[axis]
        n=np.zeros(2);n[axis]=-1 if delta[axis]>0 else 1
        if t0>t1:t0,t1=t1,t0
        if t0>enter:enter=t0;normal=n
        leave=min(leave,t1)
        if enter>leave:return None
    if -1e-7<=enter<=1 and leave>=0 and normal is not None and delta@normal<0:return max(0.,enter),normal
    return None

def resolve_pose(previous_q,candidate_q,env,predictor):
    """Return (safeXY, obstacle indices) for a genuine predicted candidate pose.

    Hurdles are traversable only while the lowest sole proxy is above their top;
    bars only while the highest anatomy proxy is below their underside. Vertical
    coordinates and all joint angles are untouched. Both endpoints must clear.
    """
    a=pose_vertical_bounds(previous_q,predictor);b=pose_vertical_bounds(candidate_q,predictor)
    active=[(i,ob) for i,ob in enumerate(env['obstacles']) if vertically_overlaps(a,b,ob)]
    position=np.asarray(previous_q[:2],float).copy();remaining=np.asarray(candidate_q[:2],float)-position
    radius=float(env['root_radius_m']);hits=[]
    for _ in range(5):
        if np.linalg.norm(remaining)<1e-8:break
        hit_time=1.;normal=None;which=None
        for index,ob in active:
            hit=_box_hit(position,remaining,ob,radius) if ob.get('shape')=='box' else _circle_hit(position,remaining,np.asarray(ob['center'],float),float(ob['radius'])+radius+EPSILON)
            if hit is not None and hit[0]<hit_time:hit_time,normal=hit;which=index
        bounds=env['bounds']
        for axis,lo,hi in [(0,bounds[0]+radius+EPSILON,bounds[1]-radius-EPSILON),(1,bounds[2]+radius+EPSILON,bounds[3]-radius-EPSILON)]:
            if abs(remaining[axis])<1e-12:continue
            t=(lo-position[axis])/remaining[axis] if remaining[axis]<0 else (hi-position[axis])/remaining[axis]
            if 0<=t<hit_time:
                hit_time=t;normal=np.zeros(2);normal[axis]=1 if remaining[axis]<0 else -1;which=-1-axis
        if normal is None:position+=remaining;break
        position+=remaining*max(0.,hit_time-1e-6);remaining*=1-hit_time
        remaining-=normal*min(0.,float(remaining@normal));position+=normal*1e-5;hits.append(which)
    return position,hits
