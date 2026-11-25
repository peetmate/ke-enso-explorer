"""Promote only the reviewed, completely validated NDMA staging run."""
from pathlib import Path
import csv, hashlib, importlib.util, io, json, shutil, sys
import pandas as pd
import yaml
ROOT=Path.cwd(); DATA=ROOT/'data/KE-enso-explorer'; SRC=DATA/'_sources'
STAGE=SRC/'.ndma_cache/refresh-20261124'
HAND=ROOT/'playbook/handovers/KE-enso-explorer/data_updates/2026-11-24/ndma'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj): p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
receipt=json.loads((STAGE/'receipt.json').read_text())
assert receipt['status']=='VALIDATED_STAGED_NOT_PROMOTED'
assert receipt['cached_replay']['equal_except_harvested_at']
assert receipt['removed']==[]
assert receipt['revised']==[], 'Review unexpected metadata revisions before promotion'
assert sha(DATA/'ndma_bulletin_index.parquet')==receipt['prior_sha256'], 'Accepted index changed concurrently'
assert sha(STAGE/'candidate/ndma_bulletin_index.parquet')==receipt['candidate_sha256']
assert sha(SRC/'ndma_index_build.py')==receipt['builder_sha256']
report=pd.read_csv(STAGE/'candidate/ndma_index_validation_report.csv')
assert report.served.all() and set(report.category_id)=={7,11}
frame=pd.read_parquet(STAGE/'candidate/ndma_bulletin_index.parquet')
assert not frame.doc_uuid.duplicated().any()
sys.path.insert(0,str(SRC)); import ndma_index_build as ndma
assert all(ndma.gate(v) for v in receipt['validation'])
assert all(v['passes_used']==2 for v in receipt['validation'])
ordering={}
for cat_id in (7,11):
 a=STAGE/f'cache/pass0/ID{cat_id}_p0001.html'; b=STAGE/f'cache/pass1/ID{cat_id}_p0001.html'
 left=[x['doc_uuid'] for x in ndma.parse_rows(a.read_text())]; right=[x['doc_uuid'] for x in ndma.parse_rows(b.read_text())]
 assert left!=right, 'Sort did not change actual row order'
 ordering[str(cat_id)]={'natural_page_2_sha256':sha(a),'sorted_page_2_sha256':sha(b),'different_order':True}
old_report=pd.read_csv(STAGE/'before/ndma_index_validation_report.csv')
assert report.set_index('category_id').duplicate_uuids.fillna('').to_dict()==old_report.set_index('category_id').duplicate_uuids.fillna('').to_dict()
receipt['ordering_evidence']=ordering
receipt['compared_revision_fields']=['title_raw','county','ref_period','uploaded_date','detail_url','pdf_url']
added=frame[frame.doc_uuid.isin([r['doc_uuid'] for r in receipt['added']])]
assert set(added.ref_period)=={'2026-10'}, 'Review unexpected periods before promotion'
assert set(added.uploaded_date.astype(str))=={'2026-11-20'}, 'Review unexpected uploads before promotion'
# Every remaining write concerns this accepted index; generators remain authoritative.
HAND.mkdir(parents=True,exist_ok=True)
shutil.copy2('/tmp/ke_ndma_refresh_run.py',HAND/'stage_refresh.py')
shutil.copy2('/tmp/ke_ndma_promote.py',HAND/'promote_reviewed.py')
shutil.copy2(STAGE/'candidate/ndma_bulletin_index.parquet',DATA/'ndma_bulletin_index.parquet')
shutil.copy2(STAGE/'candidate/ndma_index_validation_report.csv',SRC/'ndma_index_validation_report.csv')
shutil.copy2(STAGE/'cache_manifest.json',SRC/'ndma_cache_manifest.json')
ledger=list(csv.DictReader(io.StringIO((SRC/'ndma_index_ledger.csv').read_text())))
for row in ledger:
 if row['category_id'] in ('7','11'):
  v=report[report.category_id.eq(int(row['category_id']))].iloc[0]
  n=int(v['items_reported']); unique=int(v['uuids_unique']); duplicates=int(v['duplicate_listings'])
  row.update(items_reported=str(n),status='SERVED',reason=f'Validated 2026-11-24: {n} rows enumerated per sweep (server-echoed page number checked on every page) = {unique} distinct documents + {duplicates} repeated listings; closure confirmed by a second sweep under a different sort finding 0 new documents')
 if 'of 3408)' in row['category']:
  row['category']=row['category'].replace('of 3408)',f"of {frame.scope.eq('county').sum()})")
with (SRC/'ndma_index_ledger.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=ledger[0]); w.writeheader(); w.writerows(ledger)
receipt.update(status='ACCEPTED',accepted_rows=receipt['candidate_rows'],output_sha256=receipt['candidate_sha256'],
 cache_manifest='data/KE-enso-explorer/_sources/ndma_cache_manifest.json',full_rollback='data/KE-enso-explorer/_sources/.refresh_backups/ndma-20261124',runner=str((HAND/'stage_refresh.py').relative_to(ROOT)),
 validation_report='_sources/ndma_index_validation_report.csv',
 replay_command='/Users/pstewarda/miniforge3/bin/python3 '+str((HAND/'stage_refresh.py').relative_to(ROOT))+' --stage data/KE-enso-explorer/_sources/.ndma_cache/refresh-20261124 --resume',
 refresh_command='/Users/pstewarda/miniforge3/bin/python3 data/KE-enso-explorer/_sources/ndma_index_build.py (redirect OUT, REPORT_CSV and CACHE to a new stage as documented in harvest-ndma-bulletins)',
 reproduction_note='Dated runner captures this 24 November run. Use a new directory for a new edition; --resume reuses only this run. Existing maintained ndma_index_build.py supplies parsing and gates.')
dump(SRC/'ndma_index_refresh.json',receipt)
sys.path.insert(0,str(SRC)); import meta_build
meta_build.D={'ndma_bulletin_index':meta_build.D['ndma_bulletin_index']}; meta_build.main()
inv_path=DATA/'governance/acquisition_inventory.json'; inv=json.loads(inv_path.read_text())
asset=next(a for a in inv['assets'] if a['id']=='ndma_bulletin_index')
asset.update(sha256=receipt['output_sha256'],handover=str((HAND/'summary.json').relative_to(ROOT)),maintenance_validation={'date':'2026-11-24','status':'passed','receipt':'data/KE-enso-explorer/_sources/ndma_index_refresh.json'})
spec=importlib.util.spec_from_file_location('catalogue',ROOT/'scripts/build_refresh_catalogue.py'); cat=importlib.util.module_from_spec(spec); spec.loader.exec_module(cat)
record_path=ROOT/asset['catalogue_record']; old=yaml.safe_load(record_path.read_text())
record=cat.record('kenya-ndma-bulletin-index',[asset],'2026-11-24'); record['created']=old['created']
candidate=STAGE/'candidate/kenya-ndma-bulletin-index.yaml'; candidate.write_text(yaml.safe_dump(record,sort_keys=False,allow_unicode=True))
validation=cat.validate(candidate,Path('/tmp/ke-ndma-cdh-standard'),record_path)
assert validation['status']=='PASS',validation
shutil.copy2(candidate,record_path); dump(ROOT/asset['catalogue_validation_evidence'],validation); dump(inv_path,inv)
print(json.dumps({'accepted_rows':len(frame),'added':len(added),'county':int(frame.scope.eq('county').sum()),'national':int(frame.scope.eq('national').sum()),'local_catalogue':validation['status']},indent=2))
