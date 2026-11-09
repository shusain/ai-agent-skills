# Material quantities and optional budgets

For each project, inventory the original construction components by stable ID,
stage, material and assembly. Define which geometry to count and the appropriate
measurement basis for each category, such as area, volume, length or count.
Track the source/model hashes with the quantities and exclude presentation
copies. Use a project-specific reader and category mapping.

The example takeoff reads the family-wing SVG and the original
`01 | Construction timeline` scene. It leaves the native model file intact.

`takeoff_blender.py` writes all-part CSV and grouped JSON. It measures positive
mesh volume in metres with unit scale; arbitrary open shells need another method.
Concrete uses3D rectangle-union volume to remove pad/strip overlaps. Roof sheets
use actual sloped area. Price I-joists once as complete assemblies, not as two
flanges and a separately purchased web.

Wall stock equivalents use the actual selected profile's cross-section:
US38.1×88.9/139.7mm or metric45×90/140mm. The native profile is authoritative;
do not infer it from unit display. JSON reports stable `exterior`/`interior`
equivalent groups plus nominal/actual stock metadata and linear feet/metres.
Component CSV includes actual local dimensions in metres and inches; JSON also
provides timber cubic feet and concrete cubic yards alongside SI quantities.
Rips, union
cells and beam-clipped studs are geometric segments, not purchased boards. Roof
joints are not shop-cut boolean joints. A purchasing list also needs available
lengths, grades, splices, offcut reuse and waste; stringer blanks exceed the net
notched solids. Do not call the measurements an order-ready schedule.

Keep measured quantity, unit, waste, budget quantity, rate range, source and
subtotal separate. The price CLI requires explicit rate-scenario JSON.
`assets/examples/usd-rates-2026-11-02.json` is a historical illustrative snapshot,
not a current price feed. For fresh costs, establish market/currency assumptions,
verify current supplier prices and save a new dated scenario outside the skill.

Each `items` key names a row in `price_budget.py`, with `unit_low_usd`,
`unit_high_usd`, `waste_percent`, `basis`. US lumber prices are adjusted by volume
for the selected actual section (including the thicker metric profile when
selected); this is not a substitution
schedule. The supplied calculator is USD-specific: change conversion/rates/
labels together for another currency. Sources are `[title,url,note]` records.

Reconcile subtotals; mark allowance-only connectors, reinforcement, membranes and
finishes when no detailed schedule exists. Materials are not installed costs.
State exclusions such as labor, taxes, transport/sitework/equipment, engineering/
permits, services, cabinetry, fixtures/furniture and unmodeled assemblies. Costs
do not establish that conceptual long roof members are buildable as drawn.

Stage IDs permit resource demand per construction phase. Simulation-catalog
integration remains a separate selection; takeoff alone does not select gameplay
or production-catalog changes.
