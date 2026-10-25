from pathlib import Path
import hashlib,json,shutil
from PIL import Image,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'Game'
OUT=ROOT/'ImageText/exported'
OUT.mkdir(parents=True,exist_ok=True)
records={}; images=[]
for p in sorted((GAME/'Avadon Files').rglob('*')):
    if p.suffix.lower() not in {'.png','.bmp','.jpg'}: continue
    rel=p.relative_to(GAME); dest=OUT/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    b=p.read_bytes(); digest=hashlib.sha256(b).hexdigest()
    if dest.exists(): assert dest.read_bytes()==b
    else: shutil.copy2(p,dest)
    with Image.open(dest) as im:
        records[rel.as_posix()]={'asset':rel.as_posix(),'sha256':digest,'size':list(im.size),'format':im.format}
        images.append((rel,im.convert('RGB').copy()))
(ROOT/'ImageText/provenance.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
samples=[x for x in images if 'Graphics Core' in str(x[0])][:32]
samples+= [x for x in images if 'Graphics Core' not in str(x[0])][::65][:8]
canvas=Image.new('RGB',(1000,220*((len(samples)+3)//4)), '#cccccc');draw=ImageDraw.Draw(canvas)
for i,(rel,im) in enumerate(samples):
    x=(i%4)*250;y=(i//4)*220
    thumb=ImageOps.contain(im,(246,190));canvas.paste(thumb,(x+(246-thumb.width)//2,y))
    draw.text((x+3,y+192),rel.parent.name+'/'+rel.name,fill='black')
canvas.save(ROOT/'ImageText/calibration.png')
print(json.dumps({'images':len(records),'calibration_images':len(samples),'calibration_files':[r.as_posix() for r,_ in samples]},indent=2))
