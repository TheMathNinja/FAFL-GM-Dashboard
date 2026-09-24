import sys,unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from weekly_system import calculate_elo

class WeeklySystemParity(unittest.TestCase):
 def test_internal_elo_matches_reviewed_workbook(self):
  fixture=pd.read_csv(Path(__file__).parent/'fixtures/fafl_2026_elo_weeks_1_2.csv')
  current=pd.concat([pd.DataFrame(dict(season=2026,week=week,franchise_id=[f'{i:04}' for i in range(32)],
      franchise_name=fixture.franchise_name,off=fixture[f'w{week}_off'],deff=fixture[f'w{week}_def'],
      potential=fixture[f'w{week}_pot'],points=fixture[f'w{week}_off']+fixture[f'w{week}_def'])) for week in [1,2]])
  actual=calculate_elo(current,2026)
  for week in [1,2]:
   got=actual[actual.week==week].set_index('franchise_name').elo
   expected=fixture.set_index('franchise_name')[f'w{week}']
   self.assertLess((got-expected).abs().max(),1e-5)

if __name__=='__main__':unittest.main()
