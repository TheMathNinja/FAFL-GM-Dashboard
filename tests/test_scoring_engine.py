import sys,unittest,json
from pathlib import Path
from unittest.mock import patch
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import scoring_engine as e
import quarterly_bonus as q
import bonus_predictor as b
class ScoringEngineTests(unittest.TestCase):
 def current(self):return pd.read_csv(ROOT/'data/current_weekly.csv',dtype={'franchise_id':str})
 def test_mean_level_and_prior_only_noise(self):
  cur=self.current();mu,sd,tau,gap,meta=e.parameters(ROOT,cur,2026,4)
  np.testing.assert_allclose(mu.mean(1),cur[cur.week<=4].points.mean(),atol=1e-10);self.assertEqual(mu.shape,(8,32));self.assertGreater(sd,0);self.assertGreaterEqual(tau,0);self.assertEqual(max(meta['innovation_training_years']),2025);self.assertEqual(meta['reg_season_model'],meta['version']);self.assertEqual(meta['growth_factor'],0.)
 def test_later_current_scores_do_not_enter_forecast(self):
  cur=self.current();before=e.parameters(ROOT,cur,2026,3);cur.loc[cur.week>3,['points','potential']]=999999;after=e.parameters(ROOT,cur,2026,3)
  for x,y in zip(before[:4],after[:4]):np.testing.assert_array_equal(x,y)
 def test_all_consumers_use_one_joint_trajectory(self):
  cur=self.current()
  with patch.object(q,'future_pairs',side_effect=lambda root,current,league,season,week,future:(np.stack([future,future+20],-1),{'method':'test'})):
   f=q.forecast(ROOT,cur,'FAFL',2026,4,1000,dict(ids=sorted(cur.franchise_id.unique()),mu=[9999]*32,sigma=0,tau=0))
  self.assertIs(f['native_future'],f['future']);self.assertEqual(f['model']['version'],e.MODEL_VERSION)
  np.testing.assert_array_equal(f['reg_season_credits'],b.segment_samples(f['s'],f['p'],4,f['future'],f['gap'],'FAFL',0,12,f['future_potential'])[1]/2)
  for label,start,end in b.EVENTS:
   credit=b.segment_samples(f['s'],f['p'],4,f['future'],f['gap'],'FAFL',start,end,f['future_potential'])[1]/2
   np.testing.assert_allclose(credit.sum(1),16)
 def test_persistent_strength_is_shared_across_weeks(self):
  m={'shape':[5.,.1]};x=e.future(np.full(32,10000.),0,10,m,2026,9,4000);np.testing.assert_array_equal(x[:,0],x[:,1]);np.testing.assert_array_equal(x[:,1],x[:,2])
 def test_nig_center_and_scale(self):
  m={'shape':[5.,.1]};x=e.future(np.full(32,10000.),30,0,m,2026,9,4000)-10000
  self.assertLess(abs(x.mean()),.2);self.assertLess(abs(x.std()-30),.4)
 def test_catches_changed_mean_or_noise_source(self):
  with patch.object(e,'source_signature',return_value='changed'):
   with self.assertRaisesRegex(ValueError,'Mean/noise inputs changed'):e.parameters(ROOT,self.current(),2026,4)
 def test_2023_is_supported_without_native_loso_failure(self):
  cur=pd.read_csv(ROOT/'data/historical_weekly.csv',dtype={'franchise_id':str});cur=cur[cur.season==2023];mu,sd,tau,gap,meta=e.parameters(ROOT,cur,2023,4);self.assertTrue(np.isfinite(mu).all());self.assertGreater(sd,0);self.assertEqual(meta['training_years'],[2021,2022])
 def test_matches_selected_f315_at_every_research_checkpoint(self):
  expected=json.loads((ROOT/'tests/fixtures/f315_expected_parameters.json').read_text())
  for year in [2023,2024,2025,2026]:
   cur=pd.read_csv(ROOT/('data/current_weekly.csv' if year==2026 else 'data/historical_weekly.csv'),dtype={'franchise_id':str});cur=cur[cur.season==year]
   for row in [r for r in expected if r['season']==year]:
    mu,sd,tau,_,meta=e.parameters(ROOT,cur,year,row['week'])
    np.testing.assert_allclose(mu,row['mu'],atol=1e-9,rtol=0)
    self.assertAlmostEqual(sd,row['sd'],delta=3e-5);self.assertAlmostEqual(tau,row['tau'],delta=3e-5)
    np.testing.assert_allclose(meta['shape'],row['shape'],atol=1e-4,rtol=0)
