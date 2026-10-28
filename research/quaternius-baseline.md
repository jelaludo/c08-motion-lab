# Quaternius baseline — 2026-10-28

20 animations from the official **Universal Animation Library 1 Standard** download, retargeted to the existing C08 rig. Animations are CC0; C08 remains the creator's original asset. The unmodified source mannequin animation GLB is included for direct comparison. No paid-tier clips are used.

Source: https://quaternius.itch.io/universal-animation-library and https://quaternius.com/packs/universalanimationlibrary.html. License and file SHA-256 values are in `docs/quaternius/license.txt` and `provenance.json`.

## What the new tab demonstrates

- Idle, walk, jog, sprint, formal walk and crouched movement from one consistent source rig.
- Conventional crossfades; walk/jog/sprint transitions inherit the preceding cycle phase.
- Explicit jump-start → airborne → landing and sit-enter → seated idle → sit-exit sequences.
- Clip inspection, a locomotion blend demonstration, keyboard movement, and the original mannequin for comparison.
- The existing diorama, MotionBricks tests, video retargets and experimental keyboard controller retain their research role and URLs. No research clips are replaced.

## Retargeting and verification

Anatomical bone mapping transfers rest-relative rotations, aligns rest limb directions, and keeps C08 segment lengths fixed. Finger/socket/sensor/game-root tracks are excluded. Horizontal source displacement is removed for in-place playback. Pelvis height is scaled to C08; complete-avatar ground placement is baked. Jumps preserve airborne elevation with a minimum ground-clearance constraint.

The initial 30 Hz export had armor penetration between keys in several fast clips. The final export samples and bakes at 120 Hz. All 20 clips pass zero-error/zero-warning glTF validation, source-to-export joint comparisons, fixed-segment checks and dense 120 Hz skinned-geometry floor sampling. Loop endpoint pose differences are measured separately; structural validity does not establish visual quality. The tab additionally lifts the complete avatar if a playback crossfade lowers armor below the floor. This is not contact IK.

The clips still need visual evaluation for armor overlap, support contacts, hand position, seated support and the robot's sense of weight. No collision physics or planted hand/foot solver is included. Starts/stops and direction changes use basic blending; they are not a complete production locomotion system. The source Standard pack does not supply every desirable transition. The seated state has no chair in this scene.

## MotionBricks is learned in-betweening

Our pinned MotionBricks runtime accepts four recent poses and one to four targets. It predicts root path and duration, generates learned motion tokens, and decodes intermediate skeletal poses at 30 Hz. Chaining the last generated poses into the next request enables continuous generation. This differs from ordinary quaternion/keyframe interpolation or playback crossfades.

The browser research pages play exported clips; their Continuous button does not invoke AI. MotionBricks generation has run offline on the local NVIDIA GPU. GEM-X exercise clips are a separate recovery/retarget path. The Quaternius baseline uses neither model.

A useful next comparison is to use permissible target poses on a supported model rig, generate an approach/transition with MotionBricks, then compare it with the direct Quaternius sequence under the same start/end conditions. C08 is not a native MotionBricks model rig; it needs a supported-rig mapping and final retarget. Sparse targets cannot guarantee a faithful Ukemi, correct contacts or obstacle clearance.

Official documentation: https://github.com/NVlabs/MotionBricks#how-motionbricks-works and https://nvlabs.github.io/motionbricks/.
