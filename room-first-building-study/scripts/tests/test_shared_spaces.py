"""Focused issue890 shared-space tests; ordinary Python, no engine dependencies.

Checks geometry/coverage independently of SVG export, transactional mutations,
seed/order reproducibility, courtyard holes, exact junction coverage, room access
and rejection of corrupted SVG inputs. Only test-owned temporary files are used.
"""
from copy import deepcopy
from pathlib import Path
from building_study import RESOURCE_ROOT
import tempfile
import unittest
import xml.etree.ElementTree as ET

from building_study.plan_svg import NS,union_rectangles
from building_study.shared_spaces import (Partition,area,boundaries,compile_layout,components,
                           configurations,export_svg,generate,loops,read_svg,
                           validate_access,validate_partition,wall_bands)


def inside(rects,x,y):return any(a<x<c and b<y<d for a,b,c,d in rects)


class SharedSpaceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs=configurations();cls.models=[generate(c) for c in cls.configs]

    def test_exact_arbitrary_mm_split_and_shared_edge(self):
        part=Partition([(0,0,10000,10000)])
        part.split("root","x",3333,"first")
        self.assertEqual(sorted(area(r) for r in part.spaces.values()),[33330000,66670000])
        edges=[e for e in boundaries(part.spaces) if not e.exterior]
        self.assertEqual(len(edges),1)
        self.assertEqual((edges[0].axis,edges[0].at,edges[0].lo,edges[0].hi),("y",3333,0,10000))

    def test_rejected_split_is_transactional(self):
        part=Partition([(0,0,10000,10000)]);before=deepcopy(part.spaces)
        with self.assertRaisesRegex(ValueError,"intersect space interior"):part.split("root","x",0,"bad")
        self.assertEqual(part.spaces,before)
        with self.assertRaisesRegex(ValueError,"Integer orthogonal"):part.split("root","x",3333.5,"bad")
        self.assertEqual(part.spaces,before)

    def test_unassigned_strip_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unassigned"):
            validate_partition([(0,0,10000,10000)],{"left":[(0,0,4999,10000)],"right":[(5000,0,10000,10000)]})

    def test_overlapping_room_interiors_rejected(self):
        with self.assertRaisesRegex(ValueError,"overlap"):
            validate_partition([(0,0,10000,10000)],{"left":[(0,0,5001,10000)],"right":[(5000,0,10000,10000)]})

    def test_corner_contact_does_not_join_rooms(self):
        self.assertEqual(len(components([(0,0,1000,1000),(1000,1000,2000,2000)])),2)

    def test_twelve_complete_footprints_and_exact_area_accounting(self):
        self.assertEqual(len(self.models),12)
        expected={"rectangle":168000000,"l-shape":182000000,"courtyard":263000000}
        for m in self.models:
            with self.subTest(layout=m["id"]):
                validate_partition(m["footprint"],m["spaces"])
                if m["family"] in expected:self.assertEqual(area(m["footprint"]),expected[m["family"]])
                else:self.assertIn(area(m["footprint"]),(204000000,210000000))
                closed=union_rectangles(wall_bands(m["edges"]),footprint=m["footprint"])
                self.assertEqual(area(closed)+sum(area(r) for r in m["clear"].values()),area(m["footprint"]))
                self.assertEqual(area(union_rectangles(m["walls"],footprint=m["footprint"])),area(m["walls"]))

    def test_every_shared_boundary_owned_once_and_room_rings_close(self):
        for m in self.models:
            ids=[e.id for e in m["edges"]];self.assertEqual(len(ids),len(set(ids)))
            for sid in m["spaces"]:
                rings=loops(m["edges"],sid);self.assertTrue(rings)
                self.assertTrue(all(len(r)>=4 for r in rings))
            for e in m["edges"]:
                self.assertNotEqual(e.negative,e.positive)
                self.assertTrue(e.negative in m["spaces"] or e.positive in m["spaces"])

    def test_node_neighbourhood_covered_at_all_wall_junctions(self):
        for m in self.models:
            closed=union_rectangles(wall_bands(m["edges"]),footprint=m["footprint"])
            for p in {p for e in m["edges"] for p in (e.point(e.lo),e.point(e.hi))}:
                for dx,dy in ((-1,-1),(-1,1),(1,-1),(1,1)):
                    x,y=p[0]+dx,p[1]+dy
                    if inside(m["footprint"],x,y):self.assertTrue(inside(closed,x,y),(m["id"],p,dx,dy))

    def test_courtyard_hole_and_u_garden_are_preserved(self):
        for m in self.models:
            if m["family"] in ("courtyard","u-shape"):
                point=(9000,8000) if m["family"]=="courtyard" else (9000,11000)
                self.assertFalse(inside(m["footprint"],*point));self.assertFalse(inside(m["walls"],*point))
            if m["family"]=="courtyard":self.assertEqual(len(loops(m["edges"])),2)

    def test_door_access_and_junction_clearances(self):
        for m in self.models:
            validate_access(m);edges={e.id:e for e in m["edges"]}
            for op in m["openings"]:
                e=edges[op["host"]]
                self.assertGreaterEqual(op["lo"]-e.lo,350);self.assertGreaterEqual(e.hi-op["hi"],350)
            bad=dict(m,openings=[o for o in m["openings"] if o["kind"]!="entry"])
            with self.assertRaisesRegex(ValueError,"no entrance route"):validate_access(bad)

    def test_missing_room_door_and_corner_opening_rejected(self):
        m=self.models[0];ops=deepcopy(m["openings"])
        sid=next(o["space"] for o in ops if o["kind"]=="door")
        with self.assertRaisesRegex(ValueError,"no entrance route"):
            compile_layout(m,[o for o in ops if not(o["kind"]=="door" and o["space"]==sid)])
        e={e.id:e for e in m["edges"]};door=next(o for o in ops if o["kind"]=="door");door["lo"]=e[door["host"]].lo
        with self.assertRaisesRegex(ValueError,"junction clearance"):compile_layout(m,ops)

    def test_seed_repeats_and_space_order_is_irrelevant(self):
        for config,m in zip(self.configs,self.models):
            self.assertEqual(export_svg(generate(config)),export_svg(m))
            reordered=dict(m,spaces=dict(reversed(list(m["spaces"].items()))))
            self.assertEqual(export_svg(compile_layout(reordered)),export_svg(m))
        for family in ("rectangle","l-shape","u-shape","courtyard"):
            shapes=[export_svg(m) for m in self.models if m["family"]==family]
            self.assertEqual(len(set(shapes)),3)

    def test_infeasible_room_count_returns_failure(self):
        config=dict(self.configs[0],target_rooms=100)
        with self.assertRaisesRegex(ValueError,"Cannot meet room count"):generate(config)

    def test_svg_source_roundtrip_and_stale_derived_walls(self):
        with tempfile.TemporaryDirectory(prefix="shared890-") as folder:
            for m in self.models:
                path=Path(folder)/(m["id"]+".svg");path.write_bytes(export_svg(m));actual=read_svg(path)
                self.assertEqual(actual["spaces"],m["spaces"]);self.assertEqual(actual["walls"],m["walls"])
            tree=ET.parse(path);rect=tree.find(f".//*[@id='wall-cells']/{{{NS}}}rect")
            rect.set("width",str(int(rect.get("width"))+1));tree.write(path)
            with self.assertRaisesRegex(ValueError,"wall footprint is stale"):read_svg(path)

    def test_transformed_space_source_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="shared890-") as folder:
            path=Path(folder)/"bad.svg";path.write_bytes(export_svg(self.models[0]))
            tree=ET.parse(path);tree.find(".//*[@id='spaces-source']").set("transform","translate(1 0)");tree.write(path)
            with self.assertRaisesRegex(ValueError,"source layer transform"):read_svg(path)

    def test_high_window_preserves_wall_below_its_sill(self):
        m=self.models[0];ops=deepcopy(m["openings"])
        window=next(o for o in ops if o["kind"]=="window");window["sill_mm"]=1400;window["height_mm"]=700
        updated=compile_layout(m,ops)
        self.assertEqual(area(updated["walls"])-area(m["walls"]),1400*250)


if __name__=="__main__":unittest.main(verbosity=2)
