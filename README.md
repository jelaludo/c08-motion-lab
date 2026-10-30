# C08 Motion Lab

An independent, non-commercial motion notebook by **jelaludo**. Original robots, a small robot cat, and several distinct approaches to animation.

**[H3 / Video2Rig tests](https://jelaludo.github.io/c08-motion-lab/h3-motion/)** add 13 completed recovery/control comparisons from three generated robot references. They include actual original-rig exports, known-motion ground truth, camera/reader ablations and preserved negative results. Job completion is separate from visual acceptance; tail spikes, floor contact and approximate-body mismatches remain explicit. The [Dev Log](https://jelaludo.github.io/c08-motion-lab/dev-log/#h3-video2rig) records the findings.

The [H3 starting-frame pack](reference-packs/h3-2026-10-30) contains 20 exact Blender PNGs, 20 companion animation-prompt TXT files, matching Video2Rig camera files and five frozen Blender scenes. [Download the complete ZIP](https://raw.githubusercontent.com/jelaludo/c08-motion-lab/main/reference-packs/h3-2026-10-30.zip). It covers C08, B-REK43, EVA-K7, K0-Tech and C07; no generated motion is certified by the reference images.

**[Vanilla 15 / Review](https://jelaludo.github.io/c08-motion-lab/vanilla/)** | **[Reactive Arena](https://jelaludo.github.io/c08-motion-lab/reactive/)** | **[Lab home](https://jelaludo.github.io/c08-motion-lab/)** | **[MB-Predictive](https://jelaludo.github.io/c08-motion-lab/mb-predictive/)** | **[Quaternius](https://jelaludo.github.io/c08-motion-lab/quaternius/)** | **[Research gallery](https://jelaludo.github.io/c08-motion-lab/lab/)** | **[Off Shift diorama](https://jelaludo.github.io/c08-motion-lab/diorama.html)**

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

## Vanilla 15 and reviewer feedback

`docs/vanilla/` adds fifteen practical core candidates for C08: idle, walk, run, small/high/running jumps, crouch, crouch walk, lie down, get up, forward/backward rolls, sit down, seated idle, and stand from a seat. This is a curated starting set, not a statistical usage ranking. All motion inputs are Quaternius UAL 1 Standard CC0; playback recipes and source hashes are in `manifest.json`.

The backward roll reverses a forward roll; get-up reverses a fall; lie-down uses a fall-style source. These are explicitly marked prototypes. Modified jumps use authored timing/root travel. No new MotionBricks inference or physically solved contact is claimed. Loops repeat; one-shots stop in their destination pose. Sitting and lying do not automatically return to standing. Whole-avatar grounding prevents floor penetration but does not repair support or armor overlap.

Reviewers score overall quality, smoothness, contact and readability from 1 to 5, choose Keep/Rework/Reject, and add timestamped notes. Feedback belongs to the reviewer, C08 body, candidate and manifest version. It saves in browser localStorage; JSON import/export shares or backs up reviews, CSV exports a spreadsheet. Scores and comments count as reviewed even without a decision. Older feedback remains visible after animation updates; editing creates a current-version record while retaining the old one. Reviewer-name edits use a stable browser profile ID. One Export all reviews includes every saved comment, score, body, collection and version, and import retains conflicting feedback. There is no shared online review database. Reject filters a candidate out of the Keep shortlist without deleting source assets.

Rebuild the extra Death01 retarget in the provisioned workspace with `tools/retarget_vanilla_base.py` through Blender, then `tools/finalize_vanilla_base.py`, copy the resulting GLB to `docs/vanilla/c08-extra.glb`, and run `tools/refresh_vanilla_manifest.py`. Runtime composition recipes are deterministic in `vanilla.js`. `tools/review/check-vanilla.mjs` exercises playback, deformed geometry, persistence, review queues and import/export.

The Vanilla/Quaternius baseline now includes an authored relaxed hand cup: finger hinges curl toward the palmar side, opposite the ivory dorsal plate, and thumbs oppose toward the palm centre. This is an authored hand pose, not generated finger motion or object-specific grip IK.

The [next reactive-motion round](research/next-round-reactive-motion.json) records sourced findings, proposed obstacle/speed/pursuit trials, native/displayed motion recording and game-export plans, plus the current community tools worth evaluating. Reactive Arena now adds faster running zones, low-hurdle jumps and a crouch-under-bar experiment to the navigation tests.

## Reactive Arena and continuous courses (2026-10-29)

Round 4 contains **123 recorded takes and three selectable bodies: C08, B-REK43 and EVA-K7**. Six paired scenarios cover ten seeds each; three new **80-second continuous courses** combine slalom, progressive speed zones, crouching, hurdle jumps and pursuit of K0-Tech. The default opens [continuous course 1](https://jelaludo.github.io/c08-motion-lab/reactive/?take=course_reactive_1). Its native arena spans 60 by 16 metres. Course recordings are single continuous generated/prepared timelines; the separate section playlist reloads independent takes at its marked boundaries.

**Orange means run; red means faster.** All 20 revised speed-zone takes and all three courses measure a higher actual mean speed in red. The live readout distinguishes commanded speed from recorded native G1 speed. Avatar travel and environment dimensions scale with each body's leg lengths.

The **Continuous section playlist** supports selecting and reordering scenarios, start, pause/resume, skip, stop and repeating until stopped. Camera following, single-body focus, whole-arena overview, timeline inspection and slow playback remain available. A scene boundary resets playback and does not transfer neural context between independent takes. Within each 80-second course, the actual last four played native poses feed the next neural request.

The new crouch walks with alternating planted support and swinging feet. A permitted Quaternius CC0 crouch source supplies body style; explicit shortened foot paths, bounded leg IK and per-character contact adaptation repair the sliding source gait. In the tested C08 trusted-stance intervals, median sole speed falls from about 0.178 m/s to 0.0000068 m/s, with 95th-percentile 0.0000233 m/s. B-REK/EVA stance tests also pass at numerical precision, including translated/rotated scene parents and arbitrary scrubbing. These measurements apply to the marked prepared-source stance phases; they do not claim that every neural step has perfect contact.

Jumps show **run, recoil, extension, flight, landing and recovery**. Original-conditioned jump motion is phase-retimed with about 4.21 m horizontal travel; its original vertical root arc is retained. Feasible takeoff/landing poses receive bounded contact preparation, while excessive corrections release instead of snapping or stretching the legs. See the [six-phase visual study](research/reactive-round4-jump-phases.png). Neural entry/exit connects these prepared source actions to the course.

The catalog records **8,340 genuine neural requests and 4,879 explicitly classified prepared-source playback frames**. There are 100 neural-only takes and 23 hybrid takes. Sparse pose targets, source licensing, source hashes, segment mode and actual played contexts remain inspectable. MotionBricks receives poses rather than scene geometry; an external planner and swept collision controller handle navigation. Footplant and grounding corrections are additional animation processing. The prepared actions are not described as entirely neural generation.

[EVA-K7](https://jelaludo.github.io/SentryTowers_A6/eva-k7/) is an original 1.96 m hardsuit by jelaludo. Its existing 50 animated controls, 12 fixed socket joints, authored gloves and six native clips are preserved; the original asset is unchanged. It uses its own anatomical scale and an overhead underside calibrated from the actual crouched mesh. All three bodies share native motion while adapting to their own limb lengths. K0 retains its original distance-driven authored gallop and seeded navigation; this experiment does not generate quadruped animation with MotionBricks.

**Export displayed body GLB** bakes the selected character, its actual corrected pose and root movement; mark a range for shorter game clips. Keep/reviews retain body and version identity. Earlier-version kept downloads pin their original release; their current previews are clearly separate. Export all reviews includes every saved comment and score. Native played/selected-source NPZ, CSV and generation traces remain downloadable. Exact native archives live outside Pages under research; browser previews use six-decimal display precision. Full unused neural futures stay local.

All **369 take/body combinations** pass independent sampled geometry checks: 528,123 C08 poses at 120 Hz and 132,123 each for B-REK43/EVA at 30 Hz, with zero triangle/obstacle intersections and final artifact hashes verified. Native continuous sweeps, paired environments, orange/red speeds, four-pose context chains, stance contacts, deterministic scrubbing and displayed-body exports also pass. See [round 4 results](research/reactive-round4-summary.json), [full geometry validation](research/reactive-round4-fullskin-validation.json) and [source preparation](research/reactive-round4-sources/README.md).

Animation quality still needs visual review. Kinematic navigation/contact IK does not provide self-collision, physical balance, arbitrary-terrain support or actor/cat mutual contact. Historical reports describe their named release; earlier accepted downloads pin that release for reproducibility. The Vanilla 15 library and its 30 game bakes remain available unchanged.


## Biped capture round 2

Six creator-provided references are recovered with GEM-X and adapted directly from SOMA77 to C08, B-REK43, EVA-K7 and the attributed experimental Meshy fighter: 24 supplied GLB comparisons in [Biped capture](https://jelaludo.github.io/c08-motion-lab/biped-motion/). Four verified recoveries were reused; two new clips were inferred. This is recovery and retargeting, with no MotionBricks inference or G1 intermediate. Raw skeletons, per-body reports and separate body reviews make the remaining contact/weight errors inspectable. Original source videos stay private. The creator's 13 previous-round verdicts are retained separately from browser scores.


## Own capture to MotionBricks pilot

[Mocap rebuild](https://jelaludo.github.io/c08-motion-lab/mocap-rebuild/) compares six performances across raw recovery, matched filtered recovery, and genuine MotionBricks SOMA generation using single-pose versus four-pose targets. The 24 C08 comparisons include 12 generated default/action/default loops from 96 model calls. Neutral holds are authored; the entry, phase transitions and return are neural. Exact conditioning/response identity, exported loops and remaining floor/jitter errors are documented separately. Source recordings and weights remain private. See [reproduction](tools/MOCAP_REBUILD.md) and [release measurements](research/mocap-rebuild-release-validation.json).


## Viewer-first layouts

The eight test viewers prioritize animation and playback in the first screen. Comparisons have Focus/Enlarge controls; explanations, diagnostics, downloads and reviews open in accessible panels. Existing motion files and review identities are retained. Desktop and portrait/landscape phone checks are recorded in [viewport validation](research/viewer-layout-validation.json).
