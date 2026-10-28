import sys,unittest,tempfile
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from upcoming_sharks import apply
class SharksMeanTests(unittest.TestCase):
 def test_blend_is_half_and_only_upcoming_week(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tests') as d:
   p=Path(d)/'data';p.mkdir();pd.DataFrame([dict(season=2026,target_week=8,franchise_id='0001',sharks_mean=240),dict(season=2026,target_week=8,franchise_id='0002',sharks_mean=180)]).to_csv(p/'weekly_sharks_team_means.csv',index=False)
   mu=np.array([[200.,200.],[201.,202.],[203.,204.]]);x=apply(d,2026,7,['0001','0002'],mu)
   np.testing.assert_array_equal(x[0],[220,190]);np.testing.assert_array_equal(x[1:],mu[1:]);np.testing.assert_array_equal(mu[0],[200,200])
   with self.assertRaisesRegex(ValueError,'Missing'):apply(d,2026,6,['0001','0002'],mu)
if __name__=='__main__':unittest.main()
