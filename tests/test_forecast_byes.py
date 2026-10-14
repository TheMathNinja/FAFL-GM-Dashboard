import sys,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import forecast_byes as b
import scoring_engine as e
import bonus_predictor as bonus

class ForecastByeTests(unittest.TestCase):
 def test_exact_optimizer_uses_eligible_same_roster_replacement(self):
  roster=[dict(id='a',pos='WR',points=30,team='CHI'),dict(id='b',pos='WR',points=15,team='GB')]
  limits={'WR':(1,1,'off')};totals={'off':1}
  self.assertEqual(b.best_lineup(roster,limits,totals),30)
  self.assertEqual(b.best_lineup([{**p,'points':0 if p['team']=='CHI' else p['points']} for p in roster],limits,totals),15)
 def test_missing_forecast_matrix_fails_instead_of_zero_adjustment(self):
  with self.assertRaisesRegex(ValueError,'Missing as-of'):b.exposure_matrix(ROOT,2099,4,[f'{i:04}' for i in range(32)])
 def test_bye_losses_only_change_the_corresponding_future_week(self):
  cur=pd.read_csv(ROOT/'data/current_weekly.csv',dtype={'franchise_id':str});x=np.zeros((8,32))
  with patch.object(b,'exposure_matrix',return_value=x):base=e.parameters(ROOT,cur,2026,4)
  x[3,0]=20
  with patch.object(b,'exposure_matrix',return_value=x):changed=e.parameters(ROOT,cur,2026,4)
  np.testing.assert_array_equal(base[0][[0,1,2,4,5,6,7]],changed[0][[0,1,2,4,5,6,7]])
  self.assertLess(changed[0][3,0],base[0][3,0]);np.testing.assert_allclose(changed[0].mean(1),base[0].mean(1))
 def test_unstarted_quarters_keep_week_specific_forecasts(self):
  s=np.zeros((1,32));f=np.tile(np.arange(32),(100,11,1)).astype(float)
  f[:,5:8]=f[:,5:8,::-1]
  result=bonus.event_forecasts(s,s,1,f,np.zeros(32),'FAFL',f+10)
  self.assertFalse(np.array_equal(result['Q2']['probabilities'],result['Q3']['probabilities']))
 def test_week_varying_mean_is_preserved_by_sampler(self):
  mu=np.arange(32)[None,:]+np.arange(8)[:,None]*10+100
  f=e.future(mu,0,0,{'shape':[5,.1]},2026,4,100)
  np.testing.assert_array_equal(f,np.broadcast_to(mu,(100,8,32)))
