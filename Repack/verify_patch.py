"""Verify prepared payload and run our own component executable, never Avadon."""
from pathlib import Path
import csv
import json
import math
import struct
import subprocess
from PIL import Image, ImageDraw
import build_patch as bp

P = bp.PROJECT
R = bp.HERE


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def image_checks():
    root = P / 'ImagePatch/build-v4'
    manifest = load(root / 'IMAGE_PATCH_MANIFEST.json')
    checks = []
    cells = []
    for item in manifest['files']:
        target = Image.open(root / item['path']).convert('RGBA')
        require(bp.sha(root / item['path']) == item['sha256'], 'Texture hash changed')
        entries = [e for e in manifest['entries'] if e['image_id'] == item['image_id']]
        mask = Image.new('1', target.size)
        draw = ImageDraw.Draw(mask)
        for entry in entries:
            x1, y1, x2, y2 = entry['box']
            # Shared image_patch uses floor/ceil and half-open paste rectangles.
            box = (max(0, math.floor(x1)), max(0, math.floor(y1)), min(target.width, math.ceil(x2)), min(target.height, math.ceil(y2)))
            draw.rectangle((box[0], box[1], box[2]-1, box[3]-1), fill=1)
            require(entry['text_rgba'] == [245, 240, 220, 255], 'White color-key would erase text')
            require(entry['rendering']['font_size'] >= 10, 'Unreadable font size')
            # Check actual opaque ink pixels survive the native white color key.
            crop = target.crop(box)
            require(any(pixel[:3] == (245, 240, 220) and pixel[3] for pixel in crop.getdata()), 'No visible non-key glyph core')
        original = Image.open(P / 'Game' / item['sources'][0]['path']).convert('RGBA')
        require(original.size == target.size, 'Dimensions changed')
        require(all(a == b or allowed for a, b, allowed in zip(original.getdata(), target.getdata(), mask.getdata())), 'Pixels outside render rectangles changed')
        checks.append({'source': item['sources'][0]['path'], 'dimensions_preserved': True, 'outside_render_rectangles_unchanged': True, 'non_white_glyphs_survive_native_color_key': True, 'sha256': item['sha256']})
        cell = Image.new('RGB', (360, 330), (35, 35, 35))
        label = ImageDraw.Draw(cell)
        label.text((6, 5), Path(item['sources'][0]['path']).name, fill='white')
        target.thumbnail((350, 300))
        cell.paste(target, ((360-target.width)//2, 25), target)
        cells.append(cell)
    contact = Image.new('RGB', (360*4, 330*math.ceil(len(cells)/4)), (25,25,25))
    for i, cell in enumerate(cells):
        contact.paste(cell, ((i%4)*360, (i//4)*330))
    contact.save(root / 'contact.jpg', quality=92)
    result = {'status': 'passed', 'files': checks, 'changed_regions': len(manifest['entries']), 'preserved_regions': len(manifest['preserved_regions']), 'manifest_sha256': bp.sha(root/'IMAGE_PATCH_MANIFEST.json'), 'game_started': False}
    bp.write_json(root / 'STATIC_CHECKS.json', result)
    return result


def verify():
    manifest = load(R / 'BUILD_MANIFEST.json')
    require(bp.sha(P/'Game/Avadon.exe') == bp.SUPPORTED, 'Game build changed')
    for name, expected in manifest['native_sources'].items():
        require(bp.sha(R/'native'/name) == expected, 'Native source changed after compilation')
    require(bp.sha(bp.PAYLOAD/'winmm.dll') == manifest['dll_sha256'], 'DLL changed after compilation')
    require(bp.sha(bp.PAYLOAD/'AvadonChinese/translations.bin') == manifest['dictionary']['dictionary_sha256'], 'Dictionary changed')
    for suffix, report in [('', P/'TranslateFiles/reports/final_validation.json'), ('_images', P/'TranslateFiles/image-text/TranslateFiles/reports/final_validation.json')]:
        validation = load(report)
        source = P / ('avadon-the-black-fortress'+suffix+'_text.csv')
        target = P / ('avadon-the-black-fortress'+suffix+'_text_translated.csv')
        require(validation['status'] == 'passed' and validation['semantic_review'] == 'full', 'Formal review not complete')
        require(bp.sha(source) == validation['source_sha256'] and bp.sha(target) == validation['translation_sha256'], 'Formal review hash stale')
    data = (bp.PAYLOAD/'AvadonChinese/translations.bin').read_bytes()
    require(data[:8] == b'AVZH1\0\0\0', 'Dictionary header')
    count = struct.unpack_from('<I', data, 8)[0]
    entries = {};position = 12
    for i in range(count):
        a,b = struct.unpack_from('<II',data,position);position += 8
        key,value = data[position:position+a], data[position+a:position+a+b];position += a+b
        require(key not in entries, 'Duplicate dictionary key');entries[key] = value
    require(position == len(data), 'Dictionary trailing/truncated bytes')
    def rows(path):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            return [r[0] for r in csv.reader(stream)]
    originals = rows(P/'avadon-the-black-fortress_text.csv')
    translations = rows(P/'avadon-the-black-fortress_text_translated.csv')
    require(len(originals) == len(translations) == 15928, 'Record count')
    for source,target in zip(originals, translations):
        key = source.encode('cp1252')
        expected,_ = bp.runtime_target(key,target)
        require(entries.get(key) == expected.encode('utf-8'), 'Canonical translation mismatch')
        require(len(key) < 512, 'Native source input exceeds safe limit')
    images = image_checks()
    for image in manifest['images']:
        require(bp.sha(bp.PAYLOAD/image['path']) == image['sha256'], 'Engine texture changed')
        require(bp.sha(P/'Game'/image['original_source']) == image['original_sha256'], 'Original texture changed before installation')
    tests = R/'NativeTests';tests.mkdir(exist_ok=True)
    executable = bp.BUILD/'self_test.exe'
    completed = subprocess.run([str(executable), str(bp.PAYLOAD/'AvadonChinese/translations.bin'), str(bp.BUILD/'required_glyphs.bin'), str(bp.PAYLOAD/'winmm.dll'), str(tests)], capture_output=True, text=True, timeout=60)
    (tests/'test_output.log').write_text(completed.stdout+'\n'+completed.stderr, encoding='utf-8')
    require(completed.returncode == 0, 'Own component test failed: '+completed.stdout+completed.stderr)
    result = load(tests/'report.json')
    require(result['status'] == 'passed' and result['game_started'] is False and result['in_game_verified'] is False, 'Invalid component report')
    result['bindings'] = {str(path.relative_to(P)).replace('\\','/'): bp.sha(path) for path in [executable, bp.PAYLOAD/'winmm.dll', bp.PAYLOAD/'AvadonChinese/translations.bin', bp.BUILD/'required_glyphs.bin']}
    result['native_sources'] = manifest['native_sources']
    bp.write_json(tests/'report.json', result)
    Image.open(tests/'cjk_render.ppm').save(tests/'cjk_render.png')
    inventory = {path.relative_to(bp.PAYLOAD).as_posix(): bp.sha(path) for path in sorted(bp.PAYLOAD.rglob('*')) if path.is_file()}
    require(len(inventory) == 22, 'Unexpected payload count')
    final = {'status': 'passed', 'scope': 'offline_static_and_own_component_tests_only', 'supported_exe_sha256': bp.SUPPORTED, 'build_manifest_sha256': bp.sha(R/'BUILD_MANIFEST.json'), 'image_manifest_sha256': images['manifest_sha256'], 'component_report_sha256': bp.sha(tests/'report.json'), 'canonical_records_checked': len(originals), 'dictionary_keys': count, 'payload_files': inventory, 'game_started': False, 'in_game_verified': False, 'installed': False}
    bp.write_json(R/'STATIC_VALIDATION.json',final)
    print(json.dumps({'status': 'passed', 'payload_files':len(inventory), 'canonical_records':len(originals), 'game_started':False}))


if __name__ == '__main__':
    verify()
