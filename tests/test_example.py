"""A real generated DOCX must pass checks without fabricating delivery readiness."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ExampleTests(unittest.TestCase):
    def test_synthetic_docx_pipeline_keeps_unperformed_checks_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'example'
            script = Path(__file__).resolve().parents[1] / 'examples' / 'synthetic_submission.py'
            result = subprocess.run([sys.executable, str(script), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads((output / 'integrity.json').read_text())['passed'])
            self.assertTrue(json.loads((output / 'format-check.json').read_text())['passed'])
            delivery = json.loads((output / 'delivery-status.json').read_text())
            self.assertEqual(delivery['status'], 'incomplete')
            self.assertEqual(delivery['checks']['visual']['status'], 'not_checked')
            self.assertEqual(delivery['checks']['rendered_fonts']['status'], 'not_checked')
            self.assertIn('核验未完成', (output / '检查报告.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
