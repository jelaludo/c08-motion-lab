# Third-party components and provenance

- **Three.js r160:** MIT; vendored browser runtime and selected addons. License in `LICENSES/three-MIT.txt`. Source: https://github.com/mrdoob/three/tree/r160.
- **NVIDIA MotionBricks:** the neural weights are not distributed. The experiment used `MotionBricks-G1-RP-v1`, FP32, upstream commit `54fc563aeaaf819a753d72cc9fdc6713989cdd43`. Upstream code is Apache 2.0; model use is governed by NVIDIA's Open Model Agreement. Sources: https://github.com/NVlabs/motionbricks and https://huggingface.co/nvidia/MotionBricks.
- **Unitree G1 reference kinematics:** BSD-3-Clause notice in `LICENSES/unitree-BSD-3-Clause.txt`. The original simple pose-authoring proxy and generated reference-body arrays use this kinematic interface. No Unitree visual meshes or branding are embedded in C08 or K0-Tech.
- **C08 Industrial Worker and K0-TECH-01:** original workshop geometry and authored motion by jelaludo, included at the creator's request. Published asset hashes and source links are recorded under `docs/assets/`.
- **NVIDIA/Bones sample motion:** not included. No sample-conditioned clips from the earlier internal evaluation are included. Every published generated robot test uses original numerical conditioning; the exact arrays are retained.
- **GEM-X / SOMA-X:** six user-provided exercise references were processed locally using NVIDIA GEM-X native SOMA and directly retargeted to C08. Model weights and body-model assets are not distributed. Code/model/asset terms remain with their official distributions: https://github.com/NVlabs/GEM-X and https://github.com/NVlabs/SOMA-X.
- **Reference video:** raw video, extracted frames, reference overlays and human capture archives remain local. The intended derived C08 clips, source-skeleton previews and sanitized provenance are published at the user's request; they are distinct from MotionBricks-generated clips.

This repository has no blanket grant that overrides the source assets or upstream terms.
