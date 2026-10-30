"""Training-selected relative team taper and shared linear lognormal factors."""
from pathlib import Path
import json
import numpy as np
from scipy.special import expit

def selected(root,season,week,level):
 d=json.loads((Path(root)/'data/fafl_uncertainty_selected.json').read_text())
 if season!=d['forecast_season']:return None
 if max(d['training_years'])>=season:raise ValueError('Future uncertainty training')
 if not 1<=week<=11:raise ValueError('Invalid regular-season forecast origin')
 v=d['team']['coef'];x=(11-week)/10;family=d['team']['family']
 if family=='Linear':sd=v[0]+v[1]*x
 elif family=='Logistic':sd=v[0]+v[1]*expit((v[2]-week)/v[3])
 elif family=='Half-life':sd=v[0]+v[1]*2**(-(week-1)/v[2])
 elif family=='Power':sd=v[0]+v[1]*x**v[2]
 elif family=='Quadratic':sd=v[0]+v[1]*x+v[2]*x*x
 else:raise ValueError('Unknown team uncertainty family')
 if sd<0 or not np.isfinite(sd):raise ValueError('Invalid persistent SD')
 return float(level*sd),dict(version=d['version'],team_family=family,team_coef=v,team_objective='equal proper 80%/95% relative PPG interval scores',selection=d['selection'],league_coef=d['league']['coef'],training_years=d['training_years'])

def scale_pairs(pf,potential,model,season,week):
 config=model.get('selected_uncertainty')
 if not config:return pf,potential
 n=len(pf);s,end,decline=config['league_coef'];t=end+decline*(11-week)/10
 rng=np.random.default_rng(111903+season*100+week)
 off=rng.normal(size=(n//2,1));noise=rng.normal(size=(n//2,12-week));off=np.r_[off,-off];noise=np.r_[noise,-noise]
 factor=np.exp(t*off+s*noise-.5*(s*s+t*t))[:,:,None]
 scaled=np.round(pf*factor,1)
 return scaled,np.maximum(potential*factor,scaled)
