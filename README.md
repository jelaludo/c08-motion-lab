# C08 Motion Lab

An independent, non-commercial motion notebook by **jelaludo**. One original robot, a small robot cat, and several distinct approaches to animation.

**[Lab home](https://jelaludo.github.io/c08-motion-lab/)** | **[MB-Predictive](https://jelaludo.github.io/c08-motion-lab/mb-predictive/)** | **[Quaternius](https://jelaludo.github.io/c08-motion-lab/quaternius/)** | **[Research gallery](https://jelaludo.github.io/c08-motion-lab/lab/)** | **[Off Shift diorama](https://jelaludo.github.io/c08-motion-lab/diorama.html)**

The landing page separates learned prediction, conventional animation, video recovery, choreography, and the earlier research archive. MB-Predictive shows 24 actual AI experiments beside ordinary interpolation, with explicit recent-pose/target/generated-movement stages. The Quaternius tab adds a prominent WASD controller and shuffled routines that return through idle. Existing research clips remain available for future comparisons.

The diorama includes greetings, crouching, a feline roll-over, chases in both directions, reciprocal jumps, footwork, turns, reaches and a quiet finish. Its 16 scenes form a continuous loop. The expanded inspector offers **47 choices**: 36 original-input MotionBricks experiments, six video-derived C08 retargets and all five original authored C08 actions.

The **Continuous** button starts shuffled playback, visiting every available motion before repeating and blending briefly between poses. Selecting or scrubbing a clip stops the playlist. Clips are centred during Continuous; it is an animation playlist, not a newly generated continuous routine.

## What generates what

- **C08 geometry and original workshop animation:** original assets by jelaludo, from [SentryTowers A6](https://jelaludo.github.io/SentryTowers_A6/c08-worker/).
- **C08 generated motion:** NVIDIA MotionBricks G1 FP32, driven by original numeric poses and target placements authored for this experiment. The G1 motion is adapted to C08's existing proportions, rigid armor and skeleton.
- **C08 video-derived motion:** six user-provided exercise references recovered with GEM-X native SOMA, then directly adapted to C08. Ukemi, sideways/front gorilla exercise, BJJ technical stand-up, sumo stomp and deadlift are labelled separately. This path does not use MotionBricks generation.
- **K0-Tech geometry and its eight clips:** original authored workshop assets by jelaludo, from [K0-TECH-01 / Felis](https://jelaludo.github.io/SentryTowers_A6/k0-tech-01/). MotionBricks does not animate the cat.
- **The scene:** authored direction, paths, playback-rate matching, loop cleanup, action blends, ground-clearance correction and staged interactions. K0's leap over crouched C08 adds an authored vertical trajectory to the existing pounce. It is not a claim about the motion model or physical robot capability.

The assets are shown at their authored metre scale: C08 is approximately 2.3 m tall; K0-Tech is approximately 0.414 m tall.

## What is included

- `docs/`: buildless static site, vendored Three.js r160 runtime and interactive motion inspector.
- `docs/motions/`: 36 generated test GLBs with original inputs and editable bakes, plus six video-derived GLBs, source skeleton previews, provenance, hashes and per-clip validation reports. The video retarget authoring files and raw human capture archives remain local.
- `conditioning/`: original six-pose library, G1 proxy with 29 hinge sliders and an exporter. See its README for authoring instructions.
- `tools/`: research/export script snapshots. They expect the separately provisioned MotionBricks workspace layout; they are not a one-command installer.
- `research/`: diorama measurements, screenshots, motion findings and the separate local video-to-mocap investigation.
- `LICENSES/`: third-party notices for the runtime and G1 reference rig data.

No model weights, caches, Python environments, raw reference videos, NVIDIA/Bones sample motion or sample-conditioned generated clips are distributed here. The earlier local evaluation contained 24 sample-driven tests; these remain local. Eighteen new original-input experiments cover the missing motion categories without copying those sample inputs or generated outputs. Intended derived C08 clips and source-skeleton previews from the exercise references are public; source videos and full human recovery archives are not.

## Validation and honest limits

All 42 experimental GLBs pass Khronos validation without errors or warnings. Their source-to-export correspondence, finite skin data, rigid segment lengths, game-owned pivot exclusions and independent skeleton clones were checked with Three.js r160. Review findings remain visible in the inspector and JSON reports. Technical validity does not establish motion quality or contact fidelity.

Video floor work is particularly exploratory: C08's broad armor and different proportions require whole-body grounding shifts, measured up to about 0.80 m for the most difficult front-gorilla frames. Source-body cropping, speculative occluded joints, hand/foot drift and armor overlap remain. Deadlift includes body motion only, with no reconstructed bar/load/grip physics. See [video retarget notes](research/video-retargets.md).

The diorama applies a separate runtime ground-clearance guard to rigid segment extrema and blends clips. It is therefore a processed presentation, not a claim that every raw clip is contact-perfect. Chapter placements, loop continuity, desktop/mobile controls, full skinned floor bounds and the reciprocal jump clearances are measured in [`research/diorama-validation.json`](research/diorama-validation.json). Jump clearance checks sample the jumping mesh above the other actor's horizontal bounds with a 60 mm margin; they are not a full physics or mesh-intersection proof.

Still open: full armor self-collision, generalized object interaction, arbitrary terrain, physically balanced motion, reference-phone performance and consuming-game acceptance. Please report the scene/time and device when giving feedback.

## Run locally

This site has no build step. From the repository root:

```sh
python -m http.server 8080 --directory docs
```

Open `http://localhost:8080`. The runtime modules are vendored so the character assets and renderer do not need a CDN. Optional typography uses Google Fonts, with local system-font fallbacks. Opening the HTML directly as a file will not work because the viewer fetches GLB/JSON assets.

For generation, install the pinned upstream MotionBricks checkout separately: `NVlabs/motionbricks` at `54fc563aeaaf819a753d72cc9fdc6713989cdd43`. Use its lockfile, Python 3.12 and an NVIDIA CUDA GPU. Each test's `g1-motion.json` records the exact context/target arrays and generation settings. The reference pipeline ran on a Windows VM with an RTX 4090. Regeneration may vary; retain accepted outputs and their hashes.

## Feedback and attribution

This is shared for observation and discussion. Original character assets and original project work are by jelaludo. Publication does not relicense upstream models, data or third-party assets. The original C08 and K0-Tech source pages retain their provenance records. Third-party components keep their respective notices; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Keyboard playground

[Open control mode](https://jelaludo.github.io/c08-motion-lab/lab/?control=1). WASD moves, Shift runs, Space jumps, Shift + movement + Space uses the running-jump clip. U plays Ukemi and T plays sumo stomp. Keys 1?9 and 0 select ten actions; the sidebar lists them. Esc exits control. Standing jump uses an authored crouch/flight variation; running jump uses the original-input generated jump with staged travel/lift. This is a kinematic playback controller without collision physics. Flag markers indicate review findings, detailed alongside each clip.

## Quaternius baseline tab

[Open the separate baseline](https://jelaludo.github.io/c08-motion-lab/quaternius/). Twenty CC0 clips from the official free Quaternius Universal Animation Library 1 Standard pack are directly retargeted to C08. Includes source-mannequin comparison, clip inspection, a phase-aligned locomotion blend demo and a basic keyboard state machine. Existing experiments remain as research; the diorama now lives at `diorama.html` and the root is the lab hub. See [findings and provenance](research/quaternius-baseline.md). All 20 exports pass structural and 120 Hz floor checks; these checks do not establish contact fidelity or production readiness.

## MB-Predictive

Six new original-input experiments vary distance, heading and arrival posture. The chain experiment feeds each prediction's actual last four poses into the next call. A matched non-neural baseline interpolates source joints and root transforms over the same duration. Both outputs use the existing C08 adapter; only the neural result supplies predicted contact labels. This comparison illustrates the learned stepping; it is not a benchmark against an authored controller.

The public site plays recorded outputs. A loopback-only local service also supports fresh target generation on the RTX 4090. In the provisioned MotionBricks workspace, run `./Start-MB-Predictive.ps1` and open `http://127.0.0.1:8791/mb-predictive/`. Set forward/sideways placement, heading and arrival posture, then generate. The service serializes jobs, reuses the model, retargets both outputs in Blender, and validates the exported clips. New job files stay outside the public repository. GPU timing displayed in the UI excludes initialization, retargeting and export.

See [MB-Predictive research notes](research/mb-predictive.md) for input provenance, chaining checks and limits.

## Harvested midpoint and endpoint targets

MB-Predictive now contains 21 public experiments: the six authored-target examples plus 15 sampled-pose predictions (five Quaternius Standard clips, six own video captures and four of our original-input MotionBricks outputs). Each harvested case seeds four recent source poses, then generates toward its midpoint and endpoint poses in two chained requests. The source names, timestamps, fitting notes and traces stay visible. Source timing is not imposed on the prediction.

The local tab adds two bundled NVIDIA sample cases for internal evaluation only. They are excluded from the public catalog, files and screenshots. Public results rely on CC0, the user's own references or originally conditioned generated motion; we do not rely on a fair-use assumption to publish restricted sample derivatives.

In the local UI, select a harvested source, vary target spacing/rotation and choose **Generate from sampled targets**. This reuses the source context and hinge postures while placing targets differently, then runs a fresh prediction and validated C08 export. See [pose-harvest findings](research/pose-harvest.md) and [measured results](research/pose-harvest-results.json).

## Meshy test body and exploration controls

MB-Predictive offers **C08**, **Meshy fighter**, and **both bodies side by side**. The fighter is [BJJ Jiu-Jitsu Woman Girl Fighter Free](https://sketchfab.com/3d-models/bjj-jiu-jitsu-woman-girl-fighter-free-8077cada67a14af18249b6af687fcc3c) by [Tulio Portela](https://sketchfab.com/TulioPortela), Sketchfab, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The creator describes it as Meshy-generated. Our experimental modifications add a humanoid rig, skinning, scale normalization, web mesh reduction and tangents. Original texture content is retained. Attribution is visible in the player and embedded in the GLB. Our project excludes this body from production; the creator's CC BY 4.0 license remains in force.

**Combine 5 / 10 / 15** selects a recorded neural sequence on the public page. Locally, those buttons generate a fresh random source arrangement on the GPU. Each source move supplies midpoint/end targets; the next request uses the last four actually generated poses. Each sequence ends with neutral recovery. **Random until stopped** shuffles recorded short predictions with centred pose blends; it is playback, not ongoing inference. **< / >**, left/right arrows and **Space** browse or pause/play. The stage transport stays visible as the sidebar scrolls.

There are now 24 public presets (21 earlier tests plus three combined neural sequences), with two additional restricted sample evaluations locally. Both bodies consume the same G1 output; the human is retargeted at runtime on its own proportions. Body-specific contact correction, cloth physics, finger articulation and production-quality deformation remain open work. See [Meshy rig findings](research/meshy-body.md).
