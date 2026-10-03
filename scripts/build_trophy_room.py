"""Build Trophy Room from the same canonical season history as GM profiles."""
import json
from pathlib import Path
from collections import defaultdict, Counter
from gm_profiles import GM_ALIASES, _career_rows, _normalized

ROOT=Path(__file__).resolve().parents[1]
canonical={}
for row in sorted(json.loads((ROOT/'data/gm_career_seasons.json').read_text()),key=lambda r:r['season']):
    for name in row['gm'].split(','):canonical[_normalized(name)]=name.strip()
for row in json.loads((ROOT/'data/current_gms_2026.json').read_text())['profiles'].values():
    for name in row['gm'].split(','):canonical[_normalized(name)]=name.strip()
for name,aliases in GM_ALIASES.items():
    canonical[_normalized(name)]=name
    for alias in aliases:canonical[_normalized(alias)]=name
def people(value):
    return sorted(set(canonical[_normalized(p)] for p in value.split(',') if p.strip()))

def majority_franchise(rows, active):
    if active:
        return active[0]
    renamed={'Oakland Raiders':'Las Vegas Raiders','San Diego Chargers':'Los Angeles Chargers','Washington Redskins':'Washington Commanders','Washington Football Team':'Washington Commanders','St. Louis Rams':'Los Angeles Rams'}
    identity=lambda r:renamed.get(r['name'],r['name'])
    counts=Counter(map(identity,rows))
    tied={team for team,count in counts.items() if count==max(counts.values())}
    return max((r for r in rows if identity(r) in tied),key=lambda r:r['season'])['name']
def build():
    history=json.loads((ROOT/'data/gm_career_seasons.json').read_text())
    roster=json.loads((ROOT/'data/current_gms_2026.json').read_text())
    current=roster['profiles']; groups=defaultdict(list)
    names=sorted({p for r in history for p in people(r['gm'])}|{p for r in current.values() for p in people(r['gm'])})
    for person in names:
        rows=[r for r in history if person in people(r['gm'])]
        active=[team for team,r in current.items() if person in people(r['gm'])]
        assert len(active)<=1
        key=(tuple(sorted((r['season'],r['franchise_id']) for r in rows)),tuple(active))
        groups[key].append(person)
    owners=[]
    for (_,active),members in groups.items():
        rows=sorted([r for r in history if members[0] in people(r['gm'])],key=lambda r:r['season'])
        assert len({r['season'] for r in rows})==len(rows)
        pct=lambda r:(r['wins']+.5*r['ties'])/(r['wins']+r['losses']+r['ties'])
        record=lambda rs:'-'.join(str(sum(r['record_'+k] for r in rs)) for k in ('wins','losses','ties'))
        owners.append(dict(owner=' / '.join(members),members=members,franchise=majority_franchise(rows,active),active=bool(active),years=[r['season'] for r in rows],seasons=len(rows),record=record(rows),allTimeAllPlay=sum(map(pct,rows))/len(rows) if rows else None,wins=sum(r['wins'] for r in rows),losses=sum(r['losses'] for r in rows),ties=sum(r['ties'] for r in rows),history=[dict(year=r['season'],franchise=r['name'],record=record([r]),rs=(r['rs_wins']+.5*r['rs_ties'])/372,all=pct(r),finish=r['finish']) for r in rows]))
    payouts=json.loads((ROOT/'data/trophy_room/payouts.json').read_text())
    codes='DAL NYG PHI WAS CHI DET GBP MIN ATL CAR NOS TBB ARI SFO SEA LAR BUF MIA NEP NYJ BAL CIN CLE PIT HOU IND JAC TEN DEN KCC LVR LAC'.split()
    for year,p in payouts.items():
        p['year']=int(year)
        codes='DAL NYG PHI WAS CHI DET GBP MIN ATL CAR NOS TBB ARI SFO SEA LAR BUF MIA NEP NYJ BAL CIN CLE PIT HOU IND JAC TEN DEN KCC LVR LAC'.split() if int(year)<=2022 else 'DAL NYG PHI WAS CHI DET GBP MIN ATL CAR NOS TBB ARI LAR SFO SEA BUF MIA NEP NYJ BAL CIN CLE PIT HOU IND JAC TEN DEN KCC LVR LAC'.split()
        for t in p['teams']:
            r=next(r for r in history if r['season']==int(year) and int(r['franchise_id'])==codes.index(t['team'])+1)
            t.update(franchise=r['name'],gm=' / '.join(people(r['gm'])),finish=r['finish'])
    champions=json.loads((ROOT/'data/trophy_room/champions.json').read_text())
    for c in champions:c['gm']=' / '.join(people(c['gm']))
    result=dict(completedThrough=max(r['season'] for r in history),rosterSeason=roster['season'],champions=sorted(champions,key=lambda c:-c['year']),owners=owners,payouts=sorted(payouts.values(),key=lambda p:p['year']))
    output=ROOT/'docs/trophy-room/data.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(f'Trophy Room: {len(champions)} seasons, {len(owners)} GM rows, {len(history)} canonical team-seasons')
    return result
if __name__=='__main__':build()


