# Separate experiment: video to motion

Video recovery and MotionBricks solve different problems. A recovery system estimates the performance in a video. A retargeter transfers it to another skeleton. MotionBricks generates new transitions from recent and target poses. For faithfully replaying a captured ukemi, direct recovery and retargeting should be the baseline; passing everything through a generative model could change the performance.

## Proposed routes

```text
Video → GEM-X temporal Body Motion → native SOMA motion
  → validated SOMA animation/BVH bridge
  → SOMA Retargeter → G1 CSV → C08 adapter → GLB
                             ↘ selected poses → MotionBricks → new transitions
```

The alternative `Video → GVHMR/WHAM → SMPL-family motion` needs an explicit SMPL-to-SOMA fitting/conversion step. SOMA Retargeter expects a SOMA-skeleton BVH, not an arbitrary BVH file with different names/rest transforms. WHAM's standard output is SMPL; GVHMR predicts SMPL-X parameters. Body-model families are not interchangeable labels.

Sources:

- GEM-X: https://github.com/NVlabs/GEM-X — temporal `motion-video` output uses SOMA. Its saved output is a tensor dictionary, so a validated interchange export is still needed.
- SOMA-X conversion tools: https://github.com/NVlabs/SOMA-X/blob/main/docs/tools.md.
- SOMA Retargeter input contract: https://github.com/NVIDIA/soma-retargeter.
- GVHMR: https://github.com/zju3dv/GVHMR — research/non-profit software terms; SMPL-family assets are supplied separately.
- WHAM: https://github.com/yohanshin/WHAM — MIT source code, with separately supplied model/body assets.

## Local ukemi test

A separate short reference video was processed with a pinned, isolated GEM-X environment on the RTX 4090. It produced **143 frames and 77 SOMA joints at 30 Hz**, including a shoulder-roll/inversion interval around 2.20–2.67 seconds. Inference took 52.82 seconds with peak PyTorch CUDA allocation of about 3.42 GiB. Camera overlays and a world skeleton were inspected. Occluded limbs and the cropped ending remain limitations.

The recovered joint names/order match the installed MotionBricks SOMA reference. That does not by itself validate local/rest transforms, body-scale conventions, BVH units or a G1/C08 retarget. No C08 ukemi animation is claimed. Standing foot-plant correction was deliberately not imposed on the ground roll.

All source media, overlays, recovery data, credentials and inference weights remain local. This public note documents the result without redistributing them.

## Where MotionBricks adds value

- Turn a small set of captured or authored poses into approaches, departures and transitions from new starting states.
- Place the same arrival posture at a new destination or heading.
- Chain selected targets from different actions into continuous movement.
- Generate motion when only a few poses are authored.

It is optional for a finished captured clip. It does not guarantee better capture fidelity, correct hand/object contact, physical balance or error-free foot planting. We should compare direct retargeting with generated variants rather than assume every capture benefits from another model.
