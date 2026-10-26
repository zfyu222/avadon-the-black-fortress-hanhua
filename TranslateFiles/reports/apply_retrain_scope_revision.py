"""Reuse unchanged real reviews; apply the independently reviewed single-ref scope correction."""
from pathlib import Path
import sys,copy,json,hashlib,csv
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT.parents[1]/'Tools/localization'))
from translation_workflow import Workflow,write_json

def main():
    root=PROJECT/'TranslateFiles';original_path=root/'glossary/r3/glossary_original.json'
    if (root/'reports/retrain_scope_revision_receipt.json').exists():
        raise RuntimeError('This one-time scope revision was already applied; retain the existing revision and attempt history.')
    old=json.loads((root/'glossary/r3/freeze_9ac86720/glossary_decisions.json').read_text(encoding='utf-8-sig'))
    original=json.loads(original_path.read_text(encoding='utf-8-sig'))
    delta=json.loads((root/'reports/retrain_scope_review_decision.json').read_text(encoding='utf-8-sig'))
    assert delta['ref']=='non_translate:22' and original['non_translate'][22]['source']=='retrain'
    snapshot=copy.deepcopy(original)
    snapshot['non_translate'][22]['evidence_rows']=sorted(set(snapshot['non_translate'][22].get('evidence_rows',[]))|set(delta['entry_reviews'][0]['evidence_rows']))
    folder=root/'glossary/retrain_scope_fix';folder.mkdir(exist_ok=True)
    snapshot_path=folder/'glossary_original.json';write_json(snapshot_path,snapshot)
    merged=copy.deepcopy(old)
    merged['snapshot_sha256']=hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    merged['edits']=[e for e in merged['edits'] if not(e['table']=='non_translate' and e['index']==22)]+delta['edits']
    merged['entry_reviews']=[r for r in merged['entry_reviews'] if r['ref']!=delta['ref']]+delta['entry_reviews']
    merged['review_instances'][delta['ref']]='/root/retrain_semantic_diagnosis'
    merged['review_summary']+='\nTargeted scope correction: non_translate:22 freshly reviewed by /root/retrain_semantic_diagnosis; every other unchanged entry retains its original actual review and reviewer. No new full-table review claimed.'
    decisions_path=folder/'glossary_decisions.json';write_json(decisions_path,merged)
    flow=Workflow(PROJECT)
    result=flow.revise_glossary(snapshot_path,decisions_path,'User screenshot proves retrain command non-translate leaked into two natural sentences; independently reviewed whole-record scope correction; preserve unchanged review evidence and attempts.')
    write_json(root/'reports/retrain_scope_revision_receipt.json',result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
