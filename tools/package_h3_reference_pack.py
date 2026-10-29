"""Finalize the exact Blender reference pack's README, inventory and optional ZIP.

Run after both validation scripts. This uses only the Python standard library.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack-root', type=Path, required=True)
    parser.add_argument('--zip', type=Path)
    args = parser.parse_args()
    root = args.pack_root.resolve()
    metadata = [json.loads(p.read_text(encoding='utf8')) for p in sorted(root.glob('*/camera-and-pose.json'))]
    assert len(metadata) == 5
    readme = '''H3 EXACT BLENDER STARTING-FRAME PACK — 2026-10-30

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
'''
    for m in metadata:
        readme += f"{m['label']} — {m['source_asset_relative']}\n  {m['source_glb_sha256']}\n  authored idle: {m['authored_idle']}, time 0\n"
    (root / 'README.txt').write_text(readme, encoding='utf8')
    bodies = []
    for m in metadata:
        ident = m['body']
        bodies.append({'id': ident, 'label': m['label'], 'source_asset_relative': m['source_asset_relative'], 'source_glb_sha256': m['source_glb_sha256'], 'idle': m['authored_idle'], 'camera_pose_manifest': f'{ident}/camera-and-pose.json', 'blend': f'{ident}/source.blend', 'images': [f'{ident}/{name}.png' for name in ['three-quarter', 'side', 'dual-front-side', 'forward-action-wide']], 'video2rig_cameras': [f'{ident}/{name}' for name in m['video2rig_camera_files']]})
    files = {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
    assert len([n for n in files if n.endswith('.png')]) == 20
    assert len([n for n in files if n.endswith('.video2rig-cameras.json')]) == 20
    assert all(v['bytes'] < 100_000_000 for v in files.values())
    manifest = {'schema': 'h3-own-asset-reference-pack/1', 'pack_date': '2026-10-30', 'scope': 'Exact first authored idle poses; original geometry/rig retained. No AI images or recovered motion.', 'coordinate_system': 'Blender +Z up; character forward -Y; side camera +X gives image-left travel.', 'counts': {'bodies': 5, 'pngs': 20, 'prompt_companions': 20, 'video2rig_camera_jsons': 20, 'blend_scenes': 5}, 'bodies': bodies, 'files': files, 'hash_scope': 'Raw bytes of every delivered file except this manifest; ZIP is a sibling archive, not part of its own inventory.'}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding='utf8')
    if args.zip:
        destination = args.zip.resolve()
        assert root not in destination.parents, 'Put the ZIP beside the pack, not inside it.'
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(root.rglob('*')):
                if not path.is_file():
                    continue
                info = zipfile.ZipInfo(root.name + '/' + path.relative_to(root).as_posix(), (2026, 10, 30, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
        with zipfile.ZipFile(destination) as archive:
            assert archive.testzip() is None
        print(json.dumps({'status': 'passed', 'zip': str(destination), 'bytes': destination.stat().st_size, 'sha256': sha(destination), 'files': len(files) + 1}))
    else:
        print(json.dumps({'status': 'passed', 'files': len(files) + 1}))


if __name__ == '__main__':
    main()
