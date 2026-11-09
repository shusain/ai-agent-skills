"""Standalone #890 Blender assembly helpers (Blender 5 / bpy).

Reads integer-mm plans and preserves fractional stock dimensions. Writes objects in the
current authoring scene; the caller owns save/render paths. No Unreal writes.
This is an asset study recipe, not an engineering or code-compliance tool.
"""
import sys, math
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

from .plan_svg import union_rectangles as _union
from .clearance_geometry import erode_square as _erode_square
from .shared_spaces import area

def material(name,color):
    """Create a node material; derived from the project's small CityArtKit helper."""
    value=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    value.diffuse_color=(*color,1.0);value.use_nodes=True
    shader=value.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1.0)
    shader.inputs['Roughness'].default_value=.85
    return value

STAGES = [
 '01 Foundations', '02 Ground floor structure', '03 Ground subfloor',
 '04 Ground wall framing', '05 Upper floor structure', '06 Upper subfloor',
 '07 Upper wall framing', '08 Stair structure', '09 Roof framing',
 '10 Wall sheathing', '11 Roof sheathing', '12 Weather membranes',
 '13 Windows and doors', '14 Exterior cladding and trim', '15 Roof covering and drainage',
 '16 Insulation', '17 Interior lining and ceilings', '18 Floor finishes',
 '19 Interior fitout', '20 Stair guards and hardware']

TICKS_PER_MM=10000
def _ticks(rs):
    out=[]
    for r in rs:
        v=tuple(round(x*TICKS_PER_MM) for x in r)
        if v[2]>v[0] and v[3]>v[1]:out.append(v)
    return out
def _unticks(rs):return [tuple(x//TICKS_PER_MM if x%TICKS_PER_MM==0 else x/TICKS_PER_MM for x in r) for r in rs]

def union(rects,footprint=None,exclusions=()):
    """Exact integer arrangement at0.0001mm; never round US stock to whole mm."""
    return _unticks(_union(_ticks(rects),footprint=_ticks(footprint) if footprint is not None else None,exclusions=_ticks(exclusions)))

def diff(a,b): return union(a, exclusions=b) if a else []
def intersect(a,b): return union(a, footprint=b) if a and b else []
def inset(f,d): return f if not d else _unticks(_erode_square(_ticks(f),2*round(d*TICKS_PER_MM)))
def band(f,a,b): return diff(inset(f,a),inset(f,b))
def mm(rect): return tuple(v/1000 for v in rect)

class Builder:
    """Stable component IDs, reusable actual-size meshes and staged ownership."""
    def __init__(self, scene, *, stages=STAGES, component_prefix="FW"):
        self.stages = tuple(stages)
        self.component_prefix = component_prefix
        self.scene=scene; self.serial=0;self.meshes={};self.objects=[];self.cols={}
        self.mats={}
        palette={
         'timber':(.62,.38,.17),'endgrain':(.53,.29,.10), 'osb':(.62,.49,.28),
         'concrete':(.44,.46,.44),'steel':(.09,.13,.15),'membrane':(.045,.26,.30),
         'insulation':(.78,.59,.25),'cladding':(.24,.37,.31),'lining':(.86,.83,.75),
         'oak':(.51,.30,.14),'tile':(.51,.62,.60),'cabinet':(.29,.41,.37),
         'counter':(.78,.77,.68),'ceramic':(.92,.92,.86),'fabric':(.57,.40,.25),
         'linen':(.85,.79,.64),'glass':(.40,.65,.70),'ground':(.25,.29,.25),
         'dark':(.055,.072,.08),'white':(.82,.84,.79),'accent':(.76,.39,.16)}
        for k,c in palette.items(): self.mats[k]=material('Study / '+k,c)
        for k in ('timber','osb','oak','concrete','lining','cladding'):
            mat=self.mats[k];n=mat.node_tree.nodes;l=mat.node_tree.links
            noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=18 if k!='osb' else 45
            noise.inputs['Detail'].default_value=2
            bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.012
            l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],n.get('Principled BSDF').inputs['Normal'])
        shader=self.mats['glass'].node_tree.nodes.get('Principled BSDF')
        shader.inputs['Transmission Weight'].default_value=.72;shader.inputs['Roughness'].default_value=.12
        self.mats['steel'].node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.7
        for stage in self.stages:
            c=bpy.data.collections.new(stage);scene.collection.children.link(c);self.cols[stage]=c
        self.reference=bpy.data.collections.new('00 References and reserved service zones')
        scene.collection.children.link(self.reference)

    def register(self,obj,name,stage,mat,level='site',host='',assembly=''):
        self.serial+=1;obj.name=f'{self.serial:05d} | {name}'
        col=self.cols[self.stages[stage-1]] if stage else self.reference
        col.objects.link(obj)
        if obj.type=='MESH':obj.data.materials.append(self.mats[mat])
        obj['component_id']=f'{self.component_prefix}-{self.serial:05d}';obj['part']=name;obj['stage']=stage
        obj['level']=level;obj['host']=host;obj['assembly']=assembly or name.split('/')[0]
        self.objects.append(obj);return obj

    def box(self,name,rect,z0,z1,mat,stage,level='site',host='',assembly=''):
        a,b,c,d=rect
        if min(c-a,d-b,z1-z0)<.00005:return None
        dims=tuple(round(v,7) for v in (c-a,d-b,z1-z0))
        # Material is part of key: linked meshes must not acquire extra slots.
        key=(dims,mat)
        mesh=self.meshes.get(key)
        if mesh is None:
            x,y,z=(v/2 for v in dims)
            verts=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
            mesh=bpy.data.meshes.new('Solid '+str(dims))
            mesh.from_pydata(verts,[],[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)])
            self.meshes[key]=mesh
        obj=bpy.data.objects.new(name,mesh);obj.location=((a+c)/2,(b+d)/2,(z0+z1)/2)
        # Only assign a material once on a linked mesh.
        if len(mesh.materials):
            self.serial+=1;obj.name=f'{self.serial:05d} | {name}'
            (self.cols[self.stages[stage-1]] if stage else self.reference).objects.link(obj)
            for k,v in dict(component_id=f'{self.component_prefix}-{self.serial:05d}',part=name,stage=stage,level=level,host=host,assembly=assembly or name.split('/')[0]).items():obj[k]=v
            self.objects.append(obj);return obj
        return self.register(obj,name,stage,mat,level,host,assembly)

    def rects(self,name,rects,z0,z1,mat,stage,level='site',host='',assembly=''):
        return [self.box(name,mm(r),z0,z1,mat,stage,level,host,assembly) for r in rects]

    def beam(self,name,a,b,width,depth,mat,stage,level='site',host=''):
        a,b=Vector(a),Vector(b);v=b-a
        obj=self.box(name,(-width/2,-depth/2,width/2,depth/2),-v.length/2,v.length/2,mat,stage,level,host)
        if obj:
            direction=v.normalized();up=Vector((0,0,1))
            if abs(direction.dot(up))>.999:up=Vector((0,1,0))
            side=up.cross(direction).normalized();normal=direction.cross(side).normalized()
            obj.location=(a+b)/2
            obj.rotation_euler=Matrix((side,normal,direction)).transposed().to_euler()
            assert (obj.rotation_euler.to_matrix()@Vector((0,0,1))-direction).length<1e-5
        return obj

    def prism(self,name,poly,zfunc,thickness,mat,stage,level='roof',host=''):
        n=len(poly);top=[(x,y,zfunc(x,y)) for x,y in poly]
        vertices=top+[(x,y,z-thickness) for x,y,z in top]
        faces=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
        faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(name,mesh)
        return self.register(obj,name,stage,mat,level,host)

    def label(self,text,location,size=.23,rotation=(0,0,0),collection=None):
        curve=bpy.data.curves.new(text,'FONT');curve.body=text;curve.size=size
        curve.align_x='CENTER';curve.align_y='CENTER';curve.extrude=.0003
        obj=bpy.data.objects.new(text,curve);obj.location=location;obj.rotation_euler=rotation
        (collection or self.reference).objects.link(obj);curve.materials.append(self.mats['dark'])
        return obj

def wall_rect(edge,lo=None,hi=None,low=None,high=None):
    lo=edge.lo if lo is None else lo;hi=edge.hi if hi is None else hi
    if low is None:
        if edge.exterior:
            sign=1 if edge.positive else -1
            low,high=sorted((edge.at,edge.at+sign*250))
        else:low,high=edge.at-75,edge.at+75
    return (lo,low,hi,high) if edge.axis=='x' else (low,lo,high,hi)

def merged_runs(edges):
    """Merge collinear shared edges; names stay in the individual source hosts."""
    groups={}
    for e in edges:
        key=(e.axis,e.at,e.exterior, bool(e.positive) if e.exterior else None)
        groups.setdefault(key,[]).append(e)
    out=[]
    for key,es in sorted(groups.items()):
        es.sort(key=lambda e:e.lo);current=[es[0]];hi=es[0].hi
        for e in es[1:]:
            if e.lo<=hi:current.append(e);hi=max(hi,e.hi)
            else:out.append((current,current[0].lo,hi));current=[e];hi=e.hi
        out.append((current,current[0].lo,hi))
    return out
