from pathlib import Path
import json,traceback
from mb_predictive_finalize import finalize_case
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/pose-harvest';catalog=json.loads((OUT/'catalog.json').read_text())
for c in catalog['cases']:
 if c.get('retarget')!='passed':continue
 try:
  finalize_case(ROOT/c['directory'],OUT/'review'/c['id']);v=json.loads((OUT/'review'/c['id']/'validation-report.json').read_text());b=json.loads((OUT/'review'/c['id']/'linear/validation-report.json').read_text());c.update(validation='passed',minimum_floor_m=min(v['skinned_geometry_min_floor_y_m'],b['skinned_geometry_min_floor_y_m']));print('HARVEST_VALIDATED',c['id'],'floor',c['minimum_floor_m'],flush=True)
 except Exception as e:c.update(validation='failed',validation_error=str(e));traceback.print_exc()
 (OUT/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf8')
