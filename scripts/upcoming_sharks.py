"""Fresh lineup-known calibrated Sharks input for the shared FAFL team engine."""
from pathlib import Path
import datetime as dt
import numpy as np
import pandas as pd

def apply(root,season,week,ids,mu):
 path=Path(root)/'data/weekly_sharks_team_means.csv'
 q=pd.read_csv(path,dtype={'franchise_id':str});q=q[(q.season==season)&(q.target_week==week+1)]
 if q.franchise_id.duplicated().any():raise ValueError('Duplicate weekly Sharks team input')
 values=q.set_index('franchise_id').reindex(ids).sharks_mean.to_numpy()
 if not np.isfinite(values).all():raise ValueError(f'Missing calibrated Sharks team inputs for {season} week {week+1}')
 result=np.asarray(mu).copy();result[0]=.5*(result[0]+values)
 return result

def refresh(root,season,target_week):
 from build_weekly_matchups import MatchupCollector
 from collect_live_bonus import many,franchises,player_projection
 from player_availability import weekly_metadata
 from fs_pregame_calibration import load_calibration
 root=Path(root);collector=MatchupCollector('FAFL',season)
 feed=collector.get('liveScoring',f'&W={target_week}&DETAILS=1',ttl=0)
 if int(feed.get('week',-1))!=target_week:raise ValueError('MFL has not supplied the requested upcoming-week lineup feed')
 clubs=franchises(feed)
 if len(clubs)!=32:raise ValueError('Incomplete upcoming-week franchise feed')
 metadata={p['id']:p for p in many(collector.get('players','&DETAILS=1',ttl=21600).get('player'))}
 metadata=weekly_metadata(collector,metadata,target_week)
 fs=collector.get('projectedScores',f'&W={target_week}',ttl=0)
 if int(fs.get('week',target_week))!=target_week:raise ValueError('Wrong Sharks projection week')
 projections={p['id']:p.get('score') for p in many(fs.get('playerScore'))};available=sum(v not in [None,''] for v in projections.values())>=100
 if not available:raise ValueError('Weekly Sharks feed incomplete; retaining prior published forecast')
 total={};count={}
 for w in range(1,target_week):
  scores=collector.get('playerScores',f'&W={w}&COUNT=10000',ttl=300)
  for p in many(scores.get('playerScore')):
   if p.get('score') not in [None,'']:
    pid=p['id'];total[pid]=total.get(pid,0)+float(p['score']);count[pid]=count.get(pid,0)+1
 ytd={pid:total[pid]/count[pid] for pid in count};cal=load_calibration('FAFL');games=collector.game_states(target_week);rows=[]
 # Reset all players to pregame: no live score/clock can enter the pregame mean.
 for fid,club in sorted(clubs.items()):
  starters=[p for p in many(club.get('players',{}).get('player')) if p.get('status')=='starter'];value=0.
  if not starters:raise ValueError('No submitted starters for '+fid+'; retaining prior published forecast')
  for p in starters:
   row=player_projection({**p,'score':0,'gameSecondsRemaining':3600},metadata,projections,{},ytd,cal,available)
   row.update(score=0.,gameStatus='Pregame' if row['nflTeam'] in games else 'Bye',seconds=3600 if row['nflTeam'] in games else 0,projectionSeconds=3600 if row['nflTeam'] in games else 0,nflScoreboard=[])
   from live_continuous_nig import projected_points
   value+=projected_points(row,cal['conditionalLiveModel'])
  rows.append(dict(season=season,target_week=target_week,franchise_id=str(fid).zfill(4),sharks_mean=value))
 path=root/'data/weekly_sharks_team_means.csv';old=pd.read_csv(path,dtype={'franchise_id':str}) if path.exists() else pd.DataFrame(columns=rows[0]);old=old[~((old.season==season)&(old.target_week==target_week))];pd.concat([old,pd.DataFrame(rows)],ignore_index=True).to_csv(path,index=False)
 print('Refreshed calibrated Sharks starter means',season,target_week,len(rows),dt.datetime.now(dt.timezone.utc).isoformat(),flush=True)
