"""Build an isolated, local-only mesh-audit catalog from completed pilot bakes."""
from pathlib import Path
import numpy as np,json,shutil,runpy,os,argparse
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('ids',nargs='*');parser.add_argument('--source-root',type=Path,default=ROOT/'evaluation/reactive-round3');args=parser.parse_args()
out=ROOT/'logs/reactive-round3-pilot-view';out.mkdir(exist_ok=True);cases=[]
for name in args.ids or ['jump_baseline_1','jump_reactive_1','crouch_baseline_1','crouch_reactive_1']:
 source=args.source_root/name;dest=out/'takes'/name;dest.mkdir(parents=True,exist_ok=True)
 for file in ['g1-motion.npz','g1-motion.json','retarget-report.json','c08-motionbricks-test.glb','episode.json']:shutil.copy2(source/file,dest/file)
 os.environ['MB_TEST_DIRECTORY']=str(dest);runpy.run_path(str(ROOT/'tools/prepare_c08_review.py'),run_name='__main__');os.environ.pop('MB_TEST_DIRECTORY')
 d=np.load(dest/'g1-motion.npz');report=json.loads((dest/'retarget-report.json').read_text());ep=json.loads((dest/'episode.json').read_text());q=d['qpos'][0,3:7];S=np.array([[0,1,0],[-1,0,0],[0,0,1]]);r=S@Rotation.from_quat(q).as_matrix()@S.T;f=r@np.array([0,-1,0]);yaw=np.arctan2(f[0],-f[1]);A=Rotation.from_rotvec([0,0,-yaw]).as_matrix()@S;origin=A@d['qpos'][0,:3];origin[2]=0;D=np.array([[1,0,0],[0,0,1],[0,-1,0]])
 ep['display']={'display_scale':report['source_to_target_scale'],'display_basis':(D@A).tolist(),'display_origin':(D@origin).tolist(),'display_pelvis_offset':0};(dest/'episode.json').write_text(json.dumps(ep),encoding='utf8')
 cases.append({'id':name,'episode':'takes/'+name+'/episode.json','glb':'takes/'+name+'/c08-motionbricks-test.glb','preview':'takes/'+name+'/g1-preview.json'})
(out/'catalog.json').write_text(json.dumps({'cases':cases}),encoding='utf8')
