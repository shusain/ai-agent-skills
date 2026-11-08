"""Blender5 readback of the saved study and small construction-stage renders.

Run through scripts/verify_blender.py with the .blend in a fresh background process.
Checks actual saved geometry, object ownership and animation; writes a receipt
and optionally20 preview PNGs. Does not resave the native source file.
"""
import bpy,bmesh,sys,json,hashlib
from pathlib import Path
from .blender_parts import STAGES,union,area,intersect,diff
from .room_first_house import read_house
from .clearance_geometry import rectangle_fits,landing,sweep_fits
from .framing import from_dict
from .framing_checks import verify_framing

def main(args):
    """Read and check the opened native source without resaving it."""
    OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True)
    frames=OUT/'construction-frames'
    if args.render_stages:frames.mkdir(exist_ok=True)
    scene=bpy.data.scenes['01 | Construction timeline'];bpy.context.window.scene=scene
    source=args.source.resolve()
    house=read_house(source)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==scene['source_svg_sha256']
    parts=[o for o in scene.objects if o.get('stage',0)>0]
    ids=[o['component_id'] for o in parts];assert len(ids)==len(set(ids))
    assert parts
    receipt={'blend':bpy.data.filepath,'source_sha256':scene['source_svg_sha256'],'blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'component_count':len(parts),'scenes':list(bpy.data.scenes.keys()),'stage_visibility':[]}
    receipt['furnished_both_side_door_pads']=[];receipt['furnished_full90_swings']=[]
    if 'framing_profile_json' not in scene:raise ValueError('Framing profile missing; regenerate with --framing-system metric or us')
    receipt['framing_measurements']=verify_framing(scene,from_dict(json.loads(scene['framing_profile_json'])))
    expected_units=receipt['framing_measurements']['profile']['display_units']
    receipt['display_units_by_scene']={s.name:s.unit_settings.system for s in bpy.data.scenes}
    assert all(units==expected_units for units in receipt['display_units_by_scene'].values()),'Review scene units do not match selected profile'
    for level,model in house['floors'].items():
        fixtures={}
        for obj in parts:
            if obj['level']!=level or obj['stage']!=19 or 'skirting' in obj['part']:continue
            vs=[obj.matrix_world@v.co for v in obj.data.vertices]
            r=tuple(round(v*1000) for v in (min(v.x for v in vs),min(v.y for v in vs),max(v.x for v in vs),max(v.y for v in vs)))
            fixtures.setdefault(obj['host'],[]).append(r)
        edges={e.id:e for e in model['edges']}
        for op in model['openings']:
            if op['kind']=='window':continue
            e=edges[op['host']]
            for owner in (e.positive,e.negative):
                if owner is None:continue
                available=diff(model['clear'][owner],fixtures.get(owner,[]))
                assert rectangle_fits(landing(e,op,owner,1200),available),(level,op['id'],owner,'actual furnished pad')
            available=diff(model['clear'][op['space']],fixtures.get(op['space'],[]))
            assert sweep_fits(e,op,available,50),(level,op['id'],'actual furnished swing')
            receipt['furnished_both_side_door_pads'].append(level+'/'+op['id'])
            receipt['furnished_full90_swings'].append(level+'/'+op['id'])
    # Each solid source mesh must have a closed edge manifold; evaluated presentation
    # cutaway copies are not counted as source assemblies.
    meshes={o.data.name:o.data for o in parts if o.type=='MESH'};bad=[];negative=[]
    for mesh in meshes.values():
        bm=bmesh.new();bm.from_mesh(mesh)
        if any(not e.is_manifold for e in bm.edges):bad.append(mesh.name)
        if bm.calc_volume(signed=True)<-1e-8:negative.append(mesh.name)
        bm.free()
    assert not bad,bad
    receipt['closed_source_meshes']=len(meshes);receipt['negative_winding_meshes']=negative
    # Actual saved sheet extents independently reproduce the approved floor region.
    for level in ('ground','upper'):
        rects=[]
        for obj in parts:
            if obj['level']!=level or '22mm subfloor panel' not in obj['part']:continue
            vs=[obj.matrix_world@v.co for v in obj.data.vertices]
            rects.append(tuple(round(v*1000) for v in (min(v.x for v in vs),min(v.y for v in vs),max(v.x for v in vs),max(v.y for v in vs))))
        footprint=house['floors'][level]['footprint'];holes=house['stair']['opening'] if level=='upper' else []
        intended=diff(footprint,holes);actual=union(rects)
        assert area(diff(actual,intended))==area(diff(intended,actual))==0
        assert area(actual)==area(rects)
        receipt[level+'_actual_sheet_area_m2']=area(actual)/1e6
    scene.render.resolution_x=900;scene.render.resolution_y=720;scene.cycles.samples=args.samples
    for stage,name in enumerate(STAGES,1):
        frame=1+(stage-1)*10;scene.frame_set(frame)
        visible=[o for o in parts if not o.hide_render]
        assert all((not o.hide_render)==(o['stage']<=stage) for o in parts),(stage,'render visibility')
        assert all((not o.hide_viewport)==(o['stage']<=stage) for o in parts),(stage,'viewport visibility')
        receipt['stage_visibility'].append({'stage':stage,'frame':frame,'name':name,'visible_parts':len(visible)})
        scene.render.filepath=str(frames/f'{stage:02d}.png')
        print('Verify stage '+str(stage)+' / '+name,flush=True)
        if args.render_stages:bpy.ops.render.render(write_still=True,scene=scene.name)
    scene.frame_set(221)
    (OUT/'native-readback.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('NATIVE READBACK AND20 STAGES PASS',flush=True)
