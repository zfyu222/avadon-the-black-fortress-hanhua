"""Build an offline, hash-bound x86 display adapter without running the game."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import shutil
import struct
import subprocess

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT.parents[1]
HERE = Path(__file__).resolve().parent
BUILD = HERE / 'Build'
PAYLOAD = HERE / 'Payload'
SUPPORTED = 'd3d897e0b0608aad52f22e09d9b2174653b5903e6de9b1cc8e396ebc3c72d44e'
MINHOOK_COMMIT = 'c3fcafdc10146beb5919319d0683e44e3c30d537'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def pe_file_offset(data, address):
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if data[pe:pe + 4] != b'PE\0\0' or struct.unpack_from('<H', data, pe + 4)[0] != 0x14c:
        raise ValueError('Expected supported x86 PE image')
    optional = pe + 24
    if struct.unpack_from('<H', data, optional)[0] != 0x10b:
        raise ValueError('Expected PE32')
    base = struct.unpack_from('<I', data, optional + 28)[0]
    count, size = struct.unpack_from('<H', data, pe + 6)[0], struct.unpack_from('<H', data, pe + 20)[0]
    for i in range(count):
        section = optional + size + 40 * i
        virtual_size, rva, raw_size, raw = struct.unpack_from('<IIII', data, section + 8)
        if rva <= address - base < rva + min(virtual_size, raw_size):
            return raw + address - base - rva
    raise ValueError('Expected address is not file backed')

def native_display_bytes(data):
    punctuation = {0xc4: ord('-'), 0xd0: ord('-'), 0xd2: ord('"'), 0xd3: ord('"'), 0xd4: ord("'"), 0xd5: ord("'")}
    return bytes(punctuation.get(b, 32) if b > 127 else b for b in data)

def runtime_target(source, target):
    # Preserve the native display semantics of leftover legacy control bytes.
    # The formal CSV remains untouched; e.g. raw CA (shown as Ê in CP1252)
    # was displayed as a space by FUN_0046e080, not as a Latin letter.
    changes = []
    for byte in set(source):
        if byte < 128:
            continue
        char = bytes([byte]).decode('cp1252')
        if char in target:
            replacement = native_display_bytes(bytes([byte])).decode('ascii')
            target = target.replace(char, replacement)
            changes.append({'source_byte': hex(byte), 'formal_character': char, 'display_character': replacement})
    return target, changes

def dictionary():
    source = PROJECT / 'avadon-the-black-fortress_text.csv'
    translated = PROJECT / 'avadon-the-black-fortress_text_translated.csv'
    validation = json.loads((PROJECT / 'TranslateFiles/reports/final_validation.json').read_text(encoding='utf-8-sig'))
    if validation.get('status') != 'passed' or validation.get('semantic_review') != 'full' or validation['source_sha256'] != sha(source) or validation['translation_sha256'] != sha(translated):
        raise ValueError('Formal text validation is missing or stale')
    def rows(path):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            values = list(csv.reader(stream))
        if any(len(row) != 1 for row in values):
            raise ValueError('Expected one-column CSV')
        return [row[0] for row in values]
    originals, targets = rows(source), rows(translated)
    if len(originals) != len(targets) or len(originals) != validation['records']:
        raise ValueError('Formal text record alignment mismatch')
    entries, origins, collisions, adaptations = {}, {}, [], []
    def add(key, value, row, kind):
        encoded = value.encode('utf-8')
        if key in entries and entries[key] != encoded:
            collisions.append({'row': row, 'kind': kind, 'key_hex': key.hex(), 'previous': origins[key]})
            return
        entries[key] = encoded
        origins.setdefault(key, {'row': row, 'kind': kind})
    # Exact original keys always take precedence over optional display variants.
    for index, (original, target) in enumerate(zip(originals, targets), 1):
        raw = original.encode('cp1252')
        visible, changes = runtime_target(raw, target)
        if changes:
            adaptations.append({'row': index, 'changes': changes, 'evidence': 'Analysis/render_pipeline.json: FUN_0046e080 legacy sanitizer'})
        add(raw, visible, index, 'exact')
    for index, (original, target) in enumerate(zip(originals, targets), 1):
        raw = original.encode('cp1252');visible, _ = runtime_target(raw, target)
        variants = []
        if b'_' in raw:
            variants.append((raw.replace(b'_', b'"'), visible.replace('_', '"'), 'text_library_quote_escape_004711b0'))
        if raw.startswith(b'$'):
            variants.append((raw[1:], visible[1:] if visible.startswith('$') else visible, 'manual_heading_marker_removed'))
        sanitized = native_display_bytes(raw)
        if sanitized != raw:
            variants.append((sanitized, visible, 'native_display_sanitizer_0046e080'))
        for key, value, kind in variants:
            if key in entries and entries[key] != value.encode('utf-8'):
                # A canonical exact key is authoritative. Do not override it or
                # choose among conflicting semantic proposals by program.
                collisions.append({'row': index, 'kind': kind, 'key_hex': key.hex(), 'previous': origins[key], 'action': 'variant_omitted'})
                continue
            add(key, value, index, kind)
    path = PAYLOAD / 'AvadonChinese/translations.bin'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as out:
        out.write(b'AVZH1\0\0\0' + struct.pack('<I', len(entries)))
        for key, value in entries.items():
            out.write(struct.pack('<II', len(key), len(value)));out.write(key);out.write(value)
    # Standalone GDI test verifies the complete approved character inventory.
    glyphs = ''.join(sorted({c for value in targets for c in value if not c.isspace()}))
    (BUILD / 'required_glyphs.bin').write_bytes(glyphs.encode('utf-16le'))
    report = {'records': len(originals), 'keys': len(entries), 'source_sha256': sha(source), 'translation_sha256': sha(translated), 'dictionary_sha256': sha(path),
              'variants': list(origins.values()), 'omitted_conflicting_variants': collisions, 'legacy_display_adaptations': adaptations, 'original_game_data_modified': False}
    write_json(BUILD / 'dictionary_report.json', report)
    return report

def compiler():
    candidates = list(Path('C:/Program Files/Microsoft Visual Studio').glob('*/Community/VC/Auxiliary/Build/vcvars32.bat'))
    if not candidates:
        raise FileNotFoundError('An installed Visual Studio x86 toolchain is required')
    variables = sorted(candidates)[-1]
    vc = variables.parents[2]
    dumpbins = sorted(vc.glob('Tools/MSVC/*/bin/Hostx64/x86/dumpbin.exe'))
    if not dumpbins:
        raise FileNotFoundError('x86 dumpbin not found')
    return variables, dumpbins[-1]

def forwarders(dumpbin):
    original = Path('C:/Windows/SysWOW64/winmm.dll')
    output = subprocess.run([str(dumpbin), '/nologo', '/exports', str(original)], check=True, capture_output=True, text=True).stdout
    exports = []
    for line in output.splitlines():
        named = re.match(r'^\s*(\d+)\s+[0-9A-F]+\s+[0-9A-F]{8}\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s|$)', line)
        unnamed = re.match(r'^\s*(\d+)\s+[0-9A-F]{8}\s+\[NONAME\]', line)
        if named:
            exports.append({'ordinal': int(named[1]), 'name': named[2]})
        elif unnamed:
            exports.append({'ordinal': int(unnamed[1]), 'name': None})
    if len(exports) != 193 or len({e['ordinal'] for e in exports}) != 193:
        raise ValueError('Unexpected local x86 winmm export inventory; review before generating forwarding ABI')
    clock = next(i for i, e in enumerate(exports) if e['name'] == 'timeGetTime')
    header = '#pragma once\n#include <windows.h>\n#define AVZH_FORWARD_COUNT 193\n#define AVZH_CLOCK_INDEX ' + str(clock) + '\n'
    header += 'static const char* const avzh_forward_names[]={'+','.join(json.dumps(e['name']) if e['name'] else 'nullptr' for e in exports)+'};\n'
    header += 'static const WORD avzh_forward_ordinals[]={'+','.join(str(e['ordinal']) for e in exports)+'};\n'
    (BUILD / 'forward_metadata.hpp').write_text(header, encoding='utf-8')
    definitions = ['LIBRARY winmm', 'EXPORTS'];stubs = []
    for i, item in enumerate(exports):
        if i == clock:
            internal = '_ProxyClock@0'
        else:
            internal = 'Forward' + str(i)
            stubs.append('extern "C" __declspec(naked) void Forward'+str(i)+'(){\n    __asm {\n        pushfd\n        pushad\n        push '+str(i)+'\n        call ResolveForward\n        add esp,4\n        popad\n        popfd\n        jmp dword ptr [g_forwards+'+str(i*4)+']\n    }\n}\n')
        name = item['name'] or 'Ordinal'+str(item['ordinal'])
        definitions.append(f'    {name}={internal} @{item["ordinal"]}'+(' NONAME' if item['name'] is None else ''))
    (BUILD / 'forward_stubs.inc').write_text('\n'.join(stubs), encoding='utf-8')
    (BUILD / 'winmm.def').write_text('\n'.join(definitions)+'\n', encoding='ascii')
    write_json(BUILD / 'winmm_exports.json', {'reference': str(original), 'sha256': sha(original), 'exports': exports, 'system_binary_copied': False})
    return exports

def image_payload():
    root = PROJECT / 'ImagePatch/build-v9'
    manifest = json.loads((root / 'IMAGE_PATCH_MANIFEST.json').read_text(encoding='utf-8-sig'))
    translated = PROJECT / 'avadon-the-black-fortress_images_text_translated.csv'
    if manifest['translation_sha256'] != sha(translated):
        raise ValueError('Image translation changed after texture build')
    from PIL import Image
    results = []
    for item in manifest['files']:
        source = root / item['path']
        if sha(source) != item['sha256']:
            raise ValueError('Image candidate hash mismatch')
        for origin in item['sources']:
            relative = Path(origin['path'])
            original = PROJECT / 'Game' / relative
            if sha(original) != origin['file_sha256']:
                installed=json.loads((HERE/'INSTALLATION.json').read_text(encoding='utf-8-sig'))
                backup=Path(installed['backup_directory'])/origin['path']
                if sha(original)!=installed['payload_files'].get(origin['path']) or not backup.is_file() or sha(backup)!=origin['file_sha256']:
                    raise ValueError('Original backup or current installed image differs')
            # REA FUN_00471290 probes BMP, then PNG, then JPG. A PNG sibling
            # overrides a JPG while preserving the original; BMP must remain BMP.
            target_relative = relative if relative.suffix.lower() == '.bmp' else relative.with_suffix('.png')
            destination = PAYLOAD / target_relative;destination.parent.mkdir(parents=True, exist_ok=True)
            if target_relative.suffix.lower() == '.bmp':
                with Image.open(source) as image:
                    image.convert('RGB').save(destination, format='BMP')
            else:
                shutil.copy2(source, destination)
            with Image.open(destination) as image:
                if list(image.size) != [origin['width'], origin['height']]:
                    raise ValueError('Engine image dimensions changed')
            results.append({'path': target_relative.as_posix(), 'sha256': sha(destination), 'original_source': origin['path'], 'original_sha256': origin['file_sha256']})
    return results

def build(compile_code=True):
    BUILD.mkdir(parents=True, exist_ok=True);PAYLOAD.mkdir(parents=True, exist_ok=True)
    game = PROJECT / 'Game/Avadon.exe'
    if sha(game) != SUPPORTED:
        raise ValueError('Unsupported Avadon executable')
    data = game.read_bytes()
    for address, expected in [(0x46e080, '558bec81ec40080000'), (0x46df00, '558bec81ec14040000')]:
        offset = pe_file_offset(data, address)
        if data[offset:offset+9].hex() != expected:
            raise ValueError('REA hook bytes do not match the shipped file')
    mh = WORKSPACE / 'Tools/native/MinHook'
    commit = subprocess.run(['git', '-C', str(mh), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
    if commit != MINHOOK_COMMIT:
        raise ValueError('MinHook revision differs from reviewed v1.3.4')
    variables, dumpbin = compiler();forwarders(dumpbin);report = dictionary();images = image_payload()
    shutil.copy2(mh / 'LICENSE.txt', PAYLOAD / 'AvadonChinese/MinHook-LICENSE.txt')
    obj = BUILD / 'obj';obj.mkdir(exist_ok=True)
    def quote(path):
        return '"'+str(path)+'"'
    commands = ['@echo off', 'call '+quote(variables)+' >'+quote(BUILD/'compiler_env.log')+' 2>&1', 'if errorlevel 1 exit /b 1']
    objects = []
    for relative in ['src/buffer.c', 'src/hook.c', 'src/trampoline.c', 'src/hde/hde32.c']:
        target = obj / (Path(relative).stem+'.obj');objects.append(target)
        commands += ['cl /nologo /c /O2 /MT /W3 /TC /I'+quote(mh/'include')+' '+quote(mh/relative)+' /Fo'+quote(target), 'if errorlevel 1 exit /b 1']
    common = '/nologo /std:c++17 /utf-8 /O2 /Oy- /MT /EHsc /W4 /I'+quote(mh/'include')+' /I'+quote(BUILD)+' /I'+quote(HERE/'native')
    commands += ['cl '+common+' /LD '+quote(HERE/'native/adapter.cpp')+' '+ ' '.join(quote(o) for o in objects)+' /Fo'+quote(obj/'adapter.obj')+' /link /DEF:'+quote(BUILD/'winmm.def')+' /OUT:'+quote(PAYLOAD/'winmm.dll')+' /IMPLIB:'+quote(BUILD/'winmm.lib'), 'if errorlevel 1 exit /b 1']
    if (HERE/'native/self_test.cpp').exists():
        commands += ['cl '+common+' /DAVZH_SELF_TEST '+quote(HERE/'native/adapter.cpp')+' '+quote(HERE/'native/self_test.cpp')+' '+' '.join(quote(o) for o in objects)+' /Fo'+quote(str(obj)+'/')+' /link /OUT:'+quote(BUILD/'self_test.exe'), 'if errorlevel 1 exit /b 1']
    script = BUILD / 'build_native.cmd';script.write_text('\r\n'.join(commands)+'\r\n', encoding='utf-8')
    if compile_code:
        result = subprocess.run(['cmd.exe', '/d', '/c', str(script)], cwd=BUILD, capture_output=True, text=True, encoding='utf-8', errors='replace')
        (BUILD/'compiler.log').write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
        if result.returncode:
            print(result.stdout[-9000:]);print(result.stderr[-2000:]);raise RuntimeError('Native build failed; see compiler.log')
    manifest = {'status': 'built_not_installed' if compile_code else 'prepared', 'supported_exe_sha256': SUPPORTED, 'dictionary': report, 'image_build': 'ImagePatch/build-v9',
                'images': images, 'native_sources': {p.name: sha(p) for p in (HERE/'native').glob('*') if p.is_file()}, 'minhook_commit': commit,
                'game_started': False, 'in_game_verified': False, 'installed': False}
    if (PAYLOAD/'winmm.dll').exists():
        manifest['dll_sha256'] = sha(PAYLOAD/'winmm.dll')
    write_json(HERE/'BUILD_MANIFEST.json', manifest)
    print(json.dumps({'status': manifest['status'], 'dictionary_keys': report['keys'], 'textures': len(images), 'dll_sha256': manifest.get('dll_sha256')}, ensure_ascii=False))

if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--prepare-only', action='store_true');args = parser.parse_args();build(not args.prepare_only)
