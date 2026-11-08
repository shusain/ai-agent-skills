"""Issue890 shared-space generation proof; ordinary Python standard library.

Divides exact orthogonal footprints into connected spaces. Boundaries, one-sided
exterior wall bands, shared partitions, hosted openings and clear room polygons
are derived from that partition. No Blender/Unreal/production writes occur.
CLI writes twelve semantic SVGs, source models and receipts in a fresh directory.
Uses the existing plan_svg rectangle arrangement; coordinates are integer mm,
not raster samples. This is a bounded split/search prototype, not a house solver.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import random
import xml.etree.ElementTree as ET

from .plan_svg import NS, element, union_rectangles
from .clearance_geometry import erode_square,open_square,rectangle_fits,landing,sweep_fits,door_frame

MIN_WALK_MM=1200
SWING_MARGIN_MM=50


def area(rects):
    return sum((c-a)*(d-b) for a,b,c,d in rects)


def bounds(rects):
    return min(r[0] for r in rects),min(r[1] for r in rects),max(r[2] for r in rects),max(r[3] for r in rects)


def adjacent(a,b):
    return ((a[2]==b[0] or b[2]==a[0]) and max(a[1],b[1])<min(a[3],b[3])) or ((a[3]==b[1] or b[3]==a[1]) and max(a[0],b[0])<min(a[2],b[2]))


def components(rects):
    """Positive-edge connectivity; corner-only contact never joins a space."""
    remaining=set(tuple(r) for r in rects);out=[]
    while remaining:
        seed=min(remaining);remaining.remove(seed);todo=[seed];group=[]
        while todo:
            current=todo.pop();group.append(current)
            connected=sorted(r for r in remaining if adjacent(r,current))
            remaining.difference_update(connected);todo.extend(connected)
        out.append(sorted(group))
    return sorted(out)


def validate_partition(footprint,spaces):
    """Independent exact coverage, disjointness and connected-space checks."""
    if not footprint or len(components(footprint))!=1:raise ValueError("Footprint must be edge-connected")
    all_rects=[]
    for name,rects in sorted(spaces.items()):
        if not rects or len(components(rects))!=1:raise ValueError(f"Disconnected space: {name}")
        normal=union_rectangles(rects)
        if area(normal)!=area(rects):raise ValueError(f"Space overlaps itself: {name}")
        if area(union_rectangles(rects,footprint=footprint))!=area(rects):raise ValueError(f"Space outside footprint: {name}")
        all_rects.extend(rects)
    merged=union_rectangles(all_rects)
    if area(merged)!=area(all_rects):raise ValueError("Space interiors overlap")
    if area(merged)!=area(footprint):raise ValueError("Unassigned footprint area")


class Partition:
    """Transactional split/carve API; rejected operations retain prior state."""
    def __init__(self,footprint):
        self.footprint=union_rectangles(footprint)
        self.spaces={"root":self.footprint}
        validate_partition(self.footprint,self.spaces)

    def carve(self,space,mask,prefix):
        selected=union_rectangles(self.spaces[space],footprint=mask)
        rest=union_rectangles(self.spaces[space],exclusions=mask)
        if not selected or not rest:raise ValueError("A split must create positive spaces on both sides")
        candidate={k:v for k,v in self.spaces.items() if k!=space}
        names=[]
        for side,rects in (("a",selected),("b",rest)):
            for index,group in enumerate(components(rects)):
                name=f"{prefix}_{side}{index}"
                if name in candidate:raise ValueError("Space ID already exists")
                candidate[name]=union_rectangles(group);names.append(name)
        validate_partition(self.footprint,candidate)
        self.spaces=candidate
        return names

    def split(self,space,axis,at,prefix):
        if type(at) is not int or axis not in ("x","y"):raise ValueError("Integer orthogonal split required")
        a,b,c,d=bounds(self.spaces[space])
        if not ((a<at<c) if axis=="x" else (b<at<d)):raise ValueError("Split must intersect space interior")
        mask=[(a-1,b-1,at,d+1)] if axis=="x" else [(a-1,b-1,c+1,at)]
        return self.carve(space,mask,prefix)


@dataclass(frozen=True,order=True)
class Boundary:
    id:str
    axis:str
    at:int
    lo:int
    hi:int
    negative:str|None
    positive:str|None

    @property
    def exterior(self):return self.negative is None or self.positive is None
    @property
    def thickness(self):return 250 if self.exterior else 150
    def point(self,t):return (t,self.at) if self.axis=="x" else (self.at,t)


def boundaries(spaces):
    """Derive each shared edge once from the exact subdivision arrangement."""
    rects=[r for group in spaces.values() for r in group]
    xs=sorted({v for r in rects for v in (r[0],r[2])});ys=sorted({v for r in rects for v in (r[1],r[3])})
    grid={}
    for i,(x0,x1) in enumerate(zip(xs,xs[1:])):
        for j,(y0,y1) in enumerate(zip(ys,ys[1:])):
            owners=[name for name,group in sorted(spaces.items()) if any(2*a<x0+x1<2*c and 2*b<y0+y1<2*d for a,b,c,d in group)]
            if len(owners)>1:raise ValueError("Overlapping space ownership")
            if owners:grid[i,j]=owners[0]
    raw=defaultdict(list)
    for i,x in enumerate(xs):
        for j,(lo,hi) in enumerate(zip(ys,ys[1:])):
            neg,pos=grid.get((i-1,j)),grid.get((i,j))
            if neg!=pos:raw["y",x,neg,pos].append((lo,hi))
    for j,y in enumerate(ys):
        for i,(lo,hi) in enumerate(zip(xs,xs[1:])):
            neg,pos=grid.get((i,j-1)),grid.get((i,j))
            if neg!=pos:raw["x",y,neg,pos].append((lo,hi))
    out=[]
    for (axis,at,neg,pos),spans in sorted(raw.items(),key=lambda item:str(item[0])):
        merged=[]
        for lo,hi in sorted(spans):
            if merged and lo==merged[-1][1]:merged[-1]=(merged[-1][0],hi)
            else:merged.append((lo,hi))
        for lo,hi in merged:
            identity=json.dumps([axis,at,lo,hi,neg,pos],separators=(",",":"))
            out.append(Boundary("edge_"+hashlib.sha256(identity.encode()).hexdigest()[:12],axis,at,lo,hi,neg,pos))
    return sorted(out)


def loops(edges,space=None):
    """Oriented closed rings from shared edges; interior remains on the left."""
    directed=[]
    for edge in edges:
        if space is None:
            if not edge.exterior:continue
            positive=edge.positive is not None
        else:
            if space not in (edge.negative,edge.positive):continue
            positive=edge.positive==space
        a,b=edge.point(edge.lo),edge.point(edge.hi)
        forward=positive if edge.axis=="x" else not positive
        directed.append((a,b) if forward else (b,a))
    nexts={};incoming=defaultdict(int)
    for a,b in directed:
        if a in nexts:raise ValueError("Non-manifold space corner")
        nexts[a]=b;incoming[b]+=1
    if set(nexts)!=set(incoming) or any(v!=1 for v in incoming.values()):raise ValueError("Unclosed space boundary")
    rings=[]
    while nexts:
        start=min(nexts);current=start;ring=[]
        while True:
            ring.append(current);current=nexts.pop(current)
            if current==start:break
        changed=True
        while changed and len(ring)>4:
            changed=False
            for i in range(len(ring)):
                a,b,c=ring[i-1],ring[i],ring[(i+1)%len(ring)]
                if (a[0]==b[0]==c[0]) or (a[1]==b[1]==c[1]):ring.pop(i);changed=True;break
        rings.append(ring)
    return sorted(rings)


def wall_bands(edges):
    """Square-joined occupied bands; exterior thickness is wholly inward.

    Bands are later clipped to the finished envelope, including courtyard holes.
    Corner patches come from shared nodes. Opening cuts never acquire end caps.
    """
    out=[]
    for e in edges:
        cap=e.thickness if e.exterior else e.thickness//2
        if e.exterior:
            low,high=(e.at,e.at+e.thickness) if e.negative is None else (e.at-e.thickness,e.at)
        else:low,high=e.at-e.thickness//2,e.at+e.thickness//2
        out.append((e.lo-cap,low,e.hi+cap,high) if e.axis=="x" else (low,e.lo-cap,high,e.hi+cap))
    return out


def largest_rectangle(rects):
    """Largest axis-aligned contained rectangle for labels and bounded fit checks."""
    xs=sorted({v for r in rects for v in (r[0],r[2])});ys=sorted({v for r in rects for v in (r[1],r[3])})
    cells=[[any(2*a<xs[i]+xs[i+1]<2*c and 2*b<ys[j]+ys[j+1]<2*d for a,b,c,d in rects) for j in range(len(ys)-1)] for i in range(len(xs)-1)]
    best=None;best_area=-1
    for left in range(len(xs)-1):
        good=[True]*(len(ys)-1)
        for right in range(left,len(xs)-1):
            good=[v and cells[right][j] for j,v in enumerate(good)]
            start=None
            for j,ok in enumerate(good+[False]):
                if ok and start is None:start=j
                if not ok and start is not None:
                    r=(xs[left],ys[start],xs[right+1],ys[j]);size=(r[2]-r[0])*(r[3]-r[1])
                    if size>best_area:best,best_area=r,size
                    start=None
    if best is None:raise ValueError("No clear area")
    return best


def corridor_contact(rects,hall):
    edges=boundaries({"room":rects,"hall":hall})
    return max((e.hi-e.lo for e in edges if not e.exterior),default=0)


def configurations():
    """Twelve bounded fixtures: three authored circulation profiles per family."""
    out=[]
    for kind in ("rectangle","l-shape","u-shape","courtyard"):
        for index,seed in enumerate((17,41,83)):
            if kind=="rectangle":
                w,h=12000,14000;foot=[(0,0,w,h)]
                x=(6000,4200,6000)[index];y=7600
                hall=[(x-900,0,x+900,h)] if index<2 else [(0,y-900,w,y+900),(x-900,0,x+900,y)]
                profile=("Central hall","Offset hall","Cross hall")[index]
            elif kind=="l-shape":
                w,h=16000,14000;nx,ny=9000,8000
                foot=[(0,0,w,ny),(0,ny,nx,h)]
                x=(4500,8000,5500)[index];y=(4000,7000,4500)[index]
                width=1800 if index!=1 else 2000
                hall=[(x-width//2,0,x+width//2,h),(x-width//2,y-width//2,w,y+width//2)]
                profile=("Wing junction","Inner-edge hall","Offset junction")[index]
            elif kind=="u-shape":
                w,h=18000,14000;nx,ny=6000,(6000,7000,6000)[index];rx=12000
                foot=[(0,0,w,ny),(0,ny,nx,h),(rx,ny,w,h)]
                width=(1800,2000,2200)[index];entryx=(9000,8000,10000)[index]
                hall=[(nx-width,ny-width,rx+width,ny),(nx-width,ny,nx,h),(rx,ny,rx+width,h),(entryx-900,0,entryx+900,ny)]
                profile=("Garden gallery","Deep front wing","Wide gallery")[index]
            else:
                w,h=18000,16000;a,b,c,d=(6500,6000,11500,11000) if index!=1 else (7000,5500,12000,10500)
                foot=[(0,0,w,b),(0,d,w,h),(0,b,a,d),(c,b,w,d)]
                width=(1800,1800,2200)[index];entryx=(9000,9500,8000)[index]
                hall=[(a-width,b-width,c+width,b),(a-width,d,c+width,d+width),(a-width,b,a,d),(c,b,c+width,d),(entryx-900,0,entryx+900,b)]
                profile=("Central court","Offset court","Wide gallery")[index]
            out.append(dict(id=f"{kind}-{index+1}",family=kind,variant=index+1,profile=profile,seed=seed,footprint=union_rectangles(foot),hall=union_rectangles(hall,footprint=foot),target_rooms=6 if kind!="courtyard" else 8))
    return out


def generate(config):
    """Seeded candidate splits; accepted partitions always preserve exact coverage."""
    rng=random.Random(config["seed"]);part=Partition(config["footprint"])
    part.carve("root",config["hall"],"circulation")
    hall_keys=[k for k in part.spaces if k.startswith("circulation_a")]
    if len(hall_keys)!=1:raise ValueError("Circulation must be one connected space")
    hall=part.spaces.pop(hall_keys[0]);part.spaces["hall"]=hall
    step=0
    while len(part.spaces)-1<config["target_rooms"]:
        candidates=[]
        zones=sorted((k for k in part.spaces if k!="hall"),key=lambda k:(-area(part.spaces[k]),k))
        for name in zones:
            a,b,c,d=bounds(part.spaces[name])
            for axis,lo,hi in (("x",a,c),("y",b,d)):
                for n in range(6,15):
                    at=((lo+(hi-lo)*n//20)//50)*50
                    if not lo<at<hi:continue
                    mask=[(a-1,b-1,at,d+1)] if axis=="x" else [(a-1,b-1,c+1,at)]
                    sides=[union_rectangles(part.spaces[name],footprint=mask),union_rectangles(part.spaces[name],exclusions=mask)]
                    if any(not s or len(components(s))!=1 for s in sides):continue
                    if any(area(s)<11000000 or min(largest_rectangle(s)[2]-largest_rectangle(s)[0],largest_rectangle(s)[3]-largest_rectangle(s)[1])<2800 for s in sides):continue
                    if any(corridor_contact(s,hall)<1800 for s in sides):continue
                    candidates.append((name,axis,at))
            if candidates:break
        if not candidates:raise ValueError(f"Cannot meet room count for {config['id']}")
        name,axis,at=rng.choice(candidates);part.split(name,axis,at,f"split{step}");step+=1
    ordered=sorted((rects for name,rects in part.spaces.items() if name!="hall"),key=lambda r:(-area(r),bounds(r)))
    spaces={"hall":hall};names={"hall":"Hall / gallery" if config["family"]=="courtyard" else "Hall"}
    labels=["Living / dining","Kitchen","Bedroom 1","Bedroom 2","Study"]
    if len(ordered)==8:labels += ["Bedroom 3","Utility"]
    labels += ["Bath / utility" if len(ordered)==6 else "Bathroom"]
    for i,rects in enumerate(ordered):
        sid=f"room_{i+1:02d}";spaces[sid]=rects;names[sid]=labels[i]
    return compile_layout(repair_spaces(dict(config,spaces=spaces,names=names)))


def clear_geometry(model):
    """Derive closed wall bands/clear interiors before any opening cuts."""
    footprint=model["footprint"];spaces=model["spaces"]
    validate_partition(footprint,spaces);edges=boundaries(spaces)
    loops(edges)
    for sid in spaces:loops(edges,sid)
    closed=union_rectangles(wall_bands(edges),footprint=footprint)
    clear={sid:union_rectangles(rects,exclusions=closed) for sid,rects in spaces.items()}
    for sid,rects in clear.items():
        if not rects or len(components(rects))!=1:raise ValueError(f"Wall thickness disconnects clear space: {sid}")
        if sid!="hall":
            r=largest_rectangle(rects)
            if area(rects)<8500000 or min(r[2]-r[0],r[3]-r[1])<2200:raise ValueError(f"Room too small after thickness: {sid}")
    return edges,closed,clear


def walk_report(clear,width=MIN_WALK_MM):
    """Exact square-fit coverage and connected feasible-centre regions."""
    report={}
    for sid,rects in sorted(clear.items()):
        core=erode_square(rects,width)
        covered=open_square(rects,width)
        report[sid]=dict(core=core,core_components=len(components(core)),narrow=union_rectangles(rects,exclusions=covered))
    return report


def repair_spaces(model):
    """Transactionally absorb sub-width appendages into an adjacent space.

    Diagnosis uses actual wall-thickness clear interiors. Planning patches come
    from square opening with a conservative wall allowance; only patches touching
    diagnosed narrow space are considered. Coverage, connected rooms and basic fit
    are preserved. Each accepted move must reduce total narrow area. Otherwise the
    request fails, rather than hiding an unusable area or silently dropping floor.
    """
    current=dict(model,spaces={s:list(r) for s,r in model["spaces"].items()},repairs=list(model.get("repairs",[])))
    width=model.get("min_walk_mm",MIN_WALK_MM)
    budget=2*len(boundaries(current["spaces"]))
    for step in range(budget):
        edges,closed,clear=clear_geometry(current);reports=walk_report(clear,width)
        old_bad=sum(area(r["narrow"]) for r in reports.values())
        bad=[s for s,r in reports.items() if r["narrow"] or r["core_components"]!=1]
        if not bad:return current
        changed=False
        for sid in sorted(bad,key=lambda s:(s=="hall",s)):
            kept=open_square(current["spaces"][sid],width+500)
            patches=components(union_rectangles(current["spaces"][sid],exclusions=kept))
            for patch in sorted(patches,key=lambda p:(-area(p),bounds(p))):
                if not union_rectangles(patch,footprint=reports[sid]["narrow"]):continue
                remaining=union_rectangles(current["spaces"][sid],exclusions=patch)
                if not remaining or len(components(remaining))!=1:continue
                split={s:r for s,r in current["spaces"].items() if s!=sid};split[sid]=remaining;split["__patch"]=patch
                contacts=defaultdict(int)
                for edge in boundaries(split):
                    owners=(edge.negative,edge.positive)
                    if "__patch" in owners:
                        other=owners[1] if owners[0]=="__patch" else owners[0]
                        if other is not None and other!=sid:contacts[other]+=edge.hi-edge.lo
                for recipient in sorted(contacts,key=lambda s:(-contacts[s],s!="hall",s)):
                    spaces={s:list(r) for s,r in current["spaces"].items()};spaces[sid]=remaining
                    spaces[recipient]=union_rectangles(spaces[recipient]+patch)
                    candidate=dict(current,spaces=spaces)
                    try:
                        _,_,next_clear=clear_geometry(candidate);next_report=walk_report(next_clear,width)
                    except ValueError:continue
                    new_bad=sum(area(r["narrow"]) for r in next_report.values())
                    if new_bad>=old_bad or any(r["core_components"]!=1 for r in next_report.values()):continue
                    event=dict(from_space=sid,to_space=recipient,planning_patch=[list(r) for r in patch],planning_area_mm2=area(patch),narrow_before_mm2=old_bad,narrow_after_mm2=new_bad)
                    current=dict(candidate,repairs=current["repairs"]+[event]);changed=True;break
                if changed:break
            if changed:break
        if not changed:raise ValueError("Cannot safely repair minimum walk width: "+", ".join(bad))
    raise ValueError("Clearance repair budget exhausted")


def door_clear(edge,op,clear,width=MIN_WALK_MM,margin=SWING_MARGIN_MM):
    """Both-side square landings plus full swept quarter-disc into served room."""
    for sid in (edge.negative,edge.positive):
        if sid is not None and not rectangle_fits(landing(edge,op,sid,width),clear[sid]):return False
    return sweep_fits(edge,op,clear[op["space"]],margin)


def compile_layout(model,source_openings=None):
    """Derive usable geometry/openings; reject narrow parts and blocked swings."""
    footprint=model["footprint"];spaces=model["spaces"]
    edges,closed,clear=clear_geometry(model)
    min_walk=model.get("min_walk_mm",MIN_WALK_MM);swing_margin=model.get("swing_margin_mm",SWING_MARGIN_MM)
    if type(swing_margin) is not int or swing_margin<0:raise ValueError("Swing margin must be nonnegative integer mm")
    report=walk_report(clear,min_walk)
    for sid,r in report.items():
        if r["narrow"] or r["core_components"]!=1:raise ValueError(f"Minimum walk width failed: {sid}")
    openings=[]
    def add(edge,kind,width,sid,sill=0,height=2100):
        if edge.hi-edge.lo<width+700:raise ValueError("Insufficient junction clearance")
        lo=(edge.lo+edge.hi-width)//2
        if kind=="window":
            openings.append(dict(id=f"{kind}_{sid}",host=edge.id,lo=lo,hi=lo+width,kind=kind,space=sid,sill_mm=sill,height_mm=height));return True
        first,last=edge.lo+350,edge.hi-350-width
        positions={first,last,lo,*[max(first,min(last,lo+delta)) for delta in (-900,-600,-300,300,600,900)]}
        for start in sorted(positions,key=lambda t:(abs(t-lo),t)):
            for hinge in ("low","high"):
                op=dict(id=f"{kind}_{sid}",host=edge.id,lo=start,hi=start+width,kind=kind,space=sid,sill_mm=sill,height_mm=height,hinge=hinge)
                if door_clear(edge,op,clear,min_walk,swing_margin):openings.append(op);return True
        return False
    for sid in sorted(spaces) if source_openings is None else ():
        if sid=="hall":continue
        doors=[e for e in edges if set((e.negative,e.positive))=={sid,"hall"} and e.hi-e.lo>=1600]
        if not doors:raise ValueError(f"No legal hall door: {sid}")
        if not any(add(e,"door",900,sid) for e in sorted(doors,key=lambda e:(-(e.hi-e.lo),e.id))):raise ValueError(f"No clear door swing/landing: {sid}")
        windows=[e for e in edges if e.exterior and sid in (e.negative,e.positive) and e.hi-e.lo>=2100]
        if windows:add(max(windows,key=lambda e:(e.hi-e.lo,e.id)),"window",1400,sid,900,1200)
    if source_openings is None:
        entrance=[e for e in edges if e.axis=="x" and e.at==0 and e.exterior and "hall" in (e.negative,e.positive)]
        if not entrance:raise ValueError("Hall needs street entrance")
        if not any(add(e,"entry",1000,"hall") for e in sorted(entrance,key=lambda e:(-(e.hi-e.lo),e.id))):raise ValueError("No clear entrance swing/landing")
    else:openings=list(source_openings)
    by_id={e.id:e for e in edges};cuts=[]
    if len({op["id"] for op in openings})!=len(openings):raise ValueError("Duplicate opening ID")
    for op in openings:
        if op["host"] not in by_id:raise ValueError("Unknown opening host")
        e=by_id[op["host"]];t=e.thickness+1
        if any(type(op[k]) is not int for k in ("lo","hi","sill_mm","height_mm")):raise ValueError("Opening coordinates must be integer mm")
        if op["lo"]<e.lo+350 or op["hi"]>e.hi-350 or op["hi"]-op["lo"]<800:raise ValueError("Opening violates junction clearance")
        if op["space"] not in (e.negative,e.positive):raise ValueError("Opening space is not on its host")
        if op["kind"] not in ("door","window","entry") or op["sill_mm"]<0 or not 0<op["height_mm"] or op["sill_mm"]+op["height_mm"]>3000:raise ValueError("Invalid opening type or height")
        if op["kind"] in ("window","entry") and not e.exterior:raise ValueError("Exterior opening needs exterior host")
        if op["kind"]=="door" and e.exterior:raise ValueError("Room door needs shared host")
        if op["kind"]!="window" and op["sill_mm"]!=0:raise ValueError("Door must reach floor")
        if op["kind"]!="window":
            if op.get("hinge") not in ("low","high"):raise ValueError("Door hinge must be explicit")
            if not door_clear(e,op,clear,min_walk,swing_margin):raise ValueError(f"Blocked door swing/landing: {op['id']}")
        for other in openings:
            if other["id"]!=op["id"] and other["host"]==op["host"] and max(other["lo"],op["lo"])<=min(other["hi"],op["hi"]):raise ValueError("Overlapping openings")
        if op["sill_mm"]<=1200<op["sill_mm"]+op["height_mm"]:
            cuts.append((op["lo"],e.at-t,op["hi"],e.at+t) if e.axis=="x" else (e.at-t,op["lo"],e.at+t,op["hi"]))
    walls=union_rectangles(closed,exclusions=cuts)
    result=dict(model,edges=edges,clear=clear,walls=walls,openings=sorted(openings,key=lambda o:o["id"]),min_walk_mm=min_walk,swing_margin_mm=swing_margin)
    validate_access(result)
    return result


def validate_access(model):
    graph=defaultdict(set);by_id={e.id:e for e in model["edges"]}
    for op in model["openings"]:
        if op["kind"]=="window":continue
        e=by_id[op["host"]];a,b=e.negative or "outside",e.positive or "outside"
        graph[a].add(b);graph[b].add(a)
    seen={"outside"};todo=["outside"]
    while todo:
        for sid in graph[todo.pop()]-seen:seen.add(sid);todo.append(sid)
    if not set(model["spaces"])<=seen:raise ValueError("A space has no entrance route")


def path_data(rings):
    return " ".join("M "+" L ".join(f"{x} {y}" for x,y in ring)+" Z" for ring in rings)


def export_svg(model):
    """Semantic SVG2 plan: source space rectangles, shared edges and derived walls."""
    a,b,w,h=bounds(model["footprint"]);width=w-a;height=h-b
    root=ET.Element(f"{{{NS}}}svg",dict(viewBox=f"-700 -1000 {width+1400} {height+2100}",width="800",height=str(round(800*(height+2100)/(width+1400))),**{"data-shared-plan-schema":"2","data-units":"mm","data-layout-id":model["id"],"data-seed":str(model["seed"]),"data-min-walk-mm":str(model["min_walk_mm"]),"data-swing-margin-mm":str(model["swing_margin_mm"]),"role":"img"}))
    element(root,"title",{},f"{model['family']} — {model['profile']}")
    element(root,"desc",{},"Connected-space generation study. Finished envelope, shared boundaries and hosted openings. Single-level concept; no stair or structural design.")
    element(root,"style",{},".plan-wall{fill:currentColor}.plan-space{fill:currentColor;fill-opacity:.025}.plan-hall{fill:currentColor;fill-opacity:.07}.plan-line{fill:none;stroke:currentColor;stroke-width:18}.plan-window{fill:none;stroke:currentColor;stroke-width:28}.plan-label{font-family:Arial,sans-serif;font-size:260px;text-anchor:middle;fill:currentColor}.plan-detail{font-size:230px}.plan-node{fill:none;stroke:currentColor;stroke-width:20}")
    element(root,"style",{},".walk-pad{fill:currentColor;fill-opacity:.04;stroke:currentColor;stroke-width:15;stroke-dasharray:70 60}.door-sweep{fill:currentColor;fill-opacity:.08;stroke:none}")
    world=element(root,"g",dict(id="world-mm",transform=f"translate(0 {height}) scale(1 -1)"))
    fp=element(world,"g",{"id":"footprint-source","display":"none"})
    for x,y,c,d in model["footprint"]:element(fp,"rect",dict(x=x,y=y,width=c-x,height=d-y))
    source=element(world,"g",{"id":"spaces-source","display":"none"})
    for sid,rects in sorted(model["spaces"].items()):
        group=element(source,"g",{"data-space-id":sid,"data-name":model["names"][sid]})
        for x,y,c,d in rects:element(group,"rect",dict(x=x,y=y,width=c-x,height=d-y))
    semantic=element(world,"g",{"id":"shared-boundaries","display":"none"})
    for e in model["edges"]:
        p,q=e.point(e.lo),e.point(e.hi)
        element(semantic,"line",dict(id=e.id,x1=p[0],y1=p[1],x2=q[0],y2=q[1],**{"data-negative-space":e.negative or "outside","data-positive-space":e.positive or "outside","data-thickness-mm":e.thickness}))
    opgroup=element(world,"g",{"id":"opening-source","display":"none"});by_id={e.id:e for e in model["edges"]}
    for op in model["openings"]:
        e=by_id[op["host"]];p,q=e.point(op["lo"]),e.point(op["hi"])
        element(opgroup,"line",dict(id=op["id"],x1=p[0],y1=p[1],x2=q[0],y2=q[1],**{"data-host-edge":e.id,"data-kind":op["kind"],"data-space":op["space"],"data-sill-mm":op["sill_mm"],"data-height-mm":op["height_mm"],"data-hinge":op.get("hinge","none")}))
    fills=element(world,"g",{"id":"clear-spaces","data-role":"derived"})
    for sid,rects in sorted(model["clear"].items()):
        group=element(fills,"g",{"class":"plan-hall" if sid=="hall" else "plan-space","data-space-id":sid,"data-area-mm2":area(rects)})
        for x,y,c,d in rects:element(group,"rect",dict(x=x,y=y,width=c-x,height=d-y))
    cells=element(world,"g",{"id":"wall-cells","display":"none","data-role":"derived"})
    for x,y,c,d in model["walls"]:element(cells,"rect",dict(x=x,y=y,width=c-x,height=d-y))
    walls=element(world,"g",{"id":"wall-footprint","class":"plan-wall","data-role":"derived"})
    material_rings=loops(boundaries({"material":model["walls"]}),"material")
    element(walls,"path",{"d":path_data(material_rings),"fill-rule":"evenodd"})
    joints=element(world,"g",{"id":"junction-markers","display":"none"})
    for x,y in sorted({p for e in model["edges"] for p in (e.point(e.lo),e.point(e.hi))}):element(joints,"circle",dict(cx=x,cy=y,r=90,**{"class":"plan-node"}))
    guides=element(world,"g",{"id":"opening-symbols"})
    clearances=element(world,"g",{"id":"clearance-guides","display":"none"})
    for op in model["openings"]:
        e=by_id[op["host"]];p,q=e.point(op["lo"]),e.point(op["hi"])
        if op["kind"]=="window":element(guides,"line",dict(x1=p[0],y1=p[1],x2=q[0],y2=q[1],**{"class":"plan-window"}));continue
        if op["kind"]=="portal":
            for sid in (e.negative,e.positive):
                if sid is not None:
                    x,y,c,d=landing(e,op,sid,model["min_walk_mm"])
                    element(clearances,"rect",dict(x=x,y=y,width=c-x,height=d-y,**{"class":"walk-pad","data-opening-id":op["id"],"data-space-id":sid}))
            continue
        p,tangent,normal=door_frame(e,op,op["space"]);size=op["hi"]-op["lo"]
        q=(p[0]+size*tangent[0],p[1]+size*tangent[1]);end=(p[0]+size*normal[0],p[1]+size*normal[1])
        sweep=1 if tangent[0]*normal[1]-tangent[1]*normal[0]>0 else 0
        element(guides,"path",dict(d=f"M {p[0]} {p[1]} L {end[0]} {end[1]} M {q[0]} {q[1]} A {size} {size} 0 0 {sweep} {end[0]} {end[1]}",**{"class":"plan-line"}))
        for sid in (e.negative,e.positive):
            if sid is None:continue
            x,y,c,d=landing(e,op,sid,model["min_walk_mm"])
            element(clearances,"rect",dict(x=x,y=y,width=c-x,height=d-y,**{"class":"walk-pad","data-opening-id":op["id"],"data-space-id":sid}))
        radius=size+model["swing_margin_mm"];q=(p[0]+radius*tangent[0],p[1]+radius*tangent[1]);end=(p[0]+radius*normal[0],p[1]+radius*normal[1])
        element(clearances,"path",dict(d=f"M {p[0]} {p[1]} L {q[0]} {q[1]} A {radius} {radius} 0 0 {sweep} {end[0]} {end[1]} Z",**{"class":"door-sweep","data-opening-id":op["id"]}))
    annotations=element(root,"g",{"id":"room-labels"})
    for sid,rects in sorted(model["clear"].items()):
        x,y,c,d=largest_rectangle(rects);cx=(x+c)//2;cy=height-(y+d)//2
        name=model["names"][sid]
        angle=-90 if sid=="hall" and c-x<3000 and d-y>2*(c-x) else 0
        label=element(annotations,"g",dict(transform=f"translate({cx} {cy}) rotate({angle})",**{"data-room-label":sid,"data-full-name":name,"data-area-m2":f"{area(rects)/1000000:.1f}"}))
        title_lines=name.split(" / ") if " / " in name else (name.rsplit(" ",1) if name.startswith("Bedroom") else [name])
        lines=title_lines+[f"{area(rects)/1000000:.1f} m²"]
        for i,title in enumerate(lines):element(label,"text",dict(x=0,y=round((i-(len(lines)-1)/2)*360),**{"class":"plan-label"}),title)
    if model["family"] in ("u-shape","courtyard","l-shape"):
        if model["family"]=="courtyard":
            # An exterior negative-orientation ring is the actual court hole.
            holes=[ring for ring in loops(model["edges"]) if sum(ring[i][0]*ring[(i+1)%len(ring)][1]-ring[(i+1)%len(ring)][0]*ring[i][1] for i in range(len(ring)))<0]
            ring=holes[0];cx=(min(p[0] for p in ring)+max(p[0] for p in ring))//2;cy=height-(min(p[1] for p in ring)+max(p[1] for p in ring))//2
            title="Garden court"
        else:
            empty=union_rectangles([(0,0,width,height)],exclusions=model["footprint"]);x,y,c,d=largest_rectangle(empty);cx=(x+c)//2;cy=height-(y+d)//2;title="Open garden"
        element(annotations,"text",dict(x=cx,y=cy,**{"class":"plan-label plan-detail"}),title)
    element(annotations,"text",dict(x=width//2,y=-420,**{"class":"plan-label"}),f"{width/1000:g} × {height/1000:g} m envelope")
    entry=next((op for op in model["openings"] if op["kind"]=="entry"),None)
    if entry is not None:element(annotations,"text",dict(x=(entry["lo"]+entry["hi"])//2,y=height+650,**{"class":"plan-label plan-detail"}),"ENTRY / STREET")
    else:element(annotations,"text",dict(x=width//2,y=height+650,**{"class":"plan-label plan-detail"}),"UPPER FLOOR · STREET SIDE")
    ET.indent(root)
    return ET.tostring(root,encoding="utf-8",xml_declaration=True)


def read_svg(path):
    """Read source space geometry and verify its exact derived SVG contract."""
    root=ET.parse(path).getroot()
    if root.get("data-shared-plan-schema")!="2" or root.get("data-units")!="mm":raise ValueError("Shared SVG schema2/mm required")
    def rects(group):
        out=[]
        for item in group:
            if item.tag!=f"{{{NS}}}rect" or item.get("transform"):raise ValueError("Unsupported transformed source geometry")
            x,y,w,h=[int(item.get(k)) for k in ("x","y","width","height")];out.append((x,y,x+w,y+h))
        return out
    world=root.find(".//*[@id='world-mm']")
    if root.get("transform"):raise ValueError("Unsupported source transform")
    for name in ("footprint-source","spaces-source","shared-boundaries","opening-source","wall-footprint","wall-cells"):
        group=world.find(f"./*[@id='{name}']")
        if group is None or group.get("transform") or any(child.get("transform") for child in group):raise ValueError("Unsupported source layer transform")
    footprint=rects(world.find("./*[@id='footprint-source']"));spaces={};names={}
    if world.get("transform")!=f"translate(0 {bounds(footprint)[3]}) scale(1 -1)":raise ValueError("Unexpected world basis")
    for group in world.findall(f"./*[@id='spaces-source']/{{{NS}}}g"):
        sid=group.get("data-space-id")
        if group.get("transform") or sid in spaces:raise ValueError("Invalid SVG space")
        spaces[sid]=rects(group);names[sid]=group.get("data-name")
    model=dict(id=root.get("data-layout-id"),seed=int(root.get("data-seed")),family=root.get("data-layout-id").rsplit("-",1)[0],profile="readback",footprint=footprint,spaces=spaces,names=names,min_walk_mm=int(root.get("data-min-walk-mm")),swing_margin_mm=int(root.get("data-swing-margin-mm")))
    derived=boundaries(spaces);by_id={e.id:e for e in derived};source_openings=[]
    for item in world.findall(f"./*[@id='opening-source']/{{{NS}}}line"):
        host=item.get("data-host-edge")
        if host not in by_id:raise ValueError("Unknown SVG opening host")
        e=by_id[host];x1,y1,x2,y2=[int(item.get(k)) for k in ("x1","y1","x2","y2")]
        off_axis=(y1!=e.at or y2!=e.at) if e.axis=="x" else (x1!=e.at or x2!=e.at)
        if off_axis:raise ValueError("Opening is off its host edge")
        lo,hi=sorted((x1,x2) if e.axis=="x" else (y1,y2))
        op=dict(id=item.get("id"),host=host,lo=lo,hi=hi,kind=item.get("data-kind"),space=item.get("data-space"),sill_mm=int(item.get("data-sill-mm")),height_mm=int(item.get("data-height-mm")))
        if op["kind"]!="window":op["hinge"]=item.get("data-hinge")
        source_openings.append(op)
    result=compile_layout(model,source_openings)
    actual_edges=[]
    for item in world.findall(f"./*[@id='shared-boundaries']/{{{NS}}}line"):
        actual_edges.append((item.get("id"),item.get("x1"),item.get("y1"),item.get("x2"),item.get("y2"),item.get("data-negative-space"),item.get("data-positive-space"),item.get("data-thickness-mm")))
    expected=[]
    for e in result["edges"]:
        p,q=e.point(e.lo),e.point(e.hi);expected.append(tuple(str(v) for v in (e.id,p[0],p[1],q[0],q[1],e.negative or "outside",e.positive or "outside",e.thickness)))
    if sorted(actual_edges)!=sorted(expected):raise ValueError("SVG shared boundaries are stale")
    actual_ops=[]
    for item in world.findall(f"./*[@id='opening-source']/{{{NS}}}line"):
        actual_ops.append(tuple(item.get(k) for k in ("id","x1","y1","x2","y2","data-host-edge","data-kind","data-space","data-sill-mm","data-height-mm")))
    expected=[];by_id={e.id:e for e in result["edges"]}
    for op in result["openings"]:
        e=by_id[op["host"]];p,q=e.point(op["lo"]),e.point(op["hi"])
        expected.append(tuple(str(v) for v in (op["id"],p[0],p[1],q[0],q[1],e.id,op["kind"],op["space"],op["sill_mm"],op["height_mm"])))
    if sorted(actual_ops)!=sorted(expected):raise ValueError("SVG opening contract is stale")
    if sorted(rects(world.find("./*[@id='wall-cells']")))!=sorted(result["walls"]):raise ValueError("SVG wall footprint is stale")
    visible=world.findall(f"./*[@id='wall-footprint']/{{{NS}}}path")
    expected_path=path_data(loops(boundaries({"material":result["walls"]}),"material"))
    if len(visible)!=1 or visible[0].get("d")!=expected_path or visible[0].get("fill-rule")!="evenodd":raise ValueError("SVG visible wall outline is stale")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("output",type=Path)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit("Use a fresh output directory")
    models=[generate(config) for config in configurations()]
    args.output.mkdir(parents=True)
    receipt={"schema":2,"scope":"single-level orthogonal shared-space generation with square circulation clearance and idealised swept-door checks; no Blender/structural/stair acceptance","layouts":[]}
    for model in models:
        path=args.output/(model["id"]+".svg");path.write_bytes(export_svg(model));read_svg(path)
        source={k:v for k,v in model.items() if k not in ("edges",)};source["edges"]=[asdict(e) for e in model["edges"]]
        (args.output/(model["id"]+".json")).write_text(json.dumps(source,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        receipt["layouts"].append(dict(id=model["id"],family=model["family"],variant=model["variant"],profile=model["profile"],seed=model["seed"],svg=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rooms=len(model["spaces"])-1,gross_m2=area(model["footprint"])/1e6,clear_m2=sum(area(r) for r in model["clear"].values())/1e6,shared_edges=len(model["edges"]),repairs=len(model["repairs"]),svg_roundtrip="pass",coverage="pass",room_access="pass",minimum_walk_mm=model["min_walk_mm"],swing_margin_mm=model["swing_margin_mm"],walk_clearance="pass",door_sweeps="pass"))
    (args.output/"validation.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))


if __name__=="__main__":main()
