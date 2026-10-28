"""Rebuild approved image text with the matched look (stroke erase + sampled ink); no translation requests."""
from pathlib import Path
import sys,csv,json
from PIL import Image
P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'Tools/image_text'))
from core import read_json,write_json,digest
from image_patch import build
import image_style
OUT=P/'ImagePatch/build-v9';STYLES=P/'ImagePatch/v9_texture_styles.json'
LEFT='e9c93006873437590fd6d826b559a0fc75c037ee97a47bb07013fba8e6e42314'
RIGHT='a4fca4ff9d16196ab924505b8029fe3b0077cc5665905c4617bcf79b87b44df9'
FONT=ROOT/'Tools/Fonts/NotoSC/NotoSansSC-variable.ttf';SERIF=ROOT/'Tools/Fonts/NotoSC/NotoSerifSC-variable.ttf'
SOURCE=P/'ImagePatch/layout-input/avadon-the-black-fortress_images_text.csv'
TRANSLATED=P/'ImagePatch/layout-input/avadon-the-black-fortress_images_text_translated.csv'
VALIDATION=P/'TranslateFiles/image-text/TranslateFiles/reports/final_validation.json'
SEAM=read_json(P/'ImagePatch/map_seam_visual_confirmation.json')

def main():
    styles=read_json(STYLES)
    for style in styles.values():
        if 'font' in style and not Path(style['font']).is_absolute():style['font']=str((STYLES.parent/style['font']).resolve())
    if OUT.exists():raise SystemExit(f'{OUT} exists; use a new destination')
    build(P/'ImageText/work',SOURCE,TRANSLATED,VALIDATION,FONT,OUT,texture_styles=styles)
    # Two approved names cross the 700px tile seam: render once on the stitched map, then split.
    m=read_json(OUT/'IMAGE_PATCH_MANIFEST.json')
    original=Image.new('RGBA',(1400,1000));full=Image.new('RGBA',(1400,1000))
    for key,offset in [(LEFT,0),(RIGHT,700)]:
        original.paste(Image.open(P/f'ImageText/work/images/{key}.png').convert('RGBA'),(offset,0))
        full.paste(Image.open(OUT/f'images/{key}.png').convert('RGBA'),(offset,0))
    with TRANSLATED.open(encoding='utf-8-sig',newline='') as f:targets=[r[0] for r in csv.reader(f)]
    for item in SEAM['observations']:
        box=item['stitched_box'];target=targets[item['csv_row']-1]
        assert target==item['translation'],'seam translation changed'
        rendering=image_style.render_region(full,original,box,target,dict(font=str(SERIF),ink=[142,13,1]),FONT,False)
        for key,offset in [(LEFT,0),(RIGHT,700)]:
            piece=[max(box[0],offset)-offset,box[1],min(box[2],offset+700)-offset,box[3]]
            if piece[2]<=piece[0]:continue
            info=next(f for f in m['files'] if f['image_id']==key)
            m['entries'].append(dict(image_id=key,box=piece,text=target,csv_row=item['csv_row'],sources=info['sources'],mask_rgba=[0,0,0,0],
                text_rgba=rendering['text_rgba'],rendering=dict(rendering,stitched_box=box,tile_x=offset,background_mode='composite_'+rendering['background_mode'])))
    for key,offset in [(LEFT,0),(RIGHT,700)]:
        path=OUT/f'images/{key}.png';full.crop((offset,0,offset+700,1000)).save(path)
        next(f for f in m['files'] if f['image_id']==key)['sha256']=digest(path.read_bytes())
    m['composite_labels']=SEAM['observations'];m['texture_styles_sha256']=digest(STYLES.read_bytes())
    write_json(OUT/'IMAGE_PATCH_MANIFEST.json',m);full.save(OUT/'map_preview.png')
    print(json.dumps(dict(files=len(m['files']),entries=len(m['entries'])),ensure_ascii=False))

if __name__=='__main__':main()
