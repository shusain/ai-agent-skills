"""Issue890 SVG-first plan prototype; ordinary Python, standard library only.

Reads house-plan.json with named millimetre datums. Writes fresh per-floor
semantic SVGs and a validation receipt to the supplied output directory. Never
uses Blender, modifies production assets, or imports existing generators.

The SVG wall-network and opening groups are the geometry contract for later
Blender input. Resolved-footprint rectangles are a checked, derived preview;
read_svg rejects stale footprints after unsupported manual SVG changes.
Only orthogonal, constant-thickness walls are supported in this bounded study.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


@dataclass(frozen=True, order=True)
class Wall:
    id: str
    axis: str
    at: int
    lo: int
    hi: int
    thickness: int

    def contains(self, point):
        along, across = point if self.axis == "x" else point[::-1]
        return across == self.at and self.lo <= along <= self.hi

    def point(self, along):
        return (along, self.at) if self.axis == "x" else (self.at, along)


def integer(value):
    if type(value) is not int:
        raise ValueError("Coordinates must be integer millimetres")
    return value


def load_plan(path):
    source = json.loads(Path(path).read_text(encoding="utf-8"))
    if source.get("schema") != 1 or source.get("units") != "mm":
        raise ValueError("Expected schema1 millimetre plan")
    floors = {}
    for floor, data in source["floors"].items():
        walls = []
        for name, axis, at, lo, hi, thickness in data["walls"]:
            along = source[axis]
            across = source["y" if axis == "x" else "x"]
            walls.append(Wall(name, axis, integer(across[at]), integer(along[lo]),
                              integer(along[hi]), integer(thickness)))
        floors[floor] = dict(walls=walls, openings=data["openings"],
                             labels=data["labels"], z_mm=integer(data["z_mm"]))
    return floors


def resolve(walls, openings=(), free_ends=()):
    """Resolve a rectilinear network into disjoint closed wall-footprint cells.

    Shared intersections define junctions, not independent endpoint offsets.
    The result is invariant to wall/opening input order. Openings retain their
    host-wall ID, sill and height; plan cuts use a1200mm viewing plane.
    Free ends must be explicitly declared; production house has none.
    """
    walls = sorted(walls)
    if len({w.id for w in walls}) != len(walls):
        raise ValueError("Duplicate wall ID")
    by_id = {w.id: w for w in walls}
    nodes = set()
    for w in walls:
        for value in (w.at, w.lo, w.hi, w.thickness):
            integer(value)
        if w.axis not in ("x", "y") or w.hi <= w.lo or w.thickness <= 0 or w.thickness % 2:
            raise ValueError(f"Invalid wall {w.id}")
        nodes.update((w.point(w.lo), w.point(w.hi)))
    for i, a in enumerate(walls):
        for b in walls[i+1:]:
            if a.axis == b.axis:
                if a.at == b.at and max(a.lo, b.lo) < min(a.hi, b.hi):
                    raise ValueError(f"Duplicate/shared wall overlap: {a.id}, {b.id}")
            else:
                h, v = (a, b) if a.axis == "x" else (b, a)
                point = (v.at, h.at)
                if h.contains(point) and v.contains(point):
                    nodes.add(point)
    nodes = sorted(nodes)
    owners = {p: [w for w in walls if w.contains(p)] for p in nodes}
    free_ends = set(free_ends)
    for w in walls:
        for p in (w.point(w.lo), w.point(w.hi)):
            if len(owners[p]) < 2 and p not in free_ends:
                raise ValueError(f"Disconnected endpoint: {w.id} at {p}")
    if len({o[0] for o in openings}) != len(openings):
        raise ValueError("Duplicate opening ID")
    per_wall = {w.id: [] for w in walls}
    for op in sorted(openings):
        name, host, lo, hi, kind, sill, height = op
        if host not in by_id:
            raise ValueError(f"Missing opening host: {name}")
        w = by_id[host]
        for value in (lo, hi, sill, height):
            integer(value)
        if not (w.lo < lo < hi < w.hi) or kind not in ("door", "window", "portal") or sill < 0 or height <= 0:
            raise ValueError(f"Invalid opening: {name}")
        for other in per_wall[host]:
            if max(lo, other[2]) <= min(hi, other[3]):
                raise ValueError(f"Overlapping openings: {name}, {other[0]}")
        for p in nodes:
            if w.contains(p):
                others = [v for v in owners[p] if v.axis != w.axis]
                if others:
                    offset = max(v.thickness//2 for v in others)
                    at = p[0 if w.axis == "x" else 1]
                    if lo <= at+offset and hi >= at-offset:
                        raise ValueError(f"Opening crosses junction: {name} at {p}")
        per_wall[host].append(op)
    raw = []
    for w in walls:
        # Extend to the far face of perpendicular hosts, then resolve the union.
        # A free end is butt-capped; it is never silently extended or snapped.
        caps = []
        for at in (w.lo, w.hi):
            perpendicular = [v.thickness//2 for v in owners[w.point(at)] if v.axis != w.axis]
            caps.append(max(perpendicular, default=0))
        lo, hi = w.lo-caps[0], w.hi+caps[1]
        cuts = sorted((o[2], o[3]) for o in per_wall[w.id] if o[5] <= 1200 < o[5]+o[6])
        spans = []
        for a, b in cuts:
            spans.append((lo, a)); lo = b
        spans.append((lo, hi))
        for a, b in spans:
            t = w.thickness//2
            raw.append((a, w.at-t, b, w.at+t) if w.axis == "x" else (w.at-t, a, w.at+t, b))
    rects = union_rectangles(raw)
    graph = []
    for p in nodes:
        directions = set()
        for w in owners[p]:
            at = p[0 if w.axis == "x" else 1]
            if w.lo < at: directions.add(w.axis+"-")
            if w.hi > at: directions.add(w.axis+"+")
        kind = {1:"end", 2:"L" if len({d[0] for d in directions}) == 2 else "straight", 3:"T", 4:"cross"}[len(directions)]
        graph.append(dict(id=f"node_{p[0]}_{p[1]}", point=list(p), kind=kind,
                          walls=sorted(w.id for w in owners[p])))
    return dict(rectangles=[list(r) for r in rects], nodes=graph,
                area_mm2=sum((c-a)*(d-b) for a,b,c,d in rects))


def union_rectangles(raw, footprint=None, exclusions=()):
    """Exact integer rectangle union, optionally clipped and/or subtracted.

    Shared arrangement boundaries support both the original wall resolver and
    the shared-space study. Returns canonical disjoint rectangles; no writes.
    """
    raw=list(raw);exclusions=list(exclusions)
    footprint=None if footprint is None else list(footprint)
    if not raw or footprint==[]:return []
    bounds=raw+exclusions+(footprint or [])
    for rect in bounds:
        if len(rect)!=4 or any(type(v) is not int for v in rect) or rect[0]>=rect[2] or rect[1]>=rect[3]:
            raise ValueError("Expected positive integer rectangles")
    # Exact arrangement of rectangle boundaries; no floating-point mesh Boolean.
    xs = sorted({v for r in bounds for v in (r[0], r[2])})
    ys = sorted({v for r in bounds for v in (r[1], r[3])})
    rows = []
    for y0, y1 in zip(ys, ys[1:]):
        spans = []
        start = None
        for x0, x1 in zip(xs, xs[1:]):
            covered = any(2*a < x0+x1 < 2*c and 2*b < y0+y1 < 2*d for a,b,c,d in raw)
            if footprint is not None:
                covered = covered and any(2*a < x0+x1 < 2*c and 2*b < y0+y1 < 2*d for a,b,c,d in footprint)
            covered = covered and not any(2*a < x0+x1 < 2*c and 2*b < y0+y1 < 2*d for a,b,c,d in exclusions)
            if covered and start is None:
                start = x0
            if start is not None and (not covered or x1 == xs[-1]):
                spans.append((start, x0 if not covered else x1)); start = None
        rows.append((y0, y1, spans))
    active, rects = {}, []
    for y0, y1, spans in rows:
        current = set(spans)
        for span in list(active):
            if span not in current:
                rects.append(tuple(active.pop(span)))
        for x0, x1 in spans:
            key = (x0, x1)
            if key in active:
                active[key][3] = y1
            else:
                active[key] = [x0, y0, x1, y1]
    rects.extend(tuple(r) for r in active.values())
    rects = sorted(rects)
    for i, a in enumerate(rects):
        for b in rects[i+1:]:
            if max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]):
                raise AssertionError("Resolved cells overlap")
    return rects


def element(parent, tag, attrs, text=None):
    child = ET.SubElement(parent, f"{{{NS}}}{tag}", {k:str(v) for k,v in attrs.items()})
    child.text = text
    return child


def svg_bytes(floor, data, resolved):
    """Write semantic source groups and a derived footprint in the same SVG.

    Network and opening coordinates are world millimetres with Y toward the
    garden. One outer transform maps that basis to SVG's screen coordinates.
    Room annotations and stair guides are presentation only in this slice.
    """
    root = ET.Element(f"{{{NS}}}svg", dict(viewBox="-700 -900 11400 14000", width="684", height="840",
                       **{"data-plan-schema":"1","data-units":"mm","data-floor":floor,
                          "data-z-mm":str(data["z_mm"]),"role":"img","aria-labelledby":"plan-title"}))
    element(root, "title", {"id":"plan-title"}, f"Timber house: {floor} floor; joined wall network")
    element(root, "desc", {}, "Original conceptual layout. Semantic wall and opening groups drive subsequent modelling. Sizes are not structural specifications.")
    element(root, "style", {}, ".walls{fill:currentColor}.guide{fill:none;stroke:currentColor;stroke-width:20}.window{fill:none;stroke:currentColor;stroke-width:25}.label{font-family:Arial,sans-serif;font-size:240px;fill:currentColor;text-anchor:middle}.small{font-size:220px}.node{fill:none;stroke:currentColor;stroke-width:24}")
    world = element(root, "g", {"id":"world-mm","transform":"translate(0 12000) scale(1 -1)"})
    network = element(world, "g", {"id":"wall-network","display":"none","data-role":"source"})
    for w in sorted(data["walls"]):
        a, b = w.point(w.lo), w.point(w.hi)
        element(network, "line", {"id":"wall_"+w.id,"data-wall-id":w.id,"x1":a[0],"y1":a[1],"x2":b[0],"y2":b[1],"data-thickness-mm":w.thickness})
    opening_group = element(world, "g", {"id":"openings","display":"none","data-role":"source"})
    walls = {w.id:w for w in data["walls"]}
    for name, host, lo, hi, kind, sill, height in sorted(data["openings"]):
        a,b=walls[host].point(lo),walls[host].point(hi)
        element(opening_group,"line",dict(id="opening_"+name,**{"data-opening-id":name,"data-host-wall":host,"data-kind":kind,"data-sill-mm":sill,"data-height-mm":height,"x1":a[0],"y1":a[1],"x2":b[0],"y2":b[1]}))
    footprint = element(world,"g",{"id":"resolved-footprint","class":"walls","data-role":"derived"})
    for a,b,c,d in resolved["rectangles"]:
        element(footprint,"rect",dict(x=a,y=b,width=c-a,height=d-b))
    nodes = element(world,"g",{"id":"junctions","display":"none","data-role":"derived"})
    for node in resolved["nodes"]:
        element(nodes,"circle",dict(id=node["id"],cx=node["point"][0],cy=node["point"][1],r=90,**{"class":"node","data-kind":node["kind"],"data-walls":" ".join(node["walls"])}))
    for op in sorted(data["openings"]):
        name,host,lo,hi,kind,sill,height=op
        if kind == "window":
            a,b=walls[host].point(lo),walls[host].point(hi)
            element(world,"line",dict(x1=a[0],y1=a[1],x2=b[0],y2=b[1],**{"class":"window"}))
    stair = element(world,"g",{"id":"stair-guide","class":"guide","data-role":"annotation"})
    element(stair,"rect",dict(x=7300,y=1450,width=2200,height=3290))
    for x in (8300,8500):element(stair,"line",dict(x1=x,y1=1450,x2=x,y2=3690))
    element(stair,"line",dict(x1=7300,y1=3690,x2=9500,y2=3690))
    for i in range(1,9):
        for x in (7300,8500):element(stair,"line",dict(x1=x,y1=1450+i*280,x2=x+1000,y2=1450+i*280))
    labels=element(root,"g",{"id":"room-annotations","data-role":"annotation"})
    for name,x,y,title,detail in data["labels"]:
        element(labels,"text",dict(id="room_"+name,x=x,y=12000-y,**{"class":"label"}),title)
        if detail:element(labels,"text",dict(x=x,y=12000-y+340,**{"class":"label small"}),detail)
    element(labels,"text",dict(x=5000,y=-380,**{"class":"label"}),"10.00 m · REAR / GARDEN")
    element(labels,"text",dict(x=5000,y=12800,**{"class":"label"}),"FRONT · STREET / ENTRANCE")
    element(labels,"text",dict(x=-400,y=6000,transform="rotate(-90 -400 6000)",**{"class":"label"}),"12.00 m")
    ET.indent(root)
    return ET.tostring(root,encoding="utf-8",xml_declaration=True)


def read_svg(path):
    """Parse semantic SVG geometry and reject a stale derived plan footprint."""
    root=ET.parse(path).getroot()
    if root.get("data-plan-schema") != "1" or root.get("data-units") != "mm":
        raise ValueError("SVG requires plan schema1 and millimetre units")
    world=root.find(".//*[@id='world-mm']")
    if root.get("transform") or world is None or world.get("transform") != "translate(0 12000) scale(1 -1)":
        raise ValueError("Unexpected SVG coordinate transform")
    for name in ("wall-network","openings","resolved-footprint"):
        group=world.find(f"./*[@id='{name}']")
        expected="rect" if name=="resolved-footprint" else "line"
        if group is None or group.get("transform") or any(child.tag!=f"{{{NS}}}{expected}" or child.get("transform") for child in group):
            raise ValueError(f"Unsupported SVG source structure/transform: {name}")
    walls=[]
    for item in root.findall(f".//*[@id='wall-network']/{{{NS}}}line"):
        if item.get("transform"):raise ValueError("Transformed source wall is unsupported")
        x1,y1,x2,y2=[int(item.get(k)) for k in ("x1","y1","x2","y2")]
        if x1!=x2 and y1!=y2:raise ValueError("Non-orthogonal SVG wall")
        axis="x" if y1==y2 else "y"
        a,b=(x1,x2) if axis=="x" else (y1,y2)
        walls.append(Wall(item.get("data-wall-id"),axis,y1 if axis=="x" else x1,min(a,b),max(a,b),int(item.get("data-thickness-mm"))))
    if not walls:raise ValueError("Empty SVG network")
    by_id={w.id:w for w in walls}; openings=[]
    for item in root.findall(f".//*[@id='openings']/{{{NS}}}line"):
        host=item.get("data-host-wall")
        if host not in by_id:raise ValueError("Missing SVG opening host")
        w=by_id[host]
        a=(int(item.get("x1")),int(item.get("y1")));b=(int(item.get("x2")),int(item.get("y2")))
        if not w.contains(a) or not w.contains(b):raise ValueError("SVG opening off its host")
        lo,hi=sorted((a[0 if w.axis=="x" else 1],b[0 if w.axis=="x" else 1]))
        openings.append([item.get("data-opening-id"),host,lo,hi,item.get("data-kind"),int(item.get("data-sill-mm")),int(item.get("data-height-mm"))])
    result=resolve(walls,openings)
    actual=[]
    for item in root.findall(f".//*[@id='resolved-footprint']/{{{NS}}}rect"):
        a,b,w,h=[int(item.get(k)) for k in ("x","y","width","height")]
        actual.append([a,b,a+w,b+h])
    if sorted(actual)!=result["rectangles"]:raise ValueError("SVG footprint is stale relative to semantic walls/openings")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit("Output must be fresh; retained evidence is never overwritten")
    floors=load_plan(args.source)
    resolved={name:resolve(data["walls"],data["openings"]) for name,data in floors.items()}
    args.output.mkdir(parents=True)
    receipt={"schema":1,"source_sha256":hashlib.sha256(args.source.read_bytes()).hexdigest(),"floors":{},"scope":"2D orthogonal topology and semantic SVG roundtrip only; no Blender mesh or engineering acceptance"}
    for name,data in floors.items():
        path=args.output/f"timber-house-{name}.svg"
        path.write_bytes(svg_bytes(name,data,resolved[name]))
        assert read_svg(path)==resolved[name]
        receipt["floors"][name]=dict(svg=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),junctions=len(resolved[name]["nodes"]),wall_cells=len(resolved[name]["rectangles"]),area_mm2=resolved[name]["area_mm2"],roundtrip="pass")
    (args.output/"validation.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))


if __name__=="__main__":main()
