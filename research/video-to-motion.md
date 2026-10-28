# Separate experiment: video to motion

Video recovery and MotionBricks solve different problems. A recovery system estimates the performance in a video. A retargeter transfers it to another skeleton. MotionBricks generates new transitions from recent and target poses. For faithfully replaying a captured ukemi, direct recovery and retargeting should be the baseline; passing everything through a generative model could change the performance.

## Tested route

```text
Private reference video ? GEM-X temporal recovery ? native SOMA
  ? direct C08 adaptation ? published derived GLB
  ? selected conditioning poses ? MotionBricks (future comparison)
```

Six direct retargets are now available in the [Test Gallery](https://jelaludo.github.io/c08-motion-lab/lab/?test=mocap_ukemi): Ukemi, side and front gorilla exercises, technical stand-up, sumo stomp and deadlift. These are video recovery experiments, not MotionBricks-generated clips. [Retarget findings](video-retargets.md) describe validation and visible limitations.

The alternative `Video → GVHMR/WHAM → SMPL-family motion` needs an explicit SMPL-to-SOMA fitting/conversion step. SOMA Retargeter expects a SOMA-skeleton BVH, not an arbitrary BVH file with different names/rest transforms. WHAM's standard output is SMPL; GVHMR predicts SMPL-X parameters. Body-model families are not interchangeable labels.

Sources:

- GEM-X: https://github.com/NVlabs/GEM-X — temporal `motion-video` output uses SOMA. Its saved output is a tensor dictionary, so a validated interchange export is still needed.
- SOMA-X conversion tools: https://github.com/NVlabs/SOMA-X/blob/main/docs/tools.md.
- SOMA Retargeter input contract: https://github.com/NVIDIA/soma-retargeter.
- GVHMR: https://github.com/zju3dv/GVHMR — research/non-profit software terms; SMPL-family assets are supplied separately.
- WHAM: https://github.com/yohanshin/WHAM — MIT source code, with separately supplied model/body assets.

## Local ukemi test

A separate short reference video was processed with a pinned, isolated GEM-X environment on the RTX 4090. It produced **143 frames and 77 SOMA joints at 30 Hz**, including a shoulder-roll/inversion interval around 2.20–2.67 seconds. Inference took 52.82 seconds with peak PyTorch CUDA allocation of about 3.42 GiB. Camera overlays and a world skeleton were inspected. Occluded limbs and the cropped ending remain limitations.

The direct bridge preserves source joint rotations and fixed C08 segment lengths, including inverted ukemi poses. All six exports pass structural validation. Whole-avatar grounding does not solve planted hands, feet, balance or armor overlap. The front gorilla ending is speculative because the body leaves the image.

Source videos, source frames, overlays, recovery tensors and inference weights remain local. Only the intended derived C08 clips, reference skeleton previews and sanitized reports are published.

## Where MotionBricks adds value

- Turn a small set of captured or authored poses into approaches, departures and transitions from new starting states.
- Place the same arrival posture at a new destination or heading.
- Chain selected targets from different actions into continuous movement.
- Generate motion when only a few poses are authored.

It is optional for a finished captured clip. It does not guarantee better capture fidelity, correct hand/object contact, physical balance or error-free foot planting. We should compare direct retargeting with generated variants rather than assume every capture benefits from another model.
