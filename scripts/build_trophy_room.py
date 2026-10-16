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
    lineups=json.loads((ROOT/'data/trophy_room/super_bowl_lineups.json').read_text(encoding='utf8'))
    assert len(champions)==len({r['season'] for r in history})
    assert {c['year'] for c in champions}=={r['season'] for r in history}=={int(y) for y in lineups}
    for c in champions:
        rows=[r for r in history if r['season']==c['year']]
        champion=next(r for r in rows if r['finish']==1);runner=next(r for r in rows if r['finish']==2)
        game=lineups[str(c['year'])]
        assert [t['franchise'] for t in game['teams']]==[champion['name'],runner['name']]==[c['champion'],c['runner']]
        assert c['score']==' - '.join(f'{t["total"]:.1f}' for t in game['teams'])
        for side,row in [('champion',champion),('runner',runner)]:
            c[side+'Record']='-'.join(str(row['record_'+k]) for k in ['wins','losses','ties'])
        c['gm']=' / '.join(people(champion['gm']))
    result=dict(completedThrough=max(r['season'] for r in history),rosterSeason=roster['season'],champions=sorted(champions,key=lambda c:-c['year']),owners=owners,payouts=sorted(payouts.values(),key=lambda p:p['year']))
    output=ROOT/'docs/trophy-room/data.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'docs/trophy-room/lineups.json').write_bytes((ROOT/'data/trophy_room/super_bowl_lineups.json').read_bytes())
    roster_files=list((ROOT/'data/trophy_room/rosters').glob('*.json'))
    assert {p.stem for p in roster_files}=={str(c['year']) for c in champions}
    roster_dir=ROOT/'docs/trophy-room/rosters';roster_dir.mkdir(exist_ok=True)
    for p in roster_files:(roster_dir/p.name).write_bytes(p.read_bytes())
    print(f'Trophy Room: {len(champions)} seasons, {len(owners)} GM rows, {len(history)} canonical team-seasons')
    return result
if __name__=='__main__':build()


