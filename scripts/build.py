"""FAFL 2026 playoff forecast. Run from the repository root."""
import argparse,json,html,os,time,urllib.request
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from rules import fafl_outcomes,rank_field,orderkeys
from weekly_system import calculate_elo,calculate_bonus_games

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
 return min(17,max(0,(today-first_tuesday).days//7+1))

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

def fit_means(history,current,year,week,links,train_years=None,excluded_years=None):
 """Fit both remaining-PPG targets on earlier seasons only; impute from training."""
 if train_years is None:train_years=sorted(history.loc[(history.season<year)&(history.season>=2021),'season'].unique())
 prior_history=history[history.season<year] if excluded_years is None else history[~history.season.isin(excluded_years)]
 hist=history[history.season.isin(train_years)&(history.week<=12)]
 seen=hist[hist.week<=week].groupby(['season','franchise_id']).potential.mean().rename('current_pot')
 rest=hist[hist.week>week].groupby(['season','franchise_id']).agg(target=('points','mean'),target_pot=('potential','mean'))
 prior=prior_features(prior_history,links)
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

def strength_uncertainty(history,year,week,links):
 """Historical held-out-season mean error, net of weekly noise; no extra taper."""
 if week>=12:return 0.0
 hist=history[history.season<year]
 seasons=tuple(sorted(hist.loc[(hist.season>=2021)&(hist.week==12),'season'].unique()))
 if len(seasons)<2:return 0.0
 errors=[];noise=[]
 for held in seasons:
  train=tuple(y for y in seasons if y!=held)
  current=hist[(hist.season==held)&(hist.week<=week)]
  means,_=fit_means(hist,current,held,week,links,train,(held,))
  actual=hist[(hist.season==held)&hist.week.between(week+1,12)].groupby('franchise_id').points.mean().sort_index().to_numpy()
  if len(actual)!=32:raise ValueError('Incomplete strength-uncertainty history')
  error=actual-means[:,0];errors.extend(error-error.mean())
  past=hist[hist.season.isin(train)&(hist.week<=12)].groupby(['season','franchise_id']).points.std().to_numpy()
  observed=current.groupby('franchise_id').points.std().to_numpy() if week>1 else np.array([])
  sigma=np.mean(np.concatenate([past,observed]));noise.append(sigma**2/(12-week))
 return float(np.sqrt(max(0,np.mean(np.square(errors))*32/31-np.mean(noise))))

def draw_future_points(rng,mu,sigma,strength_sd,n_sims,remaining_weeks):
 weekly=rng.normal(size=(n_sims,remaining_weeks,len(mu)))*sigma
 # One offset per team per simulation, retained for every remaining week.
 offset=rng.normal(size=(n_sims,1,len(mu)))*strength_sd
 # MFL reports league scores to one decimal. Preserve that scoring lattice so
 # simulated ties occur naturally and receive the league's half-win credit.
 return np.round(np.maximum(0,mu[None,None,:]+weekly+offset),1)

def fetch_current(week):
 league=export('league');schedule=export('schedule');players=export('players')['player']
 positions={p['id']:p['position'] for p in players}
 divmap={d['id']:d['conference'] for d in league['divisions']['division']}
 meta=sorted(league['franchises']['franchise'],key=lambda f:f['id']);ids=[f['id'] for f in meta]
 if len(ids)!=32 or len(set(ids))!=32 or int(league['lastRegularSeasonWeek'])!=12:raise ValueError('Unexpected FAFL structure')
 opp=np.full((12,32),-1,int);home=np.zeros((12,32),bool)
 for w in schedule['weeklySchedule']:
  k=int(w['week'])-1
  if k not in range(12):continue
  for game in w['matchup']:
   a,b=[ids.index(f['id']) for f in game['franchise']];opp[k,a]=b;opp[k,b]=a
   for f in game['franchise']:home[k,ids.index(f['id'])]=int(f.get('isHome','0'))==1
 if (opp<0).any():raise ValueError('Incomplete regular-season schedule')
 rows=[]
 for w in range(1,week+1):
  result=export('weeklyResults',W=w)
  franchises={f['id']:f for game in result.get('matchup',[]) for f in game['franchise']}
  franchises.update({f['id']:f for f in result.get('franchise',[])})
  for game in [dict(franchise=list(franchises.values()))]:
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
 return meta,divmap,opp,home,current

def forecast(history,current,meta,divmap,opp,home,week,n_sims=3000):
 ids=[f['id'] for f in meta];conf=[np.array([i for i,f in enumerate(meta) if divmap[f['division']]==c]) for c in ['00','01']]
 div=[np.array([i for i,f in enumerate(meta) if f['division']==d]) for d in sorted(divmap)]
 assert all(len(x)==16 for x in conf) and all(len(x)==4 for x in div)
 actual=current.pivot(index='week',columns='franchise_id',values='points')[ids].to_numpy()
 pot=current.pivot(index='week',columns='franchise_id',values='potential')[ids].to_numpy()
 today=fafl_outcomes(actual[None],pot[None],opp[:week],conf,div)
 details={'training_years':list(range(2021,SEASON))}
 scores=actual[None];potentials=pot[None]
 if week==12:
  q,dw,seed,wins,ap,credits=today;mu=actual.mean(0);pmu=pot.mean(0)
 else:
  pred,details=fit_means(history,current,SEASON,week,load_links());mu,pmu=pred.T
  past=history[(history.season>=2021)&(history.season<SEASON)&(history.week<=12)].groupby(['season','franchise_id']).points.std().to_numpy()
  obs=actual.std(0,ddof=1) if week>1 else np.array([]);sigma=np.nanmean(np.concatenate([past,obs]))
  tau=strength_uncertainty(history,SEASON,week,load_links())
  rng=np.random.default_rng(SEASON*100+week);future=draw_future_points(rng,mu,sigma,tau,n_sims,12-week)
  scores=np.concatenate([np.broadcast_to(actual,(n_sims,week,32)),future],axis=1)
  potentials=np.concatenate([np.broadcast_to(pot,(n_sims,week,32)),future+(pmu-mu)],axis=1)
  q,dw,seed,wins,ap,credits=fafl_outcomes(scores,potentials,opp,conf,div)
  details['weekly_sigma']=float(sigma)
  details['strength_uncertainty']={'model':'normal_persistent_no_extra_taper','sd':tau,'multiplier':1.0}
 final_points=actual.sum(0)+(12-week)*mu;final_pot=pot.sum(0)+(12-week)*pmu
 projected_q,projected_dw,projected=rank_field(wins.mean(0)[None],ap.mean(0)[None],final_points[None],final_pot[None],credits.mean(0)[None],opp,conf,div)
 ap_week=((scores[:,:,:,None]>scores[:,:,None,:]).sum(-1)+.5*((scores[:,:,:,None]==scores[:,:,None,:]).sum(-1)-1))
 bonus_specs=[('Q1 Bonus Game',0,3),('Q2 Bonus Game',3,6),('Q3 Bonus Game',6,9),('Q4 Bonus Game',9,12),('Regular Season Bonus Game',0,12)]
 bonus_prob={}
 completed_bonus_details={}
 for label,a,b in bonus_specs:
  order=orderkeys(-ap_week[:,a:b].sum(1),-scores[:,a:b].sum(1),-potentials[:,a:b].sum(1))
  bonus=np.zeros((len(scores),32));rr=np.arange(len(scores))[:,None]
  bonus[rr,order[:,:15]]=1;bonus[rr,order[:,15:17]]=.5
  bonus_prob[label]=bonus.mean(0)
  if b<=week:
   ranks=np.empty(32,dtype=int);ranks[order[0]]=np.arange(1,33)
   completed_bonus_details[label]=(ap_week[0,a:b].sum(0),ranks)
 def team_logo(f):
  abbr=f['abbrev'];slug={'GBP':'gb','JAC':'jax','KCC':'kc','LAR':'lar','LVR':'lv','NEP':'ne','NOS':'no','SFO':'sf','TBB':'tb','WAS':'wsh'}.get(abbr,abbr.lower())
  return f'https://a.espncdn.com/i/teamlogos/nfl/500/{slug}.png'
 actual_ap=((actual[:,:,None]>actual[:,None,:]).sum(-1)+.5*((actual[:,:,None]==actual[:,None,:]).sum(-1)-1))
 def record_text(w,l,t):return f'{w}-{l}'+(f'-{t}' if t else '')
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
  name=f['name']
  playoff=float(q[:,i].mean());division=float(dw[:,i].mean());bye=float((seed[:,i]==1).mean())
  clinch='b' if bye==1 else 'd' if division==1 else 'p' if playoff==1 else 'e' if playoff==0 else ''
  matchups=[]
  for k in range(week,12):
   opponent=meta[opp[k,i]]
   matchups.append(dict(week=k+1,opponent=html.escape(opponent['name'],quote=True),opponentLogo=team_logo(opponent),site='v.' if home[k,i] else '@',probability=float(credits[:,k,i].mean())))
  bonus_games=[dict(label=label,week=b,probability=float(bonus_prob[label][i])) for label,a,b in bonus_specs if b>week]
  projected_wins=float(wins[:,i].mean());calculated=win+sum(x['probability'] for x in matchups)+sum(x['probability'] for x in bonus_games)
  if not np.isclose(projected_wins,calculated,atol=1e-9):raise ValueError('Projected-win components do not add to the forecast')
  weeks=[]
  for k in range(week):
   apw=float(actual_ap[k,i]);apl=float(31-apw);ap_ties=int(((actual[k,i]==np.delete(actual[k],i))).sum());ap_wins=int(round(apw-.5*ap_ties));ap_losses=31-ap_wins-ap_ties
   weeks.append(dict(week=k+1,points=float(actual[k,i]),allPlayRecord=record_text(ap_wins,ap_losses,ap_ties),allPlayPct=apw/31))
  played_matchups=[]
  for k in range(week):
   opponent=meta[opp[k,i]];credit=float(today[5][0,k,i])
   played_matchups.append(dict(week=k+1,opponent=html.escape(opponent['name'],quote=True),opponentLogo=team_logo(opponent),opponentAbbr=opponent['abbrev'],site='v.' if home[k,i] else '@',teamScore=float(actual[k,i]),opponentScore=float(actual[k,opp[k,i]]),result='W' if credit==1 else 'T' if credit==.5 else 'L'))
  played_bonuses=[dict(label=label,week=b,allPlayWins=float(completed_bonus_details[label][0][i]),rank=int(completed_bonus_details[label][1][i]),result='W' if bonus_prob[label][i]==1 else 'T' if bonus_prob[label][i]==.5 else 'L') for label,a,b in bonus_specs if b<=week]
  r=dict(pointsTotal=float(g.points.sum()),franchise_id=f['id'],name=html.escape(name,quote=True),logo=team_logo(f),seed=int(today[2][0,i]),clinch=clinch,projectedQual='y' if projected_dw[0,i] else 'x' if projected_q[0,i] else '',qual='y' if today[1][0,i] else 'x' if today[0][0,i] else '',record=f'{w}-{loss}'+(f'-{ties}' if ties else ''),apPct=float(today[4][0,i]/(31*week)),ppg=f'{g.points.mean():.1f}',pot=float(g.potential.mean()),off=float(g.off.mean()),deff=float(g.deff.mean()),wins=projected_wins,predPct=float(ap[:,i].mean()/372*100),finish=int(projected[0,i]),playoffSeed=str(projected[0,i]) if projected[0,i]<=7 else 'NA',odds=f'{round(playoff*100)}%',div=f'{round(division*100)}%',bye=f'{round(bye*100)}%',playoffProbability=playoff,divisionProbability=division,byeProbability=bye,projectedPotentialPoints=float(final_pot[i]),winDetails=dict(currentWins=win,matchups=matchups,bonusGames=bonus_games),actualDetails=dict(weeks=weeks,matchups=played_matchups,bonusGames=played_bonuses))
  h2h=today[5][0,:,i];hw=int((h2h==1).sum());hl=int((h2h==0).sum());ht=int((h2h==.5).sum())
  others=np.delete(actual,i,axis=1);own=actual[:,i,None]
  aw=int((own>others).sum());al=int((own<others).sum());at=int((own==others).sum())
  assert aw+al+at==31*week and aw+.5*at==today[4][0,i]
  potential_others=np.delete(pot,i,axis=1);potential_own=pot[:,i,None]
  pw=int((potential_own>potential_others).sum());pl=int((potential_own<potential_others).sum());pt=int((potential_own==potential_others).sum())
  assert pw+pl+pt==31*week
  r.update(potentialApRecord=record_text(pw,pl,pt),h2hRecord=record_text(hw,hl,ht),bonusRecord=record_text(w-hw,loss-hl,ties-ht),apRecord=record_text(aw,al,at),remainingSos=float(np.mean(today[4][0,opp[week:,i]]/(31*week))*100) if week<12 else None)
  rows.append(r);data['NFC' if divmap[f['division']]=='00' else 'AFC'].append(r)
 for r in rows:
  r['ranks']={}
  for key in ['off','deff','pot']:
   values=np.round([t[key] for t in rows],6);value=round(r[key],6)
   r['ranks'][key]=dict(rank=int(1+(values>value).sum()),tied=bool((values==value).sum()>1))
 for c in data:data[c].sort(key=lambda t:t['seed'])
 return data,details

def render(data,week,status,n_sims,updated,through_week=None,write_index=True):
 from gm_profiles import gm_profiles
 _,_,_,_,career_current,career_week,_=load_source()
 profiles=gm_profiles(ROOT,SEASON,career_week,career_current)
 template=(ROOT/'scripts/templates/playoff.html').read_text(encoding='utf8')
 out=ROOT/'docs/playoff-picture';out.mkdir(parents=True,exist_ok=True)
 through_week=week if through_week is None else through_week
 options=''.join(f'<option value="week-{w+1:02}.html"'+(' selected' if w==week else '')+f'>Week {w+1} Outlook</option>' for w in range(through_week,0,-1))
 dropdown=f'<div class="fafl-outlook-nav"><select aria-label="Weekly outlook" onchange="location.href=this.value">{options}</select></div>'
 replacements={'__GM_PROFILES__':json.dumps(profiles,allow_nan=False).replace('</','<\\/'),'__DATA__':json.dumps(data,allow_nan=False).replace('</','<\\/'),'__DRAFT__':'{}','__SHIELD__':'https://www43.myfantasyleague.com/fflnetdynamic2019/22686_league_logo.jpg','__SEASON__':str(SEASON),'__OUTLOOK__':str(week+1),'__WEEK__':str(week),'__STATUS__':status.lower(),'__SIMS__':f'{n_sims:,}','__TRAINING__':'2021–2025','__UPDATED__':updated,'__DROPDOWN__':dropdown,'__FULL_FILE__':f'week-{week+1:02}.csv'}
 for k,v in replacements.items():template=template.replace(k,v)
 if week==12:template=template.replace('Week 13 Outlook','Playoff Field')
 page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FAFL Playoff Picture</title><style>:root{color-scheme:light dark}body{margin:0;padding:12px;background:light-dark(#f5f7fa,#151c25)}#fafl-playoff-design{max-width:1100px;margin:auto}a{color:light-dark(#235789,#89bce8)}</style></head><body>'+template+'</body></html>'
 filenames=[f'week-{week+1:02}.html']+(['index.html'] if write_index else [])
 for filename in filenames:(out/filename).write_text(page,encoding='utf8')
 flat=[{k:v for k,v in r.items() if k!='ranks'} for c in data.values() for r in c]
 pd.DataFrame(flat).to_csv(out/f'week-{week+1:02}.csv',index=False)

def save_source(meta,divmap,opp,home,current,week,status):
 current.to_csv(ROOT/'data/current_weekly.csv',index=False)
 payload=dict(meta=meta,divmap=divmap,opp=opp.tolist(),home=home.tolist(),week=week,status=status,
              scraped_at=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))
 (ROOT/'data/weekly_source_context.json').write_text(json.dumps(payload,indent=2),encoding='utf8')

def load_source():
 payload=json.loads((ROOT/'data/weekly_source_context.json').read_text(encoding='utf8'))
 current=pd.read_csv(ROOT/'data/current_weekly.csv',dtype={'franchise_id':str})
 current.franchise_id=current.franchise_id.str.zfill(4)
 return payload['meta'],payload['divmap'],np.asarray(payload['opp'],dtype=int),np.asarray(payload['home'],dtype=bool),current,int(payload['week']),payload['status']

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--week',type=int);parser.add_argument('--status',choices=['official','unofficial','reported'],default='reported');parser.add_argument('--simulations',type=int,default=3000);parser.add_argument('--stage',choices=['all','source','elo-shadow','bonus','playoff'],default='all');args=parser.parse_args()
 week=args.week if args.week is not None else int(os.environ['READY_WEEK']) if os.environ.get('READY_WEEK') else completed_week()
 if not 1<=week<=17:raise ValueError('No completed regular-season week available')
 if args.simulations<100:raise ValueError('At least 100 simulations required')
 if args.stage in ['all','source']:
  meta,divmap,opp,home,current=fetch_current(week);current.franchise_id=current.franchise_id.astype(str).str.zfill(4)
  save_source(meta,divmap,opp,home,current,week,args.status)
 else:
  meta,divmap,opp,home,current,week,_=load_source()
 if args.stage=='source':
  print(f'Validated one FAFL MFL snapshot through Week {week}: {len(current)} team-week rows')
  return
 if args.stage in ['all','elo-shadow']:
  names={str(f['id']).zfill(4):f['name'] for f in meta};elo_input=current.copy();elo_input['franchise_name']=elo_input.franchise_id.map(names)
  shadow=calculate_elo(elo_input,SEASON);shadow.to_csv(ROOT/'data/elo_shadow_ratings.csv',index=False)
  if args.stage=='elo-shadow':return
 if args.stage in ['all','bonus']:
  calculate_bonus_games(current,meta).to_csv(ROOT/'data/bonus_games.csv',index=False)
  if args.stage=='bonus':return
 report_week=min(week,12);history=historical();regular=current[current.week<=12]
 stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
 for prior in range(1,report_week):
  prior_data,_=forecast(history,regular[regular.week<=prior],meta,divmap,opp,home,prior,args.simulations)
  render(prior_data,prior,'official',args.simulations,stamp,through_week=report_week,write_index=False)
 data,details=forecast(history,regular,meta,divmap,opp,home,report_week,args.simulations)
 render(data,report_week,args.status,args.simulations,stamp,through_week=report_week)
 payload=dict(season=SEASON,through_week=week,status=args.status,updated_at=stamp,simulations=args.simulations,model=details,conferences=data)
 (ROOT/'data/current_forecast.json').write_text(json.dumps(payload,indent=2,allow_nan=False),encoding='utf8')
 current.to_csv(ROOT/'data/current_weekly.csv',index=False)
 print(f'Built FAFL report through Week {week}: 32 teams, {args.simulations} simulations, {stamp}')

if __name__=='__main__':main()
