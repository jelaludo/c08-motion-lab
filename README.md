# Off Shift — C08 & K0-Tech

A non-commercial motion experiment by **jelaludo**: a heavy utility robot and his compact robot cat share a little free time. Built to invite animation and technical feedback, not to claim a finished game controller or a physics simulation.

**[Watch the moving diorama](https://jelaludo.github.io/c08-motion-lab/)** · **[Inspect the generated motions](https://jelaludo.github.io/c08-motion-lab/lab/)** · **[Leave feedback](https://github.com/jelaludo/c08-motion-lab/issues)**

The diorama includes greetings, crouching, a feline roll-over, chases in both directions, reciprocal jumps, footwork, turns, reaches and a quiet finish. Its 16 scenes form a continuous loop. The motion inspector includes all 18 original-input robot experiments, including the deliberately aggressive short-duration movement that is not used in the curated story.

## What generates what

- **C08 geometry and original workshop animation:** original assets by jelaludo, from [SentryTowers A6](https://jelaludo.github.io/SentryTowers_A6/c08-worker/).
- **C08 generated motion:** NVIDIA MotionBricks G1 FP32, driven by original numeric poses and target placements authored for this experiment. The G1 motion is adapted to C08's existing proportions, rigid armor and skeleton.
- **K0-Tech geometry and its eight clips:** original authored workshop assets by jelaludo, from [K0-TECH-01 / Felis](https://jelaludo.github.io/SentryTowers_A6/k0-tech-01/). MotionBricks does not animate the cat.
- **The scene:** authored direction, paths, playback-rate matching, loop cleanup, action blends, ground-clearance correction and staged interactions. K0's leap over crouched C08 adds an authored vertical trajectory to the existing pounce. It is not a claim about the motion model or physical robot capability.

The assets are shown at their authored metre scale: C08 is approximately 2.3 m tall; K0-Tech is approximately 0.414 m tall.

## What is included

- `docs/`: buildless static site, vendored Three.js r160 runtime and interactive motion inspector.
- `docs/motions/`: 18 self-contained test GLBs, editable Blender bakes, generated G1 arrays, conditioning inputs, source skeleton previews, provenance, hashes and per-clip validation reports.
- `conditioning/`: original six-pose library, G1 proxy with 29 hinge sliders and an exporter. See its README for authoring instructions.
- `tools/`: research/export script snapshots. They expect the separately provisioned MotionBricks workspace layout; they are not a one-command installer.
- `research/`: diorama measurements, screenshots, motion findings and the separate local video-to-mocap investigation.
- `LICENSES/`: third-party notices for the runtime and G1 reference rig data.

No MotionBricks weights, model caches, Python environments, NVIDIA/Bones sample motion or sample-conditioned generated clips are distributed here. The earlier private evaluation contained additional sample-driven tests; these are intentionally absent. The private ukemi reference video and its recovered data are also absent.

## Validation and honest limits

All 18 original-input GLBs pass Khronos validation without errors or warnings. Their source-to-export correspondence, finite skin data, rigid segment lengths, game-owned pivot exclusions and independent skeleton clones were checked with Three.js r160. Six raw motion experiments retain automatic review flags; they are visible in the inspector and their JSON reports.

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
