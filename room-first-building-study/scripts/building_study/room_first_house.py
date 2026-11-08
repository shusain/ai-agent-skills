"""Issue890 room-program-first two-storey house study; ordinary Python only.

Loads a named room program, composes three authored parametric room arrangements,
then derives their footprints/shared walls and validates room fit, relationships,
privacy, circulation, openings, floor support and an aligned U-return stair.
Reuses shared_spaces, clearance_geometry and plan_svg; no fallback generation is
invoked and no Blender/Unreal/production files are written. CLI requires a fresh
output directory and writes program/relationship data, six floor SVGs and receipts.
This is a schematic builder library, not a general architectural constraint solver.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from . import RESOURCE_ROOT
from .plan_svg import NS,element,union_rectangles
from .clearance_geometry import door_frame,landing,rectangle_fits,sweep_fits,rectangle_centres
from .shared_spaces import (area,bounds,boundaries,components,door_clear,export_svg,path_data,
                           largest_rectangle,loops,validate_partition,wall_bands,walk_report)


def load_program(path=None):
    path=Path(path) if path else RESOURCE_ROOT/"assets"/"examples"/"two-storey-program.json"
    program=json.loads(path.read_text(encoding="utf-8"))
    validate_program(program)
    return program


def validate_program(program):
    """Reject unsupported prototype module settings instead of ignoring them."""
    if program.get('schema')!=1 or program.get('units')!='mm':raise ValueError('Room program schema1/mm required')
    stair=program['stair']
    if program['floor_to_floor_mm']!=3000 or stair['shaft_mm']!=[3100,4000] or stair['rises']!=18 or stair['flight_clear_mm']!=1200 or stair['going_mm']!=280 or stair['mid_landing_depth_mm']!=1250:raise ValueError('This proof supports the selected3m/18-rise U-stair module only')


class Rooms:
    """Compose named rooms from anchored modules; envelope is derived afterwards."""
    def __init__(self):self.spaces={};self.placements=[]
    def place(self,name,x,y,width,depth,anchor):
        if name in self.spaces:raise ValueError("Duplicate room")
        if min(width,depth)<=0:raise ValueError("Positive room module required")
        self.spaces[name]=[(x,y,x+width,y+depth)]
        self.placements.append(dict(room=name,anchor=anchor,module_mm=[width,depth]))
    def extend(self,name,x,y,width,depth,anchor):
        self.spaces[name]=union_rectangles(self.spaces[name]+[(x,y,x+width,y+depth)])
        self.placements.append(dict(room=name,anchor=anchor,module_mm=[width,depth],extension=True))


def connect(a,b,kind="door",width=900,served=None):
    return dict(a=a,b=b,kind=kind,width=width,served=served or b)


def schemes(program):
    """Three room/circulation strategies; dimensions are module parameters.

    No enclosing rectangle is supplied to a splitter. Named room modules and
    their selected anchors determine each floor's union/outline.
    """
    out=[]
    # A: family rooms arranged around a compact circulation spine; side stair.
    g=Rooms();u=Rooms();left=3600;spine=2400;right=4000;x=left+spine
    g.place("study",0,0,left,3500,"front-left of foyer")
    g.place("foyer",left,0,spine,3500,"east of study")
    g.place("stair",x,400,4000,3100,"east of foyer; opening faces west")
    g.place("wc",0,3500,left,1800,"behind study; door to hall")
    g.place("living",0,5300,left,7600,"behind WC; garden-facing")
    g.place("hall",left,3500,spine,6000,"behind foyer")
    g.place("utility",x,3500,right,2400,"behind side stair")
    g.place("kitchen",x,5900,right,3600,"behind utility; beside dining")
    g.place("dining",left,9500,spine+right,3400,"behind hall and kitchen; beside living")
    u.place("bed2",0,0,left,4200,"front-left; accessed from landing")
    u.place("bed3",0,4200,left,4200,"behind bedroom2")
    u.place("landing",left,0,spine,3500,"over foyer; side-stair arrival")
    u.place("stair",x,400,4000,3100,"same shaft as ground")
    u.place("upper_hall",left,3500,spine,3800,"behind landing")
    u.place("bath",x,3500,right,2200,"over utility wet zone")
    u.place("linen",x,5700,right,1600,"beside upper hall")
    u.place("primary",left,7300,spine+right,3900,"rear sleeping zone")
    u.extend("primary",0,8400,left,2800,"private dressing wing beside sleeping zone")
    gc=[connect("outside","foyer","entry",1000),connect("foyer","study"),connect("foyer","hall","open"),connect("foyer","stair","open"),connect("hall","wc"),connect("hall","utility"),connect("hall","living","portal",1600),connect("hall","kitchen","portal",1400),connect("living","dining","open"),connect("kitchen","dining","open")]
    uc=[connect("landing","stair","open"),connect("landing","upper_hall","open"),connect("landing","bed2"),connect("upper_hall","bed3"),connect("upper_hall","primary"),connect("upper_hall","bath"),connect("upper_hall","linen")]
    out.append(dict(id="side-stair",name="Side stair / rear family rooms",note="Compact private landing; rear family spaces wrap the hall.",ground=g,upper=u,ground_connections=gc,upper_connections=uc,stair=dict(origin=[6000,3500],rotation=-90),builtins=[]))
    # B: foyer/stair at the meeting of a quiet service wing and open family wing.
    g=Rooms();u=Rooms();quiet=2600;hall=1800;core=3100;family=5000;cx=quiet+hall;fx=cx+core
    g.place("study",0,0,quiet,5000,"quiet front wing")
    g.place("foyer",quiet,0,hall+core,2500,"between study and family wing")
    g.place("stair",cx,2500,core,4000,"behind foyer; opening faces south")
    g.place("hall",quiet,2500,hall,7500,"quiet service corridor")
    g.extend("hall",cx,6500,core,1800,"cross hall behind stair")
    g.place("wc",0,5000,quiet,2000,"behind study")
    g.place("utility",0,7000,quiet,3000,"behind WC; service hall access")
    g.place("living",fx,0,family,4500,"front of open family wing")
    g.place("kitchen",fx,4500,family,3800,"between living and dining; wet stack")
    g.place("dining",fx,8300,family,3700,"garden end of family wing")
    u.place("primary",0,0,cx,5500,"front quiet suite with fitted wardrobe")
    u.place("bed2",0,5500,cx,4500,"rear quiet bedroom")
    u.place("landing",cx,0,core+hall,2500,"stair arrival and linen cupboard")
    u.place("stair",cx,2500,core,4000,"same shaft as ground")
    u.place("upper_hall",fx,2500,hall,5800,"east side of stair")
    u.extend("upper_hall",cx,6500,core,1800,"return to rear bedroom")
    u.place("bed3",fx+hall,0,family-hall,5000,"front of east wing")
    u.place("bath",fx+hall,5000,family-hall,3300,"over kitchen")
    gc=[connect("outside","foyer","entry",1000),connect("foyer","study"),connect("foyer","hall","open"),connect("foyer","stair","open"),connect("foyer","living","open"),connect("hall","wc"),connect("hall","utility"),connect("hall","kitchen","open"),connect("living","kitchen","open"),connect("kitchen","dining","open")]
    uc=[connect("landing","stair","open"),connect("landing","upper_hall","open"),connect("landing","primary"),connect("landing","bed3"),connect("upper_hall","bed2"),connect("upper_hall","bath")]
    out.append(dict(id="family-wing",name="Central stair / open family wing",note="Public family wing and quiet service corridor; longer upper circulation.",ground=g,upper=u,ground_connections=gc,upper_connections=uc,stair=dict(origin=[4400,2500],rotation=0),builtins=[dict(id="linen_builtin",space="landing",rect=[6000,250,7200,850],kind="linen")]))
    # C: garden-side stair with a deliberate second service route to kitchen.
    g=Rooms();u=Rooms();left=4000;core=3100;service=1800;wet=2400;cx=left;rx=left+core;sx=rx+service
    g.place("living",0,0,left,7000,"front family room")
    g.place("dining",0,7000,left,4500,"garden family room")
    g.place("foyer",cx,0,core,2500,"between living and study")
    g.place("hall",cx,2500,core,3000,"deliberate stair approach")
    g.place("stair",cx,5500,core,4000,"behind main hall")
    g.place("study",rx,0,service+wet,3500,"front quiet room")
    g.place("service_hall",rx,3500,service,6000,"side service route")
    g.place("wc",sx,3500,wet,2500,"off service hall")
    g.place("utility",sx,6000,wet,3500,"behind WC")
    g.place("kitchen",cx,9500,core+service,3800,"rear kitchen; linked to dining and service hall")
    u.place("primary",0,0,left,5500,"front sleeping zone")
    u.extend("primary",cx,0,core,2500,"dressing/reading zone in front of landing")
    u.place("landing",cx,2500,core,3000,"same stair-approach zone")
    u.place("stair",cx,5500,core,4000,"same shaft as ground")
    u.place("upper_hall",rx,3500,service,6000,"side of stair")
    u.extend("upper_hall",cx,9500,core+service,1800,"rear gallery to bedroom3")
    u.place("bed2",rx,0,service+wet,3500,"front east bedroom")
    u.place("bed3",0,5500,left,5800,"garden bedroom")
    u.place("bath",sx,3500,wet,3000,"over WC/utility wet core")
    u.place("linen",sx,6500,wet,3000,"off upper hall")
    gc=[connect("outside","foyer","entry",1000),connect("foyer","study"),connect("foyer","hall","open"),connect("hall","stair","open"),connect("hall","service_hall","open"),connect("foyer","living","portal",1600),connect("service_hall","wc"),connect("service_hall","utility"),connect("service_hall","kitchen","door",900),connect("living","dining","open"),connect("dining","kitchen","open")]
    uc=[connect("landing","stair","open"),connect("landing","upper_hall","open"),connect("landing","primary"),connect("upper_hall","bed2"),connect("upper_hall","bed3"),connect("upper_hall","bath"),connect("upper_hall","linen")]
    out.append(dict(id="garden-stair",name="Rear stair / service gallery",note="Separate service route and garden bedroom; a more articulated upper outline.",ground=g,upper=u,ground_connections=gc,upper_connections=uc,stair=dict(origin=[4000,5500],rotation=0),builtins=[]))
    return out


def connected_sets(names,pairs):
    groups={name:{name} for name in names}
    for a,b in pairs:
        merged=groups[a]|groups[b]
        for name in merged:groups[name]=merged
    return {name:min(group) for name,group in groups.items()}


def rule_for(program,sid):
    if sid in program["rooms"]:return program["rooms"][sid]
    if sid=="service_hall":return dict(name="Service hall",role="circulation",area_m2=[5,15],fit_mm=[1300,1800])
    if sid=="linen":return dict(name="Linen / storage",role="storage",area_m2=[2,6.5],fit_mm=[1300,1800])
    if sid=="stair":return dict(name="Stair",role="stair")
    raise ValueError("Unprogrammed space: "+sid)


def derive_floor(program,scheme,floor):
    builder=scheme[floor];spaces=builder.spaces if isinstance(builder,Rooms) else builder
    connections=scheme[floor+"_connections"]
    expected={sid for sid,r in program["rooms"].items() if r["floor"]==floor}
    if not expected<=set(spaces):raise ValueError("Missing programmed rooms: "+str(expected-set(spaces)))
    fp=union_rectangles([r for group in spaces.values() for r in group]);validate_partition(fp,spaces)
    semantic=boundaries(spaces)
    open_pairs=[(c["a"],c["b"]) for c in connections if c["kind"]=="open" and "stair" not in (c["a"],c["b"])]
    enclosure=connected_sets(spaces,open_pairs)
    omitted={e.id for e in semantic if not e.exterior and enclosure[e.negative]==enclosure[e.positive]}
    for c in connections:
        if c["a"]=="outside":continue
        candidates=[e for e in semantic if {e.negative,e.positive}=={c["a"],c["b"]}]
        if not candidates:raise ValueError(f"Missing required adjacency {scheme['id']} {floor}: {c['a']} / {c['b']}")
        if c["kind"]=="open":omitted.update(e.id for e in candidates)
    physical=[e for e in semantic if e.id not in omitted]
    closed=union_rectangles(wall_bands(physical),footprint=fp)
    clear={sid:union_rectangles(rects,exclusions=closed) for sid,rects in spaces.items()}
    for sid,rects in clear.items():
        rule=rule_for(program,sid)
        if not rects or len(components(rects))!=1:raise ValueError("Disconnected clear room "+sid)
        if rule["role"]=="stair":continue
        size=area(rects)/1e6;lo,hi=rule["area_m2"]
        if not lo<=size<=hi:raise ValueError(f"Room program area {scheme['id']} {floor} {sid}: {size:.2f} outside {lo}..{hi}")
        w,d=rule['fit_mm']
        if not rectangle_centres(rects,w,d) and not rectangle_centres(rects,d,w):raise ValueError(f"Functional fit failed {scheme['id']} {floor} {sid}: {w} x {d}")
    groups=defaultdict(list)
    for sid,r in clear.items():
        if sid!="stair":groups[enclosure[sid]].extend(r)
    report=walk_report({sid:union_rectangles(r) for sid,r in groups.items()},program["clearance"]["circulation_square_mm"])
    if any(r["narrow"] or r["core_components"]!=1 for r in report.values()):raise ValueError(f"Narrow physical space {scheme['id']} {floor}: "+str([s for s,r in report.items() if r["narrow"] or r["core_components"]!=1]))
    openings=[];margin=program["clearance"]["swing_margin_mm"];walk=program["clearance"]["circulation_square_mm"]
    for c in connections:
        if c["kind"]=="open":continue
        candidates=[e for e in physical if {e.negative or 'outside',e.positive or 'outside'}=={c['a'],c['b']}]
        placed=None
        for e in sorted(candidates,key=lambda e:(-(e.hi-e.lo),e.id)):
            width=c["width"];first,last=e.lo+350,e.hi-350-width
            if first>last:continue
            middle=(first+last)//2
            positions={first,last,middle,*[max(first,min(last,middle+d)) for d in (-900,-600,-300,300,600,900)]}
            for start in sorted(positions,key=lambda p:(abs(p-middle),p)):
                for hinge in ("low","high"):
                    op=dict(id=c['a']+'__'+c['b'],host=e.id,lo=start,hi=start+width,kind=c['kind'],space=c['served'],sill_mm=0,height_mm=2400 if c['kind']=='portal' else 2100)
                    if c['kind']!='portal':op['hinge']=hinge
                    pads=all(rectangle_fits(landing(e,op,s,walk),clear[s]) for s in (e.negative,e.positive) if s is not None)
                    swing=c['kind']=='portal' or sweep_fits(e,op,clear[c['served']],margin)
                    if pads and swing:placed=op;break
                if placed:break
            if placed:break
        if not placed:raise ValueError(f"No functional opening {scheme['id']} {floor}: {c['a']} / {c['b']}")
        openings.append(placed)
    # Each habitable/service room receives an exterior window when a legal edge exists.
    for sid in sorted(spaces):
        if rule_for(program,sid)["role"] in ("circulation","stair","storage"):continue
        window_width=900 if sid in ('wc','bath') else 1400
        edges=[e for e in physical if e.exterior and sid in (e.negative,e.positive) and e.hi-e.lo>=window_width+700]
        if not edges:raise ValueError("No exterior window opportunity: "+sid)
        e=max(edges,key=lambda e:(e.hi-e.lo,e.id));lo=(e.lo+e.hi-window_width)//2
        openings.append(dict(id='window_'+sid,host=e.id,lo=lo,hi=lo+window_width,kind='window',space=sid,sill_mm=1400 if sid in ('wc','bath') else 900,height_mm=700 if sid in ('wc','bath') else 1200))
    cuts=[];by_id={e.id:e for e in semantic}
    for op in openings:
        if op['sill_mm']<=1200<op['sill_mm']+op['height_mm']:
            e=by_id[op['host']];t=e.thickness+1
            cuts.append((op['lo'],e.at-t,op['hi'],e.at+t) if e.axis=='x' else (e.at-t,op['lo'],e.at+t,op['hi']))
    walls=union_rectangles(closed,exclusions=cuts)
    names={sid:rule_for(program,sid)['name'] for sid in spaces};names['stair']='Stairs' if floor=='ground' else 'Stair opening'
    result=dict(id=scheme['id']+'-'+floor,family='room-program',floor=floor,profile=scheme['name'],seed=0,footprint=fp,spaces=spaces,names=names,edges=semantic,physical_edges=physical,omitted_edges=sorted(omitted),clear=clear,walls=walls,openings=sorted(openings,key=lambda o:o['id']),min_walk_mm=walk,swing_margin_mm=margin,connections=connections,enclosure=enclosure,stair=scheme['stair'],builtins=scheme['builtins'] if floor=='upper' else [],program=program,placements=builder.placements if isinstance(builder,Rooms) else [])
    validate_relationships(result)
    return result


def validate_relationships(model):
    graph=defaultdict(set)
    for c in model['connections']:graph[c['a']].add(c['b']);graph[c['b']].add(c['a'])
    # Requirements compare open enclosures, so a service-hall branch remains
    # intentional circulation without forcing every door onto the same edge.
    enc=dict(model['enclosure'],outside='outside')
    links={frozenset((enc[c['a']],enc[c['b']])) for c in model['connections']}
    for a,b in model['program']['relationships']['required']:
        if a not in enc or b not in enc:continue
        if enc[a]!=enc[b] and frozenset((enc[a],enc[b])) not in links:raise ValueError('Missing program relationship: '+a+' / '+b)
    if model['floor']=='ground':
        if len({enc[s] for s in model['program']['relationships']['family_open_group']})!=1:raise ValueError('Family zones must share one open enclosure')
    if not any(c['kind']=='open' and 'stair' in (c['a'],c['b']) and rule_for(model['program'],c['b'] if c['a']=='stair' else c['a'])['role']=='circulation' for c in model['connections']):raise ValueError('Stair must open into circulation')
    source='outside' if model['floor']=='ground' else 'landing'
    seen={source};todo=[source]
    while todo:
        current=todo.pop()
        # Private rooms and stair shafts are destinations, never transit rooms.
        if current in model['spaces'] and rule_for(model['program'],current)['role'] in ('private','stair'):continue
        for target in graph[current]-seen:seen.add(target);todo.append(target)
    if not set(model['spaces'])<=seen:raise ValueError('Required route crosses private room or is absent')
    if model['floor']=='upper':
        for sid in ('primary','bed2','bed3','bath'):
            if not any(rule_for(model['program'],other)['role']=='circulation' for other in graph[sid]):raise ValueError('Private/service room lacks circulation access')


def stair_point(spec,x,y):
    a,b=spec['origin']
    if spec['rotation']==0:return a+x,b+y
    if spec['rotation']==-90:return a+y,b-x
    raise ValueError('Only reviewed stair orientations supported')


def stair_rect(spec,rect):
    a,b,c,d=rect;pts=[stair_point(spec,x,y) for x in (a,c) for y in (b,d)]
    return min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)


def stair_model(program,spec):
    """Exact rise schedule and aligned opening/arrival reservations for a U stair."""
    flight=program['stair']['flight_clear_mm'];going=program['stair']['going_mm'];run=8*going
    # 250mm all-side allowance fits exterior and interior shaft wall assemblies.
    left=275;right=1625;start=150;turn=start+run;back=turn+1250
    treads=[]
    for f,x in enumerate((left,right)):
        for i in range(9):
            y=start+i*going if f==0 else turn-i*going
            rise=i+1 if f==0 else i+10
            z=Fraction(program['floor_to_floor_mm']*rise,18)
            treads.append(dict(a=stair_point(spec,x,y),b=stair_point(spec,x+flight,y),z_mm=str(z),rise=rise))
    lower_pad=stair_rect(spec,(left,-1200,left+flight,0));upper_pad=stair_rect(spec,(right,-1200,right+flight,0))
    opening=[stair_rect(spec,(250,150,2850,3750)),stair_rect(spec,(250,0,1625,150))]
    return dict(shaft=stair_rect(spec,(0,0,3100,4000)),flights=[stair_rect(spec,(x,start,x+flight,turn)) for x in (left,right)],mid_landing=stair_rect(spec,(left,turn,right+flight,back)),lower_pad=lower_pad,upper_pad=upper_pad,lower_connector=stair_rect(spec,(left,-1200,left+flight,150)),upper_connector=stair_rect(spec,(right,-1200,right+flight,150)),opening=union_rectangles(opening),upper_bridge=stair_rect(spec,(right,0,right+flight,150)),treads=treads,rises=18,rise_mm=str(Fraction(3000,18)),flight_clear_mm=1200,going_mm=280,mid_landing_depth_mm=1250,reserved_headroom_mm=2200)


def validate_house(program,scheme,floors):
    g,u=floors['ground'],floors['upper'];stair=stair_model(program,scheme['stair'])
    if union_rectangles(u['footprint'],exclusions=g['footprint']):raise ValueError('Unsupported upper-floor projection')
    for floor in ('ground','upper'):
        m=floors[floor]
        if union_rectangles(m['spaces']['stair'])!=[stair['shaft']]:raise ValueError('Stair shaft does not match room module')
        if any(not rectangle_fits(r,m['clear']['stair']) for r in stair['flights']+[stair['mid_landing']]):raise ValueError('Stair flights/turn do not fit shaft')
    for m,pad,connector in ((g,stair['lower_pad'],stair['lower_connector']),(u,stair['upper_pad'],stair['upper_connector'])):
        circulation=union_rectangles([r for sid,rects in m['clear'].items() if rule_for(program,sid)['role']=='circulation' for r in rects])
        if not rectangle_fits(pad,circulation):raise ValueError('Stair arrival/departure pad is not in circulation')
        if not rectangle_fits(connector,union_rectangles(circulation+m['clear']['stair'])):raise ValueError('Wall blocks stair approach/arrival')
    wet=union_rectangles([r for sid in ('kitchen','utility','wc') for r in g['spaces'][sid]])
    if area(union_rectangles(u['spaces']['bath'],footprint=wet))!=area(u['spaces']['bath']):raise ValueError('Bathroom is not over ground wet/service zone')
    if not ('linen' in u['spaces'] or any(b['kind']=='linen' for b in u['builtins'])):raise ValueError('Missing linen-storage function')
    for item in u['builtins']:
        a,b,c,d=item['rect']
        if not rectangle_fits((a,b,c,d),u['clear'][item['space']]):raise ValueError('Linen built-in is outside landing')
        if any(x<y for x,y in zip(sorted((c-a,d-b)),sorted(program['linen_storage']['minimum_shelf_mm']))):raise ValueError('Linen built-in too small')
        # Keep built-ins out of all actual door landings/sweeps and stair arrival.
        altered=dict(u['clear']);altered[item['space']]=union_rectangles(altered[item['space']],exclusions=[item['rect']])
        by_id={e.id:e for e in u['edges']}
        for op in u['openings']:
            if op['kind']=='window':continue
            e=by_id[op['host']]
            if item['space'] in (e.negative,e.positive):
                if not rectangle_fits(landing(e,op,item['space'],1200),altered[item['space']]):raise ValueError('Built-in blocks door approach')
                if op['space']==item['space'] and not sweep_fits(e,op,altered[item['space']],50):raise ValueError('Built-in blocks door swing')
        if not rectangle_fits(stair['upper_pad'],union_rectangles([r for s,rs in altered.items() if rule_for(program,s)['role']=='circulation' for r in rs])):raise ValueError('Built-in blocks stair arrival')
        circulation=union_rectangles([r for s,rs in altered.items() if rule_for(program,s)['role']=='circulation' for r in rs])
        report=walk_report({'circulation':circulation})['circulation']
        if report['narrow'] or report['core_components']!=1:raise ValueError('Built-in narrows circulation')
    for m in floors.values():
        a,b,c,d=bounds(m['footprint'])
        if c-a>program['site']['plot_mm'][0] or d-b>program['site']['plot_mm'][1]:raise ValueError('Exceeds plot envelope')
    return stair


def export_floor(model,stair):
    """Reuse native SVG export, then add programme metadata and measured stair."""
    root=ET.fromstring(export_svg(model));root.attrib.pop('data-shared-plan-schema',None)
    root.set('data-room-program-schema','1');root.set('data-floor',model['floor']);root.set('data-floor-z-mm','0' if model['floor']=='ground' else '3000')
    meta=dict(program=model['program'],scheme=model['id'].rsplit('-',1)[0],floor=model['floor'],profile=model['profile'],connections=model['connections'],stair=model['stair'],builtins=model['builtins'],placements=model['placements'])
    element(root,'metadata',{'id':'house-program'},json.dumps(meta,sort_keys=True,separators=(',',':')))
    physical={e.id for e in model['physical_edges']}
    for item in root.findall(f".//*[@id='shared-boundaries']/{{{NS}}}line"):
        item.set('data-boundary-kind','wall' if item.get('id') in physical else 'open')
    world=root.find(".//*[@id='world-mm']");guides=element(world,'g',{'id':'stair-geometry','data-role':'stair-reservation'})
    element(root,'style',{},'.stair-line{fill:none;stroke:currentColor;stroke-width:20}.stair-void{fill:none;stroke:currentColor;stroke-width:20;stroke-dasharray:80 60}.functional-item{fill:none;stroke:currentColor;stroke-width:18}.zone-boundary{fill:none;stroke:currentColor;stroke-width:12;stroke-dasharray:100 100;opacity:.25}')
    for group in world.findall(f"./*[@id='clear-spaces']/{{{NS}}}g"):
        if rule_for(model['program'],group.get('data-space-id'))['role']=='circulation':group.set('class','plan-hall')
    zones=element(world,'g',{'id':'functional-boundaries','data-role':'annotation'})
    for edge in model['edges']:
        if edge.id in model['omitted_edges'] and 'stair' not in (edge.negative,edge.positive):
            p,q=edge.point(edge.lo),edge.point(edge.hi);element(zones,'line',dict(x1=p[0],y1=p[1],x2=q[0],y2=q[1],**{'class':'zone-boundary'}))
    for r in stair['flights']+[stair['mid_landing']]:
        a,b,c,d=r;element(guides,'rect',dict(x=a,y=b,width=c-a,height=d-b,**{'class':'stair-line'}))
    for tread in stair['treads']:
        a,b=tread['a'],tread['b'];element(guides,'line',dict(x1=a[0],y1=a[1],x2=b[0],y2=b[1],**{'class':'stair-line','data-rise':tread['rise'],'data-z-mm':tread['z_mm']}))
    path_local=[(875,-600),(875,3015),(2225,3015),(2225,-600)]
    pts=[stair_point(model['stair'],x,y) for x,y in path_local]
    element(guides,'polyline',{'points':' '.join(f'{x},{y}' for x,y in pts),'class':'stair-line'})
    endpoint=pts[-1] if model['floor']=='ground' else pts[0]
    # Arrowhead follows the final/initial leg; both labels preserve actual travel.
    before=pts[-2] if model['floor']=='ground' else pts[1]
    dx=0 if endpoint[0]==before[0] else (1 if endpoint[0]>before[0] else -1)
    dy=0 if endpoint[1]==before[1] else (1 if endpoint[1]>before[1] else -1)
    a=(endpoint[0]-dx*220-dy*100,endpoint[1]-dy*220+dx*100);b=(endpoint[0]-dx*220+dy*100,endpoint[1]-dy*220-dx*100)
    element(guides,'polyline',{'points':f'{a[0]},{a[1]} {endpoint[0]},{endpoint[1]} {b[0]},{b[1]}','class':'stair-line'})
    if model['floor']=='upper':
        void_source=element(guides,'g',{'id':'floor-opening-source','display':'none'})
        for r in stair['opening']:
            a,b,c,d=r;element(void_source,'rect',dict(x=a,y=b,width=c-a,height=d-b,**{'data-floor-opening':'true'}))
        element(guides,'path',{'d':path_data(loops(boundaries({'void':stair['opening']}),'void')),'class':'stair-void'})
    for pad in (stair['lower_pad'] if model['floor']=='ground' else stair['upper_pad'],):
        a,b,c,d=pad;element(world.find("./*[@id='clearance-guides']"),'rect',dict(x=a,y=b,width=c-a,height=d-b,**{'class':'walk-pad','data-stair-pad':'true'}))
    for item in model['builtins']:
        a,b,c,d=item['rect']
        if not rectangle_fits((a,b,c,d),model['clear'][item['space']]):raise ValueError('Built-in does not fit programmed room')
        element(world,'rect',dict(x=a,y=b,width=c-a,height=d-b,**{'class':'functional-item','data-function':item['kind']}))
        height=bounds(model['footprint'])[3]
        element(root.find(".//*[@id='room-labels']"),'text',dict(x=(a+c)//2,y=height-(b+d)//2,**{'class':'plan-label','data-builtin-label':'true'}),'Linen')
    for group in root.findall('.//*[@data-room-label]'):
        sid=group.get('data-room-label')
        if sid!='stair' and rule_for(model['program'],sid)['role']=='circulation':
            x,y,c,d=largest_rectangle(model['clear'][sid])
            if c-x<3000 and d-y>2*(c-x):
                height=bounds(model['footprint'])[3];group.set('transform',f'translate({(x+c)//2} {height-(y+d)//2}) rotate(-90)')
    # Stair labels are deliberately offset from the drawn flights and landings.
    for group in root.findall(".//*[@data-room-label='stair']"):
        root.find(".//*[@id='room-labels']").remove(group)
    ET.indent(root)
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def read_floor(path):
    """Read actual SVG room geometry; revalidate program and derived geometry.

    This bounded authoring contract supports regeneration, not arbitrary SVG
    editor transforms. Required relationships are sourced from the embedded brief.
    """
    root=ET.parse(path).getroot() if not isinstance(path,ET.Element) else path
    if root.get('data-room-program-schema')!='1' or root.get('data-units')!='mm':raise ValueError('Room-program SVG schema1/mm required')
    if root.get('transform'):raise ValueError('Unsupported SVG source transform')
    meta=json.loads(root.find("./*[@id='house-program']").text);floor=meta['floor'];validate_program(meta['program'])
    if root.get('data-floor-z-mm')!=('0' if floor=='ground' else '3000'):raise ValueError('Floor elevation mismatch')
    world=root.find("./*[@id='world-mm']")
    space_source=world.find("./*[@id='spaces-source']")
    if space_source is None or space_source.get('transform'):raise ValueError('Unsupported SVG source transform')
    def rects(group):
        result=[]
        if group is None or group.get('transform'):raise ValueError('Unsupported SVG source layer')
        for item in group:
            if item.tag!=f'{{{NS}}}rect' or item.get('transform'):raise ValueError('Unsupported SVG room geometry')
            x,y,w,h=[int(item.get(k)) for k in ('x','y','width','height')];result.append((x,y,x+w,y+h))
        return result
    spaces={}
    for item in world.findall(f"./*[@id='spaces-source']/{{{NS}}}g"):
        sid=item.get('data-space-id')
        if sid in spaces:raise ValueError('Duplicate SVG room')
        spaces[sid]=rects(item)
    stub=dict(id=meta['scheme'],name=meta['profile'],stair=meta['stair'],builtins=meta['builtins'])
    stub[floor]=spaces;stub[floor+'_connections']=meta['connections']
    result=derive_floor(meta['program'],stub,floor)
    actual=rects(world.find("./*[@id='footprint-source']"))
    if union_rectangles(actual)!=result['footprint']:raise ValueError('SVG footprint does not match rooms')
    if world.get('transform')!=f"translate(0 {bounds(actual)[3]}) scale(1 -1)":raise ValueError('Unexpected SVG coordinate basis')
    if sorted(rects(world.find("./*[@id='wall-cells']")))!=sorted(result['walls']):raise ValueError('Stale program wall geometry')
    expected=ET.fromstring(export_floor(result,stair_model(meta['program'],meta['stair'])))
    for group in ('shared-boundaries','opening-source','wall-footprint','stair-geometry'):
        current=world.find(f"./*[@id='{group}']");wanted=expected.find(f".//*[@id='{group}']")
        def canonical(node):return node.tag,sorted(node.attrib.items()),(node.text or '').strip(),[canonical(c) for c in node]
        if canonical(current)!=canonical(wanted):raise ValueError('Stale program SVG group: '+group)
    return result


def paired_svg(house):
    """One reviewable native SVG per house, containing both semantic floor SVGs."""
    payloads=[ET.fromstring(export_floor(house['floors'][f],house['stair'])) for f in ('ground','upper')]
    vb=[list(map(float,root.get('viewBox').split())) for root in payloads]
    width=round(max(v[2] for v in vb));height=round(max(v[3] for v in vb));gap=700
    root=ET.Element(f'{{{NS}}}svg',dict(viewBox=f'0 0 {2*width+gap} {height+900}',width='1600',height=str(round(1600*(height+900)/(2*width+gap))),**{'data-house-program-schema':'1','data-units':'mm','data-scheme-id':house['scheme']['id']}))
    element(root,'title',{},house['scheme']['name'])
    element(root,'style',{},'.floor-heading{font-family:Arial,sans-serif;font-size:320px;fill:currentColor}')
    for i,(floor,item) in enumerate(zip(('ground','upper'),payloads)):
        x=i*(width+gap);element(root,'text',dict(x=x+width//2,y=400,**{'text-anchor':'middle','class':'floor-heading'}),'GROUND · UP' if floor=='ground' else 'UPPER · DOWN / OPENING')
        for node in item.iter():
            if node.get('id'):
                node.set('data-original-id',node.get('id'));node.set('id',floor+'__'+node.get('id'))
        camera=[vb[i][0],vb[i][1]-(height-vb[i][3]),width,height]
        item.set('viewBox',' '.join(f'{v:g}' for v in camera))
        item.set('x',str(x));item.set('y','700');item.set('width',str(width));item.set('height',str(height));root.append(item)
    ET.indent(root);return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def read_house(path):
    """Read a paired native SVG, restoring child IDs and validating both floors."""
    root=ET.parse(path).getroot()
    if root.get('data-house-program-schema')!='1' or root.get('data-units')!='mm':raise ValueError('Paired house SVG schema/mm required')
    floors={}
    for child in root.findall(f'./{{{NS}}}svg'):
        child=ET.fromstring(ET.tostring(child))
        for node in child.iter():
            if node.get('data-original-id'):node.set('id',node.attrib.pop('data-original-id'))
        model=read_floor(child)
        if model['floor'] in floors:raise ValueError('Duplicate floor')
        floors[model['floor']]=model
    if set(floors)!={'ground','upper'} or floors['ground']['program']!=floors['upper']['program']:raise ValueError('Mismatched floor programs')
    stair=validate_house(floors['ground']['program'],dict(stair=floors['ground']['stair']),floors)
    return dict(floors=floors,stair=stair)


def build(program):
    validate_program(program)
    output=[]
    for scheme in schemes(program):
        floors={f:derive_floor(program,scheme,f) for f in ('ground','upper')}
        stair=validate_house(program,scheme,floors)
        output.append(dict(scheme=scheme,floors=floors,stair=stair))
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--program',type=Path)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Use a fresh output directory')
    program=load_program(args.program);houses=build(program);args.output.mkdir(parents=True)
    receipt=dict(program=program['id'],scope='Three authored parametric program-first schematics; no general solver, engineering or Blender acceptance',schemes=[])
    (args.output/'room-program.json').write_text(json.dumps(program,indent=2)+'\n',encoding='utf-8')
    for house in houses:
        scheme=house['scheme'];row=dict(id=scheme['id'],name=scheme['name'],note=scheme['note'],floors=[],stair=house['stair'])
        for floor,model in house['floors'].items():
            path=args.output/(model['id']+'.svg');payload=export_floor(model,house['stair']);path.write_bytes(payload);read_floor(path)
            source={k:v for k,v in model.items() if k not in ('edges','physical_edges')};source['edges']=[asdict(e) for e in model['edges']]
            (args.output/(model['id']+'.json')).write_text(json.dumps(source,sort_keys=True,indent=2)+'\n',encoding='utf-8')
            row['floors'].append(dict(id=model['id'],floor=floor,svg=str(path.resolve()),sha256=hashlib.sha256(payload).hexdigest(),gross_m2=area(model['footprint'])/1e6,clear_m2=sum(area(r) for sid,r in model['clear'].items() if sid!='stair')/1e6,room_areas={s:round(area(r)/1e6,2) for s,r in model['clear'].items()},checks='program/fit/physical-walk/openings/privacy pass'))
        receipt['schemes'].append(row)
        pair=args.output/(scheme['id']+'.svg');pair.write_bytes(paired_svg(house));read_house(pair);row['paired_svg']=str(pair.resolve());row['paired_sha256']=hashlib.sha256(pair.read_bytes()).hexdigest()
    (args.output/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(id=r['id'],gross_m2=round(sum(f['gross_m2'] for f in r['floors']),2),checks='program, clearances, aligned stair, upper containment, wet stack, native SVG roundtrip pass') for r in receipt['schemes']],indent=2))


if __name__=='__main__':main()
