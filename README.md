# AI Agent Skills

Reusable skills and their bundled scripts, reference material and examples.

## Room-first Building Study

[Skill instructions](room-first-building-study/SKILL.md) · [Full command reference](room-first-building-study/references/commands.md)

Generate and validate semantic SVG floor plans, then reproduce the included
two-storey family-wing house as an editable Blender model with 20 construction
stages. The worked example supports US and metric framing and model-derived
material quantities. A different house requires its own Blender recipe.

### Quick start on Windows

From a checkout of this repository, run the following in PowerShell. Set the
Blender path to your installation. The core workflow uses Blender 5 and its
bundled Python, with no add-ons, separately installed Python, or CitySimVR
checkout. The optional captioned GIF and floor-pair composer uses Pillow 10.1+.

```powershell
$studySkill = (Resolve-Path './room-first-building-study').Path
$studyRun = Join-Path (Get-Location) 'Artifacts/my-building-run'
$blenderExe = 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe'
$studyPython = Join-Path (Split-Path -Parent $blenderExe) '5.0/python/bin/python.exe'

& $studyPython "$studySkill/scripts/test_plans.py"
& $studyPython "$studySkill/scripts/plan.py" room-first --output "$studyRun/plans"
& $blenderExe --background --factory-startup --disable-autoexec --python-exit-code 1 --python "$studySkill/scripts/build_blender.py" -- --source "$studyRun/plans/family-wing.svg" --framing-system us --output "$studyRun/model"
```

Open `Artifacts/my-building-run/model/FamilyWing-ConstructionStudy.blend` in
Blender. Choose a fresh run directory on subsequent runs. The command reference
covers native readback, rendering, takeoff, and the historical price example.
The skill can also be used directly by an agent with access to the full
`room-first-building-study/` directory.
