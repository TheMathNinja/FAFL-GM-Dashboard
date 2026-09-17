"""FAFL 2026 playoff forecast. Run from the repository root."""
import argparse,json,html,os,time,urllib.request
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from rules import fafl_outcomes,rank_field

ROOT=Path(__file__).resolve().parents[1]
SEASON=2026
FEATURES=['current_pot','prior_ap','prior_pot']

def export(kind,year=SEASON,**params):
 from urllib.parse import urlencode
 url=f'https://api.myfantasyleague.com/{year}/export?'+urlencode(dict(TYPE=kind,L='22686',JSON=1,**params))
 for attempt in range(3):
  try:
   request=urllib.request.Request(url,headers={'User-Agent':'FAFL-GM-Dashboard/1.0 (league 22686)'})
   with urllib.request.urlopen(request,timeout=60) as response:result=json.load(response)
   if kind not in result:raise ValueError(f'MFL {kind} response missing required payload')
   return result[kind]
  except Exception:
   if attempt==2:raise
   time.sleep(2**attempt)

def completed_week(today=None):
 today=today or datetime.now(timezone.utc).date()
 september=date(SEASON,9,1);labor=september+timedelta(days=(-september.weekday())%7)
 first_tuesday=labor+timedelta(days=8)
 return min(12,max(0,(today-first_tuesday).days//7+1))

def historical():
 d=pd.read_csv(ROOT/'data/historical_weekly.csv',dtype={'franchise_id':str,'division':str,'conference':str})
 d.franchise_id=d.franchise_id.str.zfill(4)
 return d

def prior_features(history,links):
 ap=history[history.week.between(9,17)].groupby(['season','franchise_id']).allplay.mean().rename('prior_ap')
 pot=history[history.week.between(12,14)].groupby(['season','franchise_id']).potential.mean().rename('prior_pot')
 prior=pd.concat([ap,pot],axis=1).reset_index().rename(columns={'franchise_id':'previous_id'})
 prior.season+=1
 return links.merge(prior,on=['season','previous_id'],how='left')

def load_links():
 links=pd.concat([pd.read_csv(ROOT/'data'/name,dtype={'franchise_id':str,'previous_id':str}) for name in ['predecessors.csv','predecessors_2026.csv']],ignore_index=True)
 for c in ['franchise_id','previous_id']:links[c]=links[c].str.zfill(4)
 if links.duplicated(['season','franchise_id']).any():raise ValueError('Duplicate predecessor mapping')
 return links

def fit_means(history,current,year,week,links):
 """Fit both remaining-PPG targets on earlier seasons only; impute from training."""
 hist=history[(history.season<year)&(history.season>=2021)&(history.week<=12)]
 seen=hist[hist.week<=week].groupby(['season','franchise_id']).potential.mean().rename('current_pot')
 rest=hist[hist.week>week].groupby(['season','franchise_id']).agg(target=('points','mean'),target_pot=('potential','mean'))
 prior=prior_features(history[history.season<year],links)
 train=pd.concat([seen,rest],axis=1).reset_index().merge(prior,on=['season','franchise_id'],how='left')
 test=current.groupby('franchise_id').potential.mean().rename('current_pot').reset_index();test['season']=year
 test=test.merge(prior,on=['season','franchise_id'],how='left').sort_values('franchise_id')
 if len(train)<32 or len(test)!=32:raise ValueError('Insufficient model training/current teams')
 x=train[FEATURES].to_numpy();z=test[FEATURES].to_numpy();mean=np.nanmean(x,axis=0)
 if not np.isfinite(mean).all():raise ValueError('Missing training feature')
 x=np.where(np.isnan(x),mean,x);z=np.where(np.isnan(z),mean,z);sd=x.std(0);sd[sd==0]=1
 X=np.column_stack([np.ones(len(x)),(x-mean)/sd]);Z=np.column_stack([np.ones(len(z)),(z-mean)/sd])
 beta=np.linalg.lstsq(X.T@X,X.T@train[['target','target_pot']].to_numpy(),rcond=None)[0]
 pred=Z@beta;pred[:,0]=np.maximum(pred[:,0],0);pred[:,1]=np.maximum(pred[:,1],pred[:,0])
 return pred,dict(training_rows=len(train),training_years=sorted(int(y) for y in train.season.unique()),features=FEATURES,coefficients=beta.tolist(),feature_means=mean.tolist(),feature_sd=sd.tolist())

def fetch_current(week):
 league=export('league');schedule=export('schedule');players=export('players')['player']
 positions={p['id']:p['position'] for p in players}
 divmap={d['id']:d['conference'] for d in league['divisions']['division']}
 meta=sorted(league['franchises']['franchise'],key=lambda f:f['id']);ids=[f['id'] for f in meta]
 if len(ids)!=32 or len(set(ids))!=32 or int(league['lastRegularSeasonWeek'])!=12:raise ValueError('Unexpected FAFL structure')
 opp=np.full((12,32),-1,int)
 for w in schedule['weeklySchedule']:
  k=int(w['week'])-1
  if k not in range(12):continue
  for game in w['matchup']:
   a,b=[ids.index(f['id']) for f in game['franchise']];opp[k,a]=b;opp[k,b]=a
 if (opp<0).any():raise ValueError('Incomplete regular-season schedule')
 rows=[]
 for w in range(1,week+1):
  result=export('weeklyResults',W=w)
  for game in result['matchup']:
   for f in game['franchise']:
    starters=[p for p in f.get('player',[]) if p['status']=='starter']
    if not starters:raise ValueError(f'Missing Week {w} lineup')
    actual=float(f['score']);potential=float(f['opt_pts'])
    if abs(sum(float(p.get('score',0)) for p in starters)-actual)>.011:raise ValueError('Lineup total differs from MFL score')
    if any(p['id'] not in positions for p in starters):raise ValueError('Missing starter position')
    defense=sum(float(p.get('score',0)) for p in starters if positions[p['id']] in ['DT','DE','LB','CB','S'])
    if potential+.011<actual:raise ValueError('Potential below actual scoring')
    rows.append(dict(season=SEASON,week=w,franchise_id=f['id'],points=actual,potential=potential,off=actual-defense,deff=defense))
 current=pd.DataFrame(rows)
 if len(current)!=32*week or current.duplicated(['week','franchise_id']).any():raise ValueError('Incomplete current results')
 return meta,divmap,opp,current

def forecast(history,current,meta,divmap,opp,week,n_sims=3000):
 ids=[f['id'] for f in meta];conf=[np.array([i for i,f in enumerate(meta) if divmap[f['division']]==c]) for c in ['00','01']]
 div=[np.array([i for i,f in enumerate(meta) if f['division']==d]) for d in sorted(divmap)]
 assert all(len(x)==16 for x in conf) and all(len(x)==4 for x in div)
 actual=current.pivot(index='week',columns='franchise_id',values='points')[ids].to_numpy()
 pot=current.pivot(index='week',columns='franchise_id',values='potential')[ids].to_numpy()
 today=fafl_outcomes(actual[None],pot[None],opp[:week],conf,div)
 details={'training_years':list(range(2021,SEASON))}
 if week==12:
  q,dw,seed,wins,ap,credits=today;mu=actual.mean(0);pmu=pot.mean(0)
 else:
  pred,details=fit_means(history,current,SEASON,week,load_links());mu,pmu=pred.T
  past=history[(history.season>=2021)&(history.season<SEASON)&(history.week<=12)].groupby(['season','franchise_id']).points.std().to_numpy()
  obs=actual.std(0,ddof=1) if week>1 else np.array([]);sigma=np.nanmean(np.concatenate([past,obs]))
  rng=np.random.default_rng(SEASON*100+week);future=np.maximum(0,mu[None,None,:]+rng.normal(size=(n_sims,12-week,32))*sigma)
  scores=np.concatenate([np.broadcast_to(actual,(n_sims,week,32)),future],axis=1)
  potentials=np.concatenate([np.broadcast_to(pot,(n_sims,week,32)),future+(pmu-mu)],axis=1)
  q,dw,seed,wins,ap,credits=fafl_outcomes(scores,potentials,opp,conf,div)
  details['weekly_sigma']=float(sigma)
 final_points=actual.sum(0)+(12-week)*mu;final_pot=pot.sum(0)+(12-week)*pmu
 _,_,projected=rank_field(wins.mean(0)[None],ap.mean(0)[None],final_points[None],final_pot[None],credits.mean(0)[None],opp,conf,div)
 rows=[];data={'NFC':[],'AFC':[]}
 for i,f in enumerate(meta):
  g=current[current.franchise_id==f['id']];win=float(today[3][0,i]);ties=int((today[5][0,:,i]==.5).sum())
  # Bonus ties contribute half a win; recover each completed bonus result directly.
  for a,b in [(0,3),(3,6),(6,9),(9,12),(0,12)]:
   if b>week:continue
   sub=actual[a:b];pa=((sub[:,:,None]>sub[:,None,:]).sum(-1)+.5*((sub[:,:,None]==sub[:,None,:]).sum(-1)-1)).sum(0)
   order=np.lexsort((-pot[a:b].sum(0),-sub.sum(0),-pa));ties+=int(i in order[15:17])
  games=week+sum(b<=week for a,b in [(0,3),(3,6),(6,9),(9,12),(0,12)])
  w=int(round(win-ties/2));loss=games-w-ties
  name=f['name'];abbr=f['abbrev'];slug={'GBP':'gb','JAC':'jax','KCC':'kc','LAR':'lar','LVR':'lv','NEP':'ne','NOS':'no','SFO':'sf','TBB':'tb','WAS':'wsh'}.get(abbr,abbr.lower())
  playoff=float(q[:,i].mean());division=float(dw[:,i].mean());bye=float((seed[:,i]==1).mean())
  clinch='b' if bye==1 else 'd' if division==1 else 'p' if playoff==1 else 'e' if playoff==0 else ''
  r=dict(franchise_id=f['id'],name=html.escape(name,quote=True),logo=f'https://a.espncdn.com/i/teamlogos/nfl/500/{slug}.png',seed=int(today[2][0,i]),clinch=clinch,qual='y' if today[1][0,i] else 'x' if today[0][0,i] else '',record=f'{w}-{loss}'+(f'-{ties}' if ties else ''),apPct=float(today[4][0,i]/(31*week)),ppg=f'{g.points.mean():.1f}',pot=float(g.potential.mean()),off=float(g.off.mean()),deff=float(g.deff.mean()),wins=float(wins[:,i].mean()),predPct=float(ap[:,i].mean()/372*100),finish=int(projected[0,i]),playoffSeed=str(projected[0,i]) if projected[0,i]<=7 else 'NA',odds=f'{round(playoff*100)}%',div=f'{round(division*100)}%',bye=f'{round(bye*100)}%',playoffProbability=playoff,divisionProbability=division,byeProbability=bye,projectedPotentialPoints=float(final_pot[i]))
  rows.append(r);data['NFC' if divmap[f['division']]=='00' else 'AFC'].append(r)
 for r in rows:
  r['ranks']={}
  for key in ['off','deff','pot']:
   values=np.round([t[key] for t in rows],6);value=round(r[key],6)
   r['ranks'][key]=dict(rank=int(1+(values>value).sum()),tied=bool((values==value).sum()>1))
 for c in data:data[c].sort(key=lambda t:t['seed'])
 return data,details

def render(data,week,status,n_sims,updated):
 template=(ROOT/'scripts/templates/playoff.html').read_text(encoding='utf8')
 out=ROOT/'docs/playoff-picture';out.mkdir(parents=True,exist_ok=True)
 options=''.join(f'<option value="week-{w+1:02}.html"'+(' selected' if w==week else '')+f'>Week {w+1} Outlook</option>' for w in range(1,week+1) if w==week or (out/f'week-{w+1:02}.html').exists())
 dropdown=f'<label>Archive <select aria-label="Weekly report" onchange="location.href=this.value">{options}</select></label>'
 replacements={'__DATA__':json.dumps(data,allow_nan=False).replace('</','<\\/'),'__DRAFT__':'{}','__SHIELD__':'https://www43.myfantasyleague.com/fflnetdynamic2019/22686_league_logo.jpg','__SEASON__':str(SEASON),'__OUTLOOK__':str(week+1),'__WEEK__':str(week),'__STATUS__':status.title(),'__SIMS__':f'{n_sims:,}','__TRAINING__':'2021–2025','__UPDATED__':updated,'__DROPDOWN__':dropdown,'__FULL_FILE__':f'week-{week+1:02}.csv'}
 for k,v in replacements.items():template=template.replace(k,v)
 if week==12:template=template.replace('Week 13 Outlook','Playoff Field')
 page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FAFL Playoff Picture</title><style>:root{color-scheme:light dark}body{margin:0;padding:12px;background:light-dark(#f5f7fa,#151c25)}#fafl-playoff-design{max-width:1100px;margin:auto}a{color:light-dark(#235789,#89bce8)}</style></head><body>'+template+'</body></html>'
 for filename in ['index.html',f'week-{week+1:02}.html']:(out/filename).write_text(page,encoding='utf8')
 flat=[{k:v for k,v in r.items() if k!='ranks'} for c in data.values() for r in c]
 pd.DataFrame(flat).to_csv(out/f'week-{week+1:02}.csv',index=False)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--week',type=int);parser.add_argument('--status',choices=['official','unofficial','reported'],default='reported');parser.add_argument('--simulations',type=int,default=3000);args=parser.parse_args()
 week=args.week if args.week is not None else completed_week()
 if not 1<=week<=12:raise ValueError('No completed regular-season week available')
 if args.simulations<100:raise ValueError('At least 100 simulations required')
 meta,divmap,opp,current=fetch_current(week);data,details=forecast(historical(),current,meta,divmap,opp,week,args.simulations)
 stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC');render(data,week,args.status,args.simulations,stamp)
 payload=dict(season=SEASON,through_week=week,status=args.status,updated_at=stamp,simulations=args.simulations,model=details,conferences=data)
 (ROOT/'data/current_forecast.json').write_text(json.dumps(payload,indent=2,allow_nan=False),encoding='utf8')
 current.to_csv(ROOT/'data/current_weekly.csv',index=False)
 print(f'Built FAFL report through Week {week}: 32 teams, {args.simulations} simulations, {stamp}')

if __name__=='__main__':main()

