# AI Agent Skills

## Room-first Building Study

Design conceptual buildings from the inside out. Start with how people, equipment
and materials move between spaces, then derive the footprint and shared walls.
Use the skill for homes, workshops, shops, offices, civic buildings and other
building types. The program and construction system come from the project brief.

[Skill instructions](room-first-building-study/SKILL.md) · [Planning guide](room-first-building-study/references/planning.md) · [Blender guide](room-first-building-study/references/blender.md)

### Start a new building

Give your agent the full `room-first-building-study/` folder and a brief. Include
the intended use, spaces and equipment, site or footprint constraints, access
needs, and the output you want. For example:

> Plan a one-storey repair workshop with a receiving area, a repair bay and a
> parts room. Keep deliveries out of the work area. Show two dimensioned SVG
> options with door swings and equipment clearances for review.

1. **Program the spaces.** Define clear dimensions, required adjacencies,
   circulation and any public, staff or service routes.
2. **Review the layout.** Author project-specific SVG options showing the room
   geometry, wall junctions, hosted openings and circulation. Check the fit of
   equipment or furniture, usable walking widths, door swings, and stairs or
   floor openings where present.
3. **Model the selected option if requested.** A project-specific Blender script
   reads the reviewed geometry and builds editable assemblies grouped by
   construction stage. The script records the source hash and checks the saved
   model against the chosen layout and assembly rules.
4. **Measure the model if requested.** Inventory the original components by
   material and stage. Purchasing allowances and prices use separate inputs.

### What is reusable and where custom work starts

| Area | Reusable tools | Scope |
| --- | --- | --- |
| Layout | Rectangle unions, shared boundaries, wall junctions and clearance checks | The supplied geometry helpers work with axis-aligned shapes in integer millimetres. Angled or curved walls and opening types outside the supplied schemas need their own geometry and checks. |
| SVG | Semantic source groups for named spaces, shared walls and hosted openings | Readers validate their documented SVG schemas. Artwork or arbitrary floor-plan SVGs need a project-specific importer or a rebuilt semantic source. |
| Blender | Mesh primitives, stage collections and component metadata. US and metric timber profiles use actual stock sizes and spacings. | Each project needs an authored model recipe for its floors, structure, roof and fit-out. Other construction systems need their own assembly rules and stock data. |
| Quantities | Model-derived inventory workflow, with CSV and JSON in the worked example | Verification, takeoff categories and pricing rules follow the project recipe. Engineering, code compliance, detailed services and order-ready purchasing schedules require separate work. |

The checked-in `plan.py room-first` command generates three authored two-storey
house layouts. Its optional brief input follows that house program. The
`fallback` command generates twelve stock layouts. `build_blender.py`,
`verify_blender.py` and `takeoff_blender.py` demonstrate the full workflow for
the reviewed family-wing layout. To design a different building, start with its
brief and reuse the lower-level helpers that fit. See the
[custom project workflow](room-first-building-study/references/planning.md#author-a-new-building).

### Run the included example on Windows

The core tools run with Blender 5 and its bundled Python. The optional captioned
GIF and floor-image composer requires Pillow 10.1+. From the repository root
in PowerShell, set the Blender path to match your installation:

```powershell
$studySkill = (Resolve-Path './room-first-building-study').Path
$studyRun = Join-Path (Get-Location) 'Artifacts/my-building-run'
$blenderExe = 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe'
$studyPython = Join-Path (Split-Path -Parent $blenderExe) '5.0/python/bin/python.exe'

& $studyPython "$studySkill/scripts/test_plans.py"
& $studyPython "$studySkill/scripts/plan.py" room-first --output "$studyRun/plans"
& $blenderExe --background --factory-startup --disable-autoexec --python-exit-code 1 --python "$studySkill/scripts/build_blender.py" -- --source "$studyRun/plans/family-wing.svg" --framing-system us --output "$studyRun/model"
```

Open `Artifacts/my-building-run/model/FamilyWing-ConstructionStudy.blend` to
inspect the model and its 20 construction stages. Choose a fresh run directory
on subsequent runs. The [command reference](room-first-building-study/references/commands.md)
covers the metric profile, saved-model checks, stage renders, takeoff and the
historical pricing example.
