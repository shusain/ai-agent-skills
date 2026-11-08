"""Blender5 readback: verify the opened study, optionally render all20 stages.

Open the intended .blend as a CLI file argument in a separate background process.
After -- supply --output DIR [--source SVG] [--render-stages] [--samples12].
Writes/refreshes only its receipts and optional frames; does not resave .blend.
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
    parser.add_argument('--render-stages',action='store_true')
    parser.add_argument('--samples',type=int,default=12)
    args=parser.parse_args(blender_argv())
    if args.samples<=0:parser.error('samples must be positive')
    from building_study.verify_blender import main as verify
    verify(args)

if __name__=='__main__':main()
