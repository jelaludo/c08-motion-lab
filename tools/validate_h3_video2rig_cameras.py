"""Run with the provisioned Video2Rig Python to test its actual Camera parser."""
import argparse,json,sys,hashlib,subprocess
from pathlib import Path
import numpy as np
parser=argparse.ArgumentParser();parser.add_argument('--pack-root',type=Path,required=True);parser.add_argument('--video2rig-root',type=Path,required=True);args=parser.parse_args();sys.dont_write_bytecode=True;sys.path.insert(0,str(args.video2rig_root.resolve()))
from video2rig.clip import Camera
root=args.pack_root.resolve();result=[]
for folder in sorted(p for p in root.iterdir() if p.is_dir()):
 meta=json.loads((folder/'camera-and-pose.json').read_text());rig=next(iter(meta['source_pose'].values()));matrix=np.asarray(rig['object_world']);local=np.array([[b['matrix_armature'][i][3] for i in range(3)] for b in rig['bones'].values()]);world=local@matrix[:3,:3].T+matrix[:3,3];maximum=0
 for name in ['three-quarter','side','dual-front-side','forward-action-wide']:
  data=json.loads((folder/(name+'.video2rig-cameras.json')).read_text());assert data['frame_px']==meta['views'][name]['resolution']
  for index,record in enumerate(data['views']):
   expected=meta['views'][name] if name!='dual-front-side' else meta['views']['front' if index==0 else 'side'];camera=Camera(record,data['frame_px'],data['frame_px'],matrix,np.zeros(3));actual=camera.project(local)+np.array([record['x0_px'],0]);pixels=np.c_[world,np.ones(len(world))]@np.asarray(expected['orthographic_pixel_from_world_homogeneous']).T;pixels=pixels[:,:2]+np.array([record['x0_px'],0]);difference=float(np.abs(actual-pixels).max());maximum=max(maximum,difference)
   assert difference<.005,(folder.name,name,difference)
   assert abs(record['width_px']/record['ortho_width']-record['height_px']/record['ortho_height'])<.001
   assert record['x0_px']>=0 and record['x0_px']+record['width_px']<=data['frame_px'][0]
 result.append({'body':folder.name,'files':4,'official_Camera_max_pixel_error':maximum,'armature_world_included_by_official_parser':True})
source=args.video2rig_root/'video2rig/clip.py';commit=subprocess.check_output(['git','-C',str(args.video2rig_root),'rev-parse','HEAD'],text=True).strip()
report={'status':'passed','format':'Official Video2Rig frame_px/views ortho camera records','parser_repository':'https://github.com/canitcode/video2rig','parser_commit':commit,'clip_py_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'files':20,'scope':'Actual official Camera parser vs Blender projection matrices on every saved armature-space joint. Does not claim H3-generated future frames preserve cameras.','results':result};(root/'video2rig-camera-validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
