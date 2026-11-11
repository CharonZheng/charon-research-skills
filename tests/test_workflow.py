import copy
import sys
from pathlib import Path
import unittest
from _paths import SCRIPTS
sys.path.insert(0, str(SCRIPTS))
from workflow import consolidate, compare_profiles
from test_submission import specification


class FactTests(unittest.TestCase):
    def setUp(self):
        self.data = {'manuscript_id': 'synthetic-1', 'sources': [{'id': 'U1', 'kind': 'author_confirmation', 'locator': 'test reply', 'evidence': 'test confirmation'}],
                     'facts': [{'key': 'funding_role', 'value': 'No involvement', 'status': 'confirmed', 'source_ids': ['U1'], 'required': True}]}

    def test_confirmed_fact_reused_without_question(self):
        registry, questions = consolidate(self.data)
        later = {'manuscript_id': 'synthetic-1', 'facts': [{'key': 'funding_role', 'status': 'missing', 'required': True}]}
        result, questions = consolidate(later, registry)
        self.assertEqual(result['facts'][0]['status'], 'confirmed'); self.assertFalse(questions['new_questions'])

    def test_missing_required_questions_batched_and_not_repeated(self):
        self.data['facts'] = [{'key': k, 'status': 'missing', 'required': True, 'blocking': True, 'question': k} for k in ('ethics_basis', 'data_access')]
        registry, questions = consolidate(self.data)
        self.assertEqual(len(questions['new_questions']), 2)
        registry, questions = consolidate({'manuscript_id': 'synthetic-1'}, registry)
        self.assertFalse(questions['new_questions']); self.assertEqual(len(questions['pending_questions']), 2)

    def test_conflicting_fact_requires_explicit_resolution(self):
        registry, _ = consolidate(self.data)
        self.data['facts'][0].update(value='Involved', question='Which role?')
        conflict, questions = consolidate(self.data, registry)
        self.assertEqual(conflict['facts'][0]['status'], 'conflicting')
        self.assertTrue(questions['new_questions'])
        self.data['facts'][0]['supersedes'] = True
        resolved, _ = consolidate(self.data, conflict)
        self.assertEqual(resolved['facts'][0]['status'], 'confirmed')

    def test_manuscript_boundaries_enforced(self):
        registry, _ = consolidate(self.data); self.data['manuscript_id'] = 'different'
        with self.assertRaises(ValueError): consolidate(self.data, registry)

    def test_document_does_not_confirm_author_declaration(self):
        self.data['sources'][0]['kind'] = 'document'
        with self.assertRaises(ValueError): consolidate(self.data)

    def test_optional_unknown_does_not_interrupt(self):
        self.data['facts'] = [{'key': 'optional', 'status': 'missing'}]
        self.assertFalse(consolidate(self.data)[1]['new_questions'])

    def test_profile_delta_separates_sources(self):
        old = specification(); new = copy.deepcopy(old)
        new['checked_on'] = '2026-11-10'; new['sources'][0]['checked_on'] = '2026-11-10'
        self.assertFalse(compare_profiles(old, new)['changed'])
        new['rules'][0]['description'] = 'New requirement'
        self.assertEqual(len(compare_profiles(old, new)['changed']), 1)


if __name__ == '__main__': unittest.main()
