"""Independent expectations for Word inheritance, readback and fail-closed checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

from _paths import SCRIPTS
sys.path.insert(0, str(SCRIPTS))
from docx_tools import NS, audit, digest, load, parse, tag
from formatting import FormatResolver, apply_paragraph, check_contract, formatting_parts, match_format
import test_submission as baseline

W = NS['w']
STYLES = f'''<w:styles xmlns:w="{W}">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="SimSun"/><w:sz w:val="20"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="240"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:pPr><w:spacing w:before="40"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="0"/><w:spacing w:line="480"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Sub"><w:basedOn w:val="Heading1"/><w:rPr><w:b/></w:rPr></w:style>
<w:style w:type="character" w:styleId="Small"><w:rPr><w:sz w:val="16"/></w:rPr></w:style>
</w:styles>'''


def parts(body, styles=STYLES, extra=None):
    return {'word/document.xml': f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'.encode(),
            'word/styles.xml': styles.encode(), **(extra or {})}


def row(body, styles=STYLES, extra=None):
    return formatting_parts(parts(body, styles, extra))['word/document.xml'][0]


def para(pr='', rp='', txt='Evidence'):
    return f'<w:p><w:pPr>{pr}</w:pPr><w:r><w:rPr>{rp}</w:rPr><w:t>{txt}</w:t></w:r></w:p>'


class InheritanceTests(unittest.TestCase):
    def test_docdefaults_and_default_paragraph_style(self):
        r = row(para())
        self.assertEqual(r['paragraph']['space_before_pt'], 2)
        self.assertEqual(r['paragraph']['space_after_pt'], 6)
        self.assertEqual(r['runs'][0]['font_size_pt'], 10)
        self.assertEqual(r['runs'][0]['fonts'], {'ascii': 'Arial'})

    def test_style_chain_and_heading(self):
        r = row(para('<w:pStyle w:val="Heading1"/>'))
        self.assertEqual(r['paragraph']['heading_level'], 1)
        self.assertEqual(r['paragraph']['line_spacing'], 2)
        self.assertEqual(r['runs'][0]['font_size_pt'], 14)
        self.assertTrue(r['runs'][0]['bold'])

    def test_style_toggle_and_direct_override(self):
        self.assertFalse(row(para('<w:pStyle w:val="Sub"/>'))['runs'][0]['bold'])
        self.assertFalse(row(para('<w:pStyle w:val="Heading1"/>', '<w:b w:val="0"/>'))['runs'][0]['bold'])

    def test_character_style_and_local_override(self):
        self.assertEqual(row(para('', '<w:rStyle w:val="Small"/>'))['runs'][0]['font_size_pt'], 8)
        self.assertEqual(row(para('', '<w:rStyle w:val="Small"/><w:sz w:val="24"/>'))['runs'][0]['font_size_pt'], 12)

    def test_theme_vs_explicit_override(self):
        theme = b'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:themeElements><a:fontScheme><a:minorFont><a:latin typeface="Calibri"/></a:minorFont></a:fontScheme></a:themeElements></a:theme>'
        styles = STYLES.replace('w:ascii="Arial"', 'w:asciiTheme="minorHAnsi"')
        self.assertEqual(row(para(), styles, {'word/theme/theme1.xml': theme})['runs'][0]['fonts']['ascii'], 'Calibri')
        self.assertEqual(row(para('', '<w:rFonts w:ascii="Times New Roman"/>'), styles, {'word/theme/theme1.xml': theme})['runs'][0]['fonts']['ascii'], 'Times New Roman')

    def test_unresolved_theme_not_pass(self):
        r = row(para('', '<w:rFonts w:asciiTheme="minorHAnsi"/>'))
        self.assertEqual(match_format(r, {'font_name': 'Arial'})['status'], 'not_checked')

    def test_mixed_language_slots(self):
        r = row(para(txt='ABC中文'))
        self.assertEqual(r['runs'][0]['fonts'], {'ascii': 'Arial', 'eastAsia': 'SimSun'})
        self.assertEqual(match_format(r, {'font_ascii': 'Arial'})['status'], 'not_checked')
        self.assertEqual(match_format(r, {'font_ascii': 'Arial', 'font_east_asia': 'SimSun'})['status'], 'pass')

    def test_fixed_line_is_not_double_spacing(self):
        r = row(para('<w:spacing w:line="480" w:lineRule="exact"/>'))
        self.assertEqual(match_format(r, {'line_spacing': 2})['status'], 'not_checked')
        self.assertEqual(match_format(r, {'line_spacing_pt': 24, 'line_rule': 'exact'})['status'], 'pass')

    def test_grid_and_contextual_spacing_not_pass(self):
        r = row(para('<w:contextualSpacing/>') + '<w:sectPr><w:docGrid w:type="lines" w:linePitch="360"/></w:sectPr>')
        self.assertEqual(match_format(r, {'line_spacing': 1})['status'], 'needs_confirmation')
        self.assertEqual(match_format(r, {'space_after_pt': 6})['status'], 'needs_confirmation')

    def test_auto_or_line_based_paragraph_spacing_unknown(self):
        for attr in ('w:beforeAutospacing="1"', 'w:beforeLines="100"'):
            r = row(para(f'<w:spacing {attr}/>'))
            self.assertEqual(match_format(r, {'space_before_pt': 2})['status'], 'not_checked')

    def test_direct_spacing_disables_inherited_auto(self):
        p = parse(para('<w:spacing w:beforeAutospacing="1"/><w:contextualSpacing/>').replace('<w:p>', f'<w:p xmlns:w="{W}">', 1).encode())
        apply_paragraph(p, {'space_before_pt': 0, 'line_spacing': 2, 'heading_level': 2})
        r = FormatResolver(parts('')).paragraph(p); r['index'] = 0
        self.assertEqual(match_format(r, {'space_before_pt': 0, 'line_spacing': 2, 'heading_level': 2})['status'], 'pass')
        self.assertFalse(r['paragraph']['contextual_spacing'])
        self.assertFalse(r['paragraph']['snap_to_grid'])

    def test_half_point_and_conflicting_line_rules_rejected(self):
        for fmt in ({'font_size_pt': 11.25}, {'line_spacing': 2, 'line_spacing_pt': 24}, {'line_spacing_pt': 24}, {'style_id': 'Unknown'}):
            p = parse(para().replace('<w:p>', f'<w:p xmlns:w="{W}">', 1).encode())
            with self.assertRaises(ValueError): apply_paragraph(p, fmt, parse(STYLES.encode()))

    def test_heading_name_cannot_replace_outline_level(self):
        styles = STYLES.replace('<w:outlineLvl w:val="0"/>', '')
        self.assertEqual(row(para('<w:pStyle w:val="Heading1"/>'), styles)['paragraph']['heading_level'], 0)

    def test_complex_script_size_checked(self):
        r = row(para('', '<w:rFonts w:cs="Arial"/><w:szCs w:val="18"/>', txt='مرحبا'))
        self.assertEqual(match_format(r, {'font_size_pt': 10})['status'], 'fail')
        self.assertEqual(match_format(r, {'font_size_pt': 10, 'font_size_cs_pt': 9})['status'], 'pass')

    def test_header_story_included(self):
        data = parts(para(), extra={'word/header1.xml': f'<w:hdr xmlns:w="{W}">{para(txt="Running title")}</w:hdr>'.encode()})
        self.assertEqual(formatting_parts(data)['word/header1.xml'][0]['text'], 'Running title')

    def test_no_visible_runs_cannot_pass_fonts(self):
        self.assertEqual(match_format(row('<w:p/>'), {'font_name': 'Arial'})['status'], 'not_checked')

    def test_conditional_table_style_never_silently_passes(self):
        styles = STYLES.replace('</w:styles>', '<w:style w:type="table" w:styleId="Conditional"><w:tblStylePr w:type="firstRow"><w:rPr><w:sz w:val="18"/></w:rPr></w:tblStylePr></w:style></w:styles>')
        r = row('<w:tbl><w:tblPr><w:tblStyle w:val="Conditional"/></w:tblPr><w:tr><w:tc>' + para() + '</w:tc></w:tr></w:tbl>', styles)
        self.assertEqual(match_format(r, {'font_size_pt': 10})['status'], 'needs_confirmation')

    def test_run_exception_preserves_local_superscript_size(self):
        xml = f'<w:p xmlns:w="{W}"><w:r><w:t>Body</w:t></w:r><w:r><w:rPr><w:sz w:val="16"/><w:vertAlign w:val="superscript"/></w:rPr><w:t>1</w:t></w:r></w:p>'
        p = parse(xml.encode()); exemptions = [{'run': 1, 'properties': ['font_size_pt'], 'reason': 'Verified reference superscript'}]
        apply_paragraph(p, {'font_size_pt': 12}, run_exemptions=exemptions)
        r = FormatResolver(parts('')).paragraph(p); r['index'] = 0
        self.assertEqual(r['runs'][1]['font_size_pt'], 8)
        self.assertEqual(match_format(r, {'font_size_pt': 12}, exemptions)['status'], 'pass')
        self.assertEqual(p.findall('w:r', NS)[1].find('w:rPr/w:vertAlign', NS).get(tag('w:val')), 'superscript')

    def test_missing_style_blocks_claimed_format_pass(self):
        r = row(para('<w:pStyle w:val="Missing"/>'))
        self.assertEqual(match_format(r, {'font_size_pt': 10})['status'], 'needs_confirmation')

    def test_format_revisions_cannot_pass(self):
        r = row(para('<w:pPrChange/>'))
        self.assertEqual(match_format(r, {'font_size_pt': 10})['status'], 'needs_confirmation')


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'test.docx'
        with zipfile.ZipFile(self.path, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types/>')
            for key, value in parts(para() + para(txt='Other')).items(): z.writestr(key, value)
        self.expected = {'font_name': 'Arial', 'font_size_pt': 10, 'line_spacing': 1,
                         'space_before_pt': 2, 'space_after_pt': 6, 'heading_level': 0}
        self.contract = {'input_sha256': digest(self.path.read_bytes()), 'groups': [{'id': 'body', 'basis': {'kind': 'user', 'source': 'synthetic test'},
                         'expected': self.expected, 'targets': [{'paragraph': 0, 'expected_text': 'Evidence'}, {'paragraph': 1, 'expected_text': 'Other'}]}]}

    def test_full_contract_pass(self):
        self.assertTrue(check_contract(self.path, self.contract)['passed'])

    def test_uncovered_paragraph_blocks_pass(self):
        self.contract['groups'][0]['targets'].pop()
        self.assertFalse(check_contract(self.path, self.contract)['passed'])

    def test_basic_metric_omission_rejected(self):
        self.expected.pop('space_after_pt')
        with self.assertRaises(ValueError): check_contract(self.path, self.contract)

    def test_stale_hash_rejected(self):
        self.contract['input_sha256'] = 'stale'
        with self.assertRaises(ValueError): check_contract(self.path, self.contract)

    def test_stale_target_rejected(self):
        self.contract['groups'][0]['targets'][0]['expected_text'] = 'Changed'
        with self.assertRaises(ValueError): check_contract(self.path, self.contract)

    def test_overlap_rejected(self):
        self.contract['groups'][0]['targets'].append({'paragraph': 0, 'expected_text': 'Evidence'})
        with self.assertRaises(ValueError): check_contract(self.path, self.contract)

    def test_point_contract_requires_exact_or_atleast(self):
        self.expected.pop('line_spacing'); self.expected['line_spacing_pt'] = 12
        with self.assertRaises(ValueError): check_contract(self.path, self.contract)

    def test_documented_exemption_recorded(self):
        self.contract['groups'][0]['targets'].pop()
        self.contract['exemptions'] = [{'paragraph': 1, 'expected_text': 'Other', 'reason': 'Synthetic separate typography review'}]
        result = check_contract(self.path, self.contract)
        self.assertTrue(result['passed']); self.assertTrue(result['exemptions'])


class OperationRegressionTests(unittest.TestCase):
    setUp = baseline.SubmissionTests.setUp
    save = baseline.SubmissionTests.save
    run_format = baseline.SubmissionTests.run_format
    def test_table_explicit_opt_in(self):
        self.plan['operations'][0].update(paragraph=4, expected_text='Table cell 42', allow_table=True)
        self.assertEqual(self.run_format(), 0)
        self.assertTrue(json.loads(self.log.read_text())['integrity']['passed'])

    def test_saved_readback_and_before_after_log(self):
        self.assertEqual(self.run_format(), 0)
        log = json.loads(self.log.read_text())
        self.assertEqual(log['readback'][0]['status'], 'pass')
        self.assertEqual(log['changes'][0]['predicted_after']['runs'][0]['font_size_pt'], 12)

    def test_inherited_line_based_spacing_rejected_without_partial_output(self):
        data, root = load(self.source)
        data['word/styles.xml'] = STYLES.replace('w:before="40"', 'w:beforeLines="100"').encode()
        target = root.findall('.//w:p', NS)[3]
        from docx_tools import write_docx
        from lxml import etree as E
        data['word/document.xml'] = E.tostring(root)
        altered = self.root / 'inherited.docx'
        with zipfile.ZipFile(altered, 'w') as z:
            for k, v in data.items(): z.writestr(k, v)
        self.source = altered; self.plan['input_sha256'] = digest(altered.read_bytes())
        self.plan['operations'][0]['format']['space_before_pt'] = 0
        self.assertEqual(self.run_format(), 2); self.assertFalse(self.output.exists())

    def test_header_edit_preserves_other_package_parts(self):
        data, _ = load(self.source)
        data['word/header1.xml'] = f'<w:hdr xmlns:w="{W}">{para(txt="Running title")}</w:hdr>'.encode()
        altered = self.root / 'header.docx'
        with zipfile.ZipFile(altered, 'w') as z:
            for k, v in data.items(): z.writestr(k, v)
        self.source = altered; self.plan['input_sha256'] = digest(altered.read_bytes())
        self.plan['operations'] = [{'kind': 'paragraph_format', 'rule_id': 'R1', 'part': 'word/header1.xml', 'paragraph': 0, 'expected_text': 'Running title', 'format': {'font_size_pt': 10, 'font_name': 'Arial'}}]
        self.assertEqual(self.run_format(), 0)
        self.assertEqual(load(self.output)[0]['word/document.xml'], data['word/document.xml'])

    def test_bibliography_stops_before_numeric_table(self):
        data, root = load(self.source)
        from lxml import etree as E
        table = parse(f'<w:tbl xmlns:w="{W}"><w:tr><w:tc>{para(txt="31. Numeric table value")}</w:tc></w:tr></w:tbl>'.encode())
        root.find('w:body', NS).insert(-1, table)
        from docx_tools import write_docx
        write_docx(self.source, self.output, root)
        refs = audit(self.output)['numeric_reference_candidates']
        self.assertEqual(refs['list'], [1, 29]); self.assertNotIn(31, refs['possibly_uncited'])


if __name__ == '__main__': unittest.main()
