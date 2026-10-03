import json
from pathlib import Path
import sys
import unittest
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from gm_profiles import gm_profiles

class CareerHistoryTests(unittest.TestCase):
    def test_historical_finishes_and_balanced_records(self):
        rows = json.loads((ROOT / 'data/gm_career_seasons.json').read_text())
        for year in range(2014, 2026):
            season = [r for r in rows if r['season'] == year]
            self.assertEqual(sorted(r['finish'] for r in season), list(range(1, 33)))
            self.assertEqual(sum(r['wins'] for r in season), sum(r['losses'] for r in season))
            for r in season:
                self.assertEqual(r['wins'] + r['losses'] + r['ties'], 31 * (16 if year < 2021 else 17))
        finishes = {r['name']: r['finish'] for r in rows if r['season'] == 2018}
        self.assertEqual([finishes[n] for n in ['New York Jets', 'Minnesota Vikings', 'Los Angeles Rams', 'Baltimore Ravens']], [9, 10, 11, 12])
        self.assertIn(finishes['New England Patriots'], [13, 14])

    def test_current_games_added_once_and_future_games_excluded(self):
        before = json.loads((ROOT / 'data/gm_career_profiles.json').read_text())['profiles']
        current = pd.DataFrame([dict(week=w, franchise_id=f'{i:04}', points=float(i)) for w in [1, 2] for i in range(1, 33)])
        result = gm_profiles(ROOT, 2026, 1, current)
        for name, g in result.items():
            original = before[name]
            i = int(g['franchise_id'])
            self.assertEqual(g['wins'] - original['wins'], i - 1)
            self.assertEqual(g['losses'] - original['losses'], 32 - i)
            self.assertEqual(g['experience'], original['experience'])
        self.assertEqual(result, gm_profiles(ROOT, 2026, 1, current))
        self.assertEqual(result['Los Angeles Chargers']['gm'], 'David Overbeek')
