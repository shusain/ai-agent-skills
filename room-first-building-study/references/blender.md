# From reviewed SVG to construction assemblies

## Source and execution

Use local Blender scripting for deterministic geometry. Build standalone studies
in a separate background factory-startup process so another active scene is not
reset. Choose a fresh output directory. The recipe was authored on Blender5.0.1;
do not silently install another version/add-on or assume future APIs match.

`family_wing.py` is a reproducible worked recipe gated to the reviewed source
hash. Its roof, transfer beams and fixtures are tied to that house; the other two
SVG schemes have no matching3D recipes. For a new design, use the reviewed project geometry and author a matching recipe.

## Author a project recipe

Keep the project script and outputs outside the skill. Import helpers through
`building_study` with the skill's `scripts/` directory on Python's import path.
Read the actual semantic source and save its SHA-256 with the model.

Use `blender_parts` for rectangle bands, boxes, beams and prisms. Instantiate
`Builder(scene, stages=(...), component_prefix="...")` with a project-specific
ordered tuple of collection names and an ID prefix. Pass a one-based stage
index to the geometry methods. Stage 0 is reserved for reference objects.

Choose assemblies for the building's system and level count. Specify materials,
sections, supports, openings, service space and fit-out in the recipe. Timber
studies can reuse the supplied framing profiles. Steel, masonry and other
systems need their own assembly rules. Verify the saved file against the
project's geometry and component inventory. The bundled readback and takeoff
scripts implement the family-wing contract, so provide project-specific
verification and takeoff where needed.

## Assembly construction

For timber assemblies, use the selected [framing profile](framing.md) for actual
sections, grids and display units. The same reviewed plan can use either profile without scaling its
footprint. Plate/bearing datums and cavity fit follow the selected stock.

Derive exterior layers as bands between footprint insets. This closes convex and
concave corners without overlapping independent strips. Resolve internal core/
lining unions against exterior ownership at T nodes. Merge collinear wall runs
before laying out studs and openings.

Own corner backing before regular studs. Create king/jack studs, sills, headers
and cripples from hosted openings. Resolve blocking after all perpendicular
studs exist; creating it immediately per wall can intersect later studs. Studs/
plates terminate at transfer beams. Cut rough openings through skins, membranes
and insulation too. The example allows50mm rough frame margins around nominal
clear apertures.

Metric example outside-in composition:20mm cladding,25mm rainscreen,2mm membrane,12mm
OSB,140mm timber/insulation,36mm service reservation,15mm lining. Internal150mm
walls use90mm timber,15mm service void and15mm lining each side. US actual stock
fits within those reviewed finished faces with the residual service space
recomputed, rather than enlarging38.1mm stock to45mm. Insulation fills
free bays after timber/openings. These are example inputs, not required styles.

Keep foundations, floor beams/joists/rims/subfloor, walls, stairs, roof structure/
sheathing/covering and finishes separately inspectable. Coordinate upper bearing
lines and stair trimmers. Subtract the source upper void from joists, panels and
the lower ceiling; retain the topmost ceiling. Continue weather skins across
floor edges. Stairs need tread seats/notched stringers, landing supports and
guards outside flight widths.

Roof planes need ridges/valleys and perimeter closure for every mass. Example:
main/cross gable and dining shed. Gable/eave infill uses the same layer domains.
Roof battens follow the pitch so they do not poke through covering. Beam axes
must form a right-handed orthonormal frame; a reflected basis distorts rafters.

Stack wet rooms plausibly; reserve routes when services meshes are outside scope.
Add fixtures/furniture for use review and recheck actual bounds against rooms,
door pads and full swings.

## Ownership, sequence and evidence

Source objects carry `component_id`, `part`, `stage`, `level`, `host`, `assembly`.
In the family-wing example, the same objects reveal through 20 stages using
constant visibility keys. This is
an assembly reveal, not cranes/workers/moving-member animation. Collections also
support manual review. Structural views share objects; cutaways/exploded walls
use presentation copies retaining source identity.

The example has seven scenes: timeline, structural house, two furnished floor cutaways, exploded
wall, stairs, T junction. Complete review frame221; stages start1,11,...191 with
complete marker201. Render native geometry for evidence. Pillow can caption those
renders without replacing them with generated illustrations.

Validate source hash, disjoint layers, hosted holes, wall-frame/beam clashes,
closed positive-volume meshes, finite coordinates and unit scale. Fresh-file
readback independently checks actual floor-sheet extents, unique source IDs and
render/viewport visibility at every stage. Furnished door checks use actual
saved fixture bounds on both sides.

Headroom checks cover full tread/landing rectangles. Oriented roof members use
conservative bounds: report this lower-bound method rather than claiming exact
clearance or code approval. Geometry checks do not establish timber grades,
adequate loads/spans, exhaustive weather/fire detail or a universal clash audit.
Engine export/LOD/collision/runtime integration is separate work when selected.
