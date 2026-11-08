"""Focused ordinary-Python checks for issue890's ignored SVG plan prototype.

Exercises junction areas independently, rejected defective inputs, stable output
ordering and actual SVG geometry readback. Temporary SVGs use a test-owned temp
directory; production assets and Blender are never touched.
"""
from dataclasses import replace
from pathlib import Path
from building_study import RESOURCE_ROOT
import random
import tempfile
import unittest
import xml.etree.ElementTree as ET

from building_study.plan_svg import Wall, load_plan, resolve, svg_bytes, read_svg, NS


class PlanChecks(unittest.TestCase):
    def setUp(self):
        self.floors=load_plan(RESOURCE_ROOT/"assets"/"examples"/"orthogonal-house.json")

    def fixture(self,walls):
        ends={w.point(v) for w in walls for v in (w.lo,w.hi)}
        return resolve(walls,free_ends=ends)

    def test_l_corner_has_exact_area_and_outer_corner(self):
        result=self.fixture([Wall("h","x",0,0,2000,200),Wall("v","y",0,0,2000,200)])
        self.assertEqual(result["area_mm2"],800000)
        self.assertTrue(any(a<=-50<c and b<=-50<d for a,b,c,d in result["rectangles"]))
        self.assertEqual(next(n for n in result["nodes"] if n["point"]==[0,0])["kind"],"L")

    def test_t_join_and_mixed_thickness(self):
        for thickness,area in [(200,1180000),(100,990000)]:
            result=self.fixture([Wall("h","x",0,-2000,2000,200),Wall("v","y",0,0,2000,thickness)])
            self.assertEqual(result["area_mm2"],area)
            self.assertEqual(next(n for n in result["nodes"] if n["point"]==[0,0])["kind"],"T")

    def test_cross_join(self):
        result=self.fixture([Wall("h","x",0,-2000,2000,200),Wall("v","y",0,-2000,2000,200)])
        self.assertEqual(result["area_mm2"],1560000)
        self.assertEqual(next(n for n in result["nodes"] if n["point"]==[0,0])["kind"],"cross")

    def test_disconnected_partition_rejected(self):
        data=self.floors["ground"]
        walls=[replace(w,lo=w.lo+1) if w.id=="study" else w for w in data["walls"]]
        with self.assertRaisesRegex(ValueError,"Disconnected endpoint: study"):
            resolve(walls,data["openings"])

    def test_duplicate_shared_wall_rejected(self):
        data=self.floors["ground"];copy=replace(data["walls"][4],id="duplicate_spine")
        with self.assertRaisesRegex(ValueError,"Duplicate/shared wall overlap"):
            resolve(data["walls"]+[copy],data["openings"])

    def test_original_primary_door_junction_conflict_rejected(self):
        data=self.floors["upper"]
        ops=[o[:2]+[6000,6900]+o[4:] if o[0]=="primary_door" else o for o in data["openings"]]
        with self.assertRaisesRegex(ValueError,"Opening crosses junction: primary_door"):
            resolve(data["walls"],ops)

    def test_original_dressing_t_junction_conflict_rejected(self):
        data=self.floors["upper"]
        ops=[o[:2]+[2200,3100]+o[4:] if o[0]=="primary_inner_door" else o for o in data["openings"]]
        with self.assertRaisesRegex(ValueError,"Opening crosses junction: primary_inner_door"):
            resolve(data["walls"],ops)

    def test_openings_cannot_overlap(self):
        data=self.floors["ground"]
        with self.assertRaisesRegex(ValueError,"Overlapping openings"):
            resolve(data["walls"],data["openings"]+[["bad","spine",1400,2100,"door",0,2100]])

    def test_integer_units_required(self):
        data=self.floors["ground"]
        walls=[replace(w,at=w.at+.001) if w.id=="study" else w for w in data["walls"]]
        with self.assertRaisesRegex(ValueError,"integer millimetres"):
            resolve(walls,data["openings"])

    def test_plan_bounds_and_order_independence(self):
        for floor,data in self.floors.items():
            result=resolve(data["walls"],data["openings"])
            self.assertTrue(all(0<=a<c<=10000 and 0<=b<d<=12000 for a,b,c,d in result["rectangles"]))
            expected=svg_bytes(floor,data,result)
            for seed in range(8):
                randomizer=random.Random(seed);walls=list(data["walls"]);ops=list(data["openings"])
                randomizer.shuffle(walls);randomizer.shuffle(ops)
                actual=resolve(walls,ops)
                self.assertEqual(actual,result)
                reordered=dict(data,walls=walls,openings=ops)
                self.assertEqual(svg_bytes(floor,reordered,actual),expected)

    def test_svg_roundtrip_and_stale_fill_rejection(self):
        for floor,data in self.floors.items():
            result=resolve(data["walls"],data["openings"])
            with tempfile.TemporaryDirectory(prefix="city-plan890-") as folder:
                path=Path(folder)/"plan.svg";path.write_bytes(svg_bytes(floor,data,result))
                self.assertEqual(read_svg(path),result)
                root=ET.parse(path);rect=root.find(f".//*[@id='resolved-footprint']/{{{NS}}}rect")
                rect.set("width",str(int(rect.get("width"))+1));root.write(path)
                with self.assertRaisesRegex(ValueError,"footprint is stale"):
                    read_svg(path)

    def test_svg_source_layer_transform_is_rejected(self):
        data=self.floors["ground"];result=resolve(data["walls"],data["openings"])
        with tempfile.TemporaryDirectory(prefix="city-plan890-") as folder:
            path=Path(folder)/"plan.svg";path.write_bytes(svg_bytes("ground",data,result))
            root=ET.parse(path);group=root.find(".//*[@id='wall-network']")
            group.set("transform","translate(1 0)");root.write(path)
            with self.assertRaisesRegex(ValueError,"Unsupported SVG source structure/transform"):
                read_svg(path)


if __name__=="__main__":unittest.main(verbosity=2)
