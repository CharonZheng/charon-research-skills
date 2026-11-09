import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/journal-submission-prep/scripts'))
from layout_check import check_pdf


class LayoutTests(unittest.TestCase):
    def check(self, chars=None, expected=()):
        page = SimpleNamespace(width=600, height=800, images=[], curves=[], rects=[], lines=[], chars=chars or [])
        module = MagicMock(); module.open.return_value.__enter__.return_value.pages = [page]
        with patch.dict(sys.modules, {'pdfplumber': module}):
            return check_pdf('synthetic.pdf', expected)

    def char(self, **updates):
        return {'fontname': 'AAAAAA+LiberationSans', 'x0': 10, 'x1': 20, 'top': 10, 'bottom': 22, 'text': 'A', **updates}

    def test_substitution_is_not_accepted(self):
        r = self.check([self.char()], ['Arial'])
        self.assertFalse(r['automated_triage_clear'])
        self.assertEqual(r['findings'][0]['kind'], 'expected_font_absent')

    def test_known_family_has_no_visual_pass_claim(self):
        r = self.check([self.char()], ['Liberation Sans'])
        self.assertTrue(r['automated_triage_clear']); self.assertEqual(r['visual_validation'], 'not_checked')

    def test_cjk_font_name_cannot_match_empty_ascii_normalization(self):
        self.assertFalse(self.check([self.char()], ['宋体'])['automated_triage_clear'])

    def test_outside_and_replacement_flags(self):
        kinds = {f['kind'] for f in self.check([self.char(x1=610, text='\ufffd')])['findings']}
        self.assertEqual(kinds, {'text_outside_page', 'replacement_character'})

    def test_empty_page_flagged(self):
        self.assertEqual(self.check()['findings'][0]['kind'], 'blank_page_candidate')


if __name__ == '__main__': unittest.main()
