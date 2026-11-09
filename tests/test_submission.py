"""Behavioral tests using synthetic OOXML, without private research data."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "journal-submission-prep" / "scripts"))
from docx_tools import NS, audit, digest, load, parse, tag, verify, write_docx
from submission import check_document, main, profile


def fixture(path, revised=False):
    xml = f'''<w:document xmlns:w="{NS['w']}" xmlns:m="{NS['m']}"><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Abstract</w:t></w:r></w:p>
<w:p><w:r><w:t>One two three four five.</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Methods</w:t></w:r></w:p>
<w:p><w:bookmarkStart w:id="0" w:name="ref1"/><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> ADDIN ZOTERO_ITEM CSL_CITATION {{"id":1}} </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Evidence [1].</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r><m:oMath><m:r><m:t>x=1</m:t></m:r></m:oMath><w:bookmarkEnd w:id="0"/></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table cell 42</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
<w:p><w:r><w:t>Figure 1. Test caption</w:t></w:r></w:p>
<w:p><w:r><w:t>Table 1. Test caption</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>References</w:t></w:r></w:p>
<w:p><w:r><w:t>1. First reference.</w:t></w:r></w:p>
<w:p><w:r><w:t>29. Uncited reference.</w:t></w:r></w:p>
{'<w:p><w:ins w:id="1"><w:r><w:t>New text</w:t></w:r></w:ins></w:p>' if revised else ''}
<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:bottom="1440" w:left="1440" w:right="1440"/><w:cols w:space="720"/></w:sectPr>
</w:body></w:document>'''
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('word/document.xml', xml)
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr('word/media/test.png', b'unchanged-image-bytes')
        z.writestr('word/comments.xml', b'<comments>unchanged</comments>')


def specification():
    return {"journal": "Synthetic Test Journal", "article_type": "Research", "stage": "initial",
            "checked_on": "2026-11-09", "sources": [{"id": "S1", "kind": "user",
            "locator": "synthetic test instructions", "evidence": "test formatting", "checked_on": "2026-11-09"}],
            "rules": [{"id": "R1", "description": "test rule", "mandatory": True,
            "applicability": "applicable", "source_ids": ["S1"], "check": {"type": "required_section", "section": "Methods"}}]}


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = self.root / 'source.docx'; fixture(self.source)
        self.spec = specification(); self.profile_file = self.root / 'requirements.json'
        self.plan_file = self.root / 'plan.json'; self.output = self.root / 'output.docx'; self.log = self.root / 'log.json'
        self.plan = {"input_sha256": digest(self.source.read_bytes()), "operations": [
            {"kind": "paragraph_format", "rule_id": "R1", "paragraph": 3, "expected_text": "Evidence [1].",
             "format": {"font_name": "Times New Roman", "font_size_pt": 12, "line_spacing": 2}},
            {"kind": "page_margins", "rule_id": "R1", "section": 0, "margins_mm": {"left": 30}}]}

    def save(self):
        self.profile_file.write_text(json.dumps(self.spec)); self.plan_file.write_text(json.dumps(self.plan))

    def run_format(self, extra=()):
        self.save()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(['format', str(self.source), '--profile', str(self.profile_file), '--plan', str(self.plan_file), '--out', str(self.output), '--log', str(self.log), *extra])

    def checked(self, check):
        self.spec['rules'][0]['check'] = check; self.save(); data, sources = profile(self.profile_file)
        return check_document(self.source, data, sources)['results'][0]

    def test_format_preserves_source_fields_math_and_binary_parts(self):
        before = self.source.read_bytes(); self.assertEqual(self.run_format(), 0)
        self.assertEqual(before, self.source.read_bytes()); self.assertTrue(verify(self.source, self.output)['passed'])
        parts, root = load(self.output)
        self.assertEqual(parts['word/media/test.png'], b'unchanged-image-bytes')
        self.assertEqual(root.find('.//w:instrText', NS).text, ' ADDIN ZOTERO_ITEM CSL_CITATION {"id":1} ')
        self.assertEqual(root.find('.//m:t', NS).text, 'x=1')
        self.assertEqual(root.find('.//w:spacing', NS).get(tag('w:line')), '480')
        self.assertEqual(root.find('.//w:rFonts', NS).get(tag('w:ascii')), 'Times New Roman')

    def test_dry_run_writes_nothing(self):
        self.assertEqual(self.run_format(['--dry-run']), 0)
        self.assertFalse(self.output.exists()); self.assertFalse(self.log.exists())

    def test_reject_source_overwrite(self):
        self.output = self.source; old = self.source.read_bytes()
        self.assertEqual(self.run_format(), 2); self.assertEqual(old, self.source.read_bytes())

    def test_reject_existing_output(self):
        self.output.write_bytes(b'keep'); self.assertEqual(self.run_format(), 2)
        self.assertEqual(self.output.read_bytes(), b'keep')

    def test_reject_hardlink_output(self):
        self.output.hardlink_to(self.source); self.assertEqual(self.run_format(), 2)

    def test_reject_same_log_and_docx(self):
        self.log = self.output; self.assertEqual(self.run_format(), 2); self.assertFalse(self.output.exists())

    def test_reject_stale_plan(self):
        self.plan['input_sha256'] = 'wrong'; self.assertEqual(self.run_format(), 2)
        self.assertFalse(self.output.exists())

    def test_reject_text_mismatch(self):
        self.plan['operations'][0]['expected_text'] = 'wrong'; self.assertEqual(self.run_format(), 2)

    def test_reject_table_edit(self):
        self.plan['operations'][0].update(paragraph=4, expected_text='Table cell 42')
        self.assertEqual(self.run_format(), 2); self.assertFalse(self.output.exists())

    def test_reject_unknown_operation(self):
        self.plan['operations'][0]['kind'] = 'rewrite'; self.assertEqual(self.run_format(), 2)

    def test_reject_unresolved_and_historical_rules(self):
        self.spec['rules'][0]['resolution'] = 'unresolved'; self.assertEqual(self.run_format(), 2)
        self.spec['rules'][0].pop('resolution'); self.spec['sources'][0]['kind'] = 'historical'
        self.assertEqual(self.run_format(), 2)

    def test_one_unresolved_rule_blocks_entire_conflict_group(self):
        rule = self.spec['rules'][0]
        rule.update(conflict_group='funding', resolution='resolved', resolution_note='first source')
        other = copy.deepcopy(rule); other.update(id='R2', resolution='unresolved')
        self.spec['rules'].append(other)
        self.assertEqual(self.run_format(), 2)

    def test_bad_format_does_not_create_partial_output(self):
        self.plan['operations'][0]['format']['font_size_pt'] = -10
        self.assertEqual(self.run_format(), 2); self.assertFalse(self.output.exists())

    def test_changed_paragraph_text_breaks_integrity(self):
        _, root = load(self.source); root.find('.//w:t', NS).text = 'Changed abstract'
        write_docx(self.source, self.output, root)
        self.assertFalse(verify(self.source, self.output)['passed'])

    def test_detect_missing_reference_candidate(self):
        self.assertEqual(audit(self.source)['numeric_reference_candidates']['possibly_uncited'], [29])

    def test_section_order_and_word_limit(self):
        self.assertEqual(self.checked({'type': 'section_order', 'sections': ['Methods', 'Abstract']})['status'], 'fail')
        self.assertEqual(self.checked({'type': 'word_limit', 'section': 'Abstract', 'max': 4})['status'], 'fail')
        self.assertEqual(self.checked({'type': 'word_limit', 'section': 'Abstract', 'max': 5})['status'], 'pass')

    def test_combined_display_limit_remains_provisional(self):
        result = self.checked({'type': 'display_limit', 'max': 1})
        self.assertEqual(result['status'], 'needs_confirmation'); self.assertTrue(result['detail']['over_limit'])

    def test_unknown_applicability_is_not_pass(self):
        self.spec['rules'][0].update(applicability='unknown', applicability_reason='Need author facts')
        self.assertEqual(self.checked({'type': 'required_section', 'section': 'Methods'})['status'], 'needs_confirmation')

    def test_manual_declaration_never_autopasses(self):
        self.assertEqual(self.checked({'type': 'manual', 'instruction': 'Ethics approval'})['status'], 'not_checked')

    def test_revisions_prevent_unqualified_pass(self):
        fixture(self.source, revised=True)
        self.assertEqual(self.checked({'type': 'required_section', 'section': 'Methods'})['status'], 'needs_confirmation')

    def test_integrity_detects_text_and_math_tampering(self):
        _, root = load(self.source); root.find('.//m:t', NS).text = 'x=999'
        write_docx(self.source, self.output, root)
        self.assertFalse(verify(self.source, self.output)['passed'])

    def test_integrity_detects_binary_tampering(self):
        parts, _ = load(self.source)
        with zipfile.ZipFile(self.output, 'w') as z:
            for name, data in parts.items(): z.writestr(name, b'changed' if name.endswith('.png') else data)
        self.assertFalse(verify(self.source, self.output)['passed'])

    def test_unsupported_check_fails_explicitly(self):
        self.spec['rules'][0]['check'] = {'type': 'invented_api'}; self.save()
        with self.assertRaisesRegex(ValueError, 'Unsupported check'): profile(self.profile_file)

    def test_invalid_json_shape_fails_cleanly(self):
        self.save(); self.profile_file.write_text('[]')
        with self.assertRaisesRegex(ValueError, 'root must be an object'): profile(self.profile_file)

    def test_manifest_hashes_files_and_rejects_symlinks(self):
        stage = self.root / 'stage'; stage.mkdir(); (stage / 'paper.txt').write_text('paper')
        out = self.root / 'manifest.json'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['manifest', str(stage), '--out', str(out)]), 0)
        self.assertEqual(json.loads(out.read_text())['files'][0]['sha256'], digest(b'paper'))
        (stage / 'alias').symlink_to(self.source)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['manifest', str(stage), '--out', str(self.root / 'bad.json')]), 2)


if __name__ == '__main__':
    unittest.main()
