# Direct video recovery → C08 experiment

Six derived clips are ready: `ukemi`, `gorilla-side`, `gorilla-front`, `technical-standup`, `sumo-stomp`, and `deadlift`. Each folder contains `c08-mocap.glb` (clip `VC_<folder_with_underscores>`), editable `c08-mocap.blend`, `source-preview.json`, `retarget-report.json`, `validation-report.json`, and local review renders. Original videos/frames are excluded.

This pipeline is **GEM-X video recovery → native SOMA → direct C08 retarget**, with no MotionBricks generation and no G1 round trip. Full calibrated source joint rotations preserve torso/head motion and deliberate inversion. Reference identity/scale uses the recovered median; source and target rest limb directions are explicitly aligned. C08 segment lengths stay fixed. MOTION owns horizontal displacement; PELVIS owns complete orientation, including upside-down roll poses. ROOT, SENSOR, sockets and fingers have no animation channels.

Whole-avatar vertical placement grounds the lowest armor vertex 15mm above the floor at each 30Hz key. It does not solve support contacts, balance, armor collisions or hand/foot pinning. Corrections and near-ground horizontal drift proxies are measured in each report. Large proportion differences are visible: maximum corrections are 0.285m ukemi, 0.642m side gorilla, 0.797m front gorilla, 0.338m technical stand-up, 0.267m sumo, 0.142m deadlift. Treat these as exploratory adaptations.

All six GLBs passed glTF validation with zero errors/warnings, preserved rigid segment lengths and independent cloned skeletons, and matched baked Blender joint locations to micrometre accuracy. Dense 120Hz skinned-vertex sampling found no floor penetration (minimum clearance 3.8–14.7mm). Ukemi retains 15 frames with head below pelvis. These structural checks do not establish physical contact quality.

Representative renders reviewed locally: ukemi 70/80 (inversion and shoulder/back support), side gorilla 122 (deep knuckle posture), front gorilla 119 (approach), technical stand-up 106 (floor transition), sumo 54 (wide posture), deadlift 47 (lift phase). Motion silhouettes transfer, but armor can overlap and planted hands/feet can float or drift. Hands remain open at C08 rest shape. Front gorilla becomes an inferred full-body completion after roughly 5s because the performer approaches into face close-up. Technical stand-up hand placement is approximate; deadlift has no reconstructed bar or bar physics. Full timing is retained and provenance flags remain attached.

Rebuild with the local video-mocap Python environment:

```powershell
.\video-mocap\.venv\Scripts\python.exe tools\soma_prepare_c08.py ukemi gorilla-side gorilla-front technical-standup sumo-stomp deadlift
& tools\blender-4.5.15-windows-x64\blender.exe -b -t 2 --python tools\retarget_soma_c08.py -- ukemi
node tools\soma_validate_c08.mjs ukemi
.\video-mocap\.venv\Scripts\python.exe tools\soma_finalize_c08.py
```

Repeat the Blender command for each folder. `tools/soma_render_c08.py -- <folder>` runs under Blender to make local review frames. Raw SOMA matrices and `.blend` files are local working artifacts; publish only intended derived GLBs, previews and sanitized reports.
