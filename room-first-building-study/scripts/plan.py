"""Ordinary Python plan CLI: room-first examples, retained fallback, SVG readback.

Generation writes a fresh output directory; validation reads input only. Uses
standard library only. Run this file by absolute path from any working directory.
"""
import argparse,json,sys
from pathlib import Path
from building_study.runtime import output_path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    framing=sub.add_parser('framing',help='Inspect actual stock and native-unit spacings without Blender')
    framing.add_argument('--system',choices=['metric','us'],required=True)
    framing.add_argument('--stud-spacing');framing.add_argument('--joist-spacing');framing.add_argument('--rafter-spacing')
    room=sub.add_parser('room-first',help='Generate three bounded two-storey room-program schemes')
    room.add_argument('--output',required=True,type=output_path);room.add_argument('--program',type=Path)
    fallback=sub.add_parser('fallback',help='Generate twelve single-floor shared-space fallback layouts')
    fallback.add_argument('--output',required=True,type=output_path)
    check=sub.add_parser('validate',help='Validate an actual semantic SVG without rewriting it')
    check.add_argument('source',type=Path);check.add_argument('--kind',choices=['house','floor','fallback'],default='house')
    args=parser.parse_args()
    if args.command=='framing':
        from building_study.framing import profile
        print(json.dumps(profile(args.system,stud_spacing=args.stud_spacing,joist_spacing=args.joist_spacing,rafter_spacing=args.rafter_spacing).to_dict(),indent=2));return
    if args.command=='validate':
        from building_study.room_first_house import read_house,read_floor
        from building_study.shared_spaces import read_svg
        result={'house':read_house,'floor':read_floor,'fallback':read_svg}[args.kind](args.source)
        print(json.dumps({'validated':str(args.source.resolve()),'kind':args.kind,'floors':list(result.get('floors',{}))}));return
    argv=[sys.argv[0],str(args.output)]
    if args.command=='room-first':
        from building_study.room_first_house import main as generate
        if args.program:argv+=['--program',str(args.program.resolve())]
    else:
        from building_study.shared_spaces import main as generate
    sys.argv=argv;generate()

if __name__=='__main__':main()
