import unittest,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from build import historical,load_links,strength_uncertainty,draw_future_points

class StrengthUncertaintyTests(unittest.TestCase):
 def test_matches_independent_historical_experiment(self):
  h=historical();links=load_links()
  expected=pd.read_csv(ROOT/'tests/fixtures/expected_strength_sd.csv')
  for row in expected.itertuples():
   self.assertAlmostEqual(strength_uncertainty(h,2025,int(row.week),links),row.tau,places=9)

 def test_future_scores_cannot_change_estimate(self):
  h=historical();links=load_links();before=strength_uncertainty(h,2025,3,links)
  h.loc[h.season>=2025,['points','potential','allplay']]=99999
  self.assertEqual(before,strength_uncertainty(h,2025,3,links))

 def test_offset_persists_across_weeks(self):
  points=draw_future_points(np.random.default_rng(7),np.full(32,200),0,12,100,10)
  np.testing.assert_allclose(points,np.broadcast_to(points[:,:1,:],points.shape))
  self.assertGreater(points.std(),0)
  self.assertEqual(strength_uncertainty(historical(),2026,12,load_links()),0)
