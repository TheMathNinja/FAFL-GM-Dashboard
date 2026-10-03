import json,re,hashlib,math,sys,os
from pathlib import Path
import openpyxl
ROOT=Path(__file__).resolve().parents[1]; CACHE=Path(sys.argv[1])
RAW=Path(sys.argv[2])
codes='DAL NYG PHI WAS CHI DET GBP MIN ATL CAR NOS TBB ARI SFO SEA LAR BUF MIA NEP NYJ BAL CIN CLE PIT HOU IND JAC TEN DEN KCC LVR LAC'.split()
norm=lambda x: {'OAK':'LVR','NOR':'NOS','SDC':'LAC','STL':'LAR'}.get(x,x)
history=json.loads((ROOT/'data/gm_career_seasons.json').read_text())
seasons={}; champions=[]; records=[]; metrics=json.loads((ROOT/'data/trophy_room/award_metrics.json').read_text())
arr=lambda x: x if isinstance(x,list) else ([] if x is None else [x])
for year in range(2014,2026):
    h=[r for r in history if r['season']==year]; end=16 if year<2021 else 17
    raw=json.loads((RAW/f'FAFL-{year}-weeklyResults.json').read_text())
    weeks={}
    for w in arr(raw['allWeeklyResults']['weeklyResults']):
        if int(w['week'])>end:continue
        fs=arr(w.get('franchise'))+[f for m in arr(w.get('matchup')) for f in arr(m.get('franchise'))]
        weeks[int(w['week'])]={f['id']:f for f in fs if f['id']!='BYE'}
    assert len(weeks)==end and all(len(w)==32 for w in weeks.values())
    standings=json.loads((CACHE/f'FAFL-{year}-standings.json').read_text())['leagueStandings']['franchise']
    official={f['id']:f for f in standings}
    for r in h:
        own=r['franchise_id']; wins=ties=rsw=rst=0
        for week,fs in weeks.items():
            score=float(fs[own]['score'])
            for fid,f in fs.items():
                if fid==own:continue
                win=score>float(f['score']);tie=score==float(f['score'])
                wins+=win;ties+=tie
                if week<=12:rsw+=win;rst+=tie
        assert (r['wins'],r['losses'],r['ties'])==(wins,end*31-wins-ties,ties),(year,r['name'])
        r.update(rs_wins=rsw,rs_ties=rst,rs_losses=372-rsw-rst)
        for k,m in [('wins','h2hw'),('losses','h2hl'),('ties','h2ht')]:r['record_'+k]=int(official[own][m])
        records.append({k:r[k] for k in ['season','franchise_id','record_wins','record_losses','record_ties']})
    champ=next(r for r in h if r['finish']==1); runner=next(r for r in h if r['finish']==2)
    schedule=json.loads((RAW/f'FAFL-{year}-schedule.json').read_text())['schedule']['weeklySchedule']
    final=[m for w in arr(schedule) if int(w['week'])==end for m in arr(w.get('matchup')) if {f['id'] for f in arr(m['franchise'])}=={champ['franchise_id'],runner['franchise_id']}]
    assert len(final)==1,(year,'Super Bowl matchup')
    cs=float(weeks[end][champ['franchise_id']]['score']);rs=float(weeks[end][runner['franchise_id']]['score']);assert cs>=rs
    def record(r):return '-'.join(str(r['record_'+k]) for k in ('wins','losses','ties'))
    awards={}
    for conf,index in [('NFC',0),('AFC',16)]:
        for key in ['HC','OC','DC','GM']:
            values={}
            for r in h[index:index+16]:
                fid=r['franchise_id'];code=codes[int(fid)-1]
                v=(r['rs_wins']+.5*r['rs_ties'])/372 if key=='HC' else sum(float(weeks[w][fid]['opt_pts']) for w in range(1,13))/12 if key=='GM' else next(m[key] for m in metrics if m['year']==year and m['franchise_id']==fid)
                values[code]=v
            # Recipients will be read from published awards below, using these audited metrics.
            awards[conf+' '+key]=values
    champions.append(dict(year=year,champion=champ['name'],runner=runner['name'],championRecord=record(champ),runnerRecord=record(runner),gm=champ['gm'],score=f'{cs:.1f} - {rs:.1f}',awards=awards))

local=json.loads(Path(sys.argv[3]).read_text())
sources=json.loads((ROOT/'data/gm_career_sources.json').read_text())
for year in range(2014,2026):
    h=[r for r in history if r['season']==year]; prizes=[];periods=[];teams=[]
    if year>=2018:
        path=CACHE/f'FAFL-{year}-payouts.xlsx';b=openpyxl.load_workbook(path,data_only=True,read_only=True)
        rows=list(b['Money'].values);source=next(s['url'] for s in sources if s['year']==year and s['kind']=='payouts')
        periods=[dict(period=r[0],winners=[norm(v) if v and not str(v).startswith('#') else None for v in r[1:9]]) for r in list(b['Display'].values)[2:] if r[0]]
    else:
        src=next(s for s in local if s['year']==year);path=Path(src['source']);rows=src['rows'];source=None
    if year>=2017:
        for r in rows[1 if year>=2018 else 2:]:
            if r[0]:prizes.append(dict(prize=r[0],nfc=norm(r[1]) if r[1] else None,afc=norm(r[2]) if r[2] else None,amount=r[3]))
            if len(r)>8 and r[5] and r[5] not in ('Sum','Pay-In:'):
                assert isinstance(r[6],(float,int)),(year,r)
                teams.append(dict(team=norm(r[5]),earnings=r[6],adjustment=r[7] or 0,payout=r[8],explanation=r[9]))
        # Apply the known 2018 source correction once, at the prize recipient.
        if year==2018:
            p=next(p for p in prizes if 'Consolation Ladder' in p['prize']);p['afc']='NEP'
        for t in teams:
            items=[];weekly={}
            for p in prizes:
                for conf in ['nfc','afc']:
                    winners=[norm(x.strip()) for x in (p[conf] or '').split('/')]
                    if t['team'] not in winners or not p['amount']:continue
                    label=p['prize'];amount=p['amount']/len(winners)
                    wk=re.fullmatch(r'Week (\d+) High Score',label)
                    if wk:
                        a=weekly.setdefault((conf,len(winners)>1),dict(weeks=[],amount=0));a['weeks'].append(int(wk[1]));a['amount']+=amount
                    else:
                        label={'Conference Champ Runner-Up':'Conference Championship Runner-Up','Third Place Winner':'3rd Place Finish','Third Place Runner-Up':'4th Place Finish','Fifth Place Winner':'5th Place Finish','Fifth Place Runner-Up':'6th Place Finish'}.get(label,label)
                        if label.startswith('Playoff Participant'):label='Playoff Participant'
                        elif not label.startswith('Super Bowl'):label=conf.upper()+' '+label
                        items.append(dict(label=label,amount=amount))
            for (conf,shared),a in weekly.items():items.append(dict(label=conf.upper()+' Top Score '+('Week ' if len(a['weeks'])==1 else 'Weeks ')+', '.join(map(str,sorted(a['weeks'])))+(' (shared)' if shared else ''),amount=a['amount']))
            t['earnedBreakdown']=items;t['totalEarnings']=sum(a['amount'] for a in items)
            # The awards, not deposit corrections, determine true earnings.
    else:
        def teamname(label):
            name=label.strip()
            special={'St. Louis':'0016','Kansas City':'0030','Washington Redskins':'0004','San Diego Chargers':'0032','Oakland Raiders':'0031'}
            if name in special:return next(r for r in h if r['franchise_id']==special[name])
            candidates=[r for r in h if r['name']==name or r['name'].startswith(name+' ')]
            assert len(candidates)==1,name
            return candidates[0]
        listed={}
        for r in rows:
            if len(r)<3 or not isinstance(r[1],(float,int)) or not r[0] or r[0]=='Total':continue
            hr=teamname(r[0]);items=[]
            for amount,label in re.findall(r'\$(\d+(?:\.\d+)?)\s*([^$]+)',r[2] or ''):
                label=label.strip(' +()');label=label.replace('Defensive Coord','DC').replace('Def Coord','DC').replace('Off Coord','OC').replace('Best All-Play','HC of the Year').replace('Best Offense','OC of the Year').replace('Best Defense','DC of the Year')
                items.append(dict(label=label,amount=float(amount)))
            total=sum(i['amount'] for i in items);assert abs(total-r[1])<.001,(year,hr['name'],total,r[1])
            listed[hr['franchise_id']]=dict(team=codes[int(hr['franchise_id'])-1],earnings=total,adjustment=0,payout=total,explanation=r[2],totalEarnings=total,earnedBreakdown=items)
        for r in h:teams.append(listed.get(r['franchise_id'],dict(team=codes[int(r['franchise_id'])-1],earnings=0,adjustment=0,payout=0,earnedBreakdown=[],totalEarnings=0)))
    assert len(teams)==32 and len({t['team'] for t in teams})==32,(year,len(teams))
    for t in teams:assert abs(t['earnings']+t['adjustment']-t['payout'])<.001,(year,t)
    if year==2018:
        assert next(t for t in teams if t['team']=='NEP')['totalEarnings']==90
        assert next(t for t in teams if t['team']=='LVR')['totalEarnings']==0
    c=next(c for c in champions if c['year']==year)
    awardlabels={'HC':'Head Coach','OC':'Offensive Coordinator','DC':'Defensive Coordinator','GM':'General Manager'}
    for conf in ['NFC','AFC']:
        for key,label in awardlabels.items():
            if prizes:
                match=[p for p in prizes if p['prize']==label+' of the Year'];winner=match[0][conf.lower()] if match else None
            else:
                winner=next((t['team'] for t in teams if any(conf in a['label'] and (label in a['label'] or key+' of the Year' in a['label']) for a in t['earnedBreakdown'])),None)
            values=c['awards'][conf+' '+key]
            if winner:
                winner=norm(winner);assert winner in values,(year,winner,key)
                c['awards'][conf+' '+key]=winner+' ('+(f'{values[winner]:.3f}' if key=='HC' else f'{values[winner]:.1f}')+')'
            else:c['awards'][conf+' '+key]='Not awarded'
    seasons[str(year)]=dict(source=source,sourceLabel=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),teams=teams,prizes=prizes,periods=periods,missingAwardCells=sum(v is None for p in periods for v in p['winners']),totalEarnings=sum(t['earnings'] for t in teams),totalAdjustments=sum(t['adjustment'] for t in teams),totalPayout=sum(t['payout'] for t in teams),totalPrizeEarnings=sum(t['totalEarnings'] for t in teams))
    print(year,seasons[str(year)]['totalPrizeEarnings'],seasons[str(year)]['totalPayout'])
dest=ROOT/'data/trophy_room';dest.mkdir(exist_ok=True)
for name,payload in [('payouts',seasons),('champions',champions),('league_records',records)]: (dest/f'{name}.json').write_text(json.dumps(payload,indent=2)+'\n')
(ROOT/'data/gm_career_seasons.json').write_text(json.dumps(history,indent=2)+'\n')



