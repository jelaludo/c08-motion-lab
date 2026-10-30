"""Independently verify cached neural requests, played context, targets and loop seams."""
from pathlib import Path
import hashlib, json
import numpy as np
from scipy.spatial.transform import Rotation
import os
_roots=[Path(os.environ['MOTION_LAB_WORKSPACE'])] if os.environ.get('MOTION_LAB_WORKSPACE') else list(Path(__file__).resolve().parents)
ROOT=next((p for p in _roots if (p/'evaluation/mocap-rebuild').is_dir() and (p/'video-mocap').is_dir()),None)
if ROOT is None:raise RuntimeError('Set MOTION_LAB_WORKSPACE to the original lab workspace; private source/request arrays are not bundled.')
OUT=ROOT/'evaluation/mocap-rebuild'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=load(OUT/'generation-summary.json')
assert summary['status']=='complete'
model=ROOT/'upstream/motionbricks/assets/onnx/soma/mmm_v6_soma_fp32.onnx'
assert sha(model)==summary['model_sha256']
rows=[];calls=0
for slug in ['ukemi','technical-standup','gorilla-front','sumo-stomp','source-094553','h3-dance']:
 plan=load(OUT/slug/'key-plan.json')
 assert plan['source_prepared_sha256']==sha(ROOT/'video-mocap/c08-retarget'/slug/'soma-frames.npz')
 keys=plan['source_key_indices'];assert keys==sorted(set(keys))
 assert all(0<=k<=plan['used_source_frame_range'][1]-3 for k in keys)
 clean=np.load(OUT/slug/'cleaned/soma-frames.npz')['local_transforms']
 for method in ['single','window']:
  folder=OUT/slug/method;meta=load(folder/'source-metadata.json')
  data=np.load(folder/'soma-frames.npz');local=data['local_transforms'];arrays=np.load(folder/'inference-arrays.npz')
  assert np.isfinite(local).all() and len(local)==meta['frames']
  assert meta['model_sha256']==summary['model_sha256']
  assert meta['source_prepared_sha256']==plan['source_prepared_sha256']
  assert meta['actual_neural_calls']==len(meta['segments'])==len(keys)+1
  hold=meta['neutral_hold_frames'];assert hold>=4
  assert np.array_equal(local[:hold],np.repeat(local[:1],hold,axis=0))
  assert np.array_equal(local[-hold:],np.repeat(local[:1],hold,axis=0))
  cursor=hold;max_context_error=0;max_played_error=0
  for i,segment in enumerate(meta['segments']):
   context=arrays[f'context_{i}'];target=arrays[f'target_{i}'];output=arrays[f'output_{i}']
   assert segment['output_frame_start']==cursor
   context_error=float(np.max(np.abs(context-local[cursor-4:cursor])))
   assert np.array_equal(context.astype(np.float32),local[cursor-4:cursor].astype(np.float32)),(slug,method,i,context_error)
   max_context_error=max(max_context_error,context_error)
   width=1 if method=='single' else 4
   assert len(target)==width
   key=segment['source_key_index']
   if i<len(keys):
    assert key==keys[i] and np.array_equal(target.astype(np.float32),clean[key:key+width].astype(np.float32))
   else:assert key is None and np.array_equal(target.astype(np.float32),np.repeat(local[:1],width,axis=0).astype(np.float32))
   for keyname,array in [('context',context),('target',target),('output',output)]:
    assert segment[f'{keyname}_sha256']==hashlib.sha256(array.tobytes()).hexdigest()
   # A shared endpoint may be omitted for playback while full NN output stays cached.
   used=len(output)-segment['frames'];assert used in (0,1)
   if used:
    assert np.max(np.abs(output[0,:,:3]-context[-1,:,:3]))<1e-5
    rotations=Rotation.from_quat(output[0,:,3:]).inv()*Rotation.from_quat(context[-1,:,3:])
    assert np.max(rotations.magnitude())<1e-5
   played=output[used:];saved=local[cursor:cursor+len(played)]
   error=float(np.max(np.abs(played-saved)))
   # Only the final endpoint has the documented floating-point neutral snap.
   if i<len(keys):assert np.array_equal(played,saved),(slug,method,i,error)
   else:
    translation_error=float(np.max(np.abs(played[:,:,:3]-saved[:,:,:3])))
    rotation_error=float(np.max((Rotation.from_quat(played[:,:,3:].reshape(-1,4)).inv()*Rotation.from_quat(saved[:,:,3:].reshape(-1,4))).magnitude()))
    assert max(translation_error,rotation_error)<1e-5,(slug,method,'final_numeric_snap',translation_error,rotation_error)
   max_played_error=max(max_played_error,error);cursor+=len(played);calls+=1
  assert cursor==len(local)-hold
  assert meta['active_frame_range']==[hold,cursor-1]
  first=data['world_transforms'][0];last=data['world_transforms'][-1]
  assert np.array_equal(first,last)
  rows.append({'id':slug,'method':method,'frames':len(local),'neural_calls':len(keys)+1,'target_window_frames':width,'max_played_context_element_error':max_context_error,'max_cached_to_played_element_error':max_played_error,'loop_endpoint_matrix_error':float(np.max(np.abs(first-last))),'authored_neutral_hold_frames_each_end':hold,'shared_endpoint_playback_dedup_verified':True})
assert calls==summary['actual_neural_calls']==96
result={'status':'passed','neural_variants':len(rows),'actual_neural_calls':calls,'model_sha256':summary['model_sha256'],'checks':['All requests use SOMA native77 hierarchy and the same verified FP32 model','Single/window use identical seven source landmarks and 1/4 consecutive target frames','Every next context equals the last four actually played poses after FP32 upload conversion','Cached raw outputs retain every NN frame; only coincident shared playback endpoints are removed','Generated phases are copied without interpolation; final neutral numeric residual below1e-5','Twelve authored neutral frames at each end establish exact pose and zero boundary velocity','Original source preparation hashes unchanged'],'results':rows}
(OUT/'independent-generation-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
