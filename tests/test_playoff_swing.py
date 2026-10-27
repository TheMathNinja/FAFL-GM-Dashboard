import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import build


class PlayoffSwingTest(unittest.TestCase):
    def test_conditions_existing_draws_without_resimulation(self):
        simulations = 400
        future = np.zeros((simulations, 1, 2))
        future[:200, 0, 0] = 10
        future[200:, 0, 1] = 10
        qualified = np.zeros((simulations, 2), dtype=bool)
        qualified[:200, 0] = True
        qualified[200:, 1] = True
        rows = build.playoff_swing_rows(
            qualified, future, np.array([[1, 0]]),
            [dict(id='0001', name='A'), dict(id='0002', name='B')], 0,
            np.where(qualified,1,16))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['combined_swing'], 200.0)
        self.assertEqual(rows[0]['team_a_win_samples'], 200)
        self.assertEqual(rows[0]['team_b_win_samples'], 200)
        self.assertEqual(rows[0]['team_a_seed_if_win'],1)
        self.assertEqual(rows[0]['team_a_seed_if_loss'],8)
        self.assertEqual(rows[0]['combined_seed_swing'],14)

    def test_seed_swing_for_already_qualified_teams_and_ties(self):
        future=np.zeros((401,1,2));future[:200,0,0]=10;future[200:400,0,1]=10
        qualified=np.ones((401,2),dtype=bool)
        seeds=np.tile([1,4],(401,1));seeds[200:400]=[4,1]
        row=build.playoff_swing_rows(qualified,future,np.array([[1,0]]),
            [dict(id='0001',name='A'),dict(id='0002',name='B')],0,seeds)[0]
        self.assertEqual(row['combined_swing'],0)
        self.assertEqual(row['combined_seed_swing'],6)
        self.assertEqual(row['team_a_win_samples']+row['team_b_win_samples'],400)

    def test_no_regular_season_matchups_after_week_twelve(self):
        self.assertEqual(build.playoff_swing_rows(
            np.zeros((100, 2), dtype=bool), np.zeros((100, 0, 2)),
            np.zeros((12, 2), dtype=int), [{}, {}], 12), [])


if __name__ == '__main__':
    unittest.main()
