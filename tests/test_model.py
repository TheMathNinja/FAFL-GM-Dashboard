import unittest,sys
from pathlib import Path
from datetime import date,datetime
from zoneinfo import ZoneInfo
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from build import DEFAULT_SIMULATIONS,historical,load_links,fit_means,completed_week,draw_future_points,pool_unstarted_quarter_bonus
from rules import rank_field,fafl_outcomes
from score_schedule import schedule_decision

class ModelTests(unittest.TestCase):
 def test_production_uses_shared_simulation_count(self):
  self.assertEqual(DEFAULT_SIMULATIONS,12000)

 def test_matches_selected_experiment_at_every_checkpoint(self):
  h=historical();links=load_links();expected=pd.read_csv(ROOT/'tests/fixtures/expected_means.csv')
  for (year,week),g in expected.groupby(['season','week']):
   current=h[(h.season==year)&(h.week<=week)]
   pred,_=fit_means(h,current,year,week,links)
   np.testing.assert_allclose(pred,g[['actual_mean','potential_mean']].to_numpy(),atol=1e-8,rtol=0)

 def test_future_seasons_cannot_change_a_forecast(self):
  h=historical();current=h[(h.season==2024)&(h.week<=3)];links=load_links()
  before,_=fit_means(h,current,2024,3,links)
  h.loc[h.season>=2024,['points','potential','allplay']]=99999
  after,_=fit_means(h,current,2024,3,links)
  np.testing.assert_allclose(before,after,atol=1e-10)

 def test_qualification_matches_independent_R_cases(self):
  teams=pd.read_csv(ROOT/'tests/fixtures/rule_parity_teams.csv',dtype={'franchise_id':str,'conference':str,'division':str})
  games=pd.read_csv(ROOT/'tests/fixtures/rule_parity_games.csv',dtype={'franchise_id':str,'opponent_id':str})
  for case,t in teams.groupby('case',sort=False):
   t=t.reset_index(drop=True);ids=t.franchise_id.tolist();opp=np.zeros((12,32),int);credits=np.zeros((1,12,32))
   for i,fid in enumerate(ids):
    g=games[(games['case']==case)&(games.franchise_id==fid)]
    opp[:,i]=[ids.index(x) for x in g.opponent_id];credits[0,:,i]=g.credit
   conf=[np.flatnonzero(t.conference==c) for c in sorted(t.conference.unique())]
   div=[np.flatnonzero((t.conference==c)&(t.division==d)) for c,d in t[['conference','division']].drop_duplicates().itertuples(index=False,name=None)]
   q,dw,seed=rank_field(t.win_pct.to_numpy()[None]*17,t.ap_win_pct.to_numpy()[None]*372,t.points_for.to_numpy()[None],t.potential_points.to_numpy()[None],credits,opp,conf,div)
   np.testing.assert_array_equal(seed[0],t.expected_seed)

 def test_bonus_potential_tiebreak_and_no_unplayed_bonuses(self):
  scores=np.full((1,3,32),100.);potential=np.broadcast_to(np.arange(32)+100.,scores.shape)
  opp=np.tile(np.arange(32)^1,(3,1));conf=[np.arange(16),np.arange(16,32)];div=[np.arange(i,i+4) for i in range(0,32,4)]
  result=fafl_outcomes(scores,potential,opp,conf,div)
  self.assertEqual(result[3][0,31],2.5);self.assertEqual(result[3][0,0],1.5)
  self.assertEqual(result[3][0,15],2.0);self.assertEqual(result[3].sum(),64)
  one=fafl_outcomes(scores[:,:1],potential[:,:1],opp[:1],conf,div)
  self.assertEqual(one[3].sum(),16)

 def test_simulated_scores_use_mfl_precision_and_ties_are_half_wins(self):
  draws=draw_future_points(np.random.default_rng(1),np.full(32,200.),35.,10.,50,4)
  self.assertTrue(np.allclose(draws*10,np.round(draws*10)))
  scores=np.full((1,1,32),200.);potential=scores.copy()
  opp=np.tile(np.arange(32)^1,(1,1));conf=[np.arange(16),np.arange(16,32)];div=[np.arange(i,i+4) for i in range(0,32,4)]
  result=fafl_outcomes(scores,potential,opp,conf,div)
  self.assertTrue((result[5]==.5).all())

 def test_unstarted_bonus_games_are_pooled_without_changing_totals(self):
  base=np.zeros((32,4))
  base[:15]=1;base[15:17]=.5
  # Opposing small Monte Carlo deviations keep every column at 16 wins.
  base[14,1:]=[.8,.7,.75];base[15,1:]=[.7,.8,.75]
  data={f'Q{i+1} Bonus Game':base[:,i] for i in range(4)}
  data['Regular Season Bonus Game']=base[:,0]
  before=np.column_stack([data[f'Q{i} Bonus Game'] for i in range(1,5)])
  pooled=pool_unstarted_quarter_bonus(data,3)
  after=np.column_stack([pooled[f'Q{i} Bonus Game'] for i in range(1,5)])
  np.testing.assert_array_equal(after[:,0],before[:,0])
  np.testing.assert_allclose(after[:,1],after[:,2],atol=0,rtol=0)
  np.testing.assert_allclose(after[:,2],after[:,3],atol=0,rtol=0)
  np.testing.assert_allclose(after.sum(1),before.sum(1),atol=1e-12,rtol=0)
  np.testing.assert_allclose(after.sum(0),16,atol=1e-12,rtol=0)

 def test_dates_and_dst(self):
  self.assertEqual(completed_week(date(2026,9,14)),0)
  self.assertEqual(completed_week(date(2026,9,15)),1)
  self.assertEqual(completed_week(date(2026,9,22)),2)
  self.assertEqual(completed_week(date(2026,12,8)),13)
  for day,good,bad in [('2026-09-17','0 9 * * 4','0 10 * * 4'),('2026-11-12','0 10 * * 4','0 9 * * 4')]:
   now=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('America/New_York'))
   self.assertEqual(schedule_decision(now,2026,'schedule',good)['should_run'],'true')
   self.assertEqual(schedule_decision(now,2026,'schedule',bad)['should_run'],'false')

if __name__=='__main__':unittest.main()
