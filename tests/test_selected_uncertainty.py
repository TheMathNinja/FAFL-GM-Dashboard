import sys,json,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import selected_uncertainty as u
class SelectedUncertaintyTests(unittest.TestCase):
 def test_selected_family_and_coefficients(self):
  d=json.loads((ROOT/'data/fafl_uncertainty_selected.json').read_text())
  self.assertEqual(d['selection']['selected'],'Linear')
  self.assertTrue(d['selection']['fully_nested'])
  for w,expected in enumerate(d['team']['sd_by_week'],1):
   tau,meta=u.selected(ROOT,2026,w,200)
   self.assertAlmostEqual(tau,200*expected,places=12)
  self.assertIsNone(u.selected(ROOT,2025,4,200))
 def test_pairs_use_identical_mean_one_factors(self):
  _,m=u.selected(ROOT,2026,4,200);pf=np.full((12000,8,32),200.);pot=pf+50
  a,b=u.scale_pairs(pf,pot,{'selected_uncertainty':m},2026,4)
  c,d=u.scale_pairs(pf,pot,{'selected_uncertainty':m},2026,4)
  np.testing.assert_array_equal(a,c);np.testing.assert_array_equal(b,d)
  np.testing.assert_array_equal(a[:,:,0],a[:,:,31])
  np.testing.assert_allclose(b[:,:,0]/250,a[:,:,0]/200,atol=.000251)
  self.assertLess(abs(a.mean()-200),.1)
  self.assertTrue((b>=a).all())
 def test_legacy_pairs_unchanged(self):
  x=np.ones((10,2,32));a,b=u.scale_pairs(x,x+1,{},2025,10)
  self.assertIs(a,x)
