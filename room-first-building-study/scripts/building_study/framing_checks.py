"""Read-only Blender measurements of profile stock and grid positions.

Clipped corner pieces are counted separately from full-width stock. Verifies
geometry/metadata, not engineering adequacy. Tolerance is0.005mm for Blender's
float32 vertex storage at building-scale world coordinates.
"""
def verify_framing(scene,p):
    parts=[o for o in scene.objects if o.type=='MESH' and o.get('stage',0)>0]
    counts={'full_width_wall_studs':0,'clipped_wall_grid_fragments':0,'floor_joist_flanges':0,'roof_rafters':0};floor_rows={};floor_bottoms={}
    for o in parts:
        if 'I joist lower flange' not in o.get('part',''):continue
        vs=[o.matrix_world@v.co for v in o.data.vertices]
        key=(o['level'],round(1000*min(v.x for v in vs),2),round(1000*max(v.x for v in vs),2),round(500*(min(v.y for v in vs)+max(v.y for v in vs)),2))
        floor_bottoms[key]=1000*min(v.z for v in vs)
    for o in parts:
        role=o.get('framing_grid_role')
        if not role:continue
        dims=[1000*(max(v.co[k] for v in o.data.vertices)-min(v.co[k] for v in o.data.vertices)) for k in range(3)]
        world=[o.matrix_world@v.co for v in o.data.vertices]
        low=[1000*min(v[k] for v in world) for k in range(3)];high=[1000*max(v[k] for v in world) for k in range(3)]
        axis=0 if o['grid_axis']=='x' else 1;station=o['grid_station_mm'];origin=o.get('grid_origin_mm',0)
        spacing=p.stud_spacing_mm if role=='wall-stud' else p.joist_spacing_mm if role=='floor-joist' else p.rafter_spacing_mm
        assert abs((station-origin)/spacing-round((station-origin)/spacing))<1e-6,(o.name,'off declared grid')
        width=(high[axis]-low[axis]) if role=='wall-stud' else dims[1] if role=='floor-joist' else dims[0]
        expected=p.flange_width_mm if role=='floor-joist' else p.stud_mm
        if role=='wall-stud' and abs(width-expected)>.005:
            assert width<expected+.005,(o.name,width,expected)
            counts['clipped_wall_grid_fragments']+=1;continue
        assert abs(width-expected)<.005,(o.name,'actual stock width',width,expected)
        assert abs((low[axis]+high[axis])/2-station)<.005,(o.name,'physical grid centre')
        if role=='wall-stud':counts['full_width_wall_studs']+=1
        elif role=='floor-joist':
            assert abs(dims[2]-p.flange_thickness_mm)<.005
            key=(o['level'],round(low[0],2),round(high[0],2),round(station,2))
            assert abs(high[2]-floor_bottoms[key]-p.joist_depth_mm)<.005,(o.name,'actual I-joist depth')
            counts['floor_joist_flanges']+=1;floor_rows.setdefault(o['level'],set()).add(station)
        else:
            expected_depth=p.tie_depth_mm if 'dining rafter' in o['part'] else p.rafter_depth_mm
            assert abs(dims[1]-expected_depth)<.005,(o.name,'actual rafter depth')
            counts['roof_rafters']+=1
    for level,rows in floor_rows.items():
        values=sorted(rows)
        assert all(abs(b-a-p.joist_spacing_mm)<1e-5 for a,b in zip(values,values[1:])),(level,'actual joist row spacing')
    assert all(counts[k]>0 for k in ('full_width_wall_studs','floor_joist_flanges','roof_rafters'))
    return dict(profile=p.to_dict(),measured_counts=counts,tolerance_mm=.005)
