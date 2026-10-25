from pathlib import Path
import re, collections, json

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r'//[^\r\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"')

def strings():
    for p in sorted((ROOT/'Game/Avadon Files/Scripts').glob('*.txt')):
        data=p.read_bytes(); s=data.decode('cp1252')
        clean=list(s)
        for m in TOKEN.finditer(s):
            if not m.group().startswith('"'):
                clean[m.start():m.end()]=[' ' if c not in '\r\n' else c for c in m.group()]
        clean=''.join(clean)
        for m in TOKEN.finditer(s):
            if not m.group().startswith('"'): continue
            prefix=clean[:m.start()]
            boundary=max(prefix.rfind(';'),prefix.rfind('{'),prefix.rfind('}'))
            statement=prefix[boundary+1:].strip()
            assign=re.search(r'(\w+)\s*=\s*$',statement)
            masked=TOKEN.sub(lambda x:' '*len(x.group()),statement)
            stack=[]
            for par in re.finditer(r'[()]',masked):
                if par.group()=='(':
                    name=re.search(r'([A-Za-z_]\w*)\s*$',masked[:par.start()])
                    stack.append(name[1] if name else '?')
                elif stack: stack.pop()
            context=('assign:'+('NUMBER' if assign[1].isdigit() else assign[1])) if assign else ('call:'+stack[-1] if stack else 'UNKNOWN')
            yield dict(file=p.relative_to(ROOT/'Game').as_posix(), offset=m.start()+1,
                       length=m.end()-m.start()-2, line=len(re.findall(r'\r\n|\r|\n',s[:m.start()]))+1,
                       text=m.group()[1:-1], context=context, statement=statement[-240:])

if __name__=='__main__':
    groups=collections.defaultdict(list)
    for row in strings(): groups[row['context']].append(row)
    for k,rows in sorted(groups.items(),key=lambda kv:-len(kv[1])):
        print(k,len(rows),json.dumps(rows[:2],ensure_ascii=True)[:650])
