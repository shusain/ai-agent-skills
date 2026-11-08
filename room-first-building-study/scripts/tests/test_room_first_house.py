"""Issue890 room-first house checks; ordinary Python, no engine/production writes.

Validates named room briefs, private/public routes, real template fit, paired-floor
stair reservations/wet stacking, SVG source readback and unchanged fallback bytes.
SVG corruption cases write only test-owned temporary files.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from building_study import RESOURCE_ROOT
import tempfile
import unittest
import xml.etree.ElementTree as ET

from building_study.clearance_geometry import rectangle_centres,rectangle_fits
from building_study.plan_svg import NS,union_rectangles
from building_study.room_first_house import (build,derive_floor,export_floor,load_program,paired_svg,
    read_floor,read_house,rule_for,schemes,validate_house,validate_relationships)
from building_study.shared_spaces import area,configurations,export_svg,generate,largest_rectangle


class RoomFirstChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program=load_program();cls.houses=build(cls.program)

    def test_same_named_program_before_geometry_on_all_three_schemes(self):
        self.assertEqual(len(self.houses),3)
        for house in self.houses:
            for floor,model in house['floors'].items():
                expected={s for s,r in self.program['rooms'].items() if r['floor']==floor}
                self.assertTrue(expected<=set(model['spaces']))
                for sid in expected:self.assertEqual(model['names'][sid],self.program['rooms'][sid]['name'])
            self.assertTrue({'primary','bed2','bed3'}<=set(house['floors']['upper']['spaces']))

    def test_all_rooms_within_program_area_and_functional_fit(self):
        for house in self.houses:
            for floor,model in house['floors'].items():
                for sid,r in model['clear'].items():
                    rule=rule_for(self.program,sid)
                    if rule['role']=='stair':continue
                    self.assertGreaterEqual(area(r)/1e6,rule['area_m2'][0]);self.assertLessEqual(area(r)/1e6,rule['area_m2'][1])
                    w,d=rule['fit_mm'];self.assertTrue(rectangle_centres(r,w,d) or rectangle_centres(r,d,w))

    def test_fit_is_not_mistaken_for_largest_area_rectangle(self):
        room=self.houses[0]['floors']['upper']['clear']['primary'];r=largest_rectangle(room)
        self.assertLess(min(r[2]-r[0],r[3]-r[1]),3200)
        self.assertTrue(rectangle_centres(room,3600,3200))

    def test_program_changes_reject_unsatisfied_brief(self):
        program=deepcopy(self.program);program['rooms']['study']['area_m2']=[50,60]
        with self.assertRaisesRegex(ValueError,'Room program area'):build(program)

    def test_missing_room_is_not_relabelled_from_another_space(self):
        scheme=schemes(self.program)[0];scheme['ground'].spaces.pop('study')
        with self.assertRaisesRegex(ValueError,'Missing programmed rooms'):derive_floor(self.program,scheme,'ground')

    def test_open_family_zones_share_enclosure_without_internal_walls(self):
        for house in self.houses:
            m=house['floors']['ground'];family={m['enclosure'][s] for s in ('living','dining','kitchen')}
            self.assertEqual(len(family),1)
            for e in m['physical_edges']:
                if not e.exterior:self.assertNotEqual(m['enclosure'][e.negative],m['enclosure'][e.positive])

    def test_bedrooms_cannot_be_routes_to_other_bedrooms(self):
        model=deepcopy(self.houses[0]['floors']['upper'])
        for c in model['connections']:
            if c['b']=='bed3':c['a']='primary'
        with self.assertRaisesRegex(ValueError,'private room|circulation access'):validate_relationships(model)

    def test_aligned_stair_eighteen_equal_rises_and_real_pads(self):
        for house in self.houses:
            st=house['stair'];heights=[Fraction(t['z_mm']) for t in sorted(st['treads'],key=lambda t:t['rise'])]
            self.assertEqual(len(heights),18);self.assertEqual(heights[-1],3000)
            self.assertEqual(set(b-a for a,b in zip([Fraction(0)]+heights[:-1],heights)),{Fraction(500,3)})
            self.assertEqual(st['flight_clear_mm'],1200);self.assertEqual(st['mid_landing_depth_mm'],1250)
            for floor,pad in (('ground',st['lower_pad']),('upper',st['upper_pad'])):
                m=house['floors'][floor]
                circulation=union_rectangles([r for sid,rs in m['clear'].items() if rule_for(self.program,sid)['role']=='circulation' for r in rs])
                self.assertTrue(rectangle_fits(pad,circulation))
                self.assertEqual(union_rectangles(m['spaces']['stair']),[st['shaft']])

    def test_upper_projection_and_wet_stack_are_real_geometry(self):
        for house in self.houses:
            g,u=house['floors']['ground'],house['floors']['upper']
            self.assertFalse(union_rectangles(u['footprint'],exclusions=g['footprint']))
            wet=union_rectangles([r for s in ('kitchen','utility','wc') for r in g['spaces'][s]])
            self.assertEqual(area(union_rectangles(u['spaces']['bath'],footprint=wet)),area(u['spaces']['bath']))

    def test_misaligned_stair_is_rejected(self):
        house=deepcopy(self.houses[0]);r=house['floors']['upper']['spaces']['stair'][0]
        house['floors']['upper']['spaces']['stair']=[(r[0]+100,r[1],r[2]+100,r[3])]
        with self.assertRaisesRegex(ValueError,'shaft does not match'):validate_house(self.program,house['scheme'],house['floors'])

    def test_site_and_supported_stair_parameters_are_not_ignored(self):
        program=deepcopy(self.program);program['site']['plot_mm']=[8000,8000]
        with self.assertRaisesRegex(ValueError,'plot envelope'):build(program)
        program=deepcopy(self.program);program['floor_to_floor_mm']=3200
        with self.assertRaisesRegex(ValueError,'selected3m'):build(program)

    def test_native_six_floor_and_three_paired_svg_roundtrips(self):
        with tempfile.TemporaryDirectory(prefix='house890-') as folder:
            for house in self.houses:
                for floor,model in house['floors'].items():
                    path=Path(folder)/(model['id']+'.svg');path.write_bytes(export_floor(model,house['stair']))
                    result=read_floor(path);self.assertEqual(result['spaces'],model['spaces']);self.assertEqual(result['walls'],model['walls'])
                pair=Path(folder)/(house['scheme']['id']+'.svg');pair.write_bytes(paired_svg(house));result=read_house(pair)
                self.assertEqual(result['stair'],house['stair'])

    def test_upper_svg_has_floor_opening_and_rise_data(self):
        house=self.houses[0];root=ET.fromstring(export_floor(house['floors']['upper'],house['stair']))
        self.assertEqual(root.get('data-floor-z-mm'),'3000')
        self.assertEqual(len(root.findall('.//*[@data-floor-opening]')),2)
        self.assertEqual(len(root.findall('.//*[@data-rise]')),18)

    def test_svg_missing_named_room_and_wrong_floor_elevation_rejected(self):
        with tempfile.TemporaryDirectory(prefix='house890-') as folder:
            house=self.houses[0];path=Path(folder)/'upper.svg'
            root=ET.fromstring(export_floor(house['floors']['upper'],house['stair']))
            root.set('data-floor-z-mm','2000');ET.ElementTree(root).write(path)
            with self.assertRaisesRegex(ValueError,'elevation mismatch'):read_floor(path)
            root.set('data-floor-z-mm','3000');spaces=root.find(".//*[@id='spaces-source']")
            spaces.set('transform','translate(100 0)');ET.ElementTree(root).write(path)
            with self.assertRaisesRegex(ValueError,'source transform'):read_floor(path)
            spaces.attrib.pop('transform')
            spaces.remove(next(n for n in spaces if n.get('data-space-id')=='bed2'));ET.ElementTree(root).write(path)
            with self.assertRaisesRegex(ValueError,'Missing programmed rooms'):read_floor(path)

    def test_repeated_recipe_is_byte_identical_and_program_unmodified(self):
        before=deepcopy(self.program);again=build(self.program)
        self.assertEqual(before,self.program)
        for a,b in zip(self.houses,again):self.assertEqual(paired_svg(a),paired_svg(b))

    def test_original_fallback_twelve_svgs_remain_byte_identical(self):
        hashes=json.loads((RESOURCE_ROOT/'assets'/'regressions'/'fallback-sha256.json').read_text(encoding='utf-8'))
        for config in configurations():
            payload=export_svg(generate(config))
            self.assertEqual(hashlib.sha256(payload).hexdigest(),hashes[config['id']])


if __name__=='__main__':unittest.main(verbosity=2)
