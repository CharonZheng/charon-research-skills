#!/usr/bin/env python3
"""Aggregate file-bound checks; never infer visual review from automated checks."""
import argparse
from datetime import date
from pathlib import Path
import re
import sys

from report_io import available, digest_file, json_out, publish, read_json

CATEGORIES = ('policy', 'integrity', 'formatting', 'rendered_fonts', 'visual', 'materials')
MANUAL = {'policy', 'visual', 'materials'}
STATUSES = {'pass', 'fail', 'needs_confirmation', 'not_checked', 'not_applicable'}
LABELS = dict(zip(CATEGORIES, ('规则与来源', '内容与对象完整性', '基础格式覆盖', 'PDF 字体筛查', '逐页视觉复核', '投稿材料一致性')))


def evidence(ref, base):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str) or not ref['path'].strip():
        raise ValueError('Evidence needs a nonempty path')
    if not isinstance(ref.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', ref['sha256']):
        raise ValueError('Evidence needs a lowercase SHA-256')
    path = (base / ref['path']).resolve()
    if not path.is_file():
        return None, 'not_checked', f'Evidence file missing: {ref["path"]}'
    if digest_file(path) != ref['sha256']:
        return None, 'needs_confirmation', f'Evidence changed: {ref["path"]}'
    return path, 'pass', None


def manual_check(category, item, base, pages):
    status = item.get('status', 'not_checked')
    if status not in STATUSES:
        raise ValueError(f'Invalid status for {category}')
    if status == 'not_applicable' and category != 'materials':
        raise ValueError(f'{category} cannot be marked not applicable for a DOCX delivery')
    if status in {'pass', 'not_applicable'}:
        if not all(isinstance(item.get(key), str) and item[key].strip()
                   for key in ('note', 'reviewer', 'checked_on')):
            raise ValueError(f'{category} needs note, reviewer and checked_on')
        date.fromisoformat(item['checked_on'])
        refs = item.get('evidence')
        if not isinstance(refs, list) or not refs:
            raise ValueError(f'{category} needs review evidence')
        for ref in refs:
            _, current, reason = evidence(ref, base)
            if current != 'pass':
                return current, reason
        if category == 'visual':
            reviewed = item.get('reviewed_pages')
            image_pages = [ref.get('page') for ref in refs]
            if not pages:
                return 'not_checked', 'A bound PDF layout report is needed to establish page count'
            if (not isinstance(reviewed, list) or any(type(p) is not int for p in reviewed)
                    or sorted(reviewed) != list(range(1, pages + 1))
                    or any(type(p) is not int for p in image_pages)
                    or sorted(image_pages) != list(range(1, pages + 1))):
                return 'needs_confirmation', 'Visual evidence must cover every PDF page exactly once'
    return status, item.get('note', 'Review has not been recorded')


def automatic_check(category, item, base, manuscript_hash, pdf_hash):
    path, status, reason = evidence(item, base)
    if status != 'pass':
        return status, reason, None
    report = read_json(path)
    expected_hash = pdf_hash if category == 'rendered_fonts' else manuscript_hash
    key = 'after_sha256' if category == 'integrity' else 'input_sha256'
    if not expected_hash or report.get(key) != expected_hash:
        return 'needs_confirmation', 'Report is not bound to the current document/PDF', report
    if category == 'rendered_fonts':
        if type(report.get('pages')) is not int or report['pages'] < 1:
            raise ValueError('Layout report needs a positive page count')
        families = report.get('expected_font_families', [])
        if not isinstance(families, list) or any(not isinstance(name, str) or not name.strip() for name in families):
            raise ValueError('Layout report expected fonts must be a list of nonempty names')
        if not families:
            return 'not_checked', 'No expected font families were checked', report
        if type(report.get('automated_triage_clear')) is not bool or not isinstance(report.get('findings'), list):
            raise ValueError('Invalid layout report')
        ok = report['automated_triage_clear'] and not report['findings']
        return ('pass' if ok else 'needs_confirmation'), 'Automated PDF triage; visual review remains separate', report
    if type(report.get('passed')) is not bool:
        raise ValueError(f'{category} report needs a boolean passed value')
    if category == 'formatting':
        if not isinstance(report.get('results'), list) or not report['results'] or not isinstance(report.get('uncovered'), list):
            raise ValueError('Invalid format contract report')
        if any(not isinstance(row, dict) or row.get('status') not in STATUSES for row in report['results']):
            raise ValueError('Invalid format property result')
        if report['passed'] and (report['uncovered'] or any(r.get('status') != 'pass' for r in report['results'])):
            raise ValueError('Format report contradicts its passed value')
        if not report['passed']:
            if any(r.get('status') == 'fail' for r in report['results']):
                return 'fail', 'Format contract contains a failed property check', report
            if not report['uncovered'] and all(r.get('status') == 'pass' for r in report['results']):
                raise ValueError('Format report contradicts its failed value')
            return 'needs_confirmation', 'Format coverage or declared properties remain unresolved', report
        if report.get('exemptions') and item.get('exemptions_reviewed') is not True:
            return 'needs_confirmation', 'Format exemptions need explicit review', report
    return ('pass' if report['passed'] else 'fail'), 'Read from hash-bound machine report', report


def summarize(manuscript, review_path):
    review_path = Path(review_path)
    review = read_json(review_path)
    if type(review.get('schema_version')) is not int or review['schema_version'] != 1:
        raise ValueError('Unsupported delivery-review schema_version')
    manuscript_hash = digest_file(manuscript)
    if review.get('manuscript_sha256') != manuscript_hash:
        raise ValueError('Delivery review does not match the current manuscript')
    checks = review.get('checks', {})
    if not isinstance(checks, dict) or set(checks) - set(CATEGORIES):
        raise ValueError('Unknown or invalid delivery check categories')
    base = review_path.resolve().parent
    results, pdf_hash, render_issue, pages = {}, None, None, None
    render = review.get('rendered_pdf')
    if render is not None:
        _, current, reason = evidence(render, base)
        if current == 'pass' and render.get('source_sha256') == manuscript_hash and isinstance(render.get('renderer'), str) and render['renderer'].strip():
            pdf_hash = render['sha256']
        else:
            render_issue = (current if current != 'pass' else 'needs_confirmation',
                            reason or 'PDF needs the source manuscript hash and renderer description')
    for category in ('integrity', 'formatting', 'rendered_fonts'):
        item = checks.get(category)
        if item is None:
            results[category] = {'status': 'not_checked', 'note': 'Required check missing'}
        elif not isinstance(item, dict):
            raise ValueError('Each delivery check must be an object')
        elif category == 'rendered_fonts' and render_issue:
            results[category] = {'status': render_issue[0], 'note': render_issue[1]}
        elif category == 'integrity' and item.get('method') == 'authorized_edit_review':
            changes = item.get('authorized_changes')
            if not isinstance(changes, list) or not changes or any(not isinstance(change, str) or not change.strip() for change in changes):
                raise ValueError('Authorized edit review needs a nonempty authorized_changes list')
            _, status, note = evidence(item.get('source_docx'), base)
            if status == 'pass':
                status, note = manual_check(category, item, base, None)
            results[category] = {'status': status, 'note': note, 'method': 'authorized_edit_review'}
        else:
            status, note, report = automatic_check(category, item, base, manuscript_hash, pdf_hash)
            results[category] = {'status': status, 'note': note}
            if category == 'rendered_fonts' and pdf_hash and report and report.get('input_sha256') == pdf_hash:
                pages = report.get('pages')
    for category in ('policy', 'visual', 'materials'):
        item = checks.get(category, {})
        if not isinstance(item, dict):
            raise ValueError('Each delivery check must be an object')
        status, note = manual_check(category, item, base, pages)
        if category == 'visual' and (render_issue or not pdf_hash):
            status, note = 'not_checked', 'Visual review is not bound to a current rendered PDF'
        results[category] = {'status': status, 'note': note}
    results = {category: results[category] for category in CATEGORIES}
    states = [item['status'] for item in results.values()]
    status = 'blocked' if 'fail' in states else 'ready' if all(s in {'pass', 'not_applicable'} for s in states) else 'incomplete'
    return {'schema_version': 1, 'status': status, 'manuscript_sha256': manuscript_hash,
            'review_sha256': digest_file(review_path), 'checks': results,
            'limitations': ['Ready means the recorded checks are complete, not that the journal will accept the submission.',
                            'Official-source interpretation, rendering provenance and page inspection are reviewer attestations; this command does not perform them.',
                            'This result covers one DOCX; run it for each delivered DOCX.']}


def markdown(result):
    labels = {'ready': '已完成记录中的核验', 'incomplete': '核验未完成', 'blocked': '存在未通过项目'}
    lines = ['# 交付检查报告', '', f'结论：{labels[result["status"]]}（{result["status"]}）。', '',
             f'稿件 SHA-256：`{result["manuscript_sha256"]}`', '', '| 检查 | 状态 | 说明 |', '|---|---|---|']
    for category, item in result['checks'].items():
        note = str(item['note']).replace('|', '\\|').replace('\n', ' ')
        lines.append(f'| {LABELS[category]} | {item["status"]} | {note} |')
    lines.extend(['', '“ready”只代表上述检查记录已齐全。官网解释、渲染来源与逐页视觉检查仍依赖复核者如实记录；不保证期刊接收。',
                  '本报告只覆盖当前 DOCX，其他交付文档须分别核验。', ''])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manuscript', type=Path)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    try:
        available(args.out, (args.manuscript, args.review))
        if args.report:
            available(args.report, (args.manuscript, args.review, args.out))
        result = summarize(args.manuscript, args.review)
        if args.report:
            # Both destinations are checked before publishing either file.
            publish(args.report, lambda path: path.write_text(markdown(result), encoding='utf-8'))
        json_out(args.out, result)
        print(f'Delivery status: {result["status"]}; {args.out}')
        return {'ready': 0, 'blocked': 1, 'incomplete': 3}[result['status']]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
