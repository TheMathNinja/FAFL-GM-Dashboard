"""Point-in-time same-roster bye losses for F315; no future player projections."""
from pathlib import Path
import argparse,json,urllib.request,time
import numpy as np
import pandas as pd

def many(x):return x if isinstance(x,list) else [x] if x else []
def status_code(value):
 value=(value or '').strip().upper().replace('(','').replace(')','')
 return {'SUSPENDED':'S','OUT':'O','BYE WEEK':'BYE','INJURED RESERVE - DESIGNATED FOR RETURN':'IR-R'}.get(value,value)

def best_lineup(players,limits,totals):
 """Exact legal position-count optimization, independently by lineup group."""
 total=0.
 for group,count in totals.items():
  states={0:0.}
  for pos,(lo,hi,g) in limits.items():
   if g!=group:continue
   values=sorted((float(p['points']) for p in players if p['pos']==pos),reverse=True)
   choices={n:sum(values[:n]) for n in range(lo,min(hi,len(values))+1)};following={}
   for used,score in states.items():
    for n,points in choices.items():
     if used+n<=count:following[used+n]=max(following.get(used+n,float('-inf')),score+points)
   states=following
  if count not in states:raise ValueError('Cannot fill legal lineup even with zero-value placeholders')
  total+=states[count]
 return total

def exposure_matrix(root,season,week,ids):
 d=pd.read_csv(Path(root)/'data/forward_bye_exposure.csv',dtype={'franchise_id':str});d.franchise_id=d.franchise_id.str.zfill(4)
 d=d[(d.season==season)&(d.week==week)]
 if d.duplicated(['target_week','franchise_id']).any():raise ValueError('Duplicate forecast bye exposure')
 x=d.pivot(index='target_week',columns='franchise_id',values='bye_loss').reindex(index=range(week+1,13),columns=ids).to_numpy()
 if x.shape!=(12-week,32) or not np.isfinite(x).all():raise ValueError(f'Missing as-of Week {week} bye exposure; run forecast_byes.py before forecasting')
 return x

def export(kind,season,**kwargs):
 from urllib.parse import urlencode
 params=dict(TYPE=kind,JSON=1,**kwargs)
 if kind not in ['nflSchedule','injuries']:params['L']='22686'
 url=f'https://api.myfantasyleague.com/{season}/export?'+urlencode(params)
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'FAFL-GM-Dashboard/1.0'}),timeout=60) as response:result=json.load(response)
   if 'error' in result:raise ValueError(f'MFL {kind} returned an error')
   return result
  except Exception:
   if attempt==2:raise
   time.sleep(2**attempt)

def calculate(payload,week):
 """All score/status observations stop at week; one roster held fixed forward."""
 players={str(p['id']):p for p in many(payload['players']['players'].get('player'))}
 rule=payload['league']['league']['starters'];limits={}
 for v in many(rule['position']):
  bounds=list(map(int,v['limit'].split('-')));pos=v['name'];limits[pos]=(bounds[0],bounds[-1],'off' if pos in ['QB','RB','WR','TE'] else 'st' if pos in ['PK','PN'] else 'def')
 totals={'off':int(rule.get('iop_starters',7)),'def':int(rule['idp_starters'])};totals['st']=int(rule['count'])-sum(totals.values())
 nfl=payload['nfl'];nfl=nfl.get('fullNflSchedule',nfl);played={int(v['week']):{t['id'] for game in many(v.get('matchup')) for t in many(game.get('team'))} for v in many(nfl['nflSchedule'])}
 if any(w not in played for w in range(1,13)):raise ValueError('Missing NFL bye schedule')
 pre={str(p['id']):float(p['score']) for p in many(payload['preseason']['projectedScores'].get('playerScore')) if p.get('score') not in [None,'']}
 samples={}
 for w in range(1,week+1):
  flags={str(p['id']):status_code(p.get('status')) for p in many(payload['injuries'][str(w)]['injuries'].get('injury'))}
  for p in many(payload['scores'][str(w)]['playerScores'].get('playerScore')):
   pid=str(p['id']);score=float(p.get('score') or 0);team=players.get(pid,{}).get('team')
   if score!=0 or (flags.get(pid,'') not in {'S','O','IR','IR-R'} and team in played[w]):samples.setdefault(pid,[]).append(score)
 output=[]
 for franchise in many(payload['rosters']['rosters']['franchise']):
  roster=[]
  for item in many(franchise.get('player')):
   pid=str(item['id']);p=players.get(pid,{})
   if p.get('position') not in limits or item.get('status','ROSTER') not in ['ROSTER','']:continue
   observed=samples.get(pid,[]);ppg=float(np.mean(observed)) if observed else 0.
   estimate=(2*pre.get(pid,ppg)+len(observed)*ppg)/(2+len(observed))
   roster.append(dict(id=pid,pos=p['position'],points=max(0,estimate),team=p.get('team')))
  for pos,(_,hi,_) in limits.items():
   roster.extend(dict(id=f'vac_{pos}_{k}',pos=pos,points=0.,team='VAC') for k in range(hi))
  full=best_lineup(roster,limits,totals)
  for target in range(week+1,13):
   active=[{**p,'points':p['points'] if p['team'] in played[target] else 0.} for p in roster]
   output.append(dict(season=payload['season'],week=week,target_week=target,franchise_id=str(franchise['id']).zfill(4),bye_loss=full-best_lineup(active,limits,totals)))
 return pd.DataFrame(output)

def refresh(root,season,week,force=False):
 root=Path(root);path=root/'data/forward_bye_exposure.csv';d=pd.read_csv(path,dtype={'franchise_id':str});cache=root/'data/forecast_bye_inputs'/str(season);cache.mkdir(parents=True,exist_ok=True)
 common=None
 for w in range(1,min(week,11)+1):
  exists=((d.season==season)&(d.week==w)).any()
  if exists and not (force and w==min(week,11)):continue
  saved=cache/f'through-week-{w:02}.json'
  payload=json.loads(saved.read_text(encoding='utf8')) if saved.exists() and not (force and w==min(week,11)) else None
  if payload and any('error' in payload.get(k,{}) for k in ['league','players','nfl','preseason','rosters']):payload=None
  if payload is None:
   if common is None:common={k:export(kind,season,**params) for k,kind,params in [('league','league',{}),('players','players',{}),('nfl','nflSchedule',{'W':'ALL'}),('preseason','projectedScores',{'W':1})]}
   payload=dict(common,season=season,through_week=w,rosters=export('rosters',season,**({} if force and w==min(week,11) else {'W':w})),scores={},injuries={})
   for j in range(1,w+1):payload['scores'][str(j)]=export('playerScores',season,W=j);payload['injuries'][str(j)]=export('injuries',season,W=j)
   saved.write_text(json.dumps(payload,separators=(',',':')),encoding='utf8')
  rows=calculate(payload,w)
  if len(rows)!=(12-w)*32:raise ValueError('Incomplete roster-based forecast bye exposures')
  d=pd.concat([d[~((d.season==season)&(d.week==w))],rows],ignore_index=True)
 d=d.sort_values(['season','week','target_week','franchise_id']);d.to_csv(path,index=False)
 print('Updated point-in-time forecast bye exposures through',week)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--season',type=int,default=2026);p.add_argument('--week',type=int);p.add_argument('--refresh-current',action='store_true');a=p.parse_args()
 if a.week is None:a.week=int(json.loads((a.root/'data/weekly_source_context.json').read_text())['week'])
 refresh(a.root,a.season,a.week,a.refresh_current)
