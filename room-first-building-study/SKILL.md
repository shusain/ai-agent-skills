---
name: room-first-building-study
description: Design conceptual buildings from their room programs. Use for dimensioned SVG layout options, editable staged Blender studies, and model-derived material takeoffs across building types. Reuse geometry, clearance and assembly helpers with project-specific recipes.
---

# Room-first building study

Start with the spaces and how they work together. Derive the footprint, shared
walls and openings from that layout. Use this workflow for residential,
commercial, industrial, civic or other buildings. Select deliverables by the
requested phase.

## Plan a new building

Read [planning.md](references/planning.md). Establish use, level count, named
spaces, clear dimensions, equipment/furniture, circulation, access, service
routes, and site constraints from the brief. Author the layout and checks for
that project. Show comparable SVG options when a layout is still being chosen.
Continue from an already reviewed option when one exists.

Use the reusable rectangle, topology and clearance helpers for rectilinear
plans. Choose an appropriate geometry representation and checks for other
shapes. The bundled house recipes are worked examples. Start a new design from
its own space program and assemblies.

## Choose the construction system

Carry the project's construction system and unit standard into modeling. For
timber framing, use [framing.md](references/framing.md) and
`building_study.framing.profile` for actual US/imperial or metric stock and
spacing. Inherit a stated preference. If the standard affects the design and
is still unknown, clarify once while developing the room program. A display
unit choice alone leaves stock dimensions unchanged.

For other systems, declare the assembly materials, section dimensions and
spacing/grid inputs that apply. Preserve those inputs with the native model and
takeoff. Treat these as schematic design inputs. Structural engineering and
code compliance are separate tasks.

## Model, verify and measure

- **Model a reviewed plan:** use [blender.md](references/blender.md). Author a
  project-specific Blender recipe for the relevant levels, structure, roof,
  openings and fit-out. Keep the model editable and stage assemblies with stable
  component IDs. Coordinate service reservations when detailed meshes are
  outside scope.
- **Quantities or cost:** use [materials.md](references/materials.md). Inventory
  the original construction objects, define categories and measurement methods
  for the project, separate purchasing allowances and use explicit dated rates.
- **Reproduce the example:** use [commands.md](references/commands.md). The
  house CLI has three authored arrangements and one reviewed family-wing Blender
  recipe. The twelve-layout fallback is a separate stock-plan generator.

## Preserve these invariants

1. Use a shared coordinate basis and convert once to Blender metres. The bundled
   SVG contracts use integer-mm room datums. Keep exact sub-millimetre framing
   conversions where needed. Derive the footprint from the room union and assign
   shared walls and hosted openings a single owner.
2. Read the semantic geometry and openings from the reviewed source. Keep the
   source hash with the native model and reject stale or unsupported edits.
3. Check usable dimensions, functional fit, connected circulation, both-side
   door pads and full swings. Check aligned vertical openings and headroom when
   applicable. Verify actual fixture and equipment geometry in the saved model
   and state which checks are schematic or conservative.
4. Reuse the same source components for the completed building and construction
   stages. Exclude presentation copies from material quantities.
5. Keep unsuccessful layouts visible as failed attempts. Use fallback layouts
   only when selected and recheck coverage, identity and access after any repair.

## Included tools

`scripts/building_study/` includes shared geometry, clearance and Blender
helpers plus the family-wing implementation. `scripts/plan.py` exposes the
stock recipes and validates their supported semantic SVG schemas.
`scripts/build_blender.py`, `verify_blender.py` and `takeoff_blender.py`
reproduce the example in separate background Blender processes. Write generated
files outside the skill and keep the active Blender session intact.

Blender 5 and its bundled Python can run the core tools. Only the optional
`compose_review.py` uses Pillow for a captioned GIF and floor pair.

Deliver source identity, actual checks, review limits and the remaining design
decisions. Follow the destination project's workflow for adoption.
