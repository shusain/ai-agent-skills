# US/imperial or metric framing

Choose stock/spacing independently of internal coordinates, display units and
cost currency. Inherit a stated user preference. When genuinely unspecified,
establish it once rather than defaulting every new design to metric. Plan the
room relationships while clarifying; do not repeatedly ask after a selection.

## Supplied profiles

| Input | US (`us`) | Metric (`metric`) |
| --- | --- | --- |
| Interior studs/plates | Nominal2×4; actual1½×3½in (38.1×88.9mm) | Actual45×90mm |
| Exterior studs/plates | Nominal2×6; actual1½×5½in (38.1×139.7mm) | Actual45×140mm |
| Default stud grid |16in O.C. (406.4mm) |600mm O.C. |
| Default floor-joist grid |16in O.C. |400mm O.C. |
| Default rafter grid |24in O.C. (609.6mm) |600mm O.C. |
| Main rafters |2×10 actual38.1×234.95mm |45×220mm |
| Ceiling/collar ties |2×8 /2×6 actual sections |45×195 /45×145mm |
| Floor I-joists |9½in deep;2½in flanges,1½in flange thickness,⅜in web |245mm deep;63×38mm flanges,9mm web |
| Headers / transfer beams |9½in LVL depth;3½/5¼in multi-ply widths |240mm depth;90/140mm widths |
| Heavy bearers/ridges |5¼×11⅞in multi-ply LVL |134×300 bearer /140×300 ridge |
| Stair stringer blanks / posts |2×12 actual section /4×4 actual3½in square |45×245 /90mm square |

These are schematic profile inputs, not a grade/span/connection approval. US
nominal sizes must not be converted as full2×4in geometry. Engineered products
have their own actual dimensions; a9½in I-joist is not a solid2×10.

Stock references: [American Wood Council actual-size guidance](https://awc.org/faq/how-do-i-convert-to-metric-lumber-sizes/)
and [AWC lumber studs](https://awc.org/resources/wood-products/wall/lumber-studs/).
Spacing options are available design inputs; suitability depends on loads,
sheathing, grade, height and the chosen structural system.

## Selection and adaptation

```python
from building_study.framing import profile,feet_inches_mm,stations
p = profile('us', stud_spacing=16, joist_spacing='19.2', rafter_spacing=24)
cut_length_mm = float(feet_inches_mm(8))
stud_dimensions_m = (p.stud_mm/1000, p.interior_depth_mm/1000, cut_length_mm/1000)
grid_mm = list(stations(0, 12000, p.stud_spacing_mm))
```

For other member roles, `us_lumber('2x8')` returns actual38.1×184.15mm;
the supplied lookup covers1×2,2×4/6/8/10/12 and4×4. Use the actual section in
new recipes rather than multiplying nominal labels by25.4. Engineered LVL and
I-joists use their explicitly declared actual product dimensions.

Spacing overrides use **inches for US**, **mm for metric**. Supported US stud/
rafter spacings are12/16/24in, and joists additionally support19.2in. Metric
supports300/400/450/600mm. The CLI rejects mixed inputs such as `us` with a stud
spacing of600. Add a new documented profile when other stock systems are needed;
do not guess that every country uses the supplied45mm metric stock.

`inches_mm` and `feet_inches_mm` retain exact Fraction values; `stations` does not
accumulate floating-point drift. The Blender arrangement uses integer ticks at
0.0001mm before conversion to metres, preserving38.1,88.9,406.4 and487.68mm.
The older integer-mm SVG room contract is separate. For imperial room briefs,
report feet/inches to the user, convert datums explicitly and disclose any plan-
datum rounding; do not round framing to whole millimetres. Extending SVG plan
precision is separate from selecting lumber/spacing.

The bundled house keeps its reviewed room footprint, storey heights, openings,
stair and finish layers in either profile. Profile selection changes timber,
grids, joist/rim/header dimensions, bearings, plate datums and service-cavity fit;
it does not scale the building or claim an all-US material catalog. Custom cut
lengths still need stock-length/cut optimization for purchasing.

New recipes should consume this profile for members and grids rather than copy
metric constants from an example. Store `framing_profile_json` on the source
scene. All review scenes should use matching display units. Receipts/takeoffs
carry actual stock dimensions and selected spacings. Fresh native checks measure
full stock widths/depths and actual grid centres; corner-cut fragments are
distinguished from full-width stock. I-joists must not be emitted as narrow ripped
slivers when opening/rim clipping removes part of their flange width.

The example's measurable-grid objects carry `framing_grid_role` (`wall-stud`,
`floor-joist`, `roof-rafter`), `grid_station_mm`, `grid_axis` and optionally
`grid_origin_mm`. Preserve those tags when reusing its native metrology checker;
record corner/junction backing separately from regular grid members.

Native files generated before profile metadata was added remain viewable, but
the current takeoff/readback requires an explicit recorded profile: regenerate
with the chosen system instead of guessing from display units.
