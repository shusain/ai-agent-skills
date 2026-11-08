"""Blender5 inventory entrypoint; read-only on the opened native .blend.

After -- supply --output FRESH_DIR [--source SVG]. Writes components.csv and
quantities.json for the construction-scene metadata contract. Source SVG must
match the opened study; never count cutaway/exploded presentation copies.
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
    args=parser.parse_args(blender_argv())
    from building_study.takeoff import main as takeoff
    takeoff(args)

if __name__=='__main__':main()
