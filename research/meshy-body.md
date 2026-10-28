# Meshy fighter: geometry → rig → predictive motion

The input GLB is **BJJ Jiu-Jitsu Woman Girl Fighter Free** by **Tulio Portela**, sourced from [Sketchfab](https://sketchfab.com/3d-models/bjj-jiu-jitsu-woman-girl-fighter-free-8077cada67a14af18249b6af687fcc3c), under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The embedded metadata and Sketchfab API agree on the author/license. The creator describes Meshy AI generation. Original source SHA-256: `054fb739bef2e674f77772e50a1c276a86d44a7cb0d8b064c14f3b5ff5d5f6c9`.

The original download is preserved. It contains no skeleton or animation. This experiment uses local Blender rigging: manual anatomical landmarks, 22 bones, automatic bone-heat weights, a distance fallback for 21 unweighted vertices, and four-influence normalization. Mesh partitions were joined and reduced from 206,951 to 72,431 triangles, and height normalized to 1.70 m. Four redundant UV sets were verified identical to UV0 before removal. Material UV references were updated to the retained set; original texture content was retained. Exported tangents and a root-level skinned surface eliminate the initial glTF portability warnings.

Attribution and modification notices appear in the viewer, the GLB asset extras, `docs/assets/meshy-fighter-attribution.json` and the third-party notices. The rigged GLB remains CC BY 4.0. This project classifies it as experimental and excludes it from production.

## Runtime retarget

The fighter uses the same generated G1 positions and rest-relative rotations as C08, rather than borrowing C08's adapted joint tracks. Its own bind proportions determine segment lengths and travel scale. Torso/foot rotations and limb directions are transferred into the new rig; wrists inherit forearm swing and G1 wrist articulation. Skeleton clones and materials are independent for AI/interpolation instances.

The body selector offers C08, fighter, or both side by side. In both-body mode the second lane shows the human receiving the same AI prediction. In a single-body mode, the optional second lane shows ordinary interpolation. Source ghosts/path guides remain the G1/C08 reference view. Root-travel differences between bodies reflect their differing proportions and adaptation.

The rig and geometry are shared across experiments, while motion is evaluated in the browser from the G1 data. The avatar GLB contains the rig; this update does not export a separate baked human GLB for every motion. New local GPU predictions can drive the fighter without rebuilding its rig.

A representative-vertex ground guard lifts the complete fighter when needed. It is not planted-foot IK, physical balance, a cloth solve or an inversion/contact reconstruction. Fingers remain fixed. Gi sleeves, hips, belt and braided hair can deform poorly in extreme poses. This experiment assesses whether the pipeline works, not production asset acceptance.

## Checks

The rigged GLB passes Khronos validation with zero errors/warnings. Its 48,168 exported skin vertices have finite positions, legal joint indices, at most four influences and maximum weight-sum error about 1.8e-7. Runtime tests evaluated all deformed vertices at the midpoint of each of 24 public presets: finite skin data, approximately 3.9 mm minimum observed floor clearance, and maximum limb-length variation about 1.9 micrometres. These snapshot tests are not continuous contact certification.

Browser checks cover body selection, attribution, both-body synchronization, independent clones, human interpolation, arrow/angle-bracket navigation, Space pause/resume, asynchronous-load pause intent, natural random advancement, Stop and mobile layout. Fresh local five-move generation also passed on both bodies.

## Combined predictions and random playback

There are three recorded neural routines, with 5, 10 and 15 source moves. Each move supplies midpoint and endpoint poses from explicitly permitted sources; each subsequent neural call consumes the preceding output's actual last four poses. A final neutral recovery adds one request. Counts therefore correspond to 11, 21 and 31 actual model calls. Their complete traces and seeds are retained. All six C08 exports (AI/interpolation) pass the existing structural, clone, correspondence and dense-floor checks.

On the public page, Combine buttons load those recorded neural routines. On the local GPU page, they generate a fresh source arrangement and export. Random mode instead shuffles recorded short predictions without immediate repeats, centres their travel and blends poses briefly. It runs until stopped; these presentation blends are not new neural inference. Manual analysis stages and scrubbing leave random playback. Previous/next buttons, left/right or angle brackets navigate animations; Space toggles playback outside form controls.
