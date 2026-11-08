"""Issue890 clearance regressions; ordinary Python, no engine or scene writes.

Frozen JSON fixtures identify the four published generation-v3 layouts with
unusable appendages. Tests exercise exact morphology, connected square routes,
transactional wall-collapse repairs, full swept doors and native SVG policy.
"""
from copy import deepcopy
import json
from pathlib import Path
from building_study import RESOURCE_ROOT
import tempfile
import unittest
import xml.etree.ElementTree as ET

from building_study.clearance_geometry import erode_square,open_square,rectangle_fits,landing,sweep_fits
from building_study.plan_svg import NS,union_rectangles
from building_study.shared_spaces import (Boundary,area,boundaries,clear_geometry,compile_layout,
    components,configurations,door_clear,export_svg,generate,read_svg,repair_spaces,
    validate_partition,walk_report)


class ClearanceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=RESOURCE_ROOT/"assets"/"regressions"
        cls.old={name:json.loads((root/(name+".json")).read_text(encoding="utf-8")) for name in ("courtyard-1","courtyard-2","u-shape-1","u-shape-3")}
        cls.models={m["id"]:m for m in (generate(c) for c in configurations())}

    def test_exact_rectangle_erosion_and_opening(self):
        region=[(0,0,4000,5000)]
        self.assertEqual(erode_square(region,1200),[(600,600,3400,4400)])
        self.assertEqual(open_square(region,1200),region)

    def test_usable_l_shape_is_not_flattened(self):
        region=union_rectangles([(0,0,6000,2000),(0,2000,2000,6000)])
        self.assertEqual(open_square(region,1200),region)
        self.assertEqual(len(components(erode_square(region,1200))),1)

    def test_narrow_finger_removed_by_exact_width_not_room_area(self):
        region=[(0,0,4000,4000),(4000,0,7000,600)]
        self.assertEqual(open_square(region,1200),[(0,0,4000,4000)])
        self.assertEqual(area(union_rectangles(region,exclusions=open_square(region,1200))),1800000)

    def test_connected_floor_can_have_disconnected_walking_centres(self):
        region=[(0,0,4000,4000),(4000,1500,6000,2500),(6000,0,10000,4000)]
        self.assertEqual(len(components(region)),1)
        self.assertEqual(walk_report({"room":region})["room"]["core_components"],2)

    def test_reported_fifty_and_six_hundred_mm_cases_rejected(self):
        for name,span in (("courtyard-2",50),("u-shape-1",600)):
            old=self.old[name];_,_,clear=clear_geometry(old)
            bad=walk_report(clear)["room_05"]["narrow"]
            self.assertEqual(min(min(c-a,d-b) for a,b,c,d in bad),span)
            with self.assertRaisesRegex(ValueError,"Minimum walk width failed: room_05"):
                compile_layout(old)

    def test_four_repairs_preserve_coverage_and_room_identity(self):
        for name,old in self.old.items():
            model=self.models[name];self.assertEqual(len(model["repairs"]),1)
            self.assertEqual(set(model["spaces"]),set(old["spaces"]))
            self.assertEqual(model["names"],old["names"])
            self.assertEqual(area(model["footprint"]),area(old["footprint"]))
            validate_partition(model["footprint"],model["spaces"])
            event=model["repairs"][0]
            self.assertEqual(event["to_space"],"hall")
            self.assertGreater(event["narrow_before_mm2"],event["narrow_after_mm2"])
            self.assertEqual(event["narrow_after_mm2"],0)

    def test_regularisation_is_repeatable_idempotent_and_preserves_input(self):
        old=self.old["u-shape-1"];before=deepcopy(old)
        a=repair_spaces(old);b=repair_spaces(old)
        self.assertEqual(a,b);self.assertEqual(old,before)
        self.assertEqual(repair_spaces(a),a)

    def test_all_published_regions_and_doors_have_clearance(self):
        changed={name for name,m in self.models.items() if m["repairs"]}
        self.assertEqual(changed,set(self.old))
        for model in self.models.values():
            for report in walk_report(model["clear"]).values():
                self.assertFalse(report["narrow"]);self.assertEqual(report["core_components"],1)
            edges={e.id:e for e in model["edges"]}
            for op in model["openings"]:
                if op["kind"]!="window":self.assertTrue(door_clear(edges[op["host"]],op,model["clear"]))

    def test_reported_u_door_blocked_and_relocated_to_main_room(self):
        old=self.old["u-shape-1"];edges,_,clear=clear_geometry(old)
        door=next(o for o in old["openings"] if o["id"]=="door_room_05");door=dict(door,hinge="low")
        self.assertFalse(door_clear(next(e for e in edges if e.id==door["host"]),door,clear))
        new=self.models[old["id"]];updated=next(o for o in new["openings"] if o["id"]==door["id"])
        host=next(e for e in new["edges"] if e.id==updated["host"])
        self.assertEqual(host.axis,"y");self.assertNotEqual(host.id,door["host"])
        self.assertTrue(door_clear(host,updated,new["clear"]))

    def test_swept_leaf_catches_mid_angle_obstacle(self):
        edge=Boundary("test","x",0,0,3000,"hall","room")
        op=dict(lo=1000,hi=1900,space="room",hinge="low")
        region=union_rectangles([(0,75,3000,3000)],exclusions=[(1600,675,1650,725)])
        self.assertFalse(sweep_fits(edge,op,region))
        self.assertTrue(rectangle_fits((1000,75,1900,76),region))
        self.assertTrue(rectangle_fits((1000,75,1001,975),region))

    def test_sector_not_conservative_bounding_box(self):
        edge=Boundary("test","x",0,0,3000,"hall","room")
        op=dict(lo=1000,hi=1900,space="room",hinge="low")
        region=union_rectangles([(0,75,3000,3000)],exclusions=[(1900,975,1950,1025)])
        self.assertTrue(sweep_fits(edge,op,region))

    def test_opposite_hinge_can_avoid_obstacle(self):
        edge=Boundary("test","x",0,0,3000,"hall","room")
        op=dict(lo=1000,hi=1900,space="room",hinge="low")
        region=union_rectangles([(0,75,3000,3000)],exclusions=[(1050,975,1100,1025)])
        self.assertFalse(sweep_fits(edge,op,region))
        self.assertTrue(sweep_fits(edge,dict(op,hinge="high"),region))

    def test_svg_policy_and_hinge_are_real_inputs(self):
        with tempfile.TemporaryDirectory(prefix="clearance890-") as folder:
            path=Path(folder)/"plan.svg";path.write_bytes(export_svg(self.models["rectangle-1"]))
            model=read_svg(path);self.assertEqual(model["min_walk_mm"],1200)
            self.assertTrue(all(o.get("hinge") in ("low","high") for o in model["openings"] if o["kind"]!="window"))
            tree=ET.parse(path)
            door=next(n for n in tree.findall(f".//*[@id='opening-source']/{{{NS}}}line") if n.get("data-kind")=="door")
            door.set("data-hinge","middle");tree.write(path)
            with self.assertRaisesRegex(ValueError,"hinge must be explicit"):read_svg(path)


if __name__=="__main__":unittest.main(verbosity=2)
