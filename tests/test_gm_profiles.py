import json
from pathlib import Path
import sys
import tempfile
import unittest
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from gm_profiles import gm_profiles, _current_profiles

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

    def test_current_ownership_is_not_inherited_from_historical_team(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir()
            for name in ['gm_career_profiles.json', 'gm_career_seasons.json', 'current_gms_2026.json']:
                shutil.copy(ROOT / 'data' / name, root / 'data' / name)
            path = root / 'data/current_gms_2026.json'
            current = json.loads(path.read_text())
            current['profiles']['Dallas Cowboys']['gm'] = 'Russell Mataya'
            current['profiles']['New York Giants']['gm'] = 'Jonathan Bell'
            path.write_text(json.dumps(current))
            profiles = _current_profiles(root, 2026)
            self.assertEqual(profiles['Dallas Cowboys']['gm'], 'Russell Mataya')
            self.assertEqual(profiles['Dallas Cowboys']['experience'], 12)
            self.assertEqual(profiles['New York Giants']['gm'], 'Jonathan Bell')
            self.assertEqual(profiles['New York Giants']['experience'], 7)

    def test_career_percentage_weights_seasons_equally_and_current_year_partially(self):
        current = pd.DataFrame([
            dict(week=w, franchise_id=f'{i:04}', points=float(i))
            for w in [1, 2, 3] for i in range(1, 33)
        ])
        result = gm_profiles(ROOT, 2026, 3, current)
        rows = json.loads((ROOT / 'data/gm_career_seasons.json').read_text())
        history = [r for r in rows if r['gm'].strip() == 'Russell Mataya']
        season_pcts = [(r['wins'] + .5 * r['ties']) / (r['wins'] + r['losses'] + r['ties']) for r in history]
        current_pct = 1 / 31  # NYG is franchise 0002: one win and 30 losses each week.
        expected = (sum(season_pcts) + (3 / 17) * current_pct) / (len(season_pcts) + 3 / 17)
        self.assertAlmostEqual(result['New York Giants']['careerApPct'], expected, places=12)
        pooled = (sum(r['wins'] + .5 * r['ties'] for r in history) + 3) / (
            sum(r['wins'] + r['losses'] + r['ties'] for r in history) + 3 * 31
        )
        self.assertNotAlmostEqual(result['New York Giants']['careerApPct'], pooled, places=8)
