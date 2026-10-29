# Video2Rig recovery checks

These are our validation/export helpers, not trained readers or training pictures. Upstream [Can It Code / video2rig](https://github.com/canitcode/video2rig) is pinned to `55d51b3b9685125a8ea27841d6af9523f6352aa1`, with its separate AGPL-3.0-or-later and third-party/model terms. The checkout is **unmodified**; Blender4.x compatibility is already upstream. See [inspection](../../research/video2rig-upstream-inspection.json), [environment setup](ENVIRONMENT.md), and [dependency lock](requirements-lock.txt).

Use an isolated environment. NumPy/SciPy run math helpers; export/reimport helpers run inside Blender4.5.15. Do not commit model weights, tokens, checkpoints, training pictures or scratch blends. The Blender helpers use `MOTION_LAB_WORKSPACE` or find an ancestor with `assets/` and `experiments/video2rig/upstream/`; otherwise they fail clearly. No private filesystem path is embedded.

From the local workspace in PowerShell, dot-source the portable environment setup to keep caches on the experiment drive, then define:

```powershell
$env:MOTION_LAB_WORKSPACE = $PWD.Path
$v2rPython = Join-Path $PWD 'experiments/video2rig/.venv/Scripts/python.exe'
$v2rBlender = Join-Path $PWD 'tools/blender-4.5.15-windows-x64/blender.exe'
$qaTools = Join-Path $PWD 'public/c08-motion-lab/tools/video2rig'
```

The prepared K0 control has its original rig/static `model.blend`, exported `rig/`, `start/start.png`, exact `start/cameras.json` and `clips/native_pounce.mp4`. The native action lasts3.2seconds and holds through the four-second control:120frames at30Hz. Ground truth contains original basis matrices, joint heads/tails and timestamps. Training uses random poses, not the held-out native motion.

Recorded preflight/main training and recovery, from the upstream directory:

```powershell
Set-Location experiments/video2rig/upstream
& $v2rPython -m video2rig.reader.prepare ../k0-control --blend ../k0-control/model.blend --poses 128 --copies 8 --samples 8 --workers 6 --skip-train
& $v2rPython -m video2rig.reader.train ../k0-control --steps 50 --batch 8 --out reader/smoke.pt
& $v2rPython -m video2rig.reader.train ../k0-control --steps 500 --batch 8 --init ../k0-control/reader/smoke.pt --out reader/preflight.pt
& $v2rPython -m video2rig.reader.prepare ../k0-control --blend ../k0-control/model.blend --poses 3000 --copies 16 --samples 8 --workers 6 --skip-train
& $v2rPython -m video2rig.reader.train ../k0-control --steps 9000 --batch 24 --init ../k0-control/reader/preflight.pt --out reader/reader.pt
& $v2rPython -m video2rig run ../k0-control native_pounce
& $v2rPython -m video2rig run ../k0-h3-approx pounce
& $v2rPython -m video2rig.reader.fit ../k0-h3-approx pounce --tag=-no-contacts --set steps=false --set foot_lock=false
& $v2rPython -m video2rig.reader.fit ../k0-h3-approx pounce --tag=-soft --set lowpass_slow_hz=3
```

The main9,000steps continue from50smoke+500preflight:9,550optimizersteps total. Training held-out pixel scores differ from recovery accuracy. Before known-control recovery, write its exact30Hz ground-truth times to `work/native_pounce/timing.json`; do not substitute the AI-video cadence heuristic. H3 uses measured24Hz. Set `root_bone: LUMBAR` and Blender-facing `-Y`: a default pelvis root would miss the cat's front half.

The first H3 result transfers a wide-camera reader to a close estimated camera; retain it as a negative baseline. Camera-specific preparation uses its own static model/camera and fresh reader, without overwriting the baseline checkpoint or training on H3 video frames:

```powershell
& $v2rPython -m video2rig.reader.prepare ../k0-h3-camera-trained --blend ../k0-h3-camera-trained/model.blend --poses 1000 --copies 16 --samples 8 --workers 6 --skip-train
& $v2rPython -m video2rig.reader.train ../k0-h3-camera-trained --steps 2000 --batch 24 --init ../k0-control/reader/reader.pt --out reader/reader.pt
& $v2rPython -m video2rig run ../k0-h3-camera-trained pounce
```

For `k0-h3-camera-locked`, copy that project's rig/model/start, masks and measured timing. Hold `work/pounce/cameras-aligned.json` at scale1/offset0/turn0 and fit the **same** camera-trained readings:

```powershell
& $v2rPython -m video2rig.reader.fit ../k0-h3-camera-locked pounce --reading ../k0-h3-camera-trained/work/pounce/reader.npz --tag=-locked-estimate
Set-Location ../../..
```

That camera remains manually estimated, not the original generator camera. The exact-camera known control has a separate locked-camera fit too. Preserve all baseline files and source/checkpoint hashes.

Independent scoring/export from the workspace root:

```powershell
$v2rProject = Join-Path $PWD 'experiments/video2rig/k0-control'
$v2rMotion = Join-Path $v2rProject 'out/native_pounce.npz'
$v2rMetrics = Join-Path $v2rProject 'recovery-metrics.json'
& $v2rPython "$qaTools/video2rig_score_recovery.py" --project $v2rProject --motion $v2rMotion --out $v2rMetrics
& $v2rBlender -b "$v2rProject/model.blend" --python-exit-code 1 --python "$qaTools/video2rig_export_recovered.py" -- --project $v2rProject --motion $v2rMotion --tag known-recovered --metrics $v2rMetrics
& $v2rBlender -b --python-exit-code 1 --python "$qaTools/video2rig_validate_native_glb.py" -- --project $v2rProject --glb recovered/known-recovered.glb --reference recovery-metrics.npz --out recovered/known-recovered-glb-validation.json
& $v2rPython "$qaTools/video2rig_check_skin_parity.py" --expected "$v2rProject/recovery-metrics.npz" --actual "$v2rProject/recovered/known-recovered-glb-validation.npz" --out "$v2rProject/recovered/known-recovered-skin-parity.json"
```

The scorer adds no fitted spatial/time alignment. It reports upstream frame-zero camera adjustments separately, exact-time joint position/local rotation geodesics, root travel/height, complete-skin floor clearance and adjacent-frame quaternion geodesics. Euler wrapping cannot masquerade as a full rotation spike. Use explicit `--gt` for another known-motion project with the same original ground truth; sharing a rig does not give H3 ground truth.

Export checks compare every joint at every source timestamp and complete evaluated skin at nine poses, allowing vertex/material reordering. Run glTF Validator separately. Finite data and correct serialization alone do not establish animation quality or physical balance.

`MOTION` is an invisible transport ancestor; fitted `LUMBAR` absorbs its translation. Both all51 and visible50 chain metrics are reported. Native shoulder slides exceed a rotation-only rig with one translating root: maximum native-to-representable joint difference is about10.7mm forK0 and23.4mm forC07. Native GT and projected oracle are separate from reader predictions.

H3 has no joint ground truth or original camera calibration. Use finite/range/reprojection diagnostics and visual review, without invented accuracy claims. Published C07 is not verified as the exact H3 input; substantial frame-zero geometry/appearance differences make it an out-of-domain stress test. Its separate reader budget is1,000poses and2,000additionalsteps, rather than another full9,000-step run. No geometry was shortened or replaced to manufacture a match.
