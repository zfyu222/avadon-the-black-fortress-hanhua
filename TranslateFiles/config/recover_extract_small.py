import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path('D:/StaticHanHua/Tools/localization')))
from translation_workflow import Workflow

project = Path('D:/StaticHanHua/Projects/avadon-the-black-fortress')
flow = Workflow(project)
reason = ('Stopped official API extraction exhausted reasoning output on 128-record scopes; '
          'retain accepted results and used attempts, reduce remaining scopes to 32 records; '
          'allow one additional attempt beyond the existing limit after diagnosing rejected proper-name enforcement.')
report = {'previous_run': '887140b0f02449a99edd20819e573e68', 'reason': reason}
report['configuration'] = flow.configure({'max_attempts': 4}, reason, impact='none')
with flow.db() as db:
    revision = flow.meta(db, 'revision')
    tasks = [(row['id'], len(json.loads(row['ids']))) for row in db.execute(
        "SELECT id,ids FROM tasks WHERE revision=? AND stage='extract' AND status IN ('pending','running','failed')", (revision,))]
report['splits'] = [flow.split_extract_recovery(task, record_limit=32, worker_stopped=True)
                    for task, count in tasks if count > 32]
target = project / 'TranslateFiles/reports/extract_recovery_small_20261026.json'
target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'report': str(target), 'split_scopes': len(report['splits']),
                  'children': sum(len(row['children']) for row in report['splits']),
                  'untouched_small_scopes': sum(count <= 32 for _, count in tasks)}))
