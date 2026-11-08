"""Issue890 exact 2D clearance primitives; ordinary Python, integer mm.

Reads rectangle-union regions in memory. Computes square-footprint erosion and
opening, clearance landings and analytic quarter-disc door sweeps. No sampling,
Blender, file/scene writes or building-code compliance claims. The study uses a
1200mm square circulation envelope and50mm swing margin as configurable defaults.
Reuses plan_svg's exact arrangement; callers own connected-component/access checks.
"""
from .plan_svg import union_rectangles


def region_bounds(rects):
    return min(r[0] for r in rects),min(r[1] for r in rects),max(r[2] for r in rects),max(r[3] for r in rects)


def erode_square(rects,width):
    """Exact feasible centres of an axis-aligned width-square inside a region.

    Width must be positive/even integer mm. Complement dilation accounts for
    concave boundaries and holes; rectangle decomposition does not set resolution.
    A positive-area centre region is required (zero-tolerance exact-fit tracks
    have no positive region in this conservative prototype).
    """
    return rectangle_centres(rects,width,width)


def rectangle_centres(rects,width,depth):
    """Exact feasible centres for a rectangular functional/use template."""
    if any(type(v) is not int or v<=0 or v%2 for v in (width,depth)):raise ValueError("Positive even integer clearance dimensions required")
    if not rects:return []
    a,b,c,d=region_bounds(rects);rx=width//2;ry=depth//2
    if c-a<=width or d-b<=depth:return []
    outside=union_rectangles([(a,b,c,d)],exclusions=rects)
    obstacles=[(x-rx,y-ry,u+rx,v+ry) for x,y,u,v in outside]
    return union_rectangles([(a+rx,b+ry,c-rx,d-ry)],exclusions=obstacles)


def open_square(rects,width):
    """Region coverable by a width-square; removes sub-width fingers/bridges."""
    centres=erode_square(rects,width);r=width//2
    return union_rectangles([(a-r,b-r,c+r,d+r) for a,b,c,d in centres],footprint=rects)


def rectangle_fits(rect,region):
    a,b,c,d=rect
    return sum((u-x)*(v-y) for x,y,u,v in union_rectangles([rect],exclusions=region))==0


def door_frame(edge,opening,space):
    """Hinge on the room's finished wall face, with tangent and inward normal."""
    sign=1 if edge.positive==space else -1
    if space not in (edge.positive,edge.negative):raise ValueError("Door space must own host edge")
    offset=edge.thickness if edge.exterior else edge.thickness//2
    high=opening.get("hinge","low")=="high"
    along=opening["hi"] if high else opening["lo"]
    direction=-1 if high else 1
    if edge.axis=="x":return (along,edge.at+sign*offset),(direction,0),(0,sign)
    return (edge.at+sign*offset,along),(0,direction),(sign,0)


def landing(edge,opening,space,width):
    """Width-square arrival/turning pad on the selected finished wall face."""
    sign=1 if edge.positive==space else -1
    offset=edge.thickness if edge.exterior else edge.thickness//2
    middle=(opening["lo"]+opening["hi"])//2;half=width//2
    face=edge.at+sign*offset
    lo,hi=sorted((face,face+sign*width))
    return (middle-half,lo,middle+half,hi) if edge.axis=="x" else (lo,middle-half,hi,middle+half)


def sweep_fits(edge,opening,region,margin=50):
    """Exact full90-degree swept quarter-disc against rectangular complement.

    The leaf plus margin opens into opening['space']. A blocked rectangle hits
    the swept sector iff its nearest point in the local positive quadrant is
    strictly inside the radius. Boundary contact alone has zero collision area.
    This is a2D idealised leaf check, excluding hinges/frame/hardware/furniture.
    """
    hinge,tangent,normal=door_frame(edge,opening,opening["space"])
    radius=opening["hi"]-opening["lo"]+margin
    corners=[(hinge[0]+u*tangent[0]+v*normal[0],hinge[1]+u*tangent[1]+v*normal[1]) for u in (0,radius) for v in (0,radius)]
    box=(min(p[0] for p in corners),min(p[1] for p in corners),max(p[0] for p in corners),max(p[1] for p in corners))
    blocked=union_rectangles([box],exclusions=region)
    for a,b,c,d in blocked:
        local=[((x-hinge[0])*tangent[0]+(y-hinge[1])*tangent[1],(x-hinge[0])*normal[0]+(y-hinge[1])*normal[1]) for x in (a,c) for y in (b,d)]
        u=max(0,min(p[0] for p in local));v=max(0,min(p[1] for p in local))
        if u*u+v*v<radius*radius:return False
    return True
