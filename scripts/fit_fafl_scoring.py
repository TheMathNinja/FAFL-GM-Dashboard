"""Reproduce F315's prior-only native mean, bye adjustment and matched noise."""
from pathlib import Path
import argparse,json,numpy as np,pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp
from scipy.stats import norminvgauss
from scoring_engine import MODEL_VERSION,MODEL_NAME,source_signature

def innovations(root,season,family):
 d=pd.read_csv(root/'data/scoring_history.csv',dtype={'franchise_id':str});d=d[(d.season>=2018)&(d.season<season)&(d.week<=12)]
 blocks=[];sv=[];tv=[]
 for year,g in d.groupby('season'):
  s=g.pivot(index='week',columns='franchise_id',values='points').reindex(index=range(1,13)).sort_index(axis=1).to_numpy()
  if s.shape!=(12,32) or not np.isfinite(s).all():raise ValueError('Incomplete prior scoring season')
  scale=s.mean();means=s.mean(0);v=np.mean((s-means)**2)*12/11/scale**2
  sv.append(v);tv.append(max(1e-8,means.var(ddof=1)/scale**2-v/12));blocks.append((s-s.mean())/scale)
 if sorted(d.season.unique())!=list(range(2018,season)):raise ValueError('Missing prior scoring history')
 sigma=np.sqrt(np.mean(sv));tau=np.sqrt(np.mean(tv));nodes,hw=np.polynomial.hermite.hermgauss(16);nodes*=np.sqrt(2);lh=np.log(hw/np.sqrt(np.pi))
 def loss(v):
  sd=sigma*np.exp(v[0]);st=tau*np.exp(v[1]);total=0.
  for r in blocks:
   if family=='Normal':
    a=sd*sd;b=st*st;den=1+12*b/a;ll=-.5*((r*r).sum(0)/a-b*r.sum(0)**2/(a*a*den)+12*np.log(a)+np.log(den)+12*np.log(2*np.pi))
   else:
    rv=norminvgauss(v[2],v[2]*v[3]);m,var=rv.stats(moments='mv');scale=np.sqrt(var);lp=rv.logpdf((r[:,:,None]-st*nodes)/sd*scale+m)+np.log(scale);ll=logsumexp((lp-np.log(sd)).sum(0)+lh,axis=1)
   total-=float(ll.mean()/12)
  return total/len(blocks)
 init=[0.,0.]+([3.,.05] if family=='NIG' else []);bounds=[(-1,1),(-2,1)]+([(.7,50),(-.6,.6)] if family=='NIG' else [])
 o=minimize(loss,init,bounds=bounds,method='L-BFGS-B',options={'maxiter':100,'ftol':1e-7})
 if not np.isfinite(o.fun):raise ValueError('Innovation fit failed')
 return dict(weekly_variance=float(sigma*sigma*np.exp(2*o.x[0])),shape=o.x[2:].tolist())

def fit(root,season):
 import build as native
 from forecast_byes import exposure_matrix
 root=Path(root);native.ROOT=root;history=native.historical();links=native.load_links()
 normal=innovations(root,season,'Normal');nig=innovations(root,season,'NIG');variance={};records=[]
 for w in range(1,12):
  errors=[]
  for year in range(2022,season):
   cur=history[(history.season==year)&(history.week<=w)].copy();pred,_=native.fit_means(history,cur,year,w,links)
   scores=history[(history.season==year)&(history.week<=12)].pivot(index='week',columns='franchise_id',values='points').reindex(index=range(1,13)).sort_index(axis=1)
   ids=scores.columns.tolist();s=scores.to_numpy();level=s[:w].mean();mu=pred[:,0]-pred[:,0].mean()+level
   error=(s[w:].mean(0)-mu)/level;errors.extend(error-error.mean())
   ex=exposure_matrix(root,year,w,ids)/level;ex-=ex.mean(1,keepdims=True)
   records.append(dict(year=year,week=w,error=(s[w:]-mu)/level,x=-ex))
  variance[w]=max(0,float(np.mean(np.square(errors)))*32/31-normal['weekly_variance']/(12-w))
 # Match the research objective's equal-outlook weighting and bounded fit.
 records.sort(key=lambda r:(r['year'],r['week']))
 X=np.concatenate([r['x'].reshape(-1,1) for r in records]);target=np.concatenate([r['error'].ravel() for r in records]);weights=np.concatenate([np.full(r['error'].size,1/len(r['error'])) for r in records])
 o=minimize(lambda b:float(np.average((X@b-target)**2,weights=weights)),[0.],bounds=[(0,2)],method='L-BFGS-B');beta=float(o.x[0])
 nodes,hw=np.polynomial.hermite.hermgauss(12);nodes*=np.sqrt(2);lh=np.log(hw/np.sqrt(np.pi));residual=[]
 for year in range(2022,season):
  for w in range(1,12):
   # The reference fitter iterates season, then outlook; preserve that order.
   r=next(r for r in records if r['week']==w and r['year']==year)
   idx=np.arange(32)[(np.arange(32)+w)%4==0]
   residual.append((r['error'][:,idx]-beta*r['x'][:,idx],np.sqrt(normal['weekly_variance']),np.sqrt(variance[w])))
 def loss(v):
  rv=norminvgauss(v[2],v[2]*v[3]);mean,var=rv.stats(moments='mv');scale=np.sqrt(var);total=0.
  for rr,ss,tt in residual:
   sd=ss*np.exp(v[0]);tau=tt*np.exp(v[1]);lp=rv.logpdf((rr[:,:,None]-tau*nodes)/sd*scale+mean)+np.log(scale)
   ll=logsumexp((lp-np.log(sd)).sum(0)+lh,axis=1);total-=float(ll.mean()/len(rr))
  return total/len(residual)
 o=minimize(loss,[0.,0.]+nig['shape'],bounds=[(-.6,.6),(-2,1),(1,50),(-.6,.6)],method='L-BFGS-B',options={'maxiter':80,'ftol':1e-7})
 if not np.isfinite(o.fun):raise ValueError('F315 residual fit failed')
 return dict(source_signature=source_signature(root,season),version=MODEL_VERSION,model=MODEL_NAME,family='NIG',forecast_season=season,mean_training_years=list(range(2021,season)),noise_training_years=list(range(2018,season)),uncertainty_training_years=list(range(2022,season)),bye_coefficient=beta,weekly_variance=normal['weekly_variance']*float(np.exp(2*o.x[0])),posterior_variance={str(w):variance[w]*float(np.exp(2*o.x[1])) for w in range(1,12)},shape=o.x[2:].tolist(),loss=float(o.fun),converged=bool(o.success),growth_factor=0.)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--season',type=int,default=2026);p.add_argument('--all-seasons',action='store_true');a=p.parse_args();path=a.root/'data/fafl_scoring_model.json';saved=json.loads(path.read_text()) if path.exists() else {}
 for year in (range(2023,a.season+1) if a.all_seasons else [a.season]):
  signature=source_signature(a.root,year)
  if saved.get(str(year),{}).get('source_signature')==signature:continue
  saved[str(year)]=fit(a.root,year);print('Fitted F315',year,flush=True)
 path.write_text(json.dumps(saved,indent=2),encoding='utf8')
