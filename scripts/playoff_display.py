"""Shared playoff display fields; no fitting or simulation is performed here."""
import copy, math

def number(value):
 try:
  result=float(value)
  return result if math.isfinite(result) else None
 except (TypeError,ValueError):return None

def display_payload(data,week,weekly=(),projected_ppg=None):
 data=copy.deepcopy(data);projected_ppg=projected_ppg or {}
 if hasattr(weekly,'to_dict'):weekly=weekly.to_dict('records')
 actual={(str(r['franchise_id']).zfill(4),int(r['week'])):r for r in weekly if int(r['week'])<=week}
 for rows in data.values():
  for t in rows:
   fid=t['franchise_id'];mean=number(projected_ppg.get(fid))
   t.setdefault('rosterStrength',None);t.setdefault('rosterStrengthRank',None)
   if mean is not None and week<12:
    t.setdefault('projectedPPG',mean)
    current=number(t.get('pointsTotal'))
    if current is not None:t.setdefault('projectedPoints',current+(12-week)*mean)
   for g in t.get('actualDetails',{}).get('weeks',[]):
    source=actual.get((fid,int(g['week'])));score=number(g.get('points'))
    # Never mix a revised score row into an older frozen outlook.
    if source and score is not None and number(source.get('points')) is not None and abs(float(source['points'])-score)<.011:
     potential=number(source.get('potential'))
     if potential is not None:g.setdefault('potentialPoints',potential)
 draft={}
 for conf,rows in data.items():
  current=sorted(rows,key=lambda t:(int(t['seed'])<=7,float(t['pot']) if int(t['seed'])>7 else -int(t['seed'])))
  projected=sorted(rows,key=lambda t:(int(t['finish'])<=7,float(t['projectedPotentialPoints']) if int(t['finish'])>7 else -int(t['finish'])))
  current_order={t['franchise_id']:i+1 for i,t in enumerate(current)};projected_order={t['franchise_id']:i+1 for i,t in enumerate(projected)}
  draft[conf]=[]
  for t in rows:
   fid=t['franchise_id'];division=str(t.get('division',''))
   try:division=['East','North','South','West'][int(division)%4]
   except ValueError:pass
   group=[r for r in rows if r.get('division')==t.get('division')]
   draft[conf].append(dict(franchise_id=fid,name=t['name'],logo=t['logo'],currentPick=current_order[fid],pick=projected_order[fid],playoffSeed=t['playoffSeed'],currentPlayoffSeed=str(t['seed']) if int(t['seed'])<=7 else 'NA',currentAdjWins=t['winDetails']['currentWins'],projectedAdjWins=t['wins'],currentApPct=t['apPct'],projectedApPct=t['predPct']/100,currentDivisionRank=1+sum(int(r['seed'])<int(t['seed']) for r in group),projectedDivisionRank=1+sum(int(r['finish'])<int(t['finish']) for r in group),division=division,currentPoints=t['pointsTotal'],projectedPoints=t.get('projectedPoints'),currentPotentialPPG=t['pot'],projectedPotentialPPG=t['projectedPotentialPoints']/12,currentPotential=t['potentialPointsTotal'],potential=t['projectedPotentialPoints']))
 return data,draft
