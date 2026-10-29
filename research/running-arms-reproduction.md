# Reproducing the running-arm diagnostic

The public checkout contains the measurement script, published report, and proposed filtered GLB. It does **not** contain the original workspace's private `evaluation/` tree or its separately downloaded Quaternius source pack. Running the script from a public clone therefore requires `--workspace` pointing to a prepared local MotionBricks workspace.

From this repository, using a Python environment with NumPy and SciPy:

```powershell
python tools/diagnose_running_arms.py --workspace G:/Dev/MotionBricks
```

To keep a new experiment separate from the published evidence:

```powershell
python tools/diagnose_running_arms.py --workspace G:/Dev/MotionBricks --output G:/Dev/MotionBricks/logs/arms-reproduction
```

`--workspace` may be omitted when the current or enclosing directory contains both `evaluation/` and `assets/`. Without a suitable workspace, the script stops with an explicit list of missing inputs before writing outputs. `--output` defaults to this public repository's `research/` directory, independent of the selected workspace. Existing outputs with the same names are overwritten.

Required local source layout:

```text
evaluation/reactive-round4/speedzones_reactive_1/
  c08-motionbricks-test.glb
  g1-motion.npz
  prediction-trace.json
assets/quaternius/**/UAL1_Standard_RM.glb
```

The first three files are full-precision working artifacts from our local round-four pipeline. The Quaternius Universal Animation Library Standard Root Motion asset is a separately obtained CC0 reference; the script selects its `Sprint_Loop` animation. Source SHA-256 values in `running-arms-diagnostic.json` identify the exact inputs used for the published measurements. Supplying different inputs can produce different results.

The script regenerates the numerical diagnostics and separate proposed GLB. The published report also records interpretation notes and an independent glTF validation result. The filter changes only selected upper-body rotation accessors; source files are opened for reading, and root/leg/position animation accessors are verified unchanged in the proposed copy. This experiment does not estimate or correct center of mass or approve visual quality.
