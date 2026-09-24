"""Publish one validated FAFL snapshot to Google and read official Elo back."""
from datetime import datetime, timezone
from pathlib import Path
import json, os, time
import gspread
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
ELO_ID='1yWEzFx8hKhhlTQ47gacHSQXmZtPsX9k7hB2s6D6-g3k'
BONUS_ID='1X5DJD6K2mAL93DpPtHshVnOo4f_mJRc1CE2phcTFnTE'
BLOCKS={'OPF':(36,37,1,'off'),'DPF':(36,37,20,'deff'),'PPF':(36,37,39,'potential')}

def column_name(index):
 out=''
 while index:
  index,rem=divmod(index-1,26);out=chr(65+rem)+out
 return out

credentials=json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
client=gspread.service_account_from_dict(credentials)
elo=client.open_by_key(ELO_ID).worksheet('2026')
bonus=client.open_by_key(BONUS_ID).worksheet('Alphabetical')
scores=pd.read_csv(ROOT/'data/current_weekly.csv',dtype={'franchise_id':str})
context=json.loads((ROOT/'data/weekly_source_context.json').read_text(encoding='utf8'))
name_by_id={str(f['id']).zfill(4):f['name'] for f in context['meta']}
scores['franchise_id']=scores.franchise_id.map(lambda x:str(x).zfill(4))
scores['franchise_name']=scores.franchise_id.map(name_by_id)
week=int(scores.week.max())
if len(scores)!=32*week or scores.duplicated(['week','franchise_id']).any():raise ValueError('Validated FAFL snapshot is incomplete')

for metric,(header_row,data_row,name_col,value_col) in BLOCKS.items():
 headers=elo.row_values(header_row)
 labels=[f'W{w}{metric}' for w in range(1,18)]
 start=headers.index(labels[0])+1
 if headers[start-1:start+16]!=labels:raise ValueError(f'Unexpected {metric} workbook headers')
 names=elo.get(f'{column_name(name_col)}{data_row}:{column_name(name_col)}{data_row+31}',value_render_option='FORMATTED_VALUE')
 names=[r[0] if r else '' for r in names]
 values=[]
 for name in names:
  team=scores[scores.franchise_name==name]
  values.append([float(team.loc[team.week==w,value_col].iloc[0]) for w in range(1,week+1)])
 elo.update(values,range_name=f'{column_name(start)}{data_row}',value_input_option='RAW')

bonus_names=[r[0] if r else '' for r in bonus.get('A3:A34')]
bonus_values=[[float(scores[(scores.franchise_name==name)&(scores.week==w)].points.iloc[0]) for w in range(1,week+1)] for name in bonus_names]
bonus.update(bonus_values,range_name='BW3',value_input_option='RAW')

headers=elo.row_values(1)
labels=[f'W{w}Elo' for w in range(0,week+1)]
cols=[headers.index(label)+1 for label in labels]
team_names=[r[0] if r else '' for r in elo.get('A2:A33')]
official=None
for _ in range(12):
 parts=[]
 for w,col in enumerate(cols):
  raw=elo.get(f'{column_name(col)}2:{column_name(col)}33',value_render_option='UNFORMATTED_VALUE')
  vals=[float(r[0]) if r and isinstance(r[0],(int,float)) else np.nan for r in raw]
  parts.extend(dict(season=2026,week=w,franchise_name=n,elo=v) for n,v in zip(team_names,vals))
 candidate=pd.DataFrame(parts)
 if np.isfinite(candidate.elo).all():official=candidate;break
 time.sleep(5)
if official is None:raise ValueError('Google Elo formulas did not recalculate completely')

shadow=pd.read_csv(ROOT/'data/elo_shadow_ratings.csv')
comparison=official.merge(shadow[['season','week','franchise_name','elo']],on=['season','week','franchise_name'],how='left',suffixes=('_sheet','_shadow'))
comparison['absolute_difference']=(comparison.elo_sheet-comparison.elo_shadow).abs()
comparison['within_tolerance']=comparison.absolute_difference.le(.001)
comparison.to_csv(ROOT/'data/elo_shadow_comparison.csv',index=False)
official_output=shadow.drop(columns=['elo']).merge(official,on=['season','week','franchise_name'],how='right')
official_output.to_csv(ROOT/'data/elo_ratings.csv',index=False)
pd.DataFrame([dict(league='FAFL',season=2026,through_week=week,source_rows=len(scores),official_elo_rows=len(official),shadow_mismatches=int((~comparison.within_tolerance).sum()),synced_at=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))]).to_csv(ROOT/'data/google_weekly_sync_metadata.csv',index=False)
print(f'FAFL workbook Elo published through Week {week}; shadow mismatches: {(~comparison.within_tolerance).sum()}')
