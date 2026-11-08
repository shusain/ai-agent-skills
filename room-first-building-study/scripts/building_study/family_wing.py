"""Build #890 family-wing standalone construction study in local Blender 5.

Invoke through scripts/build_blender.py in a separate factory-startup process.
Reads the approved paired SVG through its existing semantic validator. Writes
only the requested fresh output folder: editable .blend, optional renders and receipts.
No source SVG, production asset, Unreal file or running UI scene is modified.
"""
import sys, math, json, hashlib, time
from pathlib import Path
from fractions import Fraction
from . import RESOURCE_ROOT
from .blender_parts import *
from .framing import stations,wall_domains
from .room_first_house import read_house
from .clearance_geometry import door_frame, landing, sweep_fits, rectangle_fits
import bmesh

def configure(args):
    """Validate the selected example before clearing a factory-startup scene."""
    global OUT,SOURCE,HOUSE,FLOORS,STAIR,scene,B,CHECKS,DOMAINS,OPENINGS,FURNITURE,P,T,TH,WALL_TOP,STUD_TOP,JOIST_BOTTOM,TRANSFER_BOTTOM
    if not bpy.app.background:raise RuntimeError('Use a separate background Blender process; do not reset an interactive scene')
    SOURCE=args.source.resolve()
    digest=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest!='2f6067344754366695999646d7cb69a890d11d81855b63d61360ea98f313827a':
        raise ValueError('This bounded Blender recipe requires the bundled reviewed family-wing SVG. Adapt roof, structure, fitout and identity together for another layout.')
    HOUSE=read_house(SOURCE);FLOORS=HOUSE['floors'];STAIR=HOUSE['stair']
    P=args.profile;TH=P.stud_mm;T=TH/1000;WALL_TOP=P.wall_top_m;STUD_TOP=P.stud_top_m
    JOIST_BOTTOM=.047+P.joist_depth_mm/1000;TRANSFER_BOTTOM=WALL_TOP-P.header_depth_mm/1000
    OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=False)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.name='01 | Construction timeline'
    scene.unit_settings.system='IMPERIAL' if P.system=='us' else 'METRIC'
    scene.unit_settings.length_unit='FEET' if P.system=='us' else 'METERS'
    scene['framing_profile_json']=json.dumps(P.to_dict())
    B=Builder(scene)
    CHECKS={'source_sha256':digest,'source':str(SOURCE),'units':'metres; source integer millimetres','floor_datums_m':[0,3], 'checks':{},'limitations':['Conceptual timber sizes and bearing arrangement; no structural engineering or building-code approval.','No modeled services; reserved wet chase and underfloor route only.','Study detail; no engine integration, LOD, collision or production performance claim.']}
    DOMAINS={};OPENINGS={};FURNITURE={}
    CHECKS['framing_profile']=P.to_dict()

def log(s):print(s,flush=True)
def clipped(name,r,domain,z0,z1,mat,stage,level,host=''):
    return B.rects(name,intersect([r],domain),z0,z1,mat,stage,level,host)

def transfer_plan():
    raw=[(x-P.interior_depth_mm/2,0,x+P.interior_depth_mm/2,end) for x,end in [(2600,10000),(4400,8300),(7500,8300)]]
    return intersect(raw,inset(FLOORS['upper']['footprint'],59))

def domains(level,m):
    base=wall_domains(m,P);f=base['f'];iw=base['iw'];extcore=base['extcore'];intcore=base['intcore']
    extlining=diff(band(f,235,250),iw)
    intlining=diff(diff(iw,inset(iw,15)),band(f,0,235))
    d=dict(f=f,iw=iw,extcore=extcore,intcore=intcore,core=union(extcore+intcore),
           sheathing=band(f,47,59),membrane=band(f,45,47),cladding=band(f,0,20),
           lining=union(extlining+intlining))
    DOMAINS[level]=d
    byid={e.id:e for e in m['edges']};holes=[]
    for op in m['openings']:
        e=byid[op['host']]
        r=wall_rect(e,op['lo']-50,op['hi']+50,e.at-400,e.at+400)
        holes.append(dict(op=op,e=e,rect=r,lo=max(0,op['sill_mm']-50)/1000,
                          hi=(op['sill_mm']+op['height_mm']+50)/1000))
    OPENINGS[level]=holes
    # Layer regions are a single shared arrangement, including concave corners.
    assert not intersect(extcore,intcore)
    assert not intersect(d['lining'],d['core'])
    CHECKS['checks'][level+'_wall_layer_regions_disjoint']=True
    return d

def skins(level,z):
    m=FLOORS[level];d=DOMAINS[level];holes=OPENINGS[level]
    heights=sorted({0,WALL_TOP,*[h[k] for h in holes for k in ('lo','hi')]})
    for key,mat,stage in [('sheathing','osb',10),('membrane','membrane',12),('cladding','cladding',14),('lining','lining',17)]:
        for lo,hi in zip(heights,heights[1:]):
            cuts=[h['rect'] for h in holes if h['lo']<(lo+hi)/2<h['hi']]
            region=diff(d[key],cuts)
            B.rects(f'{level}/{key}',region,z+lo,z+hi,mat,stage,level,assembly=key)
    # Continuous exterior floor-edge wrapping joins both story wall skins.
    for key,mat,stage in [('sheathing','osb',10),('membrane','membrane',12),('cladding','cladding',14)]:
        B.rects(level+'/'+key+' floor edge',d[key],z-JOIST_BOTTOM,z,mat,stage,level,assembly=key)
    # A narrow painted belt conceals the intentional cladding movement joint.
    expanded=union([(a-8,b-8,c+8,d0+8) for a,b,c,d0 in d['f']])
    B.rects(level+'/floor belt trim',diff(expanded,inset(d['f'],20)),z-.055,z+.025,'white',14,level)
    # Rainscreen battens: small vertical strips stay within the 25mm cavity.
    rain=band(d['f'],20,20+P.batten_depth_mm)
    for es,lo,hi in merged_runs([e for e in m['physical_edges'] if e.exterior]):
        e=es[0]
        for a in stations(lo+100,hi,P.stud_spacing_mm,origin=lo+100):
            r=wall_rect(e,a-P.batten_width_mm/2,a+P.batten_width_mm/2,e.at-300,e.at+300)
            for l,h in zip(heights,heights[1:]):
                cuts=[v['rect'] for v in holes if v['lo']<(l+h)/2<v['hi']]
                B.rects(level+'/rainscreen batten',diff(intersect([r],rain),cuts),z+l,z+h,'timber',14,level,e.id)

def frame(level,z):
    m=FLOORS[level];d=DOMAINS[level];stage=4 if level=='ground' else 7
    holes=OPENINGS[level];core=d['core'];occupied=[];wood=[]
    transfers=transfer_plan() if level=='ground' else []
    wood.extend((r,TRANSFER_BOTTOM,WALL_TOP) for r in transfers)
    # Full continuous plates are unioned once so all T and corner nodes close.
    for lo,hi,label in [(0,T,'sole plate'),(STUD_TOP,STUD_TOP+T,'top plate A'),(STUD_TOP+T,WALL_TOP,'top plate B')]:
        cuts=[h['rect'] for h in holes if h['lo']<(lo+hi)/2<h['hi']]
        region=diff(core,cuts+(transfers if lo>=TRANSFER_BOTTOM else []));B.rects(level+'/'+label,region,z+lo,z+hi,'timber',stage,level)
        wood.extend((r,lo,hi) for r in region)
    def member(name,r,lo=T,hi=STUD_TOP,host='',dedup=False,grid_station=None,axis=None):
        regions=intersect([r],core)
        if dedup:
            regions=diff(regions,occupied);occupied.extend(regions)
        # Studs bear on, rather than pass through, the upper transfer beams.
        pieces=[(regions,lo,min(hi,TRANSFER_BOTTOM)),(diff(regions,transfers),max(lo,TRANSFER_BOTTOM),hi)] if transfers else [(regions,lo,hi)]
        for rs,l,h in pieces:
            if h<=l:continue
            for region in rs:
                objects=B.rects(level+'/'+name,[region],z+l,z+h,'timber',stage,level,host)
                if grid_station is not None:
                    for obj in objects:
                        obj['framing_grid_role']='wall-stud';obj['grid_station_mm']=grid_station;obj['grid_axis']=axis
                wood.append((region,l,h))
    runs=merged_runs(m['physical_edges']);blocking_requests=[]
    # Own convex/concave exterior corner backing before the ordinary stud grid.
    # Three selected stud thicknesses fit the exterior band; clipping resolves returns.
    ex=[es[0] for es,lo,hi in runs if es[0].exterior]
    for a in ex:
        for b in ex:
            if a.axis!='x' or b.axis!='y':continue
            # Use merged endpoints, not room-boundary subdivisions.
            ar=next((lo,hi) for es,lo,hi in runs if a is es[0]);br=next((lo,hi) for es,lo,hi in runs if b is es[0])
            if not(ar[0]<=b.at<=ar[1] and br[0]<=a.at<=br[1]):continue
            sx=1 if b.positive else -1;sy=1 if a.positive else -1
            for i in range(3):
                x0,x1=sorted((b.at+sx*(59+TH*i),b.at+sx*(59+TH*(i+1))))
                y0,y1=sorted((a.at+sy*59,a.at+sy*P.exterior_core_end_mm))
                member('three stud corner',(x0,y0,x1,y1),dedup=True)
    for es,lo,hi in runs:
        e=es[0];hosts={v.id for v in es};hs=[h for h in holes if h['e'].id in hosts]
        if e.exterior:
            s=1 if e.positive else -1;p,q=sorted((e.at+s*59,e.at+s*P.exterior_core_end_mm))
        else:p,q=e.at-P.interior_depth_mm/2,e.at+P.interior_depth_mm/2
        def r(a,b):return wall_rect(e,a,b,p,q)
        # Explicit king/jack studs and complete rough opening assemblies.
        for h in hs:
            a=h['op']['lo']-50;b=h['op']['hi']+50;head=h['hi'];header=min(P.header_depth_mm/1000,STUD_TOP-head)
            assert header>=.14
            for station in (a-1.5*TH,b+1.5*TH):member('king stud',r(station-TH/2,station+TH/2),host=h['op']['id'],dedup=True)
            for station in (a-TH/2,b+TH/2):member('jack stud',r(station-TH/2,station+TH/2),hi=head,host=h['op']['id'])
            hw=P.exterior_header_width_mm if e.exterior else P.interior_depth_mm;centre=(p+q)/2
            member('opening header',wall_rect(e,a-TH,b+TH,centre-hw/2,centre+hw/2),head,head+header,h['op']['id'])
            if h['lo']>0:member('window rough sill',r(a,b),h['lo']-T,h['lo'],h['op']['id'])
            for station in stations(a+P.stud_spacing_mm/2,b,P.stud_spacing_mm,origin=a+P.stud_spacing_mm/2):
                if h['lo']>.1:member('lower cripple',r(station-TH/2,station+TH/2),hi=h['lo']-T,host=h['op']['id'])
                if head+header<STUD_TOP-.001:member('upper cripple',r(station-TH/2,station+TH/2),head+header,STUD_TOP,h['op']['id'])
        # End/corner backing and grid studs, including T-junction backing.
        positions=[lo+TH/2,hi-TH/2,lo+1.5*TH,hi-1.5*TH,lo+2.5*TH,hi-2.5*TH]
        grid=list(stations(lo+P.exterior_depth_mm+10,hi-P.exterior_depth_mm-10,P.stud_spacing_mm))
        positions+=grid
        for other in m['physical_edges']:
            if other.axis!=e.axis and lo<other.at<hi and other.lo<=e.at<=other.hi:
                positions.extend((other.at-TH,other.at,other.at+TH))
        for a in sorted(set(positions)):
            if any(h['op']['lo']-(3*TH+5)<a<h['op']['hi']+(3*TH+5) for h in hs):continue
            member('stud / corner backing',r(a-TH/2,a+TH/2),host=e.id,dedup=True,grid_station=a if a in grid else None,axis=e.axis)
        # One row of selected nogging; don't bridge any opening or stud.
        raw=intersect([r(lo,hi)],core)
        blocking_requests.append((raw,e.id))
    # Resolve only after all perpendicular wall studs have been owned.
    for raw,host in blocking_requests:
        cuts=[rr for rr,l,h in wood if l<1.27<h]+[h['rect'] for h in holes if h['lo']<1.3<h['hi']]
        for rr in diff(raw,cuts):member('blocking',rr,1.25,1.25+T,host)
    # Insulation is the actual free cavity, subtracting wood per height band.
    zs=sorted({T,STUD_TOP,*[max(T,min(STUD_TOP,v)) for _,a,b in wood for v in (a,b)],*[v for h in holes for v in (h['lo'],h['hi']) if T<v<STUD_TOP]})
    for a,b in zip(zs,zs[1:]):
        mid=(a+b)/2;cuts=[r for r,l,h in wood if l<mid<h]+[h['rect'] for h in holes if h['lo']<mid<h['hi']]
        B.rects(level+'/cavity insulation',diff(core,cuts),z+a,z+b,'insulation',16,level)
    CHECKS['checks'][level+'_frame_openings']=len(holes)

def foundations():
    f=FLOORS['ground']['footprint'];m=FLOORS['ground']
    # Inward bands alone cannot express outside foundation width: create one
    # union of strips, so shared corners never leave gaps or duplicate columns.
    strips=[];feet=[]
    for es,lo,hi in merged_runs([e for e in m['physical_edges'] if e.exterior]):
        e=es[0];s=1 if e.positive else -1;centre=e.at+s*(59+P.exterior_depth_mm/2)
        strips.append(wall_rect(e,lo-21,hi+21,centre-150,centre+150))
        feet.append(wall_rect(e,lo-196,hi+196,centre-325,centre+325))
    B.rects('foundation/continuous strip footing',union(feet),-1.25,-.95,'concrete',1)
    sill_bottom=-JOIST_BOTTOM-T;bearer_bottom=-JOIST_BOTTOM-P.bearer_depth_mm/1000
    B.rects('foundation/stem wall',union(strips),-.95,sill_bottom,'concrete',1)
    B.rects('foundation/damp proof sill gasket',band(f,59,P.exterior_core_end_mm),sill_bottom-.003,sill_bottom,'dark',1)
    B.rects('foundation/treated sill',band(f,59,P.exterior_core_end_mm),sill_bottom,-JOIST_BOTTOM,'timber',2,'ground')
    for x in (2.6,4.4,7.5):
        for y in (1.5,4.5,7.5,9.25):
            if rectangle_fits((int(x*1000)-250,int(y*1000)-250,int(x*1000)+250,int(y*1000)+250),f):
                B.box('foundation/pier pad',(x-.35,y-.35,x+.35,y+.35),-1.25,-1,'concrete',1)
                B.box('foundation/pier',(x-.15,y-.15,x+.15,y+.15),-1,bearer_bottom,'concrete',1)
                B.box('foundation/pier cap',(x-.16,y-.16,x+.16,y+.16),bearer_bottom-.015,bearer_bottom,'steel',2,'ground')
    # Footings and below-floor girders sit below usable internal floor space.
    for x in (2.6,4.4,7.5):
        B.rects('ground/LVL bearer',intersect([(x*1000-P.bearer_width_mm/2,0,x*1000+P.bearer_width_mm/2,12000)],inset(f,59)),bearer_bottom,-JOIST_BOTTOM,'timber',2,'ground')

def floor(level,z):
    m=FLOORS[level];f=m['footprint'];upper=level=='upper';stage=5 if upper else 2
    holes=STAIR['opening'] if upper else []
    region=diff(f,holes);DOMAINS[level]['floor']=region
    # Doubled stair headers/trimmers live outside, never across, the true void.
    trimmer=P.interior_depth_mm
    rings=diff(union([(a-trimmer,b-trimmer,c+trimmer,d+trimmer) for a,b,c,d in holes]),holes) if holes else []
    rings=intersect(rings,inset(f,59))
    B.rects(level+'/stair trimmer and header',rings,z-JOIST_BOTTOM,z-.047,'timber',stage,level)
    # Rim boards follow the actual stepped footprint, with no duplicate corners.
    rim_end=59+P.rim_mm;rim=band(f,59,rim_end)
    B.rects(level+'/rim board',diff(rim,holes),z-JOIST_BOTTOM,z-.047,'timber',stage,level)
    floorcore=diff(inset(f,rim_end),holes+rings)
    supports=[59+P.exterior_depth_mm/2,2600,4400,7500,12500-59-P.exterior_depth_mm/2]
    for yy in stations(P.joist_spacing_mm,12000,P.joist_spacing_mm):
        for x0,x1 in zip(supports,supports[1:]):
            for r in intersect([(x0,yy-P.flange_width_mm/2,x1,yy+P.flange_width_mm/2)],floorcore):
                # Selected-profile flanges/web; all parts editable.
                a,b,c,d=r
                # A header/rim may clip an arrangement cell across its width.
                # Do not turn that sliver into a ripped engineered I-joist.
                if abs(d-b-P.flange_width_mm)>.00001:continue
                fl=P.flange_thickness_mm/1000
                B.rects(level+'/I joist lower flange',[r],z-JOIST_BOTTOM,z-JOIST_BOTTOM+fl,'timber',stage,level)
                upper_objects=B.rects(level+'/I joist upper flange',[r],z-.047-fl,z-.047,'timber',stage,level)
                for obj in upper_objects:obj['framing_grid_role']='floor-joist';obj['grid_station_mm']=yy;obj['grid_axis']='y'
                web=(a,(b+d)/2-P.web_mm/2,c,(b+d)/2+P.web_mm/2)
                B.rects(level+'/I joist web',[web],z-JOIST_BOTTOM+fl,z-.047-fl,'osb',stage,level)
    if upper:
        # Exposed transfer beams: fixed locations at stair wall nodes and the
        # quiet-wing wall. No columns are placed in public circulation routes.
        for x,ys in [(2.6,[0,5,7,10]),(4.4,[0,2.5,6.5,8.3]),(7.5,[0,2.5,6.5,8.3])]:
            for a,b in zip(ys,ys[1:]):
                raw=[(x*1000-P.interior_depth_mm/2,a*1000,x*1000+P.interior_depth_mm/2,b*1000)]
                B.rects('upper/transfer LVL beam',intersect(raw,inset(f,59)),z-3+TRANSFER_BOTTOM,z-JOIST_BOTTOM,'timber',5,'ground')
    # Panel grid retains individual sheets and the exact upper opening.
    for x in range(0,13000,1200):
        for y in range(0,12000,2400):
            panels=intersect([(x,y,x+1200,y+2400)],region)
            B.rects(level+'/22mm subfloor panel',panels,z-.047,z-.025,'osb',6 if upper else 3,level)
    B.rects(level+'/acoustic underlay',region,z-.025,z-.018,'dark',18,level)
    for room,rs in m['clear'].items():
        finish=intersect(rs,region)
        mat='tile' if room in ('wc','utility','bath','kitchen') else 'oak'
        B.rects(level+'/'+room+' floor finish',finish,z-.018,z,mat,18,level,room)
    # Hidden, separate ceilings make floor interiors easy to review.
    ceiling=diff(f,STAIR['opening']) if level=='ground' else f
    B.rects(level+'/ceiling lining',ceiling,z+2.685,z+2.700,'lining',17,level,assembly='ceiling')
    CHECKS['checks'][level+'_floor_area_m2']=area(region)/1e6
    CHECKS['checks'][level+'_floor_opening_area_m2']=area(intersect(region,holes))/1e6
    assert not intersect(region,holes)

def openings(level,z):
    m=FLOORS[level]
    for h in OPENINGS[level]:
        e=h['e'];o=h['op'];a=o['lo']/1000;b=o['hi']/1000;sill=o['sill_mm']/1000;head=sill+o['height_mm']/1000
        sign=1 if e.positive else -1
        at=e.at/1000
        if e.exterior:p,q=sorted((at+sign*.055,at+sign*.22))
        else:p,q=at-.075,at+.075
        def r(lo,hi,pl=p,qh=q):return (lo,pl,hi,qh) if e.axis=='x' else (pl,lo,qh,hi)
        mat='white' if o['kind']=='window' else 'oak'
        for lo,hi in [(a-.05,a),(b,b+.05)]:B.box(level+'/'+o['id']+'/jamb',r(lo,hi),z+sill,z+head+.05,mat,13,level,o['id'])
        B.box(level+'/'+o['id']+'/frame head',r(a,b),z+head,z+head+.05,mat,13,level,o['id'])
        if o['kind']=='window':
            B.box(level+'/'+o['id']+'/sill',r(a-.07,b+.07,p-.035,q+.035),z+sill-.05,z+sill,mat,13,level,o['id'])
            # Slim frame/mullion preserves source clear aperture, glass in middepth.
            mid=(p+q)/2
            B.box(level+'/'+o['id']+'/double glazing',r(a+.025,b-.025,mid-.007,mid+.007),z+sill+.025,z+head-.025,'glass',13,level,o['id'])
            B.box(level+'/'+o['id']+'/mullion',r((a+b)/2-.022,(a+b)/2+.022,mid-.03,mid+.03),z+sill,z+head,'white',13,level,o['id'])
            B.box(level+'/'+o['id']+'/lower sash',r(a,b,mid-.03,mid+.03),z+sill,z+sill+.035,'white',13,level,o['id'])
        else:
            hinge,tangent,normal=door_frame(e,o,o['space'])
            hx,hy=(v/1000 for v in hinge);tx,ty=tangent;nx,ny=normal
            # Open65 degrees for review; local prism transformed about true hinge.
            angle=math.radians(65);vx=tx*math.cos(angle)+nx*math.sin(angle);vy=ty*math.cos(angle)+ny*math.sin(angle)
            width=b-a-.006
            door=B.box(level+'/'+o['id']+'/door leaf',(-width/2,-.02,width/2,.02),z+.012,z+head-.006,'oak',13,level,o['id'])
            door.location.x=hx+vx*width/2;door.location.y=hy+vy*width/2;door.rotation_euler.z=math.atan2(vy,vx)
            handle=(hx+vx*(width-.09),hy+vy*(width-.09),z+1.02)
            B.beam(level+'/door lever',handle,(handle[0]-.09*vy,handle[1]+.09*vx,handle[2]),.018,.018,'steel',20,level,o['id'])
        # Both-side architrave around the actual rough opening.
        faces=[(at-.087,at-.075),(at+.075,at+.087)] if not e.exterior else [(at-sign*.012,at),(at+sign*.25,at+sign*.262)]
        for pl,qh in faces:
            pl,qh=sorted((pl,qh))
            for lo,hi in [(a-.105,a-.05),(b+.05,b+.105)]:B.box(level+'/opening casing',r(lo,hi,pl,qh),z+sill-.01,z+head+.105,'white',13,level,o['id'])
            B.box(level+'/opening casing head',r(a-.105,b+.105,pl,qh),z+head+.05,z+head+.105,'white',13,level,o['id'])

def stairs():
    # Source module is consumed directly; no second set of guessed stair dims.
    r=float(Fraction(STAIR['rise_mm']))/1000
    for i in range(8):
        y=2.65+i*.28;z=(i+1)*r
        B.box('stair/lower tread',(4.675,y-.012,5.875,y+.28),z-.035,z,'oak',8,'stair')
        B.box('stair/lower riser',(4.675,y,5.875,y+.018),i*r,z-.035,'timber',8,'stair')
        y=4.89-i*.28;z=(i+10)*r
        B.box('stair/upper tread',(6.025,y-.28,7.225,y+.012),z-.035,z,'oak',8,'stair')
        B.box('stair/upper riser',(6.025,y-.018,7.225,y),(i+9)*r,z-.035,'timber',8,'stair')
    B.box('stair/rise 09 to turn',(4.675,4.89,5.875,4.908),8*r,9*r-.035,'timber',8,'stair')
    B.box('stair/rise 18 to arrival',(6.025,2.632,7.225,2.65),17*r,3-.035,'timber',8,'stair')
    B.rects('stair/turn landing deck',[STAIR['mid_landing']],1.465,1.5,'oak',8,'stair')
    for y in (4.94,5.34,5.74,6.09):B.box('stair/turn landing joist',(4.675,y-T/2,7.225,y+T/2),1.465-P.tie_depth_mm/1000,1.465,'timber',8,'stair')
    for x in (4.72,7.18):
        for y in (4.94,6.09):B.box('stair/landing support post',(x-P.post_mm/2000,y-P.post_mm/2000,x+P.post_mm/2000,y+P.post_mm/2000),0,1.465-P.tie_depth_mm/1000,'timber',8,'stair')
    def notched_stringer(x,upper=False):
        # Horizontal seats meet every tread underside;245mm stock retains an
        # approximately78mm throat at the bottom of each notch.
        base=1.5 if upper else 0;direction=-1 if upper else 1;start=4.89 if upper else 2.65
        top=[]
        for i in range(8):
            zz=base+(i+1)/6-.035
            top.extend([(start+direction*i*.28,zz),(start+direction*(i+1)*.28,zz)])
        end=start+direction*(2.24+.045);endtop=base+1.5-.035
        top.extend([(start+direction*2.24,endtop),(end,endtop)])
        bottom0=base+1/6-.035-P.stringer_depth_mm/1000;bottom1=bottom0+(2.24+.045)/.28/6
        profile=top+[(end,bottom1),(start,bottom0)];n=len(profile)
        verts=[(xx,y,z) for xx in (x-T/2,x+T/2) for y,z in profile]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        mesh=bpy.data.meshes.new('Notched stringer');mesh.from_pydata(verts,[],faces)
        B.register(bpy.data.objects.new('Stringer',mesh),'stair/'+('upper' if upper else 'lower')+' notched stringer',8,'timber','stair')
    for x in (4.72,5.275,5.83):notched_stringer(x)
    for x in (6.07,6.625,7.18):notched_stringer(x,True)
    # Intermediate/top guards and handrails. Posts sit outside1200mm flights.
    railpaths=[[(5.93,2.65,1.116666667),(5.93,4.89,2.45)],[(5.97,4.89,2.616666667),(5.97,2.65,3.95)],[(4.62,4.89,2.55),(4.62,6.20,2.55),(7.28,6.20,2.55),(7.28,4.89,2.55)],[(4.60,2.5,4.05),(4.60,6.30,4.05),(7.30,6.30,4.05),(7.30,2.5,4.05)]]
    for index,path in enumerate(railpaths):
        for a,b in zip(path,path[1:]):
            B.beam('stair/handrail',a,b,.045,.055,'oak',20,'stair')
            length=(Vector(b)-Vector(a)).length;n=max(1,math.ceil(length/.12))
            for i in range(n+1):
                p=Vector(a).lerp(Vector(b),i/n)
                if index==0:base=min(9,1+int(max(0,p.y-2.65)/.28+1e-6))/6
                elif index==1:base=min(18,10+int(max(0,4.89-p.y)/.28+1e-6))/6
                else:base=1.5 if index==2 else 3
                B.beam('stair/baluster',(p.x,p.y,base),p,.016,.016,'steel',20,'stair')
        for p in path:
            if index==0:base=(1 if p[1]<3 else 9)/6
            elif index==1:base=(10 if p[1]>4 else 18)/6
            else:base=1.5 if index==2 else 3
            B.box('stair/newel',(p[0]-.03,p[1]-.03,p[0]+.03,p[1]+.03),base,p[2]+.025,'oak',20,'stair')
    CHECKS['checks']['stair_rises']=18;CHECKS['checks']['stair_rise_m']=r
    CHECKS['checks']['stair_going_m']=.28
    CHECKS['checks']['stair_clear_flight_m']=1.2

def roofs():
    p=math.tan(math.radians(30));eave=5.90
    south=lambda x,y:eave+p*y
    north=lambda x,y:eave+p*(8.3-y)
    left=lambda x,y:eave+p*x
    right=lambda x,y:eave+p*(4.4-x)
    shed=lambda x,y:3.85-.22*(y-8.3)
    faces=[('main south',[(-.35,-.35),(12.85,-.35),(12.85,4.15),(-.35,4.15)],south),
      ('main north',[(-.35,4.15),(12.85,4.15),(12.85,8.65),(4.75,8.65),(2.2,6.1),(-.35,8.65)],north),
      ('rear wing west',[(-.35,8.65),(2.2,6.1),(2.2,10.35),(-.35,10.35)],left),
      ('rear wing east',[(2.2,6.1),(4.75,8.65),(4.75,10.35),(2.2,10.35)],right),
      ('dining shed',[(7.15,8.3),(12.85,8.3),(12.85,12.35),(7.15,12.35)],shed)]
    for name,poly,fn in faces:
        B.prism('roof/'+name+'/18mm OSB',poly,lambda x,y:fn(x,y)+.018,.018,'osb',11,host=name)
        B.prism('roof/'+name+'/breather membrane',poly,lambda x,y:fn(x,y)+.020,.002,'membrane',12,host=name)
        B.prism('roof/'+name+'/metal covering',poly,lambda x,y:fn(x,y)+.049,.001,'steel',15,host=name)
        # Battens follow constantY slices; clip by polygon intersections.
        for yy in [min(y for x,y in poly)+.12+i*.6 for i in range(20)]:
            cross=[]
            for (x1,y1),(x2,y2) in zip(poly,poly[1:]+poly[:1]):
                if (y1<=yy<y2) or (y2<=yy<y1):cross.append(x1+(yy-y1)*(x2-x1)/(y2-y1))
            if len(cross)==2:
                a,b=sorted(cross);a+=.025;b-=.025
                if b-a<.1:continue
                half=P.batten_width_mm/2000;depth=P.batten_depth_mm/1000
                B.prism('roof/'+name+'/batten',[(a,yy-half),(b,yy-half),(b,yy+half),(a,yy+half)],lambda x,y:fn(x,y)+.02+depth,depth,'timber',15,host=name)
        # Raised metal seams run in the pitch direction, clipped to each face.
        axis='y' if name.startswith('main') or name=='dining shed' else 'x'
        vals=[min(v[0 if axis=='y' else 1] for v in poly)+i*.45 for i in range(40)]
        for v in vals:
            hits=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                k=0 if axis=='y' else 1;j=1-k
                if (a[k]<=v<b[k]) or (b[k]<=v<a[k]):hits.append(a[j]+(v-a[k])*(b[j]-a[j])/(b[k]-a[k]))
            if len(hits)==2:
                a,b=sorted(hits);v1=(v,a) if axis=='y' else (a,v);v2=(v,b) if axis=='y' else (b,v)
                B.beam('roof/standing seam',(*v1,fn(*v1)+.06),(*v2,fn(*v2)+.06),.012,.022,'steel',15,'roof',name)
    ridge=eave+p*4.15
    rw=P.ridge_width_mm/1000;rd=P.ridge_depth_mm/1000;offset=rd/2+.005
    B.beam('roof/main ridge',(-.35,4.15,ridge-offset),(12.85,4.15,ridge-offset),rw,rd,'timber',9,'roof')
    B.beam('roof/cross ridge',(2.2,6.1,eave+p*2.2-offset),(2.2,10.35,eave+p*2.2-offset),rw,rd,'timber',9,'roof')
    for a,b in [((-.35,8.65),(2.2,6.1)),((2.2,6.1),(4.75,8.65))]:
        B.beam('roof/valley beam',(*a,north(*a)-offset),(*b,north(*b)-offset),rw,rd,'timber',9,'roof')
        B.beam('roof/valley flashing',(*a,north(*a)+.055),(*b,north(*b)+.055),.28,.004,'steel',15,'roof')
    def rafter(name,a,b,depth,station,axis,origin):
        obj=B.beam(name,a,b,T,depth,'timber',9,'roof')
        obj['framing_grid_role']='roof-rafter';obj['grid_station_mm']=station;obj['grid_origin_mm']=origin;obj['grid_axis']=axis
    depth=P.rafter_depth_mm/1000;rafter_offset=depth*math.cos(math.radians(30))/2+.005
    for xm in stations(-250,12850,P.rafter_spacing_mm,origin=-250):
        x=xm/1000
        rafter('roof/front rafter',(x,-.35,south(x,-.35)-rafter_offset),(x,4.08,south(x,4.08)-rafter_offset),depth,xm,'x',-250)
        end=min(8.65,6.1+abs(x-2.2)) if x<4.75 else 8.65
        rafter('roof/rear rafter',(x,4.22,north(x,4.22)-rafter_offset),(x,end-.035,north(x,end-.035)-rafter_offset),depth,xm,'x',-250)
        B.beam('roof/ceiling tie',(x,.15,5.80),(x,8.15,5.80),T,P.tie_depth_mm/1000,'timber',9,'roof')
        B.beam('roof/collar tie',(x,2.8,7.39),(x,5.5,7.39),T,P.collar_depth_mm/1000,'timber',9,'roof')
    for ym in stations(6350,10350,P.rafter_spacing_mm,origin=6350):
        y=ym/1000
        a=max(-.35,8.3-y);b=min(4.75,y-3.9)
        if a<2.1:rafter('roof/cross west rafter',(a,y,left(a,y)-rafter_offset),(2.13,y,left(2.13,y)-rafter_offset),depth,ym,'y',6350)
        if b>2.3:rafter('roof/cross east rafter',(2.27,y,right(2.27,y)-rafter_offset),(b,y,right(b,y)-rafter_offset),depth,ym,'y',6350)
    shed_depth=P.tie_depth_mm/1000;shed_offset=shed_depth*math.cos(math.atan(.22))/2+.005
    for xm in stations(7200,12850,P.rafter_spacing_mm,origin=7200):
        x=xm/1000
        rafter('roof/dining rafter',(x,8.3,shed(x,8.3)-shed_offset),(x,12.35,shed(x,12.35)-shed_offset),shed_depth,xm,'x',7200)
    hw=P.exterior_header_width_mm/1000
    B.box('roof/dining rear beam',(7.5,11.77-hw/2,12.5,11.77+hw/2),WALL_TOP,WALL_TOP+P.header_depth_mm/1000,'timber',9,'roof')
    ledger_width=T if P.system=='us' else .06
    ledger_depth=P.rafter_depth_mm/1000 if P.system=='us' else .24
    B.box('roof/dining ledger',(7.5,8.3-ledger_width,12.5,8.3),3.76-ledger_depth,3.76,'timber',9,'roof')
    # Gable/end infill from rectangular upper wall tops to the exact roof plane.
    # Panel strips use linear roof heights, so triangles close without stair-step gaps.
    infill_owned={}
    def infill(name,a,b,fn,level,zbase,stageframe):
        length=(Vector(b)-Vector(a)).length;steps=max(1,math.ceil(length/(P.rafter_spacing_mm/1000)))
        # For each interval, a sloping top prism across the250mm wall depth.
        vx=(b[0]-a[0])/length;vy=(b[1]-a[1])/length
        nx,ny=-vy,vx
        for i in range(steps):
            u=i/steps;v=(i+1)/steps
            s=(a[0]+u*(b[0]-a[0]),a[1]+u*(b[1]-a[1]));t=(a[0]+v*(b[0]-a[0]),a[1]+v*(b[1]-a[1]))
            # The directed polygon has interior to its left.
            for lo,hi,mat,stage in [(.047,.059,'osb',10),(.045,.047,'membrane',12),(0,.020,'cladding',14),(.235,.250,'lining',17),(.059,P.exterior_core_end_mm/1000,'insulation',16)]:
                poly=[(s[0]+nx*lo,s[1]+ny*lo),(t[0]+nx*lo,t[1]+ny*lo),(t[0]+nx*hi,t[1]+ny*hi),(s[0]+nx*hi,s[1]+ny*hi)]
                if mat=='insulation':
                    gap=T/2+.0005
                    poly=[(s[0]+vx*gap+nx*lo,s[1]+vy*gap+ny*lo),(t[0]-vx*gap+nx*lo,t[1]-vy*gap+ny*lo),(t[0]-vx*gap+nx*hi,t[1]-vy*gap+ny*hi),(s[0]+vx*gap+nx*hi,s[1]+vy*gap+ny*hi)]
                # Reuse the resolved footprint bands and explicit ownership at
                # all roof-wall corners, rather than overlap independent skins.
                key=(level,mat);prior=infill_owned.setdefault(key,[])
                raw=[tuple(v*1000 for v in (min(x for x,y in poly),min(y for x,y in poly),max(x for x,y in poly),max(y for x,y in poly)))]
                domain=DOMAINS[level]['extcore'] if mat=='insulation' else DOMAINS[level][{'osb':'sheathing','membrane':'membrane','cladding':'cladding','lining':'lining'}[mat]]
                regions=diff(intersect(raw,domain),prior);prior.extend(regions)
                for rect in regions:
                    x,y,u,v=mm(rect);poly2=[(x,y),(u,y),(u,v),(x,v)]
                    tops=[(x,y,max(zbase,fn(x,y))) for x,y in poly2]
                    verts=[(x,y,zbase) for x,y in poly2]+tops
                    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
                    B.register(bpy.data.objects.new(name,mesh),'roof/'+name+'/gable layer',stage,mat,level,assembly='gable infill')
            for end in [s] if i else [s]:
                centre=(59+P.exterior_depth_mm/2)/1000
                cx=end[0]+nx*centre;cy=end[1]+ny*centre;top=fn(cx,cy)-T
                dx=abs(vx)*T/2+abs(nx)*P.exterior_depth_mm/2000;dy=abs(vy)*T/2+abs(ny)*P.exterior_depth_mm/2000
                if top>zbase:B.box('roof/'+name+'/gable stud',(cx-dx,cy-dy,cx+dx,cy+dy),zbase,top,'timber',stageframe,level)
            centre=(59+P.exterior_depth_mm/2)/1000
            B.beam('roof/'+name+'/sloping top plate',(s[0]+nx*centre,s[1]+ny*centre,fn(*s)-T/2),(t[0]+nx*centre,t[1]+ny*centre,fn(*t)-T/2),P.exterior_depth_mm/1000,T,'timber',9,level)
    # Exterior boundary orientation counterclockwise.
    for x,reverse in [(0,True),(12.5,False)]:
        if reverse:
            infill('west south',(0,4.15),(0,0),south,'upper',3+WALL_TOP,9)
            infill('west north',(0,8.3),(0,4.15),north,'upper',3+WALL_TOP,9)
        else:
            infill('east south',(12.5,0),(12.5,4.15),south,'upper',3+WALL_TOP,9)
            infill('east north',(12.5,4.15),(12.5,8.3),north,'upper',3+WALL_TOP,9)
    infill('rear cross east',(4.4,10),(2.2,10),right,'upper',3+WALL_TOP,9)
    infill('rear cross west',(2.2,10),(0,10),left,'upper',3+WALL_TOP,9)
    infill('dining east',(12.5,8.3),(12.5,12),shed,'ground',WALL_TOP,9)
    infill('dining west',(7.5,12),(7.5,8.3),shed,'ground',WALL_TOP,9)
    infill('front eave',(0,0),(12.5,0),lambda x,y:eave,'upper',3+WALL_TOP,9)
    infill('rear eave',(12.5,8.3),(4.4,8.3),lambda x,y:eave,'upper',3+WALL_TOP,9)
    infill('cross west eave',(0,10),(0,8.3),lambda x,y:eave,'upper',3+WALL_TOP,9)
    infill('cross east eave',(4.4,8.3),(4.4,10),lambda x,y:eave,'upper',3+WALL_TOP,9)
    infill('dining rear eave',(12.5,12),(7.5,12),shed,'ground',WALL_TOP,9)
    # Metal ridge caps cover both peak joints independently of roof sheets.
    for poly,fn in [([(-.38,3.99),(12.88,3.99),(12.88,4.15),(-.38,4.15)],south),([(-.38,4.15),(12.88,4.15),(12.88,4.31),(-.38,4.31)],north),([(2.04,6.1),(2.2,6.1),(2.2,10.39),(2.04,10.39)],left),([(2.2,6.1),(2.36,6.1),(2.36,10.39),(2.2,10.39)],right)]:
        B.prism('roof/ridge cap',poly,lambda x,y:fn(x,y)+.075,.002,'steel',15)
    # Horizontal eave closure between upper walls and rafters.
    for a,b,fn in [((-.35,-.35),(12.85,-.35),south),((4.75,8.65),(12.85,8.65),north),((-.35,8.65),(-.35,10.35),left),((4.75,8.65),(4.75,10.35),right),((7.15,12.35),(12.85,12.35),shed)]:
        B.beam('roof/fascia',(*a,fn(*a)-.08),(*b,fn(*b)-.08),.025,.20,'white',14,'roof')
        B.beam('roof/gutter',(*a,fn(*a)-.03),(*b,fn(*b)-.03),.14,.08,'steel',15,'roof')
    # Gable bargeboards and folded verge flashings complete roof perimeter.
    for a,b,fn in [((-.35,-.35),(-.35,4.15),south),((-.35,4.15),(-.35,8.65),north),((12.85,-.35),(12.85,4.15),south),((12.85,4.15),(12.85,8.65),north),((-.35,10.35),(2.2,10.35),left),((2.2,10.35),(4.75,10.35),right),((7.15,8.3),(7.15,12.35),shed),((12.85,8.3),(12.85,12.35),shed)]:
        B.beam('roof/bargeboard',(*a,fn(*a)-.065),(*b,fn(*b)-.065),.035,.20,'white',14,'roof')
        B.beam('roof/verge flashing',(*a,fn(*a)+.055),(*b,fn(*b)+.055),.10,.006,'steel',15,'roof')
    for x,y,top in [(12.75,-.35,south(12.75,-.35)),(12.75,8.65,north(12.75,8.65)),(4.65,10.35,right(4.65,10.35)),(12.75,12.35,shed(12.75,12.35))]:
        B.beam('roof/downpipe',(x,y,-.5),(x,y,top-.05),.075,.075,'steel',15,'roof')
    CHECKS['checks']['roof_surface_count']=len(faces)

def fitout(level,z):
    # Simple solid furniture is dimensioned and tied to source room IDs.
    items=[]
    def item(room,name,r,height,mat='cabinet',bottom=0):
        box=B.box(level+'/'+room+'/'+name,r,z+bottom,z+bottom+height,mat,19,level,room)
        items.append((room,name,tuple(round(v*1000) for v in r)))
        return box
    def table(room,name,r,top=.75,mat='oak'):
        item(room,name+' top',r,.05,mat,top-.05)
        a,b,c,d=r
        for x in (a+.07,c-.07):
            for y in (b+.07,d-.07):item(room,name+' leg',(x-.025,y-.025,x+.025,y+.025),top-.05,'oak')
    def chair(room,x,y,rot=0):
        r=(x-.20,y-.20,x+.20,y+.20);item(room,'chair seat',r,.06,'fabric',.44)
        back=(x-.2,y+.17,x+.2,y+.22) if not rot else ((x+.17,y-.2,x+.22,y+.2) if rot>0 else (x-.22,y-.2,x-.17,y+.2))
        item(room,'chair back',back,.48,'fabric',.48)
        for dx in (-.15,.15):
            for dy in (-.15,.15):item(room,'chair leg',(x+dx-.018,y+dy-.018,x+dx+.018,y+dy+.018),.44,'oak')
    def bed(room,r):
        a,b,c,d=r;item(room,'bed platform',r,.24,'oak',.12)
        item(room,'mattress',(a+.03,b+.03,c-.03,d-.03),.22,'linen',.36)
        item(room,'duvet',(a+.02,b+.02,c-.02,d-.5),.08,'fabric',.57)
        item(room,'headboard',(a-.025,d-.04,c+.025,d+.025),.95,'oak')
        item(room,'pillow',(a+.12,d-.47,c-.12,d-.12),.11,'white',.59)
    if level=='ground':
        table('study','desk',(.25,3.3,.9,4.7));chair('study',1.22,4.05,1)
        item('utility','utility cabinet',(.25,7.3,.88,9.45),.88)
        item('utility','worktop',(.25,7.28,.91,9.47),.04,'counter',.88)
        for y in (7.65,8.35):
            item('utility','laundry appliance',(.30,y-.29,.86,y+.29),.79,'white',.04)
            item('utility','appliance face',(.86,y-.22,.87,y+.22),.43,'steel',.23)
        item('wc','WC cistern',(.29,6.22,.52,6.72),.85,'ceramic')
        item('wc','WC pan',(.52,6.25,1.04,6.68),.42,'ceramic')
        item('wc','wash basin',(.27,5.21,.76,5.72),.18,'ceramic',.72)
        item('living','sofa base',(11.3,.8,12.18,3.6),.43,'fabric')
        item('living','sofa back',(12.0,.8,12.2,3.6),.83,'fabric')
        for y in (.8,3.4):item('living','sofa arm',(11.3,y,12.2,y+.2),.68,'fabric')
        for y in (1.1,2.05,3.0):item('living','sofa cushion',(11.35,y-.3,11.99,y+.3),.13,'linen',.43)
        table('living','coffee table',(9.6,2.1,10.8,2.7),.40)
        item('living','media console',(8.2,.27,9.8,.72),.55)
        item('kitchen','base cabinets',(11.62,5.45,12.24,8.04),.88)
        item('kitchen','stone worktop',(11.59,5.42,12.25,8.06),.04,'counter',.88)
        item('kitchen','sink bowl',(11.69,6.5,12.14,7.04),.06,'steel',.925)
        item('kitchen','hob',(11.68,5.55,12.17,6.07),.016,'dark',.925)
        item('kitchen','fridge',(11.48,4.61,12.24,5.35),1.95,'steel')
        item('kitchen','peninsula',(9.5,7.62,11.6,8.22),.88)
        item('kitchen','peninsula worktop',(9.48,7.60,11.62,8.24),.04,'counter',.88)
        table('dining','dining table',(9.55,9.05,10.45,10.85))
        for x in (9.18,10.82):
            for y in (9.45,10.45):chair('dining',x,y,-1 if x<10 else 1)
    else:
        bed('primary',(1.2,3.0,3.0,5.0))
        item('primary','wardrobe',(.6,.26,3.0,.86),2.25)
        bed('bed2',(.8,7.45,2.2,9.45))
        table('bed2','desk',(.26,6.0,.86,7.3));chair('bed2',1.15,6.6,1)
        item('bed2','wardrobe',(.6,5.59,2.4,6.19),2.2)
        bed('bed3',(11.35,2.6,12.22,4.6))
        table('bed3','desk',(10.65,.26,11.85,.86));chair('bed3',11.25,1.16)
        item('bed3','wardrobe',(9.59,4.33,10.95,4.92),2.2)
        item('bath','bath shell',(11.46,5.2,12.2,6.9),.54,'ceramic')
        item('bath','bath inset',(11.52,5.28,12.14,6.82),.015,'tile',.545)
        item('bath','vanity',(10.6,7.42,12.1,8.05),.8)
        item('bath','basin',(10.88,7.47,11.7,7.97),.12,'ceramic',.8)
        item('bath','WC cistern',(9.62,5.2,10.12,5.42),.83,'ceramic')
        item('bath','WC pan',(9.65,5.42,10.09,5.91),.42,'ceramic')
        item('landing','linen cupboard',(6,.25,7.2,.85),2.25)
    # Every modeled fixture stays in its assigned clear source room. Door pads
    # and full90deg swept sectors are rechecked with these physical obstacles.
    model=FLOORS[level];checks=[]
    for room,name,r in items:
        assert rectangle_fits(r,model['clear'][room]),(level,room,name,r)
    for h in OPENINGS[level]:
        o=h['op'];e=h['e']
        if o['kind']=='window':continue
        obstacles=[r for room,name,r in items if room==o['space']]
        available=diff(model['clear'][o['space']],obstacles)
        assert sweep_fits(e,o,available,50),(level,o['id'],'furniture swing')
        pad=landing(e,o,o['space'],1200)
        assert rectangle_fits(pad,available),(level,o['id'],'furniture landing')
        checks.append(o['id'])
    FURNITURE[level]=items
    CHECKS['checks'][level+'_furniture_in_clear_rooms']=len(items)
    CHECKS['checks'][level+'_furnished_door_pads_and_swings']=checks

def skirting(level,z):
    m=FLOORS[level];d=DOMAINS[level]
    # Offset each clear room edge strip, union, then subtract opening pads.
    for room,rs in m['clear'].items():
        strips=band(rs,0,12)
        # Virtual room boundaries in open zones are deliberately not trimmed.
        actual=union([wall_rect(e,e.lo,e.hi,e.at-275,e.at+275) for e in m['physical_edges']])
        strips=intersect(strips,actual)
        cuts=[h['rect'] for h in OPENINGS[level] if h['lo']==0]
        B.rects(level+'/skirting',diff(strips,cuts),z,z+.09,'white',19,level,room)

def reservations():
    # Metadata-only empties: no pipe/outlet assets and no rendered obstruction.
    for name,loc,size in [('Wet stack: kitchen to bath',(12.125,7.325,1.5),.125),('Underfloor distribution: utility',(1.3,8.5,-.75),.25)]:
        obj=bpy.data.objects.new(name,None);B.reference.objects.link(obj);obj.location=loc
        obj.empty_display_type='CUBE';obj.empty_display_size=size;obj.hide_render=True
        obj['purpose']='Reserved coordination zone; no services geometry'
    scene['utility_route_m']=json.dumps([[1.3,8.5,-.75],[3.5,8.5,-.75],[3.5,6,-.75],[10.5,6,-.75],[12.125,7.325,-.75]])

def camera(scene,name,loc,target,scale=22):
    data=bpy.data.cameras.new(name);obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    obj.location=loc;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO';data.ortho_scale=scale;data.lens=42;scene.camera=obj
    return obj

def lighting(scene):
    scene.unit_settings.system='IMPERIAL' if P.system=='us' else 'METRIC'
    scene.unit_settings.length_unit='FEET' if P.system=='us' else 'METERS'
    world=bpy.data.worlds.new(scene.name+' World');world.use_nodes=True
    world.node_tree.nodes.get('Background').inputs[0].default_value=(.70,.77,.82,1)
    world.node_tree.nodes.get('Background').inputs[1].default_value=.5;scene.world=world
    for name,loc,power,size in [('Key',(-5,-5,17),2100,10),('Fill',(17,9,13),1500,9),('Rim',(1,18,15),1700,8)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc
        obj.rotation_euler=(Vector((6,5,2))-obj.location).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=1500;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    scene.render.film_transparent=False

def scene_objects(name,objects,cut=None):
    out=bpy.data.scenes.new(name);out.unit_settings.system='METRIC';col=bpy.data.collections.new(name+' geometry');out.collection.children.link(col)
    for obj in objects:
        if obj is None:continue
        if cut is None:col.objects.link(obj);continue
        # Presentation-only copies clip the real source mesh. Native assemblies
        # retain complete members and source ownership in the construction scene.
        verts=[obj.matrix_world@v.co for v in obj.data.vertices]
        if not verts or min(v.z for v in verts)>=cut:continue
        cp=obj.copy();cp.data=obj.data.copy();cp.animation_data_clear();col.objects.link(cp)
        if max(v.z for v in verts)>cut:
            bm=bmesh.new();bm.from_mesh(cp.data)
            inv=cp.matrix_world.inverted();point=inv@Vector((0,0,cut));normal=cp.matrix_world.to_3x3().transposed()@Vector((0,0,1))
            result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=point,plane_no=normal,clear_outer=True,clear_inner=False)
            boundary=[e for e in result['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
            if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
            bm.to_mesh(cp.data);bm.free();cp.data.update()
    lighting(out);return out,col

def wall_specimen():
    out=bpy.data.scenes.new('05 | Exploded wall assembly');col=bpy.data.collections.new('Exploded wall specimen');out.collection.children.link(col)
    # Individual layer objects copied from the exact front living-wall region.
    layers=[('Cladding 20mm','cladding',14,-1.7),('Rainscreen 25mm','batten',14,-1.2),('Membrane 2mm','membrane',12,-.65),('OSB 12mm','sheathing',10,-.15),('Studs '+P.stock_labels['exterior'],'stud',4,.6),(f'Insulation {P.exterior_depth_mm:g}mm','insulation',16,1.2),('Lining 15mm','lining',17,2.0)]
    for label,key,stage,shift in layers:
        for obj in B.objects:
            if obj.type!='MESH' or obj.get('level')!='ground' or obj.get('stage')!=stage:continue
            part=obj['part'];match=key in part
            if key=='stud':match=any(v in part for v in ('stud','plate','header','sill','cripple','blocking'))
            if not match:continue
            # Crop this real member to a straight4m wall specimen with window.
            # Axis-aligned original wall members make exact box crop possible.
            if any(abs(v)>.0001 for v in obj.rotation_euler):continue
            vs=[obj.matrix_world@v.co for v in obj.data.vertices]
            lo=[max(min(v[i] for v in vs),[8.0,0,0][i]) for i in range(3)]
            hi=[min(max(v[i] for v in vs),[12.0,.251,WALL_TOP][i]) for i in range(3)]
            if min(hi[i]-lo[i] for i in range(3))<.00001:continue
            cp=obj.copy();cp.data=obj.data.copy();cp.animation_data_clear();col.objects.link(cp)
            # Since these are boxes, resize vertices around their local centre.
            old=[max(v.co[i] for v in cp.data.vertices)-min(v.co[i] for v in cp.data.vertices) for i in range(3)]
            for v in cp.data.vertices:
                for i in range(3):v.co[i]*=(hi[i]-lo[i])/old[i]
            cp.location=((lo[0]+hi[0])/2-8,(lo[1]+hi[1])/2+shift,(lo[2]+hi[2])/2)
            cp.name=label+' | '+obj['part']
        B.label(label,(2,shift-.09,2.98),.18,rotation=(math.pi/2,0,0),collection=col)
    # The cavity is deliberately an annotated void, rather than a services mesh.
    B.label(f'{235-P.exterior_core_end_mm:g}mm reserved service cavity',(2,1.70,.15),.15,rotation=(math.pi/2,0,0),collection=col)
    lighting(out);camera(out,'Wall assembly camera',(9,-10,7),(2,.2,1.4),8.6)
    out.render.resolution_x=1600;out.render.resolution_y=1100
    return out

def junction_detail():
    out=bpy.data.scenes.new('07 | Shared T junction detail');col=bpy.data.collections.new('T junction source crop');out.collection.children.link(col)
    crop=(1.85,4.25,3.2,5.75)
    for obj in B.objects:
        if obj.type!='MESH' or obj.get('level')!='ground':continue
        if obj.get('stage')!=4 and obj.get('part')!='upper/transfer LVL beam':continue
        if any(abs(v)>.0001 for v in obj.rotation_euler):continue
        vs=[obj.matrix_world@v.co for v in obj.data.vertices]
        lo=[max(min(v[i] for v in vs),[crop[0],crop[1],0][i]) for i in range(3)]
        hi=[min(max(v[i] for v in vs),[crop[2],crop[3],WALL_TOP][i]) for i in range(3)]
        if min(hi[i]-lo[i] for i in range(3))<.00001:continue
        cp=obj.copy();cp.data=obj.data.copy();cp.animation_data_clear();col.objects.link(cp)
        old=[max(v.co[i] for v in cp.data.vertices)-min(v.co[i] for v in cp.data.vertices) for i in range(3)]
        for v in cp.data.vertices:
            for i in range(3):v.co[i]*=(hi[i]-lo[i])/old[i]
        cp.location=tuple((lo[i]+hi[i])/2 for i in range(3))
    lighting(out);camera(out,'T junction camera',(6,1,5.4),(2.6,5,1.35),4.6)
    return out

def stage_animation():
    scene.frame_start=1;scene.frame_end=221;scene.render.fps=12
    for i,name in enumerate(STAGES,1):scene.timeline_markers.new(name,frame=1+(i-1)*10)
    scene.timeline_markers.new('Complete / review',frame=201)
    for obj in B.objects:
        st=obj.get('stage',0)
        if not st:continue
        frame=1+(st-1)*10
        for prop in ('hide_render','hide_viewport'):
            setattr(obj,prop,True);obj.keyframe_insert(data_path=prop,frame=max(0,frame-1))
            setattr(obj,prop,False);obj.keyframe_insert(data_path=prop,frame=frame)
        if obj.animation_data:
            action=obj.animation_data.action
            # Blender5 slots store curves in action layers/channel bags.
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for fc in bag.fcurves:
                            for k in fc.keyframe_points:k.interpolation='CONSTANT'
    scene.frame_set(221)

def validate_geometry():
    ids=[o['component_id'] for o in B.objects];assert len(ids)==len(set(ids))
    bad=[]
    for o in B.objects:
        if o.type!='MESH':continue
        if any(not math.isfinite(c) for v in o.data.vertices for c in v.co):bad.append(o.name)
        assert all(abs(s-1)<1e-6 for s in o.scale),o.name
    assert not bad
    unique={o.data.name:o.data for o in B.objects if o.type=='MESH'}
    for mesh in unique.values():
        bm=bmesh.new();bm.from_mesh(mesh)
        assert all(e.is_manifold for e in bm.edges),mesh.name
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
        assert bm.calc_volume(signed=True)>1e-12,mesh.name
        bm.to_mesh(mesh);bm.free();mesh.update()
    CHECKS['checks']['closed_positive_volume_source_meshes']=len(unique)
    # Independent3D check of the actual wall members and their transfer beams.
    # Flush butt contacts are allowed; positive-volume duplicates/clashes fail.
    for level,stage in [('ground',4),('upper',7)]:
        members=[]
        for o in B.objects:
            if o.type!='MESH' or o.get('level')!=level:continue
            if o.get('stage')!=stage and not(level=='ground' and o.get('part')=='upper/transfer LVL beam'):continue
            assert all(abs(a)<1e-6 for a in o.rotation_euler)
            vs=[o.matrix_world@v.co for v in o.data.vertices]
            members.append((o,[min(v[k] for v in vs) for k in range(3)],[max(v[k] for v in vs) for k in range(3)]))
        clashes=[]
        for i,(o,a,b) in enumerate(members):
            for p,c,d in members[i+1:]:
                if all(min(b[k],d[k])-max(a[k],c[k])>1e-5 for k in range(3)):
                    clashes.append((o.name,p.name))
        CHECKS['checks'][level+'_wall_frame_3d_clashes']=clashes
        assert not clashes,clashes[:12]
    # Conservative full tread/landing rectangles against overhead member bounds.
    # Oriented roof members use their AABBs; this can only reduce clear height.
    # Handrails/risers belong to the stair and are not overhead obstructions.
    overhead=[o for o in B.objects if o.type=='MESH' and o.get('stage') in (5,6,9,17) and o.get('level')!='stair']
    bounds=[]
    for o in overhead:
        vs=[o.matrix_world@v.co for v in o.data.vertices]
        bounds.append((o,[min(v[k] for v in vs) for k in range(3)],[max(v[k] for v in vs) for k in range(3)]))
    walks=[(mm(STAIR[k]),z) for k,z in [('mid_landing',1.5),('lower_pad',0),('upper_pad',3),('upper_bridge',3)]]
    walks += [((4.675,2.65+i*.28,5.875,2.65+(i+1)*.28),(i+1)/6) for i in range(8)]
    walks += [((6.025,4.89-(i+1)*.28,7.225,4.89-i*.28),(i+10)/6) for i in range(8)]
    minhead=99;blockers=[]
    for (a,b,c,d),z in walks:
        for o,mn,mx in bounds:
            if min(c,mx[0])-max(a,mn[0])>1e-5 and min(d,mx[1])-max(b,mn[1])>1e-5 and mn[2]>z+.05:
                h=mn[2]-z
                if h<minhead:minhead=h
                if h<2.2:blockers.append((o.name,h))
    CHECKS['checks']['modeled_stair_headroom_full_tread_and_pad_min_m']=round(minhead,4)
    CHECKS['checks']['stair_headroom_blockers']=blockers
    assert not blockers,blockers
    CHECKS['checks']['unique_component_ids']=True;CHECKS['checks']['finite_geometry_unit_scale']=True
    CHECKS['component_count']=len(B.objects)
    CHECKS['counts_by_stage']={name:sum(o.get('stage')==i for o in B.objects) for i,name in enumerate(STAGES,1)}
    CHECKS['objects']=[dict(id=o['component_id'],part=o['part'],stage=o['stage'],level=o['level'],host=o['host']) for o in B.objects]

def main(args):
    configure(args)
    log('Reading approved family-wing SVG; generating assemblies')
    for level,m in FLOORS.items():domains(level,m)
    foundations()
    for level,z in [('ground',0),('upper',3)]:
        frame(level,z);floor(level,z);skins(level,z);openings(level,z);fitout(level,z);skirting(level,z)
        log('Built '+level)
    stairs();roofs();reservations()
    bpy.context.view_layer.update()
    from .framing_checks import verify_framing
    CHECKS['framing_measurements']=verify_framing(scene,P)
    validate_geometry();log('Geometry checks passed; '+str(len(B.objects))+' components')
    lighting(scene);camera(scene,'Construction camera',(24,-29,23),(6,5,3.4),23.3)
    # Site plinth is presentation only, not a building component or animation part.
    plinth=B.box('presentation/site',( -1.8,-1.8,14.3,13.8),-1.5,-1.3,'ground',0)
    mesh_objects=[o for o in B.objects if o.type=='MESH' and o.get('stage')]
    structure,_=scene_objects('02 | Structural study',[o for o in mesh_objects if o['stage']<=9])
    camera(structure,'Structure camera',(23,-28,22),(6,5,3.1),23)
    ground,gcol=scene_objects('03 | Ground floor cutaway',[o for o in mesh_objects if o['level'] in ('ground','stair') and o['stage'] not in (5,6,9) and o.get('assembly')!='ceiling'],cut=1.15)
    camera(ground,'Ground review camera',(6,-4,29),(6,5.4,0),16.7)
    upper,ucol=scene_objects('04 | Upper floor cutaway',[o for o in mesh_objects if o['level'] in ('upper','stair') and o['stage']!=9 and o.get('assembly')!='ceiling'],cut=4.15)
    camera(upper,'Upper review camera',(6,-4,31),(6,4.7,3),16.7)
    for level,col,z in [('ground',gcol,.10),('upper',ucol,3.10)]:
        for room,rs in FLOORS[level]['spaces'].items():
            if room=='stair':continue
            # Label source room at largest clear rectangle; move above furnishings.
            clear=FLOORS[level]['clear'][room];r=max(clear,key=lambda r:(r[2]-r[0])*(r[3]-r[1]))
            text=FLOORS[level]['names'].get(room,room).replace(' / ','\n')
            B.label(text,((r[0]+r[2])/2000,(r[1]+r[3])/2000,z),.20,collection=col)
    specimen=wall_specimen()
    stairscene,_=scene_objects('06 | Stair assembly',[o for o in mesh_objects if o['level']=='stair'])
    # A cropped copy of the actual upper floor supports the top guard in this
    # isolated review; the source floor and animation still own each part once.
    context=bpy.data.collections.new('Actual upper floor / review crop');stairscene.collection.children.link(context)
    for obj in mesh_objects:
        if obj['level']!='upper' or obj['stage'] not in (5,6,18):continue
        if any(abs(v)>.0001 for v in obj.rotation_euler):continue
        vs=[obj.matrix_world@v.co for v in obj.data.vertices]
        lo=[max(min(v[i] for v in vs),[4.4,1.3,2.708][i]) for i in range(3)]
        hi=[min(max(v[i] for v in vs),[7.5,6.5,3][i]) for i in range(3)]
        if min(hi[i]-lo[i] for i in range(3))<.00001:continue
        cp=obj.copy();cp.data=obj.data.copy();cp.animation_data_clear();context.objects.link(cp)
        old=[max(v.co[i] for v in cp.data.vertices)-min(v.co[i] for v in cp.data.vertices) for i in range(3)]
        for v in cp.data.vertices:
            for i in range(3):v.co[i]*=(hi[i]-lo[i])/old[i]
        cp.location=tuple((lo[i]+hi[i])/2 for i in range(3))
    camera(stairscene,'Stair assembly camera',(11,-3,7.5),(5.9,4.3,1.75),8.4)
    junction=junction_detail()
    stage_animation()
    for sc in (structure,ground,upper,specimen,stairscene,junction):sc.frame_set(221)
    bpy.context.window.scene=scene
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.clip_end=300
                a.spaces.active.shading.type='MATERIAL'
    scene['study_schema']=1;scene['source_svg_path']=str(SOURCE);scene['source_svg_sha256']=CHECKS['source_sha256']
    scene['instructions']='Choose scenes for structure, floor cutaways or exploded wall. Timeline1..201 reveals20 separate construction stages; final221. Collections also toggle independently. Services are metadata only.'
    txt=bpy.data.texts.new('READ ME | Family-wing construction study')
    txt.write('Issue #890 / standalone local Blender study\n\n'+scene['instructions']+'\n\nSource: '+str(SOURCE)+'\nSHA256: '+CHECKS['source_sha256']+'\n\n'+ '\n'.join(CHECKS['limitations']))
    (OUT/'assembly-receipt.json').write_text(json.dumps(CHECKS,indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FamilyWing-ConstructionStudy.blend'))
    # Each picture is rendered from the actual saved native geometry.
    for sc,file in [(scene,'01-assembled'),(structure,'02-structure'),(ground,'03-ground-cutaway'),(upper,'04-upper-cutaway'),(specimen,'05-wall-layers'),(stairscene,'06-stair-assembly'),(junction,'07-shared-junction')]:
        bpy.context.window.scene=sc;sc.render.filepath=str(OUT/(file+'.png'))
        sc.cycles.samples=args.samples
        if args.render:
            log('Rendering '+file);bpy.ops.render.render(write_still=True,scene=sc.name)
    bpy.context.window.scene=scene
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FamilyWing-ConstructionStudy.blend'))
    log('COMPLETE '+str(OUT))
