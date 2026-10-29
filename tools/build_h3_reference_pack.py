"""Blender 4.5: exact authored-idle references; no AI image generation.

blender -b --threads 8 --python build_h3_reference_pack.py -- \
  --assets-root G:/Dev/MotionBricks/assets --output /path/to/reference-packs/h3-2026-10-30
"""
import argparse,hashlib,json,math,re,struct,sys,zlib
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view

SPECS=[
 ('c08','C08 Industrial Worker','biped','c08-worker/c08_d0_lod1.glb','Standby_Idle'),
 ('brek43','B-REK43','biped','b-rek43/b_rek43_d0_lod1.glb','Recon_Idle'),
 ('eva-k7','EVA-K7','biped','eva-k7/eva_k7_d0_lod1.glb','Suit_Idle'),
 ('k0-tech','K0-Tech','quadruped','k0-tech-01/k0_tech_01_d0_lod1.glb','Watch_Idle'),
 ('c07','C07 Cheetah','quadruped','c07-cheetah/c07_d0_lod1.glb','Watch_Idle'),
]
def sha(file):return hashlib.sha256(Path(file).read_bytes()).hexdigest()
def rows(matrix):return [[float(v) for v in row] for row in matrix]
def dump(file,data):Path(file).write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf8')
def video2rig_cameras(meta):
 def record(info,name,x0=0):
  m=info['camera_to_world_blender'];axes=[[m[i][j] for i in range(3)] for j in range(3)]
  axes=[[v/math.sqrt(sum(x*x for x in axis)) for v in axis] for axis in axes]
  return {'name':name,'width_px':info['resolution'][0],'height_px':info['resolution'][1],'type':'ortho','location':[m[i][3] for i in range(3)],'right':axes[0],'up':axes[1],'forward':[-v for v in axes[2]],'ortho_width':info['orthographic_horizontal_span_m'],'ortho_height':info['orthographic_vertical_span_m'],'x0_px':x0}
 views=meta['views'];result={name:{'frame_px':views[name]['resolution'],'views':[record(views[name],name)],'hover':0} for name in ['three-quarter','side','forward-action-wide']}
 result['dual-front-side']={'frame_px':[1536,768],'views':[record(views['front'],'front',0),record(views['side'],'side',768)],'hover':0}
 return result
def normalize_prompt(text):
 text=re.sub(r'\b(ONE|time|Pause|Hold|over|about|coordinated|VANILLA|approximately)(?=\d)',r'\1 ',text)
 text=re.sub(r'(\d)(m/s|ms|seconds?|degrees?|m|s)\b',r'\1 \2',text)
 text=text.replace('≤',' ≤ ')
 return re.sub(r'[ \t]{2,}',' ',text)
def evaluated_points(objects):
 graph=bpy.context.evaluated_depsgraph_get();points=[]
 for obj in objects:
  if obj.type!='MESH':continue
  evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh()
  points.extend(evaluated.matrix_world@v.co for v in mesh.vertices)
  evaluated.to_mesh_clear()
 if not points or not all(math.isfinite(v) for p in points for v in p):raise RuntimeError('Non-finite or empty character geometry')
 return points
def bounds(points):return Vector([min(p[i] for p in points) for i in range(3)]),Vector([max(p[i] for p in points) for i in range(3)])
def setup(scene,args):
 scene.render.engine=args.engine
 if args.engine=='CYCLES':scene.cycles.device='CPU';scene.cycles.samples=args.samples;scene.cycles.seed=0
 elif hasattr(scene,'eevee'):
  if hasattr(scene.eevee,'taa_render_samples'):scene.eevee.taa_render_samples=args.samples
  if hasattr(scene.eevee,'use_raytracing'):scene.eevee.use_raytracing=False
 scene.render.threads_mode='FIXED';scene.render.threads=8
 scene.render.resolution_percentage=100;scene.render.pixel_aspect_x=scene.render.pixel_aspect_y=1
 scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8';scene.render.image_settings.compression=50
 scene.render.film_transparent=False;scene.render.use_stamp=False;scene.render.fps=30
 scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0;scene.view_settings.gamma=1
 scene.frame_start=scene.frame_end=0;scene.frame_set(0)
def material(name,color,roughness):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=roughness;return m
def area(collection,name,position,target,power,size):
 light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
 obj=bpy.data.objects.new(name,light);collection.objects.link(obj);obj.location=position;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler();return obj
def camera_scene(name,asset,studio,cameras,world,target,direction,scale,width,height,args):
 scene=bpy.data.scenes.new('REF_'+name);setup(scene,args)
 for collection in (asset,studio,cameras):scene.collection.children.link(collection)
 scene.world=world;scene.render.resolution_x=width;scene.render.resolution_y=height
 data=bpy.data.cameras.new('Camera_'+name);data.type='ORTHO';data.sensor_fit='VERTICAL';data.ortho_scale=scale;data.clip_start=.001;data.clip_end=max(100,scale*100)
 cam=bpy.data.objects.new('Camera_'+name,data);cameras.objects.link(cam);position=Vector(target)+Vector(direction).normalized()*max(10,scale*8);rotation=(Vector(target)-position).to_track_quat('-Z','Y');cam.matrix_world=Matrix.LocRotScale(position,rotation,Vector((1,1,1)));scene.camera=cam;cam['reference_width']=width;cam['reference_height']=height
 scene.render.filepath='//'+name+'.png';return scene
def camera_info(scene,points):
 bpy.context.window.scene=scene;bpy.context.view_layer.update();cam=scene.camera;w,h=scene.render.resolution_x,scene.render.resolution_y
 p=cam.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=w,y=h,scale_x=1,scale_y=1);view=cam.matrix_world.inverted();ndc=[world_to_camera_view(scene,cam,v) for v in points]
 extent={'min':[min(v[i] for v in ndc) for i in [0,1]],'max':[max(v[i] for v in ndc) for i in [0,1]]}
 if min(extent['min'])<.025 or max(extent['max'])>.975:raise RuntimeError('Character clipped / insufficient margin: '+scene.name+str(extent))
 cv=Matrix(((1,0,0,0),(0,-1,0,0),(0,0,-1,0),(0,0,0,1)))@view
 world_to_clip=p@view
 pixel=Matrix(((w/2,0,0,w/2),(0,-h/2,0,h/2),(0,0,0,1)))@world_to_clip
 forward=pixel@Vector((0,-1,0,0));direction=Vector((forward.x,forward.y));direction.normalize()
 return {'camera':cam.name,'projection':'ORTHOGRAPHIC','resolution':[w,h],'pixel_aspect':[1,1],'orthographic_vertical_span_m':float(2/p[1][1]),'orthographic_horizontal_span_m':float(2/p[0][0]),'pixels_per_camera_plane_m':[float(w*p[0][0]/2),float(h*p[1][1]/2)],'camera_to_world_blender':rows(cam.matrix_world),'world_to_camera_blender':rows(view),'world_to_camera_cv_xright_ydown_zforward':rows(cv),'projection_camera_to_clip':rows(p),'world_to_clip':rows(world_to_clip),'orthographic_pixel_from_world_homogeneous':rows(pixel),'image_coordinates':'pixel origin top-left; matrix applied to [x,y,z,1]','screen_forward_direction_xy':list(direction),'character_projected_bounds_normalized_bottom_left':extent,'clip_range_m':[cam.data.clip_start,cam.data.clip_end]}
def png_rgba(file):
 data=Path(file).read_bytes();pos=8;packed=b'';extra=[]
 while pos<len(data):
  n=struct.unpack_from('>I',data,pos)[0];kind=data[pos+4:pos+8];chunk=data[pos+8:pos+8+n];pos+=12+n
  if kind==b'IHDR':w,h,depth,color,_,_,interlace=struct.unpack('>IIBBBBB',chunk)
  elif kind==b'IDAT':packed+=chunk
  elif kind in [b'sRGB',b'gAMA',b'cHRM',b'iCCP']:extra.append((kind,chunk))
 if depth!=8 or color!=6 or interlace:raise RuntimeError('Expected noninterlaced8bit RGBA PNG')
 raw=zlib.decompress(packed);stride=w*4;previous=bytearray(stride);pixels=[];offset=0
 def paeth(a,b,c):
  p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c);return a if pa<=pb and pa<=pc else b if pb<=pc else c
 for _ in range(h):
  mode=raw[offset];offset+=1;row=bytearray(raw[offset:offset+stride]);offset+=stride
  for i in range(stride):
   a=row[i-4] if i>=4 else 0;b=previous[i];c=previous[i-4] if i>=4 else 0
   prediction=0 if mode==0 else a if mode==1 else b if mode==2 else (a+b)//2 if mode==3 else paeth(a,b,c) if mode==4 else None
   if prediction is None:raise RuntimeError('Unsupported PNG filter')
   row[i]=(row[i]+prediction)&255
  pixels.append(bytes(row));previous=row
 return w,h,pixels,extra
def concat_png(left,right,destination):
 w,h,a,extra=png_rgba(left);w2,h2,b,_=png_rgba(right);assert (w,h)==(w2,h2)
 def chunk(kind,value):return struct.pack('>I',len(value))+kind+value+struct.pack('>I',zlib.crc32(kind+value)&0xffffffff)
 joined=[x+y for x,y in zip(a,b)]
 data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w+w2,h,8,6,0,0,0))
 for kind,value in extra:data+=chunk(kind,value)
 data+=chunk(b'IDAT',zlib.compress(b''.join(b'\x00'+row for row in joined),9))+chunk(b'IEND',b'');Path(destination).write_bytes(data)
 return {'left_pixels_sha256':hashlib.sha256(b''.join(a)).hexdigest(),'right_pixels_sha256':hashlib.sha256(b''.join(b)).hexdigest(),'same_pose':True,'same_camera_plane_pixel_scale':True,'panel_rectangles_top_left_xywh':[[0,0,w,h],[w,0,w2,h2]]}
def prompt_text(label,kind,view,available,height,length):
 wide=view=='forward-action-wide';dual=view=='dual-front-side';cap=max(.05,available*.8);unit=height if kind=='biped' else length;travel=min(cap,.25*height if kind=='biped' else .10*length) if not wide else cap
 text=f'''{label} — {view} / exact Blender starting frame

Choose ONE prompt below for ONE4–8second clip. These are test prompts, not a guarantee that H3 obeys camera, timing, geometry or contact constraints. Reject/rework changed identity, missing parts, drifting cameras, unmatched panels or cropped motion.

REFERENCE CONTRACT
The image is the original model at time0 of its authored idle. Preserve its silhouette, proportions, panel layout, colors, sensors, hands/paws and tail exactly. No added limbs, props, deformation redesign, cuts, zoom, orbit, tracking or camera shake. Fixed neutral studio, stationary floor, full body visible throughout. Animate joints and root; preserve rigid armor and component lengths.
'''
 if dual:text+='DUAL VIEW: left is front, right is side. Both panels depict the SAME performance at the SAME instant, same pose/phase, duration and pixel scale. Never generate independent actions, stagger timing, resize panels or move the divider. The renderer preserves this at frame0; future generated agreement must be reviewed.\n'
 if wide:text+=f'FORWARD FRAME: the character faces IMAGE-LEFT, starts on the right, and moves toward image-left. Keep total forward displacement at or below approximately{travel:.2f}m ({travel/unit:.2f} reference units). One reference unit is '+('standing body height' if kind=='biped' else 'nose-to-tail bounding length')+'. Stay well inside all borders and stop at the new location. Do not return to the starting position.\n'
 else:text+=f'STANDARD FRAME: use for idle, crouch, small turns and vertical actions. Small root travel only, approximately{travel:.2f}m total. For a longer run/forward jump, use forward-action-wide.png instead of moving/zooming this camera.\n'
 if kind=='biped':
  prompts=[('Idle / ends standing','Six seconds. Hold the supplied stance initially, then a restrained natural weight shift. Feet remain supported; subtle coordinated arm movement. End in the same standing state, without drifting.'),('Squat / ends crouched','Six seconds. Pause0.5s, lower through hips and knees over2s, keep weight between the planted feet, then hold the low crouch. End crouched, not automatically standing.'),('Crouch walk / ends crouched',f'Seven seconds. Lower smoothly, make two short alternating crouched steps with planted support and a clearly swinging opposite foot, total travel≤{travel:.2f}m, brake and hold crouched. No foot skating.'),('Small vertical jump / ends recovered','Six seconds. Still stance, visible recoil, leg extension/takeoff, short vertical flight, soft knee-flexion landing, then standing recovery. Keep horizontal travel tiny and full body inside the fixed frame.'),('Sidestep / ends turned','Six seconds. One small deliberate sidestep, transfer support, then turn the torso/feet together about30degrees. End balanced in the new heading; do not force a return to the initial heading.')]
  if wide:prompts[0]=('Walk–run–stop / ends at destination',f'Eight seconds. Hold0.5s, walk briefly, accelerate into a short running burst with smooth reciprocal arms, then brake with visible support steps. Advance≤{travel:.2f}m toward image-left and finish standing at the new location. No treadmill sliding or camera tracking.')
  if wide:prompts[3]=('Running forward jump / ends at destination',f'Eight seconds. Short run-up, planted recoil, full extension, a clearly forward flight, soft landing and braking recovery. Total travel≤{travel:.2f}m toward image-left, including run-up and recovery. Keep the original body identity, tail-free silhouette and fixed camera; finish standing at the new location, not at the start.')
  menu='''VANILLA15 MENU / NEW-FRAME REQUIREMENTS
Idle, walk, run, small jump, high jump, running jump, crouch down, crouch walk, stand from crouch, sit down, seated idle, sit-to-stand, lie down, forward roll, backward roll.
Use the wide frame for traveling run/jump. High jumps need full visible height; shorten/reject any action exceeding the frame. Stand-from-crouch needs a new CROUCHED starting frame. Sit down / seated idle / sit-to-stand require a real visible chair and a newly rendered chair-interaction starting frame; this empty studio idle image does not supply one. Floor work/rolls need floor-appropriate starting poses plus front/side/depth evidence; a backward roll should start from an appropriate seated/floor reference. No invented chair, grip or hidden support is validated by this pack.
'''
 else:
  prompts=[('Watch idle / ends standing','Six seconds. Hold the exact supplied quadruped stance, a restrained head look and small tail response. Four paws stay supported. End standing without body drift.'),('Crouch / stalk / ends low',f'Seven seconds. Lower the body under controlled leg flexion, make two small alternating stalk steps, total travel≤{travel:.2f}m, then stop low. Preserve paw count, rigid joints and complete tail.'),('Sit down / ends seated','Six seconds. Move the hindquarters down with visible paw support and coordinated front legs. End sitting; do not automatically stand up. Keep the original mechanical anatomy.'),('Small step and turn / ends at new heading','Six seconds. One small lateral support step and a coordinated30degree turn. Paws lift and plant in a clear order; the torso and tail follow naturally. End standing in the new heading.'),('Low hop / ends recovered','Six seconds. Crouch, visibly push off, a low short flight and a four-paw landing with leg flexion. Keep forward travel tiny, then recover standing. Fixed camera; no tail or paws outside the frame.')]
  if wide:prompts[0]=('Walk–trot/gallop–stop / ends at destination',f'Eight seconds. Begin still, a short walk, a brief coordinated faster stride, then braking support steps. Move toward image-left by≤{travel:.2f}m total and hold standing at the new location. If the action does not fit, shorten it; never zoom, track or crop the tail.')
  if wide:prompts[4]=('Forward pounce / ends at destination',f'Seven seconds. Still stance, deliberate crouch/recoil, strong leg extension, visible forward flight, fore/hind paw landing and recovery. Total forward travel≤{travel:.2f}m toward image-left. Keep the complete robot and tail visible; finish standing at the new location, without returning to the start.')
  menu='''QUADRUPED MENU / NEW-FRAME REQUIREMENTS
Watch idle; walk; trot; short gallop-stop; forward pounce; low crouch/stalk; sit down; stand from sit. Use wide for travel/pounce. A stand-from-sit clip requires a newly rendered SEATED reference. Keep long-tail clearance visible. Rolling/floor contact needs additional side/front/depth evidence. A pretty generated pounce is not proof of editable rig recovery or physical balance.
'''
 text+='\nSEPARATE PROMPTS — DO NOT COMBINE THESE INTO ONE VIDEO\n'
 for i,(title,prompt) in enumerate(prompts,1):text+=f'\n{i}. {title}\n{prompt}\n'
 return normalize_prompt(text+'\n'+menu+'\nReview the output against this starting frame, camera JSON and original rig. Matching the first frame alone does not establish subsequent geometry/camera consistency.\n')
def build(spec,args,temp):
 ident,label,kind,relative,idle=spec;source=args.assets_root/relative;folder=args.output/ident;folder.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(source));imported=list(scene.objects);helpers={b.custom_shape for o in imported if o.type=='ARMATURE' for b in o.pose.bones if b.custom_shape};objects=[o for o in imported if o not in helpers];
 for helper in helpers:helper.hide_render=True
 for obj in objects:
  if obj.animation_data:
   for track in obj.animation_data.nla_tracks:track.mute=True
 action=bpy.data.actions.get(idle)
 if not action:raise RuntimeError('Missing authored idle '+idle)
 for obj in objects:
  if obj.type=='ARMATURE':obj.animation_data_create();obj.animation_data.action=action;obj.animation_data.action_slot=action.slots[0]
 scene.frame_set(int(action.frame_range[0]));bpy.context.view_layer.update();original=evaluated_points(objects)
 bases={o.name:o.matrix_basis.copy() for o in objects};bones={o.name:{b.name:b.matrix_basis.copy() for b in o.pose.bones} for o in objects if o.type=='ARMATURE'}
 for obj in objects:
  if obj.animation_data:obj.animation_data.action=None
  obj.matrix_basis=bases[obj.name]
  if obj.type=='ARMATURE':
   for bone in obj.pose.bones:bone.matrix_basis=bones[obj.name][bone.name]
 bpy.context.view_layer.update();points=evaluated_points(objects);difference=max((a-b).length for a,b in zip(original,points))
 if difference>1e-6:raise RuntimeError('Freezing changed original pose '+str(difference))
 low,high=bounds(points);size=high-low;height=size.z;length=size.y;scale=max(height*2.2,max(size.x,size.y)*1.45);center=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z+height*.95))
 asset=bpy.data.collections.new('ASSET_ORIGINAL_FROZEN');studio=bpy.data.collections.new('STUDIO');cameras=bpy.data.collections.new('REFERENCE_CAMERAS')
 for obj in objects:
  for collection in list(obj.users_collection):collection.objects.unlink(obj)
  asset.objects.link(obj)
 scene.collection.children.link(asset);scene.collection.children.link(studio);scene.collection.children.link(cameras)
 bpy.ops.mesh.primitive_plane_add(size=max(30,scale*30),location=(center.x,center.y,low.z-.002));floor=bpy.context.object;floor.name='STUDIO_FLOOR';floor.data.materials.append(material('Studio matte neutral',(.31,.33,.32),.9))
 for collection in list(floor.users_collection):collection.objects.unlink(floor)
 studio.objects.link(floor)
 extent=max(height,size.x,size.y);look=Vector((center.x,center.y,low.z+height*.6));power=1100*(extent/2)**2
 area(studio,'Key',look+Vector((extent*1.8,-extent*2.2,extent*3)),look,power,extent*2)
 area(studio,'Fill',look+Vector((-extent*2,-extent*.6,extent*1.6)),look,power*.65,extent*2.2)
 area(studio,'Rim',look+Vector((extent*.7,extent*2,extent*2.4)),look,power*.95,extent*1.8)
 world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.22,.25,.24,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
 elevation=math.tan(math.radians(8));scenes={name:camera_scene(name,asset,studio,cameras,world,center,direction,scale,768,768,args) for name,direction in [('three-quarter',(1,-1.25,elevation*math.sqrt(1+1.25**2))),('front',(0,-1,elevation)),('side',(1,0,elevation))]}
 wide_width=max(3*length,4.4*height);wide_height=wide_width/2;wide_target=center+Vector((0,-wide_width*.22,0));scenes['forward-action-wide']=camera_scene('forward-action-wide',asset,studio,cameras,world,wide_target,(1,0,elevation),wide_height,1536,768,args)
 views={name:camera_info(s,points) for name,s in scenes.items()};wide=views['forward-action-wide'];available=max(0,(wide['character_projected_bounds_normalized_bottom_left']['min'][0]-.05)*wide['orthographic_horizontal_span_m']);wide['available_forward_travel_before_left_5percent_margin_m']=available
 pose={o.name:{'object_world':rows(o.matrix_world),'bones':{b.name:{'matrix_armature':rows(b.matrix),'matrix_world':rows(o.matrix_world@b.matrix),'matrix_basis':rows(b.matrix_basis),'rest_matrix_local':rows(b.bone.matrix_local)} for b in o.pose.bones}} for o in objects if o.type=='ARMATURE'}
 snapshot={'body':ident,'label':label,'kind':kind,'source_asset_relative':relative,'source_glb_sha256':sha(source),'authored_idle':idle,'authored_time_s':0,'blender_frame':0,'frozen_pose':True,'active_actions':False,'nla_tracks_muted':True,'new_character_geometry':False,'mesh_vertices':len(points),'max_pose_freeze_vertex_difference_m':difference,'bounds_world_m':{'min':list(low),'max':list(high)},'world_coordinates':'Blender +Z up; character forward -Y. Side camera +X gives image-left forward.','source_pose':pose,'studio':{'floor_z_m':float(low.z-.002),'note':'Separate neutral studio geometry; character geometry and transforms remain unchanged.'},'views':views,'render':{'blender_version':bpy.app.version_string,'engine':args.engine,'samples':args.samples,'color_transform':'AgX / Medium High Contrast','resolution_percentage':100,'pixel_aspect':[1,1]},'limitations':['Authored idle starting frame only; no generated motion or recovery is being certified.','Orthographic cameras are exact for these renders; H3 may change camera, shape or timing.','Dual panels share original pose/scale; generated future panel agreement must be inspected.']}
 for s in scenes.values():s['h3_reference_body']=ident;s['source_sha256']=snapshot['source_glb_sha256'];s['authored_idle']=idle;s['frozen_start_frame']=0
 bpy.context.window.scene=scenes['three-quarter'];bpy.data.scenes.remove(scene);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'source.blend'),compress=True)
 for name,s in scenes.items():
  bpy.context.window.scene=s;s.render.filepath=str(temp/(ident+'-front.png') if name=='front' else folder/(name+'.png'));bpy.ops.render.render(write_still=True,scene=s.name)
 views['dual-front-side']={'projection':'two matched orthographic panels','resolution':[1536,768],'left_camera':views['front'],'right_camera':views['side'],**concat_png(temp/(ident+'-front.png'),folder/'side.png',folder/'dual-front-side.png')}
 snapshot['video2rig_camera_files']=[]
 for name,data in video2rig_cameras(snapshot).items():
  filename=name+'.video2rig-cameras.json';dump(folder/filename,data);snapshot['video2rig_camera_files'].append(filename)
 for name in ['three-quarter','side','dual-front-side','forward-action-wide']:(folder/(name+'.txt')).write_text(prompt_text(label,kind,name,available,height,length),encoding='utf8')
 snapshot['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in folder.iterdir() if p.suffix in ['.png','.txt','.blend'] or p.name.endswith('.video2rig-cameras.json')}
 if snapshot['files']['source.blend']['bytes']>=100_000_000:raise RuntimeError('Blend exceeds public file budget')
 dump(folder/'camera-and-pose.json',snapshot);print('H3_PACK_BODY',ident,len(points),difference,available,flush=True);return snapshot
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--assets-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--body',choices=[s[0] for s in SPECS]);parser.add_argument('--engine',choices=['BLENDER_EEVEE_NEXT','CYCLES'],default='BLENDER_EEVEE_NEXT');parser.add_argument('--samples',type=int,default=32);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);args.assets_root=args.assets_root.resolve();args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=True)
 temp=args.output.parent/('_render-temp-'+args.output.name);temp.mkdir(exist_ok=True)
 records=[build(spec,args,temp) for spec in SPECS if not args.body or args.body==spec[0]]
 if not args.body:dump(args.output/'manifest.json',{'schema':'h3-own-asset-reference-pack/1','pack_date':'2026-10-30','scope':'Exact first authored idle poses; original geometry/rig retained. No AI images or recovered motion.','bodies':[{'id':r['body'],'label':r['label'],'source_glb_sha256':r['source_glb_sha256'],'idle':r['authored_idle'],'camera_pose_manifest':r['body']+'/camera-and-pose.json','blend':r['body']+'/source.blend','images':[r['body']+'/'+name+'.png' for name in ['three-quarter','side','dual-front-side','forward-action-wide']]} for r in records]})
 for spec in SPECS:
  candidate=temp/(spec[0]+'-front.png')
  if candidate.exists():candidate.unlink()
 if not any(temp.iterdir()):temp.rmdir()
 print('H3_PACK_DONE',len(records),flush=True)
if __name__=='__main__':main()
