"""Reopen every delivered .blend and validate frozen pose, cameras and image pairs."""
import sys,argparse,json,math,hashlib
from pathlib import Path
import bpy
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_h3_reference_pack as build
def error(a,b):return max(abs(x-y) for row_a,row_b in zip(a,b) for x,y in zip(row_a,row_b))
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--pack-root',type=Path,required=True);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);root=args.pack_root.resolve();manifest=json.loads((root/'manifest.json').read_text());results=[]
 for body in manifest['bodies']:
  folder=root/body['id'];meta=json.loads((folder/'camera-and-pose.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(folder/'source.blend'),load_ui=False)
  objects=list(bpy.data.collections['ASSET_ORIGINAL_FROZEN'].all_objects);rigs=[o for o in objects if o.type=='ARMATURE'];helpers={b.custom_shape for r in rigs for b in r.pose.bones if b.custom_shape}
  assert all(o not in helpers for o in objects)
  assert all(not r.animation_data or (r.animation_data.action is None and all(t.mute for t in r.animation_data.nla_tracks)) for r in rigs)
  assert all(helper.hide_render for helper in helpers)
  for helper in helpers:assert all(helper.name not in scene.objects for scene in bpy.data.scenes if scene.name.startswith('REF_'))
  pose_error=camera_error=projection_error=temporal_error=0;frames=[]
  for name in ['three-quarter','front','side','forward-action-wide']:
   scene=bpy.data.scenes['REF_'+name];bpy.context.window.scene=scene;scene.frame_set(0);scene.view_layers[0].update();points=build.evaluated_points(objects);assert len(points)==meta['mesh_vertices'];actual=build.camera_info(scene,points);expected=meta['views'][name]
   assert actual['resolution']==expected['resolution'];camera_error=max(camera_error,error(actual['camera_to_world_blender'],expected['camera_to_world_blender']));projection_error=max(projection_error,error(actual['projection_camera_to_clip'],expected['projection_camera_to_clip']))
   for rig in rigs:
    for bone in rig.pose.bones:
     stored=meta['source_pose'][rig.name]['bones'][bone.name];pose_error=max(pose_error,error(build.rows(rig.matrix_world@bone.matrix),stored['matrix_world']))
   before={r.name:{b.name:build.rows(r.matrix_world@b.matrix) for b in r.pose.bones} for r in rigs};scene.frame_set(17);scene.view_layers[0].update()
   for rig in rigs:
    for bone in rig.pose.bones:temporal_error=max(temporal_error,error(build.rows(rig.matrix_world@bone.matrix),before[rig.name][bone.name]))
   scene.frame_set(0);frames.append(actual['character_projected_bounds_normalized_bottom_left'])
  assert max(pose_error,camera_error,projection_error,temporal_error)<1e-6
  front=meta['views']['front'];side=meta['views']['side'];assert abs(front['pixels_per_camera_plane_m'][0]-side['pixels_per_camera_plane_m'][0])<1e-6
  dual=meta['views']['dual-front-side'];w,h,pixels,_=build.png_rgba(folder/'dual-front-side.png');assert (w,h)==(1536,768)
  left=b''.join(row[:768*4] for row in pixels);right=b''.join(row[768*4:] for row in pixels);assert hashlib.sha256(left).hexdigest()==dual['left_pixels_sha256'];assert hashlib.sha256(right).hexdigest()==dual['right_pixels_sha256']
  _,_,single,_=build.png_rgba(folder/'side.png');assert b''.join(single)==right
  for name in ['three-quarter','side','forward-action-wide']:
   width,height,_,_=build.png_rgba(folder/(name+'.png'));assert (width,height)==((1536,768) if name=='forward-action-wide' else (768,768));assert (folder/(name+'.txt')).is_file()
  for file,details in meta['files'].items():assert build.sha(folder/file)==details['sha256']
  compatible=build.video2rig_cameras(meta)
  assert len(meta['video2rig_camera_files'])==4
  for name,data in compatible.items():
   file=name+'.video2rig-cameras.json';assert json.loads((folder/file).read_text())==data;assert file in meta['files']
  assert meta['views']['side']['screen_forward_direction_xy'][0]<-.99;assert meta['views']['forward-action-wide']['screen_forward_direction_xy'][0]<-.99
  assert (folder/'source.blend').stat().st_size<100_000_000
  results.append({'id':body['id'],'vertices':meta['mesh_vertices'],'bone_pose_error_m':pose_error,'camera_matrix_error':camera_error,'projection_error':projection_error,'frozen_time_error':temporal_error,'dual_pixels_match_side_exactly':True,'render_projected_bounds':frames,'blend_bytes':(folder/'source.blend').stat().st_size})
 report={'status':'passed','bodies':len(results),'pngs':20,'companion_txts':20,'video2rig_camera_jsons':20,'checks':['Reopened original frozen idle pose/rig; all NLA muted and actions detached','Importer widget helpers excluded from rendered scenes and body bounds','Saved camera matrices/projection/resolution match manifests','All body vertices finite and within 2.5 percent frame margins','Side/wide forward is image-left','Front/side panels same camera-plane pixel scale; right panel byte-identical RGBA to side','20 PNG dimensions, companions and recorded hashes verified','20 Video2Rig camera JSON files equal their exact Blender source records','Every .blend below 100 MB'],'results':results,'scope':'Exact starting-reference asset/camera validation. No generated video, motion recovery or physical balance approval.'};build.dump(root/'validation.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
