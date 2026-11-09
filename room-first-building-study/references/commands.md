# Commands and execution contracts

Run the examples below from the repository root in PowerShell. The script paths
can also be absolute from any working directory. Blender 5 runs the model
scripts and supplies the Python 3.11+ interpreter for the plan, price, and plan
test scripts. You can use another Python 3.11+ interpreter for those scripts if
you already have one. Only the optional review composer requires Pillow 10.1+.

```powershell
$studySkill = (Resolve-Path ./room-first-building-study).Path
$studyRun = Join-Path (Get-Location) 'Artifacts/my-building-run'
$blenderExe = 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe'
$studyPython = Join-Path (Split-Path -Parent $blenderExe) '5.0/python/bin/python.exe'
```

Use the executable and bundled Python paths from your Blender installation. Generated runs must
be outside the skill source directory. Generators reject existing output folders;
choose a new run name rather than overwriting review evidence. The readback
command may refresh its own receipt/frame files in the existing model run.

## Reuse the helpers for a new design

Start with [the project workflow](planning.md#author-a-new-building). Put the
skill's `scripts/` directory on the new project's Python import path and use the
relevant functions from `building_study`. The commands below exercise the
bundled examples and their file contracts.

## Generate the worked-example plans

```powershell
& $studyPython "$studySkill/scripts/test_plans.py"
& $studyPython "$studySkill/scripts/plan.py" room-first --output "$studyRun/plans"
& $studyPython "$studySkill/scripts/plan.py" validate "$studyRun/plans/family-wing.svg"
```

Optional `--program PATH` supplies a brief that follows the bundled two-storey
house program. Generation writes six floor SVGs, three paired house SVGs,
models/program data and validation receipts. The bundled paired SVG can be used
directly for exact reproduction after the user has already selected family-wing.
For other floor/readback contracts, use `validate --kind floor` or `fallback`.

```powershell
& $studyPython "$studySkill/scripts/plan.py" fallback --output "$studyRun/fallback"
```

This explicitly writes the twelve single-floor rectangle/L/U/courtyard fallback
plans, with the retained morphology and door checks. It does not replace a failed
room program automatically. The lower-level library APIs can be imported through
`building_study` with `scripts` on Python's path; do not copy individual modules
into the current working directory to satisfy imports.

## Build and verify the family-wing example

Establish the user's framing preference first; inspect either profile without
Blender when useful:

```powershell
& $studyPython "$studySkill/scripts/plan.py" framing --system us
& $studyPython "$studySkill/scripts/plan.py" framing --system metric --stud-spacing 400
```

The example builder requires the exact reviewed family-wing source. For a new
layout, [author a matching recipe](blender.md#author-a-project-recipe).

```powershell
& $blenderExe --background --factory-startup --disable-autoexec --python-exit-code 1 --python "$studySkill/scripts/build_blender.py" -- --framing-system us --output "$studyRun/model" --render
```

`--framing-system` is required (`us` or `metric`); it changes physical geometry,
not just Blender's unit display. Use optional `--stud-spacing`, `--joist-spacing`
and `--rafter-spacing` in that system's native units. For example, US
`--stud-spacing 24 --joist-spacing 19.2 --rafter-spacing 16`, or metric
`--stud-spacing 400 --joist-spacing 400 --rafter-spacing 600`.

Optional `--source PATH` chooses the reviewed paired SVG explicitly. `--samples N`
controls renders. Without `--render`, generation/checks/native save still run but
seven PNG views are skipped. Output includes `FamilyWing-ConstructionStudy.blend`
and `assembly-receipt.json`; native component count is measured, not hard-coded.
The builder refuses an interactive Blender process. Open the saved file for
review without closing or replacing another user's active scene.

```powershell
& $blenderExe --background --factory-startup --disable-autoexec "$studyRun/model/FamilyWing-ConstructionStudy.blend" --python-exit-code 1 --python "$studySkill/scripts/verify_blender.py" -- --output "$studyRun/model" --render-stages
python "$studySkill/scripts/compose_review.py" --run "$studyRun/model" --output "$studyRun/review"
```

Readback does not resave the native file. It writes `native-readback.json` and,
with `--render-stages`, 20 source-stage PNGs. Omit that flag to run checks and
retain earlier frames. Use a Python interpreter with Pillow 10.1+ for the
composer. It reads all stage PNGs and pairs floor renders when present. Use
`--font PATH` to override Pillow's portable default font.

## Example takeoff and historical price snapshot

```powershell
& $blenderExe --background --factory-startup --disable-autoexec "$studyRun/model/FamilyWing-ConstructionStudy.blend" --python-exit-code 1 --python "$studySkill/scripts/takeoff_blender.py" -- --output "$studyRun/takeoff"
& $studyPython "$studySkill/scripts/price_takeoff.py" --quantities "$studyRun/takeoff/quantities.json" --rates "$studySkill/assets/examples/usd-rates-2026-11-02.json" --output "$studyRun/example-budget"
```

The takeoff reads the recorded profile from the native source, without another
unit-system guess, and reports actual sizes/spacings and stock equivalents.
The takeoff writes `components.csv` and `quantities.json`; pricing writes
`costs.csv`, `estimate.json`, `estimate.html`. That bundled rate file reproduces
the historical USD example. It does not supply current prices. Read materials.md
before presenting costs; supply a newly researched scenario for a fresh estimate.

## Provenance and limits

Packaged from the local CitySimVR #890 room-first/family-wing study and its four
sliver regressions. The small material helper is derived from CityArtKit; no
CitySim checkout/import path remains required. Original review assets and native
files stay in their original project. The skill contains source/example inputs,
not large generated Blender binaries or rendered evidence.

The room-program generator is three authored arrangements, not a general solver;
the Blender example is one reviewed geometry. The test suite's unchanged fallback
hashes cover a real retained behavior, not old production compatibility policy.
Project-specific Git/Gitea/Drone procedures are not inherited as universal skill
instructions. Follow the destination repository's process when adopting tools.
