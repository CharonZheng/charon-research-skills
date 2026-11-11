"""Delivery gates reject stale evidence, missing pages and unknown mandatory checks."""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from _paths import SCRIPTS
sys.path.insert(0, str(SCRIPTS))
from doctor import font_probe, inspect_environment
from readiness import main, summarize
from report_io import digest_file


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.doc = self.root / 'paper.docx'
        self.doc.write_bytes(b'synthetic manuscript bytes')
        self.doc_hash = digest_file(self.doc)
        self.review_path = self.root / 'delivery-review.json'
        self.pdf = self.file('paper.pdf', b'synthetic rendered PDF bytes')
        note = self.file('review.md', b'Synthetic test-only reviewer attestation')
        manual = {'status': 'pass', 'reviewer': 'synthetic test reviewer',
                  'checked_on': '2026-11-11', 'note': 'Synthetic test-only review', 'evidence': [note]}
        self.review = {'schema_version': 1, 'manuscript_sha256': self.doc_hash,
                       'rendered_pdf': {**self.pdf, 'source_sha256': self.doc_hash, 'renderer': 'synthetic fixture'},
                       'checks': {'policy': copy.deepcopy(manual), 'materials': copy.deepcopy(manual),
                                  'visual': {**manual, 'reviewed_pages': [1, 2], 'evidence': [
                                      {**self.file('page-1.png', b'test page 1'), 'page': 1},
                                      {**self.file('page-2.png', b'test page 2'), 'page': 2}]}}}
        self.machine('integrity', {'passed': True, 'after_sha256': self.doc_hash})
        self.machine('formatting', {'passed': True, 'input_sha256': self.doc_hash,
                                    'results': [{'status': 'pass'}], 'uncovered': [], 'exemptions': []})
        self.machine('rendered_fonts', {'input_sha256': self.pdf['sha256'], 'pages': 2,
                                        'expected_font_families': ['Test Font'], 'fonts': ['TestFont'],
                                        'automated_triage_clear': True, 'findings': []})

    def file(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return {'path': name, 'sha256': digest_file(path)}

    def machine(self, category, data):
        self.review['checks'][category] = self.file(category + '.json', json.dumps(data).encode())

    def save(self):
        self.review_path.write_text(json.dumps(self.review), encoding='utf-8')

    def result(self):
        self.save()
        return summarize(self.doc, self.review_path)

    def test_complete_bound_records_are_ready(self):
        self.assertEqual(self.result()['status'], 'ready')

    def test_missing_required_category_remains_incomplete(self):
        del self.review['checks']['visual']
        self.assertEqual(self.result()['status'], 'incomplete')

    def test_unknown_manual_state_cannot_pass(self):
        self.review['checks']['policy']['status'] = 'needs_confirmation'
        self.assertEqual(self.result()['status'], 'incomplete')

    def test_failed_integrity_blocks_delivery(self):
        self.machine('integrity', {'passed': False, 'after_sha256': self.doc_hash})
        self.assertEqual(self.result()['status'], 'blocked')

    def test_changed_manuscript_rejects_old_review(self):
        self.doc.write_bytes(b'changed manuscript')
        with self.assertRaisesRegex(ValueError, 'current manuscript'):
            self.result()

    def test_changed_report_invalidates_evidence(self):
        (self.root / 'formatting.json').write_text('{}')
        self.assertEqual(self.result()['checks']['formatting']['status'], 'needs_confirmation')

    def test_missing_evidence_is_not_checked(self):
        (self.root / 'integrity.json').unlink()
        self.assertEqual(self.result()['checks']['integrity']['status'], 'not_checked')

    def test_old_format_report_is_not_reused(self):
        self.machine('formatting', {'passed': True, 'input_sha256': '0' * 64,
                                    'results': [{'status': 'pass'}], 'uncovered': []})
        self.assertEqual(self.result()['checks']['formatting']['status'], 'needs_confirmation')

    def test_missing_page_and_duplicate_page_do_not_pass(self):
        for pages in ([1], [1, 1]):
            self.review['checks']['visual']['reviewed_pages'] = pages
            self.assertEqual(self.result()['checks']['visual']['status'], 'needs_confirmation')

    def test_page_images_are_individually_bound(self):
        (self.root / 'page-2.png').write_bytes(b'render changed')
        self.assertEqual(self.result()['checks']['visual']['status'], 'needs_confirmation')

    def test_pdf_change_invalidates_fonts_and_visual(self):
        (self.root / 'paper.pdf').write_bytes(b'other render')
        result = self.result()
        self.assertNotEqual(result['checks']['rendered_fonts']['status'], 'pass')
        self.assertNotEqual(result['checks']['visual']['status'], 'pass')

    def test_render_without_source_binding_does_not_pass(self):
        self.review['rendered_pdf']['source_sha256'] = '0' * 64
        self.assertEqual(self.result()['status'], 'incomplete')

    def test_no_expected_fonts_does_not_complete_font_check(self):
        self.machine('rendered_fonts', {'input_sha256': self.pdf['sha256'], 'pages': 2,
                                        'expected_font_families': [], 'automated_triage_clear': True, 'findings': []})
        self.assertEqual(self.result()['checks']['rendered_fonts']['status'], 'not_checked')

    def test_font_findings_do_not_disappear_behind_clear_flag(self):
        self.machine('rendered_fonts', {'input_sha256': self.pdf['sha256'], 'pages': 2,
                                        'expected_font_families': ['Test Font'], 'automated_triage_clear': True,
                                        'findings': [{'kind': 'expected_font_absent'}]})
        self.assertEqual(self.result()['status'], 'incomplete')

    def test_exemptions_require_review(self):
        self.machine('formatting', {'passed': True, 'input_sha256': self.doc_hash,
                                    'results': [{'status': 'pass'}], 'uncovered': [],
                                    'exemptions': [{'reason': 'special object'}]})
        self.assertEqual(self.result()['checks']['formatting']['status'], 'needs_confirmation')

    def test_format_report_cannot_hide_uncovered_paragraphs(self):
        self.machine('formatting', {'passed': True, 'input_sha256': self.doc_hash,
                                    'results': [{'status': 'pass'}], 'uncovered': [{'paragraph': 4}]})
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            self.result()

    def test_unresolved_format_property_is_incomplete_not_a_measured_failure(self):
        self.machine('formatting', {'passed': False, 'input_sha256': self.doc_hash,
                                    'results': [{'status': 'needs_confirmation'}], 'uncovered': []})
        self.assertEqual(self.result()['status'], 'incomplete')

    def test_actual_format_failure_is_not_hidden_by_unreviewed_exemptions(self):
        self.machine('formatting', {'passed': False, 'input_sha256': self.doc_hash,
                                    'results': [{'status': 'fail'}], 'uncovered': [],
                                    'exemptions': [{'reason': 'complex object'}]})
        self.assertEqual(self.result()['status'], 'blocked')

    def test_required_visual_check_cannot_be_disabled(self):
        self.review['checks']['visual']['status'] = 'not_applicable'
        with self.assertRaisesRegex(ValueError, 'cannot be marked'):
            self.result()

    def test_authorized_content_edit_uses_disclosed_manual_review(self):
        item = copy.deepcopy(self.review['checks']['policy'])
        item.update(method='authorized_edit_review', source_docx=self.file('original.docx', b'original source'),
                    authorized_changes=['User-authorized removal of author identity; before/after map in review.md'])
        self.review['checks']['integrity'] = item
        result = self.result()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['checks']['integrity']['method'], 'authorized_edit_review')

    def test_authorized_edit_cannot_hide_changed_original(self):
        item = copy.deepcopy(self.review['checks']['policy'])
        item.update(method='authorized_edit_review', source_docx=self.file('original.docx', b'original source'),
                    authorized_changes=['Authorized edit recorded in review.md'])
        self.review['checks']['integrity'] = item
        (self.root / 'original.docx').write_bytes(b'changed source')
        self.assertEqual(self.result()['checks']['integrity']['status'], 'needs_confirmation')

    def test_manual_pass_needs_traceable_evidence(self):
        self.review['checks']['policy']['evidence'] = []
        with self.assertRaisesRegex(ValueError, 'review evidence'):
            self.result()

    def test_malformed_machine_report_is_rejected_without_output(self):
        self.machine('formatting', {'passed': True, 'input_sha256': self.doc_hash,
                                    'results': ['invalid property record'], 'uncovered': []})
        self.save()
        out = self.root / 'invalid-status.json'
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.doc), '--review', str(self.review_path), '--out', str(out)]), 2)
        self.assertFalse(out.exists())

    def test_cli_exit_codes_and_readable_report(self):
        del self.review['checks']['visual']
        self.save()
        args = [str(self.doc), '--review', str(self.review_path), '--out', str(self.root / 'status.json'),
                '--report', str(self.root / 'report.md')]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args), 3)
        self.assertIn('核验未完成', (self.root / 'report.md').read_text(encoding='utf-8'))
        before = (self.root / 'status.json').read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args), 2)
        self.assertEqual(before, (self.root / 'status.json').read_bytes())


class DoctorTests(unittest.TestCase):
    def test_missing_dependency_blocks_docx_mode(self):
        with patch('doctor.module_probe', return_value={'status': 'fail', 'reason': 'missing'}):
            self.assertEqual(inspect_environment()['status'], 'blocked')

    def test_requirements_only_does_not_require_docx_tools(self):
        with patch('doctor.module_probe', side_effect=AssertionError('unexpected import')):
            self.assertEqual(inspect_environment('requirements')['status'], 'ready')

    def test_font_fallback_is_not_accepted(self):
        result = subprocess.CompletedProcess([], 0, stdout='Liberation Sans\n', stderr='')
        with patch('doctor.shutil.which', return_value='/test/fc-match'), patch('doctor.subprocess.run', return_value=result):
            self.assertEqual(font_probe('Arial')['status'], 'needs_confirmation')

    def test_missing_renderer_stays_incomplete(self):
        with patch('doctor.shutil.which', return_value=None), patch('doctor.module_probe', return_value={'status': 'pass'}):
            self.assertEqual(inspect_environment('render')['status'], 'incomplete')

    def test_diagnostics_cli_runs_without_site_packages(self):
        result = subprocess.run([sys.executable, '-S', str(SCRIPTS / 'submission.py'), 'doctor'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['checks']['lxml']['status'], 'fail')
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
