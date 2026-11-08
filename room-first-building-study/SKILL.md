---
name: room-first-building-study
description: Design room-first SVG layouts and inspectable staged Blender buildings using US/imperial or metric framing. Use for inside-out architectural asset studies and model-derived material takeoffs; the included two-storey house is a bounded worked example.
---

# Room-first building study

Start with how rooms work together, then derive the footprint and shared walls.
Keep one geometric source for SVG review, Blender assemblies and quantities.
Deliver only the phase requested; plan review does not automatically select
Blender authoring, engineering, engine integration or publication.

## Establish the construction standard

Use either **US/imperial** or **metric** lumber and spacing. Inherit the user's
choice from the request/context; if it is unknown and affects the design,
clarify once while developing the room program. Do not silently reuse metric
45mm stock or600mm spacing for a US building. Read
[framing.md](references/framing.md) for actual stock dimensions, defaults and
overrides. A display-unit change alone does not change physical lumber.

Use `building_study.framing.profile` for every new building recipe, including
building types beyond the bundled house. US nominal2×4 is modeled at its actual
1½×3½ inches; metric45×90 is a different stock choice. Record the chosen profile
with native outputs and quantities. The build CLI requires `--framing-system`.

## Choose the current phase

- **Plan or revise a building:** read [planning.md](references/planning.md).
  Define named rooms, usable size/fit, access/privacy and adjacency relationships;
  compose foyer/halls/stairs intentionally. Show useful SVG alternatives before
  3D when the layout has not already been reviewed.
- **Build a reviewed plan:** read [blender.md](references/blender.md). Consume the
  actual semantic SVG and its identity, build layers with shared junctions and
  openings, and preserve component/stage ownership. Continue from an already
  selected layout without requesting the same approval again.
- **Quantities or cost:** read [materials.md](references/materials.md). Inventory
  original construction objects, separate measured quantities from purchasing
  allowances, and keep prices as explicit dated inputs.
- **Reproduce the included house or run checks:** use
  [commands.md](references/commands.md). The library supports exact rectilinear
  geometry; the three room-first arrangements are authored examples. The Blender
  recipe supports the reviewed family-wing SVG specifically. Adapt the roof,
  structure, fixtures and validation together for another design; changing a
  brief does not automatically solve a new building.

## Preserve these invariants

1. Use one internal coordinate basis and convert once to Blender metres.
   The current SVG contract uses integer-mm room datums; framing geometry keeps
   sub-millimetre inch conversions exactly instead of rounding stock/spacing.
   Derive boundaries and wall material from room unions. Shared walls/openings
   have single owners; independent wall boxes do not resolve L/T junctions.
2. Reject stale or unsupported SVG source edits. Read named geometry and hosted
   openings, not labels or a disconnected JSON description. Record the reviewed
   source hash with the native output.
3. Room area alone does not establish usability. Check functional fit, minimum
   walking-width regions, connected circulation, both-side door pads, full swings
   and aligned stair openings. Recheck physical fixtures and overhead members
   after modeling. State which checks are schematic or conservative.
4. Use the same source components for the completed building and its construction
   sequence. Presentation cutaways/exploded copies retain provenance but are not
   additional material consumption.
5. The retained footprint-first generator is an explicit fallback. Failed room
   briefs should fail visibly; do not silently substitute a different plan or
   collapse spaces without checking coverage, identity and access.

## Included implementation

`scripts/plan.py` exposes room-first examples, the twelve-layout fallback and
actual SVG readback. `scripts/building_study/` contains shared topology,
rectangle/clearance code and the bounded Blender recipe. Tests retain the four
sliver/door regressions and unchanged fallback hashes.

`scripts/build_blender.py`, `verify_blender.py` and `takeoff_blender.py` run in
separate background Blender processes; explicit output paths keep generated
files outside the skill. Blender 5 and its bundled Python can run the model,
plan, verification, takeoff, and price tools with no add-ons or separate
packages. Only the optional `compose_review.py` uses Pillow for a captioned GIF
and floor pair. See the command reference for exact arguments.

Treat lumber sizes, spacing, supports and roof systems as declared design inputs,
not automatic code/engineering approval. Both metric and US profiles are working
geometry choices, with explicit stud/joist/rafter spacing overrides.
Services can remain coordinated reservations when detailed meshes are outside
scope. Keep production assets and the user's active Blender session intact.

Carry forward source identity, actual checks, review limits and next decisions in
delivered evidence. Follow the destination project's workflow for adoption; this
skill grants no permission to publish, message others or deploy.
