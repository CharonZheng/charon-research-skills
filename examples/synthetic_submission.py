"""Generate synthetic DOCX inputs and run real checks; visual review stays pending."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('directory', type=Path)
    parser.add_argument('--font-family', default='Times New Roman', help='Synthetic target only; not a journal default')
    args = parser.parse_args(); out = args.directory
    out.mkdir(parents=True, exist_ok=False)
    doc = Document()
    doc.add_paragraph('Synthetic manuscript formatting test', style='Title')
    doc.add_heading('Abstract', 1)
    doc.add_paragraph('This synthetic document tests formatting changes while preserving equations, tables and citation fields. No real research data are included.')
    doc.add_heading('Methods', 1)
    body = doc.add_paragraph('The formatting operation changes paragraph appearance while retaining scientific text. ')
    field = OxmlElement('w:fldChar'); field.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldCharType', 'begin'); body.add_run()._r.append(field)
    instr = OxmlElement('w:instrText'); instr.text = ' ADDIN ZOTERO_ITEM CSL_CITATION {"id":1} '; body.add_run()._r.append(instr)
    separator = OxmlElement('w:fldChar'); separator.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldCharType', 'separate'); body.add_run()._r.append(separator)
    body.add_run('[1]')
    end = OxmlElement('w:fldChar'); end.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldCharType', 'end'); body.add_run()._r.append(end)
    doc.add_heading('Results', 1)
    doc.add_paragraph('Table 1. Synthetic values retained without modification.')
    table = doc.add_table(rows=2, cols=2); table.style = 'Table Grid'
    for cell, value in zip([c for row in table.rows for c in row.cells], ['Condition', 'Value', 'Synthetic A', '42']): cell.text = value
    p = doc.add_paragraph('Editable equation ')
    math = OxmlElement('m:oMath'); run = OxmlElement('m:r'); text = OxmlElement('m:t'); text.text = 'x = 1'; run.append(text); math.append(run); p._p.append(math)
    doc.add_heading('Discussion', 1)
    doc.add_paragraph('A structural comparison and a separate visual inspection are needed. The fixture contains no ethics, funding or conflict declarations.')
    doc.add_heading('References', 1)
    doc.add_paragraph('1. Synthetic reference for software testing only.')
    doc.add_paragraph('29. Deliberately uncited reference for detection testing.')
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Inches(0.65)
    doc.sections[0].header.paragraphs[0].text = 'Synthetic running title'
    doc.styles['Normal'].font.name = 'Times New Roman'; doc.styles['Normal'].font.size = Pt(10)
    for name in ('Title', 'Heading 1'):
        doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)
    for border in doc.styles.element.xpath('.//w:pBdr'):
        border.getparent().remove(border)
    source = out / 'source.docx'; doc.save(source)
    root = Path(__file__).resolve().parents[1]
    skill = root / 'skills' / 'journal-submission-prep'
    if not skill.is_dir():
        skill = root / 'journal-submission-prep'
    sys.path.insert(0, str(skill / 'scripts'))
    from docx_tools import audit
    report = audit(source)
    profile = {'journal': 'Synthetic Test Journal', 'article_type': 'Research', 'stage': 'initial', 'checked_on': '2026-11-11',
               'sources': [{'id': 'S1', 'kind': 'user', 'locator': 'Synthetic fixture specification', 'evidence': f'{args.font_family}; title 18 pt, headings 14 pt, body 12 pt double spacing; table/reference/header text 10 pt single spacing. Paragraph spacing and outline levels follow the synthetic role map.', 'checked_on': '2026-11-11'}],
               'rules': [{'id': 'R1', 'description': 'Test paragraph formatting', 'mandatory': True, 'applicability': 'applicable', 'source_ids': ['S1'], 'check': {'type': 'manual'}}]}
    profile_file = out / 'requirements.json'; profile_file.write_text(json.dumps(profile))
    operations, groups = [], []
    for part, rows in report['formatting'].items():
        for row in rows:
            if not row['text'].strip(): continue
            title = row['paragraph']['style_id'] == 'Title'
            heading = row['paragraph']['heading_level']
            compact = row['in_table'] or part != 'word/document.xml' or row['text'].startswith(('1.', '29.', 'Table 1.'))
            fmt = {'font_name': args.font_family, 'font_size_pt': 18 if title else 14 if heading else 10 if compact else 12,
                   'line_spacing': 1.2 if title or heading else 1 if compact else 2,
                   'space_before_pt': 6 if heading else 0, 'space_after_pt': 6 if title or heading else 3 if compact else 6,
                   'heading_level': heading}
            target = {'part': part, 'paragraph': row['index'], 'expected_text': row['text']}
            operations.append({'kind': 'paragraph_format', 'rule_id': 'R1', 'allow_table': row['in_table'], **target, 'format': fmt})
            groups.append({'id': f'group-{len(groups)}', 'role': 'heading' if heading else 'title' if title else 'compact' if compact else 'body',
                           'basis': {'kind': 'user', 'source': 'Synthetic fixture specification'}, 'expected': fmt, 'targets': [target]})
    plan = {'input_sha256': report['sha256'], 'operations': operations}
    plan_file = out / 'plan.json'; plan_file.write_text(json.dumps(plan))
    script = skill / 'scripts' / 'submission.py'
    commands = [
        ['audit', str(source), '--out', str(out / 'audit.json')],
        ['check', str(source), '--profile', str(profile_file), '--out', str(out / 'check.json')],
        ['format', str(source), '--profile', str(profile_file), '--plan', str(plan_file), '--out', str(out / 'formatted.docx'), '--log', str(out / 'format-log.json')],
        ['verify', str(source), str(out / 'formatted.docx'), '--out', str(out / 'integrity.json')]]
    for cmd in commands:
        result = subprocess.run([sys.executable, str(script), *cmd])
        expected = 3 if cmd[0] == 'check' else 0
        if result.returncode != expected:
            raise RuntimeError(f'{cmd[0]} returned {result.returncode}, expected {expected}')
    contract_file = out / 'format-contract.json'
    contract_file.write_text(json.dumps({'input_sha256': hashlib.sha256((out / 'formatted.docx').read_bytes()).hexdigest(), 'groups': groups}))
    subprocess.run([sys.executable, str(script), 'format-audit', str(out / 'formatted.docx'), '--contract', str(contract_file), '--out', str(out / 'format-check.json')], check=True)
    restored = Document(out / 'formatted.docx')
    assert restored.tables[0].cell(1, 1).text == '42'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == report['sha256']
    assert json.loads((out / 'integrity.json').read_text())['passed']
    def ref(name):
        return {'path': name, 'sha256': hashlib.sha256((out / name).read_bytes()).hexdigest()}
    review = {'schema_version': 1,
              'manuscript_sha256': hashlib.sha256((out / 'formatted.docx').read_bytes()).hexdigest(),
              'checks': {'integrity': ref('integrity.json'), 'formatting': ref('format-check.json'),
                         'policy': {'status': 'not_checked', 'note': 'Synthetic rules only; no real journal policy was verified.'},
                         'visual': {'status': 'not_checked', 'note': 'Render and inspect all pages separately.'},
                         'materials': {'status': 'not_checked', 'note': 'No real submission package was assembled.'}}}
    (out / 'delivery-review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result = subprocess.run([sys.executable, str(script), 'readiness', str(out / 'formatted.docx'),
                             '--review', str(out / 'delivery-review.json'), '--out', str(out / 'delivery-status.json'),
                             '--report', str(out / '检查报告.md')])
    if result.returncode != 3:
        raise RuntimeError('Synthetic example must remain incomplete until real policy and visual checks are recorded')
    print('Synthetic formatting and integrity checks passed. Delivery remains incomplete; see the readable report in the output directory.')


if __name__ == '__main__':
    main()
