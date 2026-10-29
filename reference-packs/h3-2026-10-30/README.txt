H3 EXACT BLENDER STARTING-FRAME PACK — 2026-10-30

Five user-owned original robot assets; 20 rendered starting images, 20 companion
prompt menus, 20 directly usable Video2Rig camera files, and five frozen .blend
scenes. These are starting references, not generated animation or mocap results.

START HERE
1. Choose a body folder. Open its PNG and the TXT with the same basename.
2. Copy ONE action prompt into H3 for ONE 4–8 second clip. Review identity,
   contact, full-body framing and camera consistency; compliance is not assured.
3. Preserve the original generated output and settings for the recovery test.
4. For Video2Rig, use that PNG's .video2rig-cameras.json with the matching
   original rig exported from source.blend. The official exporter handles the
   original armature_world transform. Do not apply it a second time.

FILES IN EACH BODY FOLDER
three-quarter.png           768 × 768, centered three-quarter reference
side.png                    768 × 768, image-left-facing profile
dual-front-side.png         1536 × 768, front left / side right
forward-action-wide.png     1536 × 768, actor right / travel room to image-left
Each PNG has a same-basename .txt and .video2rig-cameras.json.
camera-and-pose.json        source hash, exact bones, camera matrices and hashes
source.blend                original geometry/rig, frozen first authored idle,
                            neutral studio and four selectable camera scenes

CAMERA AND POSE CONTRACT
All references use the exact same authored starting pose for that body. No new
limbs, remodeled geometry, T pose, hand-cupping edits or AI-generated pixels.
Actions are detached and all NLA tracks muted in the saved .blend. Importer
bone-widget helpers are excluded from body bounds and rendered camera scenes.
Blender coordinates: +Z up, body forward -Y. Side and wide cameras are on +X,
so forward projects image-left. Cameras are orthographic, not pinhole.
Dual panels have identical pose and pixels per metre; their future generated
motion must depict the SAME event and timing. Each camera record retains its
pixel rectangle (side x0_px = 768). Never resize/crop/redivide it before recovery.
The wide frame allows more forward travel; the companion TXT gives a conservative
body-specific bound. The studio floor is 2 mm below the lowest original vertex;
the model itself was not moved to manufacture contact.

PROMPT CHOICES AND LIMITS
Bipeds: idle, squat ending crouched, crouch walk, small vertical jump and turn.
The wide menu adds walk–run–stop and a phased forward running jump. Quadrupeds:
watch idle, crouch/stalk, sit, turn, low hop; wide adds faster gait and pounce.
Each prompt has its own end state; every action need not return to idle.
The biped Vanilla 15 menu also names future tests. Chair interactions need a new
visible-chair reference. Standing from crouch/sit needs a matching low/seated
starting frame. Floor rolls need suitable floor poses and depth evidence.
These empty-studio idle images do not validate those missing interactions.
Stable first-frame pixels do not establish later geometry, camera consistency,
editable recovery, center of mass, balance or game-ready animation quality.

REPRODUCE (Blender 4.5.15 LTS; EEVEE, 32 samples, AgX)
The public repository tools/ folder contains the portable scripts below.
Supply an assets root containing the relative GLB paths listed at the end.
Examples (replace executable and absolute paths for your installation):

blender -b --threads 8 --python tools/build_h3_reference_pack.py -- --assets-root /path/to/assets --output /path/to/reference-packs/h3-2026-10-30
blender -b --threads 8 --python tools/validate_h3_reference_pack.py -- --pack-root /path/to/reference-packs/h3-2026-10-30
python tools/validate_h3_video2rig_cameras.py --pack-root /path/to/reference-packs/h3-2026-10-30 --video2rig-root /path/to/video2rig
python tools/package_h3_reference_pack.py --pack-root /path/to/reference-packs/h3-2026-10-30 --zip /path/to/reference-packs/h3-2026-10-30.zip

The Video2Rig validation additionally needs its normal Python environment
(NumPy, SciPy, OpenCV). It imports the official Camera implementation and checks
every saved joint against Blender's pixel projection, including armature_world.
The provided report records the parser's exact source commit and clip.py hash.
Rendering is deterministic in pose/camera setup; pixel byte identity across
different Blender builds, GPU drivers or platforms is not promised.
validation.json records saved-scene/pose, image, framing, panel and file checks.
manifest.json inventories every delivered file except itself (avoiding a hash
cycle). The ZIP lives alongside this folder, outside the Pages docs directory.

ORIGINAL DATA SOURCES / SHA-256
B-REK43 — b-rek43/b_rek43_d0_lod1.glb
  59a461ef42f5c9e3abe81af5bd6a6bfdf100fa040482fce6ce2b66110354a798
  authored idle: Recon_Idle, time 0
C07 Cheetah — c07-cheetah/c07_d0_lod1.glb
  13bd05e4a4a9101d31d45c4a392fe016ef59d0124945bf1ebaf2dbc913c7eae7
  authored idle: Watch_Idle, time 0
C08 Industrial Worker — c08-worker/c08_d0_lod1.glb
  44714a9ea5cea3ac797e670dc8aba57930e618f3a78809077a0b19597007a368
  authored idle: Standby_Idle, time 0
EVA-K7 — eva-k7/eva_k7_d0_lod1.glb
  17b210d3586a21f669f1de66926867a143d99b5106770064bedd211b79279ac2
  authored idle: Suit_Idle, time 0
K0-Tech — k0-tech-01/k0_tech_01_d0_lod1.glb
  9c1844d47c3953f4b456190459a1ca9bcc4778effed1166a787c2ac18d937754
  authored idle: Watch_Idle, time 0
