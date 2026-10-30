"""F315: one prior-fitted FAFL scoring process for every forecast consumer."""
from pathlib import Path
import hashlib, inspect, json
import numpy as np
import pandas as pd
from scipy.stats import norminvgauss

MODEL_VERSION='fafl-f315-upcoming-sharks50-nig-v2'
MODEL_NAME='F315 + 50% upcoming-week calibrated Sharks / retained NIG uncertainty'

def source_signature(root,season):
 import build as native
 root=Path(root);native.ROOT=root
 h=native.historical();h=h[h.season<season][['season','week','franchise_id','points','potential','allplay']].sort_values(['season','week','franchise_id'])
 n=pd.read_csv(root/'data/scoring_history.csv',dtype={'franchise_id':str});n=n[(n.season>=2018)&(n.season<season)&(n.week<=12)][['season','week','franchise_id','points']].sort_values(['season','week','franchise_id'])
 links=native.load_links();links=links[links.season<=season].sort_values(['season','franchise_id'])
 exposure=pd.read_csv(root/'data/forward_bye_exposure.csv',dtype={'franchise_id':str});exposure=exposure[exposure.season<season].sort_values(['season','week','target_week','franchise_id'])
 parts=[MODEL_VERSION,inspect.getsource(native.fit_means),inspect.getsource(native.prior_features),h.to_csv(index=False),n.to_csv(index=False),links.to_csv(index=False),exposure.to_csv(index=False)]
 parts += [(root/'scripts'/file).read_text(encoding='utf8') for file in ['scoring_engine.py','fit_fafl_scoring.py','forecast_byes.py']]
 parts += [(root/'scripts/selected_uncertainty.py').read_text(),(root/'data/fafl_uncertainty_selected.json').read_text()]
 return hashlib.sha256('\n'.join(parts).encode('utf8')).hexdigest()

def parameters(root,current,season,week):
 import build as native
 from forecast_byes import exposure_matrix
 root=Path(root);native.ROOT=root
 f=json.loads((root/'data/fafl_scoring_model.json').read_text(encoding='utf8'))[str(season)]
 if f.get('source_signature')!=source_signature(root,season):raise ValueError('Mean/noise inputs changed: run fit_fafl_scoring.py before forecasting')
 if f['version']!=MODEL_VERSION or f['family']!='NIG':raise ValueError('Scoring model/version mismatch: refit the shared FAFL engine')
 if max(f['mean_training_years']+f['noise_training_years']+f['uncertainty_training_years'])>=season:raise ValueError('Forecast training includes the test season')
 seen=current[current.week<=week].copy();seen.franchise_id=seen.franchise_id.astype(str).str.zfill(4);ids=sorted(seen.franchise_id.unique())
 s=seen.pivot(index='week',columns='franchise_id',values='points').reindex(index=range(1,week+1),columns=ids).to_numpy();p=seen.pivot(index='week',columns='franchise_id',values='potential').reindex(index=range(1,week+1),columns=ids).to_numpy()
 if len(ids)!=32 or not np.isfinite(s).all() or not np.isfinite(p).all():raise ValueError('Missing as-of team scores')
 pred,details=native.fit_means(native.historical(),seen,season,week,native.load_links());level=float(s.mean())
 if details['training_years']!=f['mean_training_years']:raise ValueError('Mean and uncertainty use different training seasons')
 loss=exposure_matrix(root,season,week,ids);centered_loss=loss-loss.mean(1,keepdims=True)
 mu=np.broadcast_to(pred[:,0]-pred[:,0].mean()+level,loss.shape).copy()-f['bye_coefficient']*centered_loss
 sigma=level*np.sqrt(f['weekly_variance']);tau=level*np.sqrt(f['posterior_variance'][str(week)]);gap=np.maximum(0,(p-s).mean(0))
 from selected_uncertainty import selected
 chosen=selected(root,season,week,level)
 if chosen:tau,selected_meta=chosen
 native_mu=mu.copy()
 from upcoming_sharks import apply
 mu=apply(root,season,week,ids,mu)
 signature=hashlib.sha256((f['source_signature']+loss.tobytes().hex()).encode()).hexdigest()
 metadata=dict(native_mean=native_mu.tolist(),upcoming_sharks_weight=.5,source_signature=signature,fit_signature=f['source_signature'],version=MODEL_VERSION,model=MODEL_NAME,family='NIG',distribution='Normal-inverse-Gaussian',shape=f['shape'],growth_factor=0.,bye_coefficient=f['bye_coefficient'],training_years=f['mean_training_years'],innovation_training_years=f['noise_training_years'],uncertainty_training_years=f['uncertainty_training_years'],mean_method='week-specific native three-input regression centered on observed league YTD PPG; forecast-week same-roster bye losses',features=details['features'],coefficients=details['coefficients'],feature_means=details['feature_means'],feature_sd=details['feature_sd'],weekly_volatility='league-wide normalized weekly SD; residual-matched to the bye-adjusted mean',strength_uncertainty='week-specific persistent Normal team offset, residual-matched to the bye-adjusted mean',reg_season_model=MODEL_VERSION,reg_season_distribution='Normal-inverse-Gaussian',all_consumers=['H2H','All-Play','quarterly Bonus Games','Reg Season Bonus Game','playoff qualification'])
 if chosen:
  metadata.update(version=selected_meta['version'],reg_season_model=selected_meta['version'],model='F315 + 50% Sharks / selected relative interval team + linear lognormal league uncertainty',uncertainty_training_years=selected_meta['training_years'],selected_uncertainty=selected_meta,strength_uncertainty='training-selected relative persistent Normal SD; shared weekly/persistent mean-one lognormal league factors')
 return mu,float(sigma),float(tau),gap,metadata

def future(mu,sigma,tau,model,season,week,n):
 if n<2 or n%2:raise ValueError('Simulations must be a positive even count')
 rng=np.random.default_rng(890817+season*100+week);a,ratio=model['shape'];rv=norminvgauss(a,a*ratio);m,v=rv.stats(moments='mv')
 z=(rv.rvs(size=(n,12-week,32),random_state=rng)-m)/np.sqrt(v)
 off=rng.normal(size=(n//2,1,32));off=np.concatenate([off,-off])
 means=np.broadcast_to(np.asarray(mu),(12-week,32))
 return np.round(np.maximum(0,means[None]+z*sigma+off*tau),1)
