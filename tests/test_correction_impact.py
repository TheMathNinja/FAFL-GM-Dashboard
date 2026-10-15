import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import correction_impact as m


class CorrectionImpactTest(unittest.TestCase):
    def test_material_team_results_are_reported(self):
        before = {'season': 2026, 'week': 5,
                  'all_play': {'0001': {'name': 'Carolina Panthers', 'score': 120, 'wins': 13},
                               '0002': {'name': 'Seattle Seahawks', 'score': 115, 'wins': 12}},
                  'bonus': {'Q1:0001': {'name': 'Carolina Panthers', 'event': 'Q1', 'result': 'T'}}}
        after = {'season': 2026, 'week': 5,
                 'all_play': {'0001': {'name': 'Carolina Panthers', 'score': 119, 'wins': 12},
                              '0002': {'name': 'Seattle Seahawks', 'score': 115, 'wins': 13}},
                 'bonus': {'Q1:0001': {'name': 'Carolina Panthers', 'event': 'Q1', 'result': 'L'}}}
        with patch.dict(os.environ, {'GITHUB_RUN_ID': '123'}):
            impact = m.changes(before, after)
        self.assertEqual(impact['all_play'][0]['new_wins'], 12)
        self.assertTrue(impact['all_play'][0]['score_corrected'])
        self.assertFalse(impact['all_play'][1]['score_corrected'])
        self.assertEqual(impact['bonus_games'][0]['new_result'], 'L')


if __name__ == '__main__':
    unittest.main()
