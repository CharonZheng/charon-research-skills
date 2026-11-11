"""Use the same tests in the development tree and the public collection."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / 'skills' / 'journal-submission-prep'
if not SKILL_ROOT.is_dir():
    SKILL_ROOT = ROOT / 'journal-submission-prep'
SCRIPTS = SKILL_ROOT / 'scripts'
