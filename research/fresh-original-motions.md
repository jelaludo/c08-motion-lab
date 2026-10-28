# Fresh original conditioning experiments

18 new motion tests generated from numerical poses and trajectories authored for this workspace. No NVIDIA/Bones sample CSV/BVH, sample-conditioned generated clip, or recovered reference video was read by the generator. The base poses came from our own six-pose library; exact new context/target arrays and authoring notes are retained in `authored-inputs.json` and each test's `g1-motion.json`.

All 18 generated, adapted and passed the existing structural/export checks. Eleven retain automatic motion/contact flags; a technical pass does not mean a physically feasible, contact-clean or semantically successful motion. No generated joint values were clamped. Inputs were deliberately authored within the recorded G1 joint limits.

Categories: slow/brisk walk, jog, start/stop, crouched forward/backward/left/right, duck-under, seated lowering/hold/rise, guarded side steps, asymmetric limp, arms-forward walk, skipping experiment and playful torso/arm sequence. Names describe requested target styles; the model's actual motion needs review. There is no independent G1 head/finger control or enforced object contact. The seated tests have no chair, and the ducking test has no supplied obstacle geometry.

The first ducking request translated farther than the C08 adapter could support during its predicted planted-foot interval. A compact-travel rerun succeeds; the original failed source and diagnostic remain under `fresh_duck_under/attempt-1/`. The rerun still needs a large pelvis correction and retains a G1 limit flag, so it remains an experimental test.

Each `fresh_*/` directory contains the generated G1 arrays, metadata, source skeleton preview, C08 GLB/Blender bake, adapter and Three.js/Khronos reports, hashes and a rendered midpoint `preview.png`. Rendered poses were inspected for seated hold, crouched left motion, guarded steps, limp, arms-forward walk and the torso/arm sequence. This inspection is not a complete contact or temporal review.

Reproduction scripts: `tools/original_generate_round3.py`, `tools/original_retarget_round3.py`, `tools/original_review_round3.py`, `tools/original_render_round3.py`. Run generation/review in the existing pinned MotionBricks environment and retarget/render in Blender. Process environment variable `MB_ONLY_TESTS` limits adaptation/review/render to comma-separated IDs; generation accepts `--only` IDs. Output catalog is separate from the previous round.
