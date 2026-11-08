"""Python/Pillow: compose actual rendered stages into a captioned GIF/floor pair.

Reads --run DIR/native-readback.json and its construction-frames; writes a fresh
--output DIR. Optional --font PATH overrides Pillow's portable default font.
No geometry edits, AI-image generation, source mutation or external downloads.
"""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from building_study.runtime import output_path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True,type=Path);parser.add_argument('--output',required=True,type=output_path)
    parser.add_argument('--font',type=Path)
    args=parser.parse_args();receipt=json.loads((args.run/'native-readback.json').read_text(encoding='utf-8'))
    paths=[args.run/'construction-frames'/f"{s['stage']:02d}.png" for s in receipt['stage_visibility']]
    if not paths or any(not p.is_file() for p in paths):raise ValueError('Render every stage before composing the sequence')
    font=ImageFont.truetype(str(args.font),23) if args.font else ImageFont.load_default(size=23)
    small=ImageFont.truetype(str(args.font),17) if args.font else ImageFont.load_default(size=17)
    args.output.mkdir(parents=True,exist_ok=False);frames=[];durations=[]
    for row,path in zip(receipt['stage_visibility'],paths):
        im=Image.open(path).convert('RGB');im.thumbnail((900,720))
        canvas=Image.new('RGB',(900,795),(28,39,43));canvas.paste(im,((900-im.width)//2,(720-im.height)//2));d=ImageDraw.Draw(canvas)
        d.text((24,730),row['name'],font=font,fill=(240,239,225))
        d.text((24,764),f"{row['visible_parts']:,} source components | SVG to local Blender",font=small,fill=(173,193,191))
        frames.append(canvas);durations.append(1600 if row['stage'] in (9,20) else 700)
    frames[0].save(args.output/'construction-sequence.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True)
    floors=[args.run/'03-ground-cutaway.png',args.run/'04-upper-cutaway.png']
    if all(p.is_file() for p in floors):
        pair=Image.new('RGB',(1600,700),(236,234,224));draw=ImageDraw.Draw(pair)
        for i,path in enumerate(floors):
            im=Image.open(path).convert('RGB');im.thumbnail((800,640));pair.paste(im,(i*800+(800-im.width)//2,0))
            draw.text((i*800+24,657),'GROUND' if i==0 else 'UPPER',font=small,fill=(35,48,47))
        pair.save(args.output/'floor-review.png')
    print(args.output.resolve())

if __name__=='__main__':main()
