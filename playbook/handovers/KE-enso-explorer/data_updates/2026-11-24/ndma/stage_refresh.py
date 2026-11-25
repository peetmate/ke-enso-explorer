"""Stage an NDMA index refresh with complete two-order closure and cache replay.

Never writes accepted data. Run from repository root using the data-stack Python.
The stage directory must be new, or --resume must explicitly reuse the same run.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pandas as pd

ROOT = Path.cwd()
SOURCES = ROOT / 'data/KE-enso-explorer/_sources'
sys.path.insert(0, str(SOURCES))
import ndma_index_build as builder


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class StableLibrary(builder.Harvester):
    """Abort if page denominators change within or between the two sweeps."""
    def __init__(self, expected=None, **kwargs):
        super().__init__(**kwargs)
        self.expected = dict(expected or {})

    def checked(self, cat, body):
        echo = builder.page_echo(body)
        if echo is None:
            raise ValueError(f'Missing pager echo: category {cat}')
        counts = tuple(echo[1:])
        prior = self.expected.setdefault(cat, counts)
        if counts != prior:
            raise ValueError(f'Library changed during run: category {cat}: {prior} -> {counts}')
        return body

    def category_page(self, cat):
        return self.checked(cat, super().category_page(cat))

    def sort(self, cat, *args):
        return self.checked(cat, super().sort(cat, *args))

    def page(self, cat, page, *args):
        body = self.checked(cat, super().page(cat, page, *args))
        if page % 20 == 0:
            print(f'PROGRESS category={cat} page={page + 1} network={self.net} cache={self.cache_hits}', flush=True)
        return body


def sweep(stage, name, tls, expected=None):
    target = stage / name
    target.mkdir(exist_ok=True)
    builder.OUT = target / 'ndma_bulletin_index.parquet'
    builder.REPORT_CSV = target / 'ndma_index_validation_report.csv'
    h = StableLibrary(expected=expected, refresh=False, verify=(tls == 'TLS-OK'))
    ck = pd.read_parquet(builder.COUNTY_KEY)
    valid = set(ck.county)
    when = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    rows, reports = [], []
    for cat in sorted(builder.CATEGORIES):
        got, report = builder.harvest(h, cat, valid, None, when)
        if not builder.gate(report):
            raise ValueError(f'Category {cat} failed validation: {report}')
        rows.extend(got)
        reports.append(report)
        # Re-read the publisher's count after each full two-order harvest.
        h.category_page(cat)
    frame = builder.write_outputs(rows, reports, ck, when, tls, h)
    if frame.doc_uuid.duplicated().any():
        raise ValueError('Document identity duplicated across categories')
    if set(frame.county.dropna()) - valid:
        raise ValueError('Unknown county name')
    if frame.loc[frame.scope.eq('county'), 'county'].nunique() > 47:
        raise ValueError('Invalid county count')
    return frame, reports, h


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    stage = args.stage.resolve()
    if stage.exists() and not args.resume:
        raise ValueError('Stage already exists: use a new directory or --resume for this run')
    stage.mkdir(parents=True, exist_ok=True)
    builder.CACHE = stage / 'cache'
    before = stage / 'before'
    if not before.exists():
        before.mkdir()
        shutil.copy2(SOURCES.parent / 'ndma_bulletin_index.parquet', before / 'ndma_bulletin_index.parquet')
        for name in ['ndma_index_validation_report.csv', 'ndma_index_ledger.csv', 'ndma_index_refresh.json', 'ndma_cache_manifest.json']:
            if (SOURCES / name).exists(): shutil.copy2(SOURCES / name, before / name)
    tls = builder.check_tls()
    if not args.resume:
        builder.selftest(StableLibrary(refresh=False, verify=(tls == 'TLS-OK')))
    frame, reports, first = sweep(stage, 'candidate', tls)
    repeat, repeat_reports, replay = sweep(stage, 'replay', tls, first.expected)
    pd.testing.assert_frame_equal(frame.drop(columns='harvested_at'), repeat.drop(columns='harvested_at'))
    original = pd.read_parquet(before / 'ndma_bulletin_index.parquet')
    removed = sorted(set(original.doc_uuid) - set(frame.doc_uuid))
    if removed:
        raise ValueError(f'Previously accepted document identities missing: {removed}')
    fields = ['title_raw', 'county', 'ref_period', 'uploaded_date', 'detail_url', 'pdf_url']
    shared = original.set_index('doc_uuid').join(frame.set_index('doc_uuid'), how='inner', lsuffix='_old', rsuffix='_new')
    revised = []
    for key, row in shared.iterrows():
        changes = {c: {'before': str(row[c+'_old']), 'after': str(row[c+'_new'])} for c in fields
                   if str(row[c+'_old']) != str(row[c+'_new'])}
        if changes: revised.append({'doc_uuid': key, 'changes': changes})
    additions = frame[~frame.doc_uuid.isin(original.doc_uuid)][['doc_uuid', 'title_raw', 'county', 'ref_period', 'uploaded_date']]
    manifest = {str(p.relative_to(stage)): digest(p) for p in sorted(builder.CACHE.rglob('*.html'))}
    (stage / 'cache_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    receipt = {'status': 'VALIDATED_STAGED_NOT_PROMOTED', 'date': '2026-11-24',
               'previous_rows': len(original), 'candidate_rows': len(frame),
               'added': json.loads(additions.to_json(orient='records', date_format='iso')),
               'removed': removed, 'revised': revised, 'validation': reports,
               'cached_replay': {'equal_except_harvested_at': True, 'network_requests': replay.net, 'cache_hits': replay.cache_hits},
               'first_run': {'network_requests': first.net, 'cache_hits': first.cache_hits},
               'prior_sha256': digest(before / 'ndma_bulletin_index.parquet'),
               'candidate_sha256': digest(stage / 'candidate/ndma_bulletin_index.parquet'),
               'cache_manifest_sha256': digest(stage / 'cache_manifest.json'),
               'builder_sha256': digest(Path(builder.__file__)), 'runner_sha256': digest(__file__),
               'raw_cache': str(builder.CACHE), 'rollback': str(before),
               'scope': 'Document metadata only; no PDFs, indicator extraction, publication or permission inference.'}
    (stage / 'receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: receipt[k] for k in ['status','previous_rows','candidate_rows','removed','cached_replay']}, indent=2))
    print(f'Added={len(additions)} revised={len(revised)}; evidence={stage}', flush=True)


if __name__ == '__main__':
    main()
