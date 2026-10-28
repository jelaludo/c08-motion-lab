# Third-party components and provenance

- **Three.js r160:** MIT; vendored browser runtime and selected addons. License in `LICENSES/three-MIT.txt`. Source: https://github.com/mrdoob/three/tree/r160.
- **NVIDIA MotionBricks:** the neural weights are not distributed. The experiment used `MotionBricks-G1-RP-v1`, FP32, upstream commit `54fc563aeaaf819a753d72cc9fdc6713989cdd43`. Upstream code is Apache 2.0; model use is governed by NVIDIA's Open Model Agreement. Sources: https://github.com/NVlabs/motionbricks and https://huggingface.co/nvidia/MotionBricks.
- **Unitree G1 reference kinematics:** BSD-3-Clause notice in `LICENSES/unitree-BSD-3-Clause.txt`. The original simple pose-authoring proxy and generated reference-body arrays use this kinematic interface. No Unitree visual meshes or branding are embedded in C08 or K0-Tech.
- **C08 Industrial Worker and K0-TECH-01:** original workshop geometry and authored motion by jelaludo, included at the creator's request. Published asset hashes and source links are recorded under `docs/assets/`.
- **NVIDIA/Bones sample motion:** not included. No sample-conditioned clips from the earlier internal evaluation are included. Every published generated robot test uses original numerical conditioning; the exact arrays are retained.
- **GEM-X / SOMA-X:** six user-provided exercise references were processed locally using NVIDIA GEM-X native SOMA and directly retargeted to C08. Model weights and body-model assets are not distributed. Code/model/asset terms remain with their official distributions: https://github.com/NVlabs/GEM-X and https://github.com/NVlabs/SOMA-X.
- **Reference video:** raw video, extracted frames, reference overlays and human capture archives remain local. The intended derived C08 clips, source-skeleton previews and sanitized provenance are published at the user's request; they are distinct from MotionBricks-generated clips.

This repository has no blanket grant that overrides the source assets or upstream terms.

## Quaternius Universal Animation Library 1 Standard

The new baseline tab includes 20 retargeted animations and the original Standard mannequin GLB from Quaternius. Source: https://quaternius.itch.io/universal-animation-library. Animation/source pack license: CC0 1.0 Universal, included at `docs/quaternius/license.txt`. C08 geometry remains the original creator asset under its existing terms. Only the free Standard download was used; no paid-tier assets were obtained.

## Landing page typography
The landing page requests DM Sans and Space Grotesk through Google Fonts; these font families are offered under the SIL Open Font License. System fonts provide the fallback.

## Sampled-pose conditioning
The predictive tab includes five new Quaternius CC0 source-pose experiments, six from user-provided capture recoveries, and four from our original-input MotionBricks outputs. Generated outputs are identified separately from their source clips. Two bundled NVIDIA sample experiments remain local under the sample evaluation terms; neither their sampled poses nor their conditioned outputs are published. See research/pose-harvest.md.

## Meshy-generated fighter test body (CC BY 4.0)

**BJJ Jiu-Jitsu Woman Girl Fighter Free** by **Tulio Portela** (https://sketchfab.com/TulioPortela). Source: https://sketchfab.com/3d-models/bjj-jiu-jitsu-woman-girl-fighter-free-8077cada67a14af18249b6af687fcc3c. License: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/. Creator description identifies Meshy AI generation.

Lab changes: normalized size, joined/reduced mesh, duplicate UV cleanup, humanoid landmark rig, automatic heat skinning with four-weight normalization, tangent export and runtime G1 retargeting. Original textures retained. This is an experimental secondary body in MB-Predictive, excluded from this project's production pipeline. Attribution and modification notices also accompany the GLB and player. The creator's license continues to apply.
