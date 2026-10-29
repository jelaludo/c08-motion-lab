"""Focused geometry checks for the external controller, independent of neural inference."""
import numpy as np
from reactive_behavior_collision import resolve_pose

class Anatomy:
    names=['left_ankle_roll_link','right_ankle_roll_link','torso_link']
    def transforms(self,q):
        # q[2] supplies ankle height, q[7] the highest G1 joint for this fixture.
        out=np.zeros((len(q),3,7));out[:,0,2]=out[:,1,2]=q[:,2];out[:,2,2]=q[:,7]
        return out

def candidate(x,ankle=.036,top_joint=1.085):
    q=np.zeros(36);q[0]=x;q[2]=ankle;q[6]=1.;q[7]=top_joint;return q

env={'bounds':[-5,10,-5,5],'root_radius_m':1.05,'obstacles':[{'shape':'box','center':[2.,0.],'depth':.35,'width':4.,'base_z':0.,'height':.18}]}
predictor=Anatomy()
before=candidate(0.);after=candidate(4.);original=after.copy();xy,hits=resolve_pose(before,after,env,predictor)
assert hits==[0] and xy[0]<.776,(xy,hits)
assert np.array_equal(after,original),'Collision solver changed a neural pose'
xy,hits=resolve_pose(candidate(0.,.5),candidate(4.,.5),env,predictor)
assert not hits and np.allclose(xy,[4,0]),(xy,hits)
xy,hits=resolve_pose(candidate(0.,.5),candidate(4.,.036),env,predictor)
assert hits and xy[0]<.776,'Endpoint sweep must block a descending sole'
env['obstacles'][0].update(base_z=1.62,height=.2)
xy,hits=resolve_pose(candidate(0.),candidate(4.),env,predictor)
assert hits,'Standing head passed through an overhead bar'
xy,hits=resolve_pose(candidate(0.,top_joint=.70),candidate(4.,top_joint=.70),env,predictor)
assert not hits and np.allclose(xy,[4,0]),(xy,hits)
xy,hits=resolve_pose(candidate(0.,top_joint=.70),candidate(4.,top_joint=1.085),env,predictor)
assert hits,'Rising head passed through an overhead bar'
env['obstacles']=[{'center':[2,0],'radius':.5,'height':3.}]
xy,hits=resolve_pose(candidate(0.),candidate(4.),env,predictor)
assert hits and xy[0]<.451,'Continuous circle sweep tunneled through a pillar'
print('PASS: grounded/airborne hurdle, standing/crouched bar, vertical endpoint sweeps, circle tunneling, unchanged neural Z/joints')
