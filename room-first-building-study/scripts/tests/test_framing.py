"""Stock, native-unit spacing and exact conversion regressions; no Blender."""
import unittest
from fractions import Fraction
from building_study.framing import profile,inches_mm,feet_inches_mm,stations,from_dict,us_lumber

class FramingChecks(unittest.TestCase):
    def test_us_actual_stock_is_not_nominal_or_metric_substitution(self):
        p=profile('us')
        self.assertEqual((p.stud_mm,p.interior_depth_mm,p.exterior_depth_mm),(38.1,88.9,139.7))
        self.assertEqual((p.rafter_depth_mm,p.tie_depth_mm,p.stringer_depth_mm),(234.95,184.15,285.75))
        self.assertEqual((p.header_depth_mm,p.exterior_header_width_mm),(241.3,133.35))
        self.assertEqual(p.stock_labels,{'interior':'2x4','exterior':'2x6'})
    def test_metric_stock_and_grids(self):
        p=profile('metric')
        self.assertEqual((p.stud_mm,p.interior_depth_mm,p.exterior_depth_mm),(45,90,140))
        self.assertEqual((p.stud_spacing_mm,p.joist_spacing_mm,p.rafter_spacing_mm),(600,400,600))
    def test_us_stock_lookup_supports_new_recipes(self):
        self.assertEqual(us_lumber('2x8'),(38.1,184.15))
        self.assertEqual(us_lumber('4x4'),(88.9,88.9))
        with self.assertRaises(ValueError):us_lumber('2x5')
    def test_us_default_and_optional_spacings(self):
        p=profile('us');self.assertEqual((p.stud_spacing_mm,p.joist_spacing_mm,p.rafter_spacing_mm),(406.4,406.4,609.6))
        p=profile('us',stud_spacing='24',joist_spacing='19.2',rafter_spacing='16')
        self.assertEqual((p.stud_spacing_mm,p.joist_spacing_mm,p.rafter_spacing_mm),(609.6,487.68,406.4))
    def test_metric_overrides_are_mm(self):
        p=profile('metric',stud_spacing='400',joist_spacing='450',rafter_spacing='600')
        self.assertEqual((p.stud_spacing_mm,p.joist_spacing_mm,p.rafter_spacing_mm),(400,450,600))
    def test_reject_mixed_unit_or_unrecognized_profile_inputs(self):
        for system,kw in [('us',{'stud_spacing':600}),('metric',{'stud_spacing':16}),('us',{'stud_spacing':0}),('imperial',{})]:
            with self.assertRaises(ValueError):profile(system,**kw)
    def test_fractional_inch_inputs_are_exact(self):
        self.assertEqual(inches_mm('1/16'),Fraction(127,80))
        self.assertEqual(feet_inches_mm(8,'1/2'),Fraction('2451.1'))
    def test_grid_has_no_accumulating_rounding_or_whole_mm_quantization(self):
        g=list(stations(0,40640.1,406.4))
        self.assertEqual(len(g),101);self.assertEqual(g[-1],40640)
        self.assertEqual(g[:4],[0,406.4,812.8,1219.2])
        self.assertEqual(list(stations(-250,1000,609.6,origin=-250)),[-250,359.6,969.2])
    def test_profile_roundtrip_retains_actual_dimensions(self):
        p=profile('us',stud_spacing=24)
        self.assertEqual(from_dict(p.to_dict()),p)
    def test_floor_and_plate_datums_follow_stock_depth(self):
        for system in ('metric','us'):
            p=profile(system)
            self.assertAlmostEqual(p.wall_top_m+p.joist_depth_mm/1000+.047,3)
            self.assertAlmostEqual(p.stud_top_m+2*p.stud_mm/1000,p.wall_top_m)

if __name__=='__main__':unittest.main()
