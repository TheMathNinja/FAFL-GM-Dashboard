"""Shared FAFL weekly calculations derived from one validated MFL snapshot."""
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SEASON=2026
ELO_CONFIG={
 2026:dict(base=10.0,scale=400.0,weights=np.array([0.3153683886,0.3527872871,0.3318443243]),
           k=np.array([1.814857758,2.64520699,2.035659131,1.585434349,1.280374471,
                       1.106321326,1.049116739,1.094602538,1.228620551,1.437012603,
                       1.705620523,2.020286138,2.366851274,2.731157759,3.099047419,
                       3.456362083,3.788943577]))
}

def all_play(values):
 values=np.asarray(values,float)
 return (values[:,None]>values[None,:]).sum(1)+.5*((values[:,None]==values[None,:]).sum(1)-1)

def expected_all_play(ratings,base,scale):
 strength=base**(np.asarray(ratings,float)/scale)
 return (strength[:,None]/(strength[:,None]+strength[None,:])).sum(1)-.5

def calculate_elo(current,season=SEASON,seed_path=None):
 if season not in ELO_CONFIG:raise ValueError(f'No reviewed FAFL Elo configuration for {season}')
 cfg=ELO_CONFIG[season];seed_path=seed_path or ROOT/'data'/f'elo_seed_{season}.csv'
 seed=pd.read_csv(seed_path);seed_names=seed.franchise_name.tolist()
 if len(seed)!=32 or seed.franchise_name.duplicated().any() or not np.isfinite(seed.elo).all():
  raise ValueError('FAFL Elo seed must contain 32 distinct finite ratings')
 ratings=seed.set_index('franchise_name').elo.astype(float)
 output=[pd.DataFrame(dict(season=season,week=0,franchise_name=seed_names,elo=ratings.loc[seed_names].to_numpy()))]
 for week in sorted(current.week.unique()):
  frame=current[current.week==week].copy()
  if len(frame)!=32:raise ValueError(f'Incomplete FAFL Week {week} Elo inputs')
  frame=frame.set_index('franchise_name').loc[seed_names].reset_index()
  frame['composite']=frame[['off','deff','potential']].to_numpy()@cfg['weights']
  frame['adjusted_all_play']=all_play(frame.composite)
  frame['actual_all_play']=all_play(frame.points)
  frame['expected_all_play']=expected_all_play(ratings.loc[seed_names],cfg['base'],cfg['scale'])
  frame['k']=cfg['k'][int(week)-1]
  frame['elo']=ratings.loc[seed_names].to_numpy()+frame.k*(frame.adjusted_all_play-frame.expected_all_play)
  ratings=pd.Series(frame.elo.to_numpy(),index=frame.franchise_name)
  output.append(frame.assign(season=season)[['season','week','franchise_name','elo','off','deff','potential','composite','adjusted_all_play','actual_all_play','expected_all_play','k']])
 result=pd.concat(output,ignore_index=True)
 if len(result[result.week==current.week.max()])!=32:raise ValueError('Latest FAFL Elo output is incomplete')
 return result

def calculate_bonus_games(current,meta):
 names={str(f['id']).zfill(4):f['name'] for f in meta};d=current.copy();d.franchise_id=d.franchise_id.astype(str).str.zfill(4)
 events=[]
 for label,a,b in [('Q1',1,3),('Q2',4,6),('Q3',7,9),('Q4',10,12),('Season',1,12)]:
  if int(d.week.max())<b:continue
  segment=d[d.week.between(a,b)]
  ids=sorted(names);scores=segment.pivot(index='week',columns='franchise_id',values='points')[ids].to_numpy()
  potential=segment.groupby('franchise_id').potential.sum().reindex(ids).to_numpy();points=scores.sum(0)
  ap=np.vstack([all_play(row) for row in scores]).sum(0)
  order=np.lexsort((-potential,-points,-ap));result=np.zeros(32);result[order[:15]]=1;result[order[15:17]]=.5
  events.extend(dict(season=SEASON,event=label,start_week=a,end_week=b,franchise_id=i,
                     franchise_name=names[i],all_play=ap[j],points=points[j],potential=potential[j],bonus_result=result[j])
                for j,i in enumerate(ids))
 return pd.DataFrame(events,columns=['season','event','start_week','end_week','franchise_id','franchise_name','all_play','points','potential','bonus_result'])

def write_weekly_outputs(current,meta,season=SEASON):
 current=current.copy();names={str(f['id']).zfill(4):f['name'] for f in meta};current.franchise_id=current.franchise_id.astype(str).str.zfill(4)
 current['franchise_name']=current.franchise_id.map(names)
 if current.franchise_name.isna().any() or len(current)!=32*int(current.week.max()):raise ValueError('Shared FAFL snapshot is incomplete')
 elo=calculate_elo(current,season);bonus=calculate_bonus_games(current,meta);data=ROOT/'data';data.mkdir(exist_ok=True)
 elo.to_csv(data/'elo_ratings.csv',index=False);bonus.to_csv(data/'bonus_games.csv',index=False)
 metadata=dict(season=season,through_week=int(current.week.max()),teams=32,team_week_rows=len(current),elo_rows=len(elo),
               bonus_events=int(bonus.event.nunique()) if len(bonus) else 0,refreshed_at=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))
 (data/'weekly_system_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
 return elo,bonus,metadata
