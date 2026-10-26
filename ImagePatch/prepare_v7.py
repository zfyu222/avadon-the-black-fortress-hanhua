"""Rebuild approved image text with a softer map plate; no translation requests."""
from pathlib import Path
import sys,json,copy,csv,math
from PIL import Image,ImageDraw,ImageFilter
P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'Tools/image_text'))
from core import read_json,write_json,digest
from image_patch import build,layout,clean_map_ink
BASE=P/'ImagePatch/build-v4';OUT=P/'ImagePatch/build-v7'
LEFT='e9c93006873437590fd6d826b559a0fc75c037ee97a47bb07013fba8e6e42314'
RIGHT='a4fca4ff9d16196ab924505b8029fe3b0077cc5665905c4617bcf79b87b44df9'
FONT=ROOT/'Tools/Fonts/NotoSC/NotoSansSC-variable.ttf'
SOURCE=P/'ImagePatch/layout-input/avadon-the-black-fortress_images_text.csv'
TRANSLATED=P/'ImagePatch/layout-input/avadon-the-black-fortress_images_text_translated.csv'
VALIDATION=P/'TranslateFiles/image-text/TranslateFiles/reports/final_validation.json'

def main():
    manifest=read_json(BASE/'IMAGE_PATCH_MANIFEST.json')
    style={f['image_id']:dict(mask_rgba=[72,50,25,64],erase_text_ink=True,stroke_width=1)
        for f in manifest['files'] if any('/G'+str(i)+'.' in f['sources'][0]['path'] for i in [176,177,231,232,233])}
    with SOURCE.open(encoding='utf-8-sig',newline='') as f:source_rows=[r[0] for r in csv.reader(f)]
    for item in manifest['files']:
        if item['image_id'] not in style:continue
        regions=[e for e in manifest['entries'] if e['image_id']==item['image_id']]
        style[item['image_id']]['dark_rows']=[e['csv_row'] for e in regions if 'FIVE NATIONS' in source_rows[e['csv_row']-1] or 'LYNAEUS' in source_rows[e['csv_row']-1]]
    write_json(P/'ImagePatch/v7_texture_styles.json',style)
    original=Image.new('RGBA',(1400,1000));original.paste(Image.open(P/f'ImageText/work/images/{LEFT}.png'),(0,0));original.paste(Image.open(P/f'ImageText/work/images/{RIGHT}.png'),(700,0))
    original.save(P/'ImagePatch/map_original_stitched.png')
    if not OUT.exists():
        build(P/'ImageText/work',SOURCE,TRANSLATED,VALIDATION,FONT,OUT,mask_alpha=255,text_rgba=(245,240,220,255),texture_styles=style)
    # These two complete approved names cross the 700px resource seam. Render
    # once in stitched coordinates, then split; never duplicate a full label
    # independently onto each tile. Sources/translation CSVs remain unchanged.
    m=read_json(OUT/'IMAGE_PATCH_MANIFEST.json')
    if not m.get('composite_labels'):
        full=Image.new('RGBA',(1400,1000));full.paste(Image.open(OUT/f'images/{LEFT}.png'),(0,0));full.paste(Image.open(OUT/f'images/{RIGHT}.png'),(700,0))
        with SOURCE.open(encoding='utf-8-sig',newline='') as f:sources=[r[0] for r in csv.reader(f)]
        with TRANSLATED.open(encoding='utf-8-sig',newline='') as f:targets=[r[0] for r in csv.reader(f)]
        observations=[]
        for text,box in [('HOLKLANDA',[680,365,830,398]),('WRETCH LANDS',[684,809,868,887])]:
            row=sources.index(text)+1;target=targets[row-1];width,height=box[2]-box[0],box[3]-box[1]
            clean,erased=clean_map_ink(original.crop(box));full.paste(clean,tuple(box))
            plate=Image.new('RGBA',(width,height),(72,50,25,64));draw=ImageDraw.Draw(plate)
            font,lines,step=layout(target,FONT,width-4,height-4,max_size=26)
            y=max(2,(height-step*len(lines))//2)
            for line in lines:draw.text(((width-font.getlength(line))/2,y),line,font=font,fill=(245,240,220,255),anchor='lt',stroke_width=1,stroke_fill='black');y+=step
            full.alpha_composite(plate,(box[0],box[1]))
            observations.append(dict(source=text,csv_row=row,translation=target,stitched_box=box,
                confirmation=dict(status='agent_visual_confirmed',human_approval=False,reason='Viewed both original tiles and their exact horizontal composite; complete red map label is readable across the seam.'),
                image_ids=[LEFT,RIGHT],source_image_sha256={key:digest((P/f'ImageText/work/images/{key}.png').read_bytes()) for key in [LEFT,RIGHT]}))
            for key,offset in [(LEFT,0),(RIGHT,700)]:
                piece=[max(box[0],offset)-offset,box[1],min(box[2],offset+700)-offset,box[3]]
                if piece[2]<=piece[0]:continue
                item=next(f for f in m['files'] if f['image_id']==key)
                ink=plate.crop((max(0,offset-box[0]),0,min(width,offset+700-box[0]),height))
                has_text=any(pixel[:3]==(245,240,220) for pixel in ink.getdata())
                m['entries'].append(dict(image_id=key,box=piece,text=target,csv_row=row,sources=item['sources'],mask_rgba=[72,50,25,64],text_rgba=[245,240,220,255],
                    rendering=dict(font_size=font.size,lines=lines,background_mode='composite_text' if has_text else 'composite_source_erase',erased_ink_pixels=erased,stitched_box=box,tile_x=offset)))
        for key,offset in [(LEFT,0),(RIGHT,700)]:
            path=OUT/f'images/{key}.png';full.crop((offset,0,offset+700,1000)).save(path)
            next(f for f in m['files'] if f['image_id']==key)['sha256']=digest(path.read_bytes())
        m['composite_labels']=observations
        m['texture_styles_sha256']=digest((P/'ImagePatch/v7_texture_styles.json').read_bytes())
        write_json(OUT/'IMAGE_PATCH_MANIFEST.json',m)
        write_json(P/'ImagePatch/map_seam_visual_confirmation.json',dict(source_csv_sha256=digest(SOURCE.read_bytes()),translation_sha256=digest(TRANSLATED.read_bytes()),observations=observations,agent_viewed_original_composite=True))
        full.save(OUT/'map_preview.png')
    print(str(OUT))

if __name__=='__main__':main()
