# Pose harvesting for MB-Predictive

The experiment extracts source motion poses and uses them as conditioning for new MotionBricks predictions. It is inference, not retraining, and does not copy or retime a complete source clip into the output.

## Published source groups

- Five Quaternius Universal Animation Library 1 Standard clips: Walk Loop, Dance Loop, Interact, Jump Start and Crouch Forward Loop. Source license: CC0.
- Six user-provided capture recoveries: deadlift, sumo stomp, technical stand-up, Ukemi, side gorilla and front gorilla. Raw videos and full recovery archives remain local.
- Four prior MotionBricks outputs driven only by our original numerical conditioning: run, jump, dance and deep crouch. This tests a second generation from model-generated source poses, without bundled sample conditioning.

Fifteen new public predictions bring the tab to 21 experiments. Each has a corresponding non-neural interpolation control. Two additional bundled NVIDIA sample cases are available only in the local evaluation view and are excluded from the public repository.

## What gets sampled

Each source contributes four initial poses spaced at 30 Hz, its midpoint pose, and its final pose. The first four become the recent context. The midpoint and endpoint become two separate one-pose target requests. The second request receives the first prediction's actual last four generated poses as context.

A target window of up to four poses is supported by MotionBricks, but this experiment deliberately uses one target per request. Source timestamps identify the sampled poses; they do not constrain generated duration. Pose names describe their source, not a claim that the model faithfully reconstructs that exercise.

Quaternius poses are sampled from the original humanoid GLB in Blender, not from an already adapted C08 bake. Capture poses come from native recovered SOMA transforms. Native G1 outputs and the local evaluation CSVs are sampled in their own rig coordinates.

The independent G1 XML forward-kinematics implementation matched Newton to about 1.2 micrometres in the reference check. Human poses are fitted to bounded G1 hinge coordinates using normalized limb directions and soft torso/foot orientation objectives. Root orientation includes inversion. The maximum limb-direction fitting errors across the selected human-source frames range from roughly 0.2 to 5.1 degrees. These are direction-fit measurements, not full-body/contact fidelity scores. G1 proportions, fingers, joint limits and missing image evidence limit what transfers.

Source hashes, timestamps, fitted input poses, fitting errors, generated segment boundaries and exact context chains are retained in the reports. Automated checks verify that the converted source poses are exactly the poses supplied to the generator.

## Local variations

The local MB-Predictive UI can reuse any harvested source's context and target postures. Target spacing and heading are adjustable; source hinge angles remain unchanged. A fresh model call generates the intervening movement, followed by retargeting, export and validation. Source provenance and placement adjustments remain attached. New jobs stay local.

The source-harvest base contains 21 public experiments and two restricted sample evaluations locally. Three later combined neural routines bring the current totals to 24 public and 26 local presets. The same controls work with the permitted sources without depending on the restricted branch.

## C08 adaptation findings

All 17 new neural outputs and 17 interpolation controls passed structural checks, including glTF validation, independent skeleton clones, fixed limb lengths and source-to-export correspondence. The new experimental C08 adaptations receive a complete-avatar grounding pass and are baked at 120 Hz, retaining the source model's 30 Hz timing. Dense floor checks found at least approximately 12 mm clearance (one clip remains higher). These checks establish export integrity and floor clearance, not realistic support contacts.

Ukemi is a particularly revealing limit. The initial standing-oriented adapter buried armor by about 0.63 m during inversion. That original result is preserved locally under `evaluation/pose-harvest/original-ukemi-grounding`. The new adaptation needs up to approximately 0.642 m of whole-body lift. This changes the vertical/contact relationship substantially and is visibly flagged. It is not a repaired capture, a physical roll, or proof that two key poses reproduce an Ukemi.

Other source limits remain: the front gorilla endpoint is largely inferred from a close-up, technical stand-up feet are occluded, and deadlift has no recovered bar/load/grip interaction. Predicted joint-limit findings and armor overlaps remain research issues. Raw model outputs are preserved; grounding changes the C08 adaptation rather than the conditioning or generated G1 motion.

## Source terms

The public set uses explicit source permissions: Quaternius CC0, user-owned references, and our originally conditioned MotionBricks outputs. NVIDIA's bundled sample license permits internal evaluation and derivatives for that purpose, and restricts distribution. We keep those sampled poses and their conditioned outputs local.

Sampling a midpoint and endpoint does not itself establish fair use. The U.S. Copyright Office describes fair use as a fact-specific inquiry with no automatic numerical sampling rule. The public package does not depend on that legal conclusion.

Sources: [Quaternius](https://quaternius.com/packs/universalanimationlibrary.html), [NVIDIA sample-data license](https://github.com/NVlabs/MotionBricks/blob/main/assets/motions/LICENSE.txt), [MotionBricks model/source terms](https://github.com/NVlabs/MotionBricks#license), [Copyright Office fair-use guidance](https://www.copyright.gov/fair-use/).
