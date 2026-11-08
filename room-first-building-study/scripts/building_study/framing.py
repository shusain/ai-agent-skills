"""Framing stock and spacing profiles, independent of plan/display coordinates.

Ordinary Python. Inch conversions use Decimal/Fraction before a single conversion
to numeric mm at the geometry boundary. US sizes are actual dressed dimensions,
not nominal2x labels converted to inches. Profiles are asset inputs, not span/code
approval. No files or scenes are written by this module.
"""
from dataclasses import dataclass,asdict,replace,fields
from decimal import Decimal
from fractions import Fraction

def inches_mm(value):
    """Convert an inch count or fraction string exactly, returning Fraction mm."""
    return Fraction(str(value))*Fraction(127,5)

def feet_inches_mm(feet=0,inches=0):
    return inches_mm(Fraction(str(feet))*12+Fraction(str(inches)))

US_LUMBER={name:tuple(float(inches_mm(v)) for v in section) for name,section in {
    '1x2':('.75','1.5'),'2x4':('1.5','3.5'),'2x6':('1.5','5.5'),
    '2x8':('1.5','7.25'),'2x10':('1.5','9.25'),'2x12':('1.5','11.25'),
    '4x4':('3.5','3.5')}.items()}

def us_lumber(nominal):
    """Actual dressed section in mm for a supported US nominal stock label."""
    if nominal not in US_LUMBER:raise ValueError('Unsupported US stock label: '+nominal)
    return US_LUMBER[nominal]

def stations(start,stop,spacing,origin=0):
    """Exact grid stations in [start,stop), with no cumulative float drift."""
    a,b,s,o=(Fraction(str(v)) for v in (start,stop,spacing,origin))
    if s<=0:raise ValueError('Spacing must be positive')
    i=-((-(a-o))//s)
    while o+i*s<b:
        yield float(o+i*s);i+=1

@dataclass(frozen=True)
class FramingProfile:
    system:str
    stud_mm:float
    interior_depth_mm:float
    exterior_depth_mm:float
    stud_spacing_mm:float
    joist_spacing_mm:float
    rafter_spacing_mm:float
    joist_depth_mm:float
    flange_width_mm:float
    flange_thickness_mm:float
    web_mm:float
    rim_mm:float
    rafter_depth_mm:float
    tie_depth_mm:float
    collar_depth_mm:float
    header_depth_mm:float
    exterior_header_width_mm:float
    bearer_width_mm:float
    bearer_depth_mm:float
    ridge_width_mm:float
    ridge_depth_mm:float
    post_mm:float
    stringer_depth_mm:float
    batten_width_mm:float
    batten_depth_mm:float

    @property
    def exterior_core_end_mm(self):return 59+self.exterior_depth_mm
    @property
    def wall_top_m(self):return 3-.047-self.joist_depth_mm/1000
    @property
    def stud_top_m(self):return self.wall_top_m-2*self.stud_mm/1000
    @property
    def stock_labels(self):
        labels={}
        for side,depth in [('interior',self.interior_depth_mm),('exterior',self.exterior_depth_mm)]:
            actual=f'{self.stud_mm:g}x{depth:g} mm'
            labels[side]=next((name for name,section in US_LUMBER.items() if section==(self.stud_mm,depth)),actual) if self.system=='us' else actual
        return labels
    def to_dict(self):
        return dict(asdict(self),stock_labels=self.stock_labels,spacing_input_units='inches' if self.system=='us' else 'mm',geometry_units='mm',display_units='IMPERIAL' if self.system=='us' else 'METRIC',
                    spacing_labels={role:(f'{getattr(self,role+"_spacing_mm")/25.4:g} in O.C.' if self.system=='us' else f'{getattr(self,role+"_spacing_mm"):g} mm O.C.') for role in ('stud','joist','rafter')},
                    actual_wall_stock_mm={'interior':[self.stud_mm,self.interior_depth_mm],'exterior':[self.stud_mm,self.exterior_depth_mm]},
                    actual_wall_stock_in={'interior':[self.stud_mm/25.4,self.interior_depth_mm/25.4],'exterior':[self.stud_mm/25.4,self.exterior_depth_mm/25.4]})

METRIC=FramingProfile('metric',45,90,140,600,400,600,245,63,38,9,45,220,195,145,240,140,134,300,140,300,90,245,40,25)
def _inch(v):return float(inches_mm(v))
US=FramingProfile('us',_inch('1.5'),_inch('3.5'),_inch('5.5'),_inch(16),_inch(16),_inch(24),
                  _inch('9.5'),_inch('2.5'),_inch('1.5'),_inch('3/8'),_inch('1.125'),
                  _inch('9.25'),_inch('7.25'),_inch('5.5'),_inch('9.5'),_inch('5.25'),
                  _inch('5.25'),_inch('11.875'),_inch('5.25'),_inch('11.875'),_inch('3.5'),_inch('11.25'),_inch('1.5'),_inch('.75'))

def profile(system,*,stud_spacing=None,joist_spacing=None,rafter_spacing=None):
    """Select stock and optional native-unit spacings (US inches, metric mm)."""
    if system not in ('metric','us'):raise ValueError('Choose metric or us framing')
    p=US if system=='us' else METRIC;changes={}
    for role,value in [('stud',stud_spacing),('joist',joist_spacing),('rafter',rafter_spacing)]:
        if value is None:continue
        n=Decimal(str(value))
        allowed=map(Decimal,('12','16','19.2','24')) if system=='us' and role=='joist' else map(Decimal,('12','16','24')) if system=='us' else map(Decimal,('300','400','450','600'))
        if n not in allowed:raise ValueError(f'Unsupported {role} spacing {value} for {system}; supply native units (US inches or metric mm)')
        changes[role+'_spacing_mm']=float(inches_mm(n)) if system=='us' else float(n)
    return replace(p,**changes)

def wall_domains(model,p):
    """Keep reviewed finished faces; fit selected stock inside their wall bands."""
    from .blender_parts import union,intersect,diff,inset,band,wall_rect
    f=model['footprint'];iw=intersect(union([wall_rect(e) for e in model['physical_edges'] if not e.exterior]),f)
    end=p.exterior_core_end_mm
    return dict(f=f,iw=iw,extcore=band(f,59,end),intcore=diff(inset(iw,(150-p.interior_depth_mm)/2),band(f,0,end)))

def from_dict(data):
    return FramingProfile(**{f.name:data[f.name] for f in fields(FramingProfile)})
