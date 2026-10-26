"""Bind user-reported English to existing approved translations, no API calls."""
from pathlib import Path
import csv
import struct
import shutil
import build_patch as bp

def main():
    p=bp.PROJECT;out=bp.HERE/'UserFeedback/20261026';out.mkdir(parents=True,exist_ok=True)
    probes=['Gameplay Settings','Avadon Settings','Avadon Instructions','Select a topic to the left.','Hold Tab key to see entire map.','Hold Shift key to see creature names.','Welcome to Avadon! These messages will pop up']
    def rows(path):
        with path.open(encoding='utf-8-sig',newline='') as stream:return [row[0] for row in csv.reader(stream)]
    source=rows(p/'avadon-the-black-fortress_text.csv');target=rows(p/'avadon-the-black-fortress_text_translated.csv')
    data=(bp.PAYLOAD/'AvadonChinese/translations.bin').read_bytes();count=struct.unpack_from('<I',data,8)[0];position=12;entries={}
    for _ in range(count):
        a,b=struct.unpack_from('<II',data,position);position+=8;entries[data[position:position+a]]=data[position+a:position+a+b];position+=a+b
    matches=[]
    for probe in probes:
        found=[]
        for i,(a,b) in enumerate(zip(source,target),1):
            if probe in a:
                expected,_=bp.runtime_target(a.encode('cp1252'),b)
                assert entries.get(a.encode('cp1252'))==expected.encode('utf-8')
                found.append({'csv_row':i,'source':a,'approved_translation':b,'compiled_dictionary_exact_key':True})
        assert found,'Reported source absent: '+probe
        matches.append({'reported_probe':probe,'matches':found})
    images=[]
    for index,name in enumerate(['codex-clipboard-546351d4-4a80-4aed-afed-47a3604f7147.png','codex-clipboard-38b43364-18de-411c-a87f-932810812b2e.png','codex-clipboard-329a8f1c-4319-4ddb-8485-5050f6d76a2e.png'],1):
        origin=Path('C:/Users/zfyu2/AppData/Local/Temp')/name;destination=out/'screenshots'/f'{index}.png';destination.parent.mkdir(exist_ok=True)
        shutil.copy2(origin,destination);assert bp.sha(origin)==bp.sha(destination)
        images.append({'path':destination.relative_to(p).as_posix(),'sha256':bp.sha(destination)})
    bp.write_json(out/'report.json',{'user_test_result':'body_localization_failed_images_visible','screenshots':images,'reported_source_matches':matches,'source_sha256':bp.sha(p/'avadon-the-black-fortress_text.csv'),'translation_sha256':bp.sha(p/'avadon-the-black-fortress_text_translated.csv'),'repair':'independent_DLL_bootstrap_instead_of_timer_only','repair_component_test': 'passed_without_timeGetTime','repaired_game_test':'pending_user_retest','paid_api_requests':0,'game_started_by_agent':False})
    print({'reported_probes':len(matches),'all_present_in_approved_translation_and_dictionary':True})

if __name__=='__main__':main()
