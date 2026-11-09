# Room program, geometry and SVG review

## Room-first decisions

Record the intended use, level count, site constraints and construction
system. For timber projects, carry the user's US/imperial or metric preference
into the brief and use [framing.md](framing.md) for actual stock dimensions.
Room-plan coordinates and the construction standard are separate choices.

Establish room purpose, floor, useful clear-area range and a rectangular use/fit
template before positioning. Specify adjacency, door/open connections, private
rooms that must not serve as routes, entry orientation, circulation roles, stairs
and wet/service relationships. Derive the exterior union after room placement.
Foyer, halls and landings are designed spaces rather than leftover gaps. Open
living/kitchen/dining use zones may share one enclosure without walls on virtual
boundaries.

## Author a new building

1. Define a project program with stable space and level IDs, functional fit
   templates and relationships. For example, a workshop might need a delivery
   route between receiving and parts storage, and independent staff access to
   the repair bay. Derive the footprint from the union of the placed spaces.
2. For axis-aligned plans, use `plan_svg.union_rectangles` for envelope and
   material domains, and `shared_spaces.boundaries` for shared-edge ownership.
   Declare wall thickness and opening rules for the project. Use
   `clearance_geometry` with project dimensions to check fit, walking regions,
   door pads and swings. Check relationships and routes across levels where
   applicable.
3. Export dimensioned, comparable SVGs with semantic source geometry and
   separate derived graphics. Use a reader that reconstructs and validates the
   geometry consumed by modeling. For a custom schema, author the reader
   and validate source/derived consistency before building.
4. Carry the selected SVG and its source hash into a matching
   [Blender recipe](blender.md#author-a-project-recipe).

The low-level geometry functions accept project-authored space IDs and
coordinates. The higher-level single-floor compiler in `shared_spaces` carries
fallback defaults for wall thickness, room size and door types. Use it only
where those assumptions fit. For angled or curved walls, supply geometry and
validation that represent those shapes.

## Included house program

The example brief is `assets/examples/two-storey-program.json`. The three recipes
in `building_study.room_first_house.schemes` place named modules with anchor
annotations; they are not an adjacency optimizer. Adjust or author a recipe when
another brief does not fit. Do not relax requirements merely to make it pass.
The current U-stair supports the reviewed3m rise,18 equal risers,1200mm flights,
280mm going,1250mm turn landing and3100×4000mm aligned shaft. Other dimensions
need a revised module and checks.

## Deterministic geometry

- `plan_svg.union_rectangles` is an exact arrangement of integer-mm rectangles
  with footprint clipping and exclusions. It yields disjoint material cells,
  not a raster approximation.
- `shared_spaces.boundaries` derives each shared edge once, with its two space
  owners. Constant wall thickness and inward exterior bands resolve boundaries;
  stable sorting makes output independent of input order.
- `clearance_geometry.rectangle_centres` / `erode_square` compute feasible centres
  of a moving rectangle/square. Positive-area connectivity excludes corner-only
  paths. A large room can still contain a narrow finger or disconnected walking
  centres. `open_square` exposes/removes such fingers.
- Functional fit must check feasible template positions directly. The single
  largest-area rectangle or bounding box may give a wrong answer in an L room.
- An opening owns a host edge, interval, served space, sill/head and hinge.
  `landing` checks pads; `sweep_fits` checks the full ideal90-degree sector with
  margin. An open portal has no leaf. Example1200mm/50mm thresholds are study
  inputs, not universal code/accessibility rules.

## Repairs and explicit fallback

`shared_spaces.repair_spaces` transactionally transfers narrow appendages to a
neighbor. Accept only repairs retaining room names/identity, exact disjoint
coverage, connectivity, access and door usability. Preserve useful L-shaped rooms;
cosmetic overlap is not a wall-gap repair.

The fallback generates three variants each of rectangle, L, U and courtyard
footprints. Four frozen pre-repair cases in `assets/regressions` reproduce50mm/
600mm slivers and doorway failures. Its twelve SVG hashes remain regression
evidence even when room-first design is preferred.

## Worked-example SVG contract

In `room_first_house`, `read_floor/read_house` reconstruct actual named rectangles and revalidate the
program, envelope, walls, openings and stair data. Paired SVGs contain two semantic
floor trees; the reader restores child IDs. Important groups: `spaces-source`,
`footprint-source`, `shared-boundaries`, `opening-source`, `wall-cells`,
`wall-footprint`, `stair-geometry`. Units are mm; world Y points garden/north.
One outer transform maps to SVG screen coordinates. Arbitrary nested editor
transforms, stale paths and mismatched floor elevations are rejected.

Consume this source instead of tracing screenshots. Bundled family-wing.svg is
the exact reviewed paired source, SHA256
`2f6067344754366695999646d7cb69a890d11d81855b63d61360ea98f313827a`.

Review alternatives at common scale/orientation with dimensions, names, doors/
swings, circulation, stairs/openings and optional clearance overlays. Continue
from an already selected scheme. Input checks do not establish load paths,
physical stair headroom or fully furnished navigation.
