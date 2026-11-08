"""Read-only Blender5 material takeoff for the existing #890 study.

Run with the saved .blend opened in a fresh background process. Counts only the
construction scene (never the presentation copies). Writes requested-output
JSON/CSV; never resaves geometry. Quantities are modeled material, not a
stock-length/cutting/engineering schedule. Runtime: Blender5 Python / bpy.
"""
import sys,json,csv,hashlib,collections
from pathlib import Path
import bpy,bmesh
from .blender_parts import union,intersect,diff,inset,band,wall_rect,area
from .room_first_house import read_house
from .framing import from_dict,wall_domains

def main(args):
    """Inventory the opened source scene; write a fresh local takeoff."""
    ROOT=args.output.resolve()
    SOURCE=args.source.resolve()
    house=read_house(SOURCE);domains={}
    scene=bpy.data.scenes['01 | Construction timeline'];scene.frame_set(221);bpy.context.view_layer.update()
    if 'framing_profile_json' not in scene:raise ValueError('Framing profile missing; regenerate with --framing-system metric or us')
    profile=from_dict(json.loads(scene['framing_profile_json']))
    for level,m in house['floors'].items():
        d=wall_domains(m,profile);domains[level]=(d['extcore'],d['intcore'])
    scene=bpy.data.scenes['01 | Construction timeline'];scene.frame_set(221);bpy.context.view_layer.update()
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=scene['source_svg_sha256']:
        raise ValueError('Source SVG does not match the opened Blender study')
    ROOT.mkdir(parents=True,exist_ok=False)
    parts=[o for o in scene.objects if o.type=='MESH' and o.get('stage',0)>0]
    assert parts and len(parts)==len({o['component_id'] for o in parts})
    rows=[];cache={};groups=collections.defaultdict(lambda:dict(segments=0,volume_m3=0,area_m2=0,length_m=0))
    def category(o,mat):
        s=o['stage'];p=o['part']
        if mat=='concrete':return 'Foundations: concrete'
        if 'I joist upper flange' in p:return 'Floors: engineered I-joist upper flanges'
        if 'I joist lower flange' in p:return 'Floors: engineered I-joist lower flanges'
        if 'I joist web' in p:return 'Floors: engineered I-joist webs'
        if 'subfloor panel' in p:return 'Panels: 22mm subfloor'
        if 'LVL' in p or 'opening header' in p:return 'Beams: LVL bearers / transfers / headers'
        if 'rim board' in p or 'stair trimmer and header' in p:return 'Floors: rim / trimmer timber'
        if 'treated sill' in p:return 'Timber: treated foundation sill'
        if s in (4,7):return 'Walls: '+p.split('/',1)[1]
        if s==9:return 'Roof framing: '+p.split('/')[-1]
        if s==8:return 'Stair structure: '+p.split('/')[-1]
        if mat=='osb' and s==10:return 'Panels: 12mm wall sheathing'
        if mat=='osb' and s==11:return 'Panels: 18mm roof sheathing'
        if mat=='membrane':return 'Membranes: '+('roof' if o['level']=='roof' else 'wall')
        if mat=='insulation':return 'Insulation: wall cavities'
        if mat=='cladding':return 'Cladding: exterior skin'
        if mat=='lining':return 'Lining: '+('ceilings' if 'ceiling' in p else 'walls')
        if s==18 and 'floor finish' in p:return 'Floor finish: '+mat
        if s==15 and ('metal covering' in p):return 'Roof finish: metal field panels'
        if s==14 and 'batten' in p:return 'Battens: rainscreen'
        if s==15 and 'batten' in p:return 'Battens: roof'
        if s==13 and 'jamb' in p and 'window' in o['host']:return 'Windows: jamb segments'
        if s==13 and 'door leaf' in p:return 'Doors: leaves'
        return 'Other: '+mat+' / stage '+str(s)
    for o in parts:
        mesh=o.data
        if mesh.name not in cache:
            bm=bmesh.new();bm.from_mesh(mesh);vol=abs(bm.calc_volume());bm.free()
            dims=[max(v.co[k] for v in mesh.vertices)-min(v.co[k] for v in mesh.vertices) for k in range(3)]
            toparea=sum(p.area for p in mesh.polygons if p.normal.z>.1)
            cache[mesh.name]=(vol,dims,toparea)
        vol,dims,top=cache[mesh.name];mat=mesh.materials[0].name.split(' / ')[-1];p=o['part'];cat=category(o,mat)
        measured_area=0;length=0
        if cat=='Panels: 22mm subfloor':measured_area=vol/.022
        elif cat=='Panels: 12mm wall sheathing':measured_area=vol/.012
        elif cat=='Panels: 18mm roof sheathing' or cat=='Roof finish: metal field panels':measured_area=top
        elif cat=='Cladding: exterior skin':measured_area=vol/.020
        elif mat=='lining':measured_area=vol/.015
        elif 'Floor finish:' in cat:measured_area=vol/.018
        elif 'I-joist' in cat:length=dims[0]
        g=groups[cat];g['segments']+=1;g['volume_m3']+=vol;g['area_m2']+=measured_area;g['length_m']+=length
        if o['stage'] in (4,7) and 'opening header' not in p:
            vs=[o.matrix_world@v.co for v in mesh.vertices]
            rect=tuple(round(v*1000,4) for v in (min(v.x for v in vs),min(v.y for v in vs),max(v.x for v in vs),max(v.y for v in vs)))
            for k,domain,depth in [('exterior',domains[o['level']][0],profile.exterior_depth_mm/1000),('interior',domains[o['level']][1],profile.interior_depth_mm/1000)]:
                overlap=area(intersect([rect],domain));fraction=overlap/area([rect])
                a=groups['EQUIVALENT wall stock: '+k];a['volume_m3']+=vol*fraction;a['length_m']+=vol*fraction/(profile.stud_mm/1000*depth)
        rows.append(dict(id=o['component_id'],part=p,stage=o['stage'],level=o['level'],host=o['host'],material=mat,category=cat,framing_system=profile.system,
                         local_x_m=dims[0],local_y_m=dims[1],local_z_m=dims[2],local_x_in=dims[0]/.0254,local_y_in=dims[1]/.0254,local_z_in=dims[2]/.0254,
                         net_volume_m3=vol,measured_area_m2=measured_area,length_m=length,length_ft=length/.3048))
    stats=dict(feature_counts={'windows':sum(o['kind']=='window' for m in house['floors'].values() for o in m['openings']),'interior_doors':sum(o['kind']=='door' for m in house['floors'].values() for o in m['openings']),'entry_doors':sum(o['kind']=='entry' for m in house['floors'].values() for o in m['openings']),'rafters':sum(o['stage']==9 and 'rafter' in o['part'] for o in parts)},source_blend=bpy.data.filepath,blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
               component_count=len(parts),groups=dict(sorted(groups.items())),total_timber_m3=sum(r['net_volume_m3'] for r in rows if r['material']=='timber'))
    stats['framing_profile']=profile.to_dict()
    stats['wall_stock_equivalents']={key:dict(groups['EQUIVALENT wall stock: '+key],label=profile.stock_labels[key],thickness_mm=profile.stud_mm,depth_mm=depth) for key,depth in [('exterior',profile.exterior_depth_mm),('interior',profile.interior_depth_mm)]}
    for key in stats['wall_stock_equivalents']:
        stats['wall_stock_equivalents'][key]['length_ft']=stats['wall_stock_equivalents'][key]['length_m']/.3048
        stats['wall_stock_equivalents'][key]['actual_section_in']=[profile.stud_mm/25.4,stats['wall_stock_equivalents'][key]['depth_mm']/25.4]
    concrete=[]
    for o in parts:
        if o.data.materials[0].name!='Study / concrete':continue
        vs=[o.matrix_world@v.co for v in o.data.vertices]
        concrete.append(([round(min(v[k] for v in vs)*1000,4) for k in range(3)],[round(max(v[k] for v in vs)*1000,4) for k in range(3)]))
    levels=sorted({v[2] for pair in concrete for v in pair});cv=0
    for z0,z1 in zip(levels,levels[1:]):
        rects=[(a[0],a[1],b[0],b[1]) for a,b in concrete if a[2]<(z0+z1)/2<b[2]]
        cv+=area(union(rects))*(z1-z0)/1e9
    stats['foundation_union_m3']=cv
    stats['foundation_union_yd3']=cv/.764554857984
    stats['total_timber_ft3']=stats['total_timber_m3']/.028316846592
    (ROOT/'quantities.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    with (ROOT/'components.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({k:{a:round(b,3) for a,b in v.items()} for k,v in stats['groups'].items() if not k.startswith('Other:')},indent=2))
    print('Total timber m3',stats['total_timber_m3'])
