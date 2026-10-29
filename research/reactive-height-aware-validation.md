# Height-aware interaction validation

The generator selects sparse target poses for MotionBricks. An external controller
uses continuous horizontal sweeps to stop or slide the root. It never lifts a
predicted root, edits its quaternion, or edits its joint angles. The independent
NPZ audit compares those values exactly against the selected untouched predictions.

Hurdles and overhead bars are native G1 boxes: `center` is XY, `depth` follows X,
`width` follows Y, `base_z` is the underside, and `height` is the box thickness.
Both endpoint poses must clear the obstacle's vertical interval before the
horizontal sweep may pass it. FK ankle centres minus 0.17 m bound the sole;
the highest G1 joint plus 0.86 m bounds C08's upper anatomy. These offsets were
measured against the actual source skin, including angled toes and the head.
They are navigation bounds; the exported character is checked separately.

B-REK43 has different body proportions. Its overhead underside can be specified
in `display_by_body.brek.base_z`. The viewer and exported selection manifest
describe that calibrated geometry. This is a body-adjusted test course rather
than a claim that both characters fit the same physical opening.

The mesh audit evaluates the actual C08 baked clip with its authored cupped
hands, or B-REK43 through the same runtime adapter as the viewer. Bone-local
vertex bounds screen distant obstacles. Near obstacles use exact triangles
against height-clipped cylinders or native box SAT tests. The B-REK audit keeps
its authored hand rig and body-grounding correction. Default sampling is 120 Hz;
pilot checks use 30 Hz. This is sampled geometry testing, not continuous
articulated dynamics.

The first moving-crouch pilot failed despite low target poses. Replanning after
the first 0.5 seconds repeatedly discarded the lower endpoint while the model
rose during its intermediate movement. The 32-second pilot produced 2,353 C08
and 776 B-REK triangle/bar intersections at 30 Hz. The corresponding reports are
retained as negative controls. The jump pilot crossed both hurdles with zero
triangle/box intersections on both bodies; the locomotion-only baseline stopped
before the first hurdle. Later results must be read from the final reports.

Run the controller checks with:

```
python tools/test_reactive_behavior_collision.py
python tools/validate_reactive_physics.py
node tools/review/validate-reactive-armor.mjs <reactive-directory> 120 <report.json> c08
node tools/review/validate-reactive-armor.mjs <reactive-directory> 30 <report.json> brek
```

Full unused neural futures remain in the local research workspace. Public NPZ
downloads retain the exact selected untouched predictions and the played poses;
the public context/target trace retains every real inference request.
