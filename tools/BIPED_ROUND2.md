Biped-only round reproduction

These scripts use the existing local lab workspace, not an empty clone. Private reference videos, GEM-X weights and recovered SOMA motion are intentionally not published. Set MOTION_LAB_WORKSPACE to the original directory containing assets/, video-mocap/, tools/review/node_modules and public/c08-motion-lab/.

1. Recover a user-owned reference with video_run_ukemi.py and video_export_ukemi.py in the isolated GEM-X environment, then evaluate exact transforms with soma_prepare_c08.py. Existing source hashes can be reused; never silently reuse a different video.
2. Blender 4.5 LTS: blender --background --python tools/retarget_soma_bipeds.py -- ukemi --body c08. Bodies: c08, brek43, eva-k7, meshy-fighter. Source slug points to video-mocap/c08-retarget/<slug>/soma-frames.npz. Outputs are private video-mocap/biped-round2/<slug>/<body>/.
3. Node: node tools/validate_soma_bipeds.mjs ukemi:c08 ukemi:brek43 ukemi:eva-k7 ukemi:meshy-fighter. Requires Three 0.160 and gltf-validator from original lab tools/review/node_modules. Embedded texture bytes are validated by glTF validator; the Node geometry-only pass substitutes image objects and does not judge texture appearance. Actual browser render QA is separate.
4. build_biped_catalog.py copies only validated GLBs and non-private reports into the public biped-motion gallery using the private round manifest. All source human video/frames remain private.

Retargeting uses native SOMA rotation deltas, original target bind directions and proportions, retaining full pelvis orientation during rolls. All original skin vertices and weights participate in a 15 mm whole-avatar grounding correction per key. This correction changes vertical root motion; it is not hand/foot pinning, balance or a collision solve. Every correction is reported. Meshy output retains CC BY 4.0 attribution to Tulio Portela. Original fingers remain at rest.
