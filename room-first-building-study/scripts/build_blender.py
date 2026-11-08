"""Blender5 entrypoint for the reviewed family-wing construction example.

Use a separate --background --factory-startup process. Arguments after --:
--output FRESH_DIR [--source SVG] [--render] [--samples32]. Geometry generation
always validates; renders are optional. Does not touch an existing Blender UI.
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from building_study.runtime import blender_argv,example_svg,output_path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=example_svg())
    parser.add_argument('--output',type=output_path,required=True)
    parser.add_argument('--framing-system',choices=['metric','us'],required=True,help='Physical stock profile, independent of layout dimensions')
    parser.add_argument('--stud-spacing',help='US inches (12,16,24) or metric mm (300,400,450,600)')
    parser.add_argument('--joist-spacing',help='US inches (12,16,19.2,24) or metric mm')
    parser.add_argument('--rafter-spacing',help='US inches (12,16,24) or metric mm')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--samples',type=int,default=32)
    args=parser.parse_args(blender_argv())
    if args.samples<=0:parser.error('samples must be positive')
    from building_study.framing import profile
    args.profile=profile(args.framing_system,stud_spacing=args.stud_spacing,joist_spacing=args.joist_spacing,rafter_spacing=args.rafter_spacing)
    from building_study.family_wing import main as build
    build(args)

if __name__=='__main__':main()
