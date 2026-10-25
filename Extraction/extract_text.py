"""Read-only extraction for Steam build 4252712; never modifies Game/."""
from pathlib import Path
import csv, hashlib, json, re, struct, collections
from inspect_scripts import ROOT, strings

NAME='avadon-the-black-fortress'
GAME=ROOT/'Game'
OUT=ROOT/'Extraction'
EXE_HASH='d3d897e0b0608aad52f22e09d9b2174653b5903e6de9b1cc8e396ebc3c72d44e'

def sha(b): return hashlib.sha256(b).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def evidence(name): return json.loads((ROOT/'Analysis'/name).read_text(encoding='utf-8'))

def main():
    rows=[]; exclusions=[]; manifest={}
    for p in sorted((GAME/'Avadon Files/Scripts').glob('*.txt')):
        manifest[p.relative_to(GAME).as_posix()]={'sha256':sha(p.read_bytes()),'size':p.stat().st_size}
    for r in strings():
        r['encoding']='cp1252'; r['kind']='script'; r['classification']='display'
        if r['context'] in {'assign:cr_default_script','assign:ob_default_script'}:
            r['reason']='script resource identifier'; exclusions.append(r); continue
        if r['context']=='call:set_coloradj':
            r['reason']='malformed string in numeric color-adjustment parameter; not a display call'; exclusions.append(r); continue
        if not r['text'].strip():
            r['reason']='empty/whitespace slot'; exclusions.append(r); continue
        assert r['context']!='UNKNOWN',r
        original=(GAME/r['file']).read_bytes()[r['offset']:r['offset']+r['length']]
        assert original.decode('cp1252')==r['text']
        rows.append(r)

    p=GAME/'Avadon Files/AvScenData.dat'; b=p.read_bytes()
    manifest[p.relative_to(GAME).as_posix()]={'sha256':sha(b),'size':len(b)}
    zones=struct.unpack_from('<h',b)[0]
    assert zones==24 and len(b)==0x1168+zones*0x3d42c
    def field(offset,capacity,context,**kw):
        raw=b[offset:offset+capacity]; assert b'\0' in raw
        text=raw.split(b'\0',1)[0].decode('cp1252')
        if text.strip():
            rows.append(dict(kind='dat',file=p.relative_to(GAME).as_posix(),offset=offset,
                             length=len(text),capacity=capacity,encoding='cp1252',text=text,
                             context=context,classification='display',**kw))
    for z in range(zones): field(4+z*44,32,'zone_name',zone=z,reference_function='0x4283f0;0x4518f0')
    for z in range(zones):
        for layer in range(2):
            base=0x1168+z*0x3d42c+layer*0x161f8
            for i in range(10):
                field(base+0x15604+i*256,256,'terrain_message',zone=z,layer=layer,slot=i,reference_function='0x451f90')
                field(base+0x16054+i*40,40,'map_label',zone=z,layer=layer,slot=i,reference_function='0x451f90;0x456c10')

    exe=(GAME/'Avadon.exe').read_bytes(); assert sha(exe)==EXE_HASH
    manifest['Avadon.exe']={'sha256':sha(exe),'size':len(exe)}
    # PE metadata only: virtual address, RVA and file offset remain distinct.
    pe=struct.unpack_from('<I',exe,0x3c)[0];n=struct.unpack_from('<H',exe,pe+6)[0]
    optsize=struct.unpack_from('<H',exe,pe+20)[0]; imagebase=struct.unpack_from('<I',exe,pe+24+28)[0]
    sections=[]
    for i in range(n):
        off=pe+24+optsize+40*i
        vs,va,rs,rp=struct.unpack_from('<IIII',exe,off+8)
        sections.append((va,rs,rp))
    def native(a,text,encoding,context,ev):
        rva=a-imagebase
        sec=next((x for x in sections if x[0]<=rva<x[0]+x[1]),None)
        if not sec: return
        offset=sec[2]+rva-sec[0]; raw=text.encode(encoding)
        assert exe[offset:offset+len(raw)]==raw,(hex(a),text)
        rows.append(dict(kind='native',file='Avadon.exe',address=hex(a),rva=hex(rva),
                         offset=offset,length=len(raw),capacity=len(raw)+(2 if encoding=='utf-16-le' else 1),
                         encoding=encoding,text=text,context=context,classification='display',evidence_id=ev,
                         reference_function='not individually traced; reviewed game literal/table region',
                         repack_note='requires relocation or display-layer hook when translation exceeds capacity'))
    s=evidence('ghidra-strings.json')
    for r in s['normalized_result']:
        a=int(r['address'],16);t=r['value']
        include=(0x5a6160<=a<0x5ad790 or 0x5ae9b4<=a<0x5aea08 or 0x5aecc0<=a<0x5aede8
                 or 0x5aee70<=a<0x5af394 or a in {0x5af6c8,0x5af6f4,0x5af710,0x5b097c}
                 or 0x5af9ec<=a<0x5b0488 or 0x5b0660<=a<0x5b06ec
                 or 0x5cdc26<=a<=0x5ce2f2 or 0x5ce7d0<=a<=0x5ce960
                 or 0x5cef68<=a<=0x5cefa4 or 0x5d07d0<=a<=0x5d0839
                 or 0x601038<=a<=0x6010aa)
        reason=None
        if not include: reason='outside reviewed display-text regions'
        elif (not re.search('[A-Za-z]',re.sub(r'%[-+ #0-9.*hlL]*[a-zA-Z%]','',t))): reason='format/punctuation only'
        elif ('_' in t and a not in {0x5af710}) or re.match(r'(?i)\s*(?:DEBUG|Error|Talking Error|Shop Error|Abil slot|Ability num|Char using|Item being|Creature assigned|Floating text)',t): reason='engine diagnostic'
        elif re.search(r'https?://|\.dat$|^%s.*(?:Save|Spiderweb|Avadon Files)|^%sSave',t): reason='URL or filesystem template'
        elif t in {'Unused','mobnull','mobbasic','Zone Name','NullZoneSc'}: reason='unused/default/resource identifier'
        elif a in {0x5ac6bc,0x5ac4fc,0x5ac508,0x5ac514,0x5ac984,0x5ab6d8}: reason='debug diagnostic'
        if reason:
            exclusions.append(dict(kind='native',address=r['address'],text=t,reason=reason));continue
        encoding='utf-16-le' if r['string']['encoding'].startswith('UTF-16') else 'ascii'
        native(a,t,encoding,'native_ui_or_message',s['evidence_id'])
    # Ghidra's defined-string inventory omits some short labels; obtain their bytes through REA.
    short_addresses={0x5a9198,0x5a9f88,0x5a9f8c,0x5aa504,0x5aa50c,0x5aa534,0x5aa538,0x5aa66c,
                     0x5af9e4,0x5af9f4,0x5ae9b4}
    for name in ['game_literals','ui_tables','class_table','damage_table']:
        ev=evidence(name+'.json');d=ev['normalized_result'];raw=bytes.fromhex(d['bytes_hex']);base=int(d['address'],16)
        for m in re.finditer(rb'[\x20-\x7e]+\x00',raw):
            a=base+m.start();t=m.group()[:-1].decode('ascii')
            if name=='game_literals' and a not in short_addresses: continue
            if not t.strip() or any(x.get('address')==hex(a) for x in rows):continue
            native(a,t,'ascii','short_label_or_fixed_ui_table',ev['evidence_id'])

    corpus=[];index={};mapping=[]
    for r in rows:
        t=r.pop('text')
        if t not in index:
            index[t]=len(corpus);corpus.append(t);mapping.append({'row':len(corpus),'text':t,'sources':[]})
        mapping[index[t]]['sources'].append(r)
    path=ROOT/(NAME+'_text.csv')
    if path.exists():
        with path.open(encoding='utf-8-sig',newline='') as f: old=list(csv.reader(f))
        assert old==[[t] for t in corpus], 'Refusing to overwrite a different existing corpus'
    else:
        with path.open('x',encoding='utf-8-sig',newline='') as f:csv.writer(f,lineterminator='\n').writerows([[t] for t in corpus])
    with path.open(encoding='utf-8-sig',newline='') as f:assert list(csv.reader(f))==[[t] for t in corpus]
    write_json(ROOT/(NAME+'_text.mapping.json'),{'schema':1,'source_sha256':sha(path.read_bytes()),'deduplication':'exact text; all source occurrences retained','entries':mapping})
    write_json(OUT/'source_manifest.json',manifest)
    write_json(OUT/'excluded_strings.json',exclusions)
    report={'unique_texts':len(corpus),'source_occurrences':len(rows),'by_kind':dict(collections.Counter(x['kind'] for x in rows)),
            'script_files':279,'zone_count':zones,'imagebase':hex(imagebase),'csv_sha256':sha(path.read_bytes()),
            'validation':'all mapped source spans match original bytes; single-column CSV round-trip passed',
            'limitations':['Static reviewed corpus, not proof of complete runtime coverage.','Native diagnostics, third-party library strings, format-only strings and internal keys excluded.','Native literals not all individually traced; repacking must verify call site and capacity.','Chinese encoding/font support and runtime rendering unverified.']}
    write_json(OUT/'report.json',report);print(json.dumps(report,ensure_ascii=True,indent=2))

if __name__=='__main__': main()
