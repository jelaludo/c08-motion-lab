# MB-Predictive — actual learned in-betweening

This tab focuses on MotionBricks' core capability: four recent skeletal poses and one to four target poses condition a new motion prediction. Our six experiments use one target per generation, with original numerical G1 inputs. They do not load restricted sample motions or Quaternius animations.

## Experiments

1. A short neutral arrival.
2. The same starting stance and a farther destination.
3. A new destination and 45-degree arrival heading.
4. An arrival in a crouched posture.
5. An arrival with a reaching posture.
6. Three chained predictions: the actual last four generated poses become the next context.

The UI exposes recent poses, target poses, generated animation, source-skeleton conditioning ghosts, root paths, inference measurements and full prediction traces. G1 conditioning skeletons are scaled for display alongside C08. C08 is an adapted output, not the native model rig.

The paired non-neural control interpolates root position, hinge angles and root quaternion between the same source endpoints, using the same per-segment duration chosen by the neural model. It does not synthesize steps. This is a demonstration of the difference between interpolation and learned motion, not a quality benchmark against Quaternius or a production animation controller. Both results use the existing C08 adapter; the neural output additionally supplies predicted contact labels. Adapter contact locking therefore differs between branches.

## Generation and evidence

MotionBricks-G1-RP-v1 FP32 runs locally on an RTX 4090. Per-generation inference is measured around the synchronized engine call; displayed numbers exclude model initialization, Blender retargeting, export and validation. Durations are chosen within the runtime's default allowed token counts (8–14). Endpoint correction is enabled. Files record the upstream commit, all inputs, frame boundaries, inference seconds and last-four context values.

All six neural outputs and six interpolation outputs pass zero-error/zero-warning glTF validation, finite skin checks, rigid segment lengths, source-to-export joint comparisons and independent clone checks. Skinned floor bounds are sampled at 120 Hz. Exact chain links are checked by comparing each segment's recorded context with the preceding segment's final four generated poses. Technical validity does not guarantee motion quality, physical balance, contact accuracy or collision avoidance; model joint-limit findings remain visible.

## Fresh generation on this PC

`Start-MB-Predictive.ps1` starts a loopback-only server at `http://127.0.0.1:8791/mb-predictive/`. The local-only controls accept bounded numeric target placement, heading and an original arrival posture. The service performs a fresh model call, creates the interpolation control, retargets to C08 and validates the export before the UI loads it.

Jobs are serialized on one worker and reuse the initialized model. New files stay under `evaluation/mb-predictive/local-jobs`, outside the public checkout. Only intended derived static presets are published. The server has no remote listener or CORS access. Its input accepts no filenames, shell commands, uploads or arbitrary source paths.

The public GitHub Pages site plays recorded predictions; it does not run TensorRT or access this PC's GPU. The local server is an experimental integration in the already provisioned workspace, not a standalone installer or public inference service.

Official method and API: https://github.com/NVlabs/MotionBricks#how-motionbricks-works and https://github.com/NVlabs/MotionBricks/blob/main/docs/runtime_api.md.
