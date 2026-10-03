import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_trophy_room import build,people,majority_franchise
from gm_profiles import _career_rows,_profile_from_rows
class TrophyRoomTests(unittest.TestCase):
    def test_majority_franchise_and_latest_tie(self):
        rows=[dict(season=y,franchise_id='0030',name='Kansas City Chiefs') for y in range(2014,2018)]
        rows.append(dict(season=2019,franchise_id='0015',name='Seattle Seahawks'))
        self.assertEqual(majority_franchise(rows,[]),'Kansas City Chiefs')
        self.assertEqual(majority_franchise(rows,['Seattle Seahawks']),'Seattle Seahawks')
        self.assertEqual(majority_franchise([rows[0],rows[-1]],[]),'Seattle Seahawks')
        self.assertEqual(majority_franchise([],['Washington Commanders']),'Washington Commanders')
        moved=[dict(season=2022,franchise_id='0015',name='Seattle Seahawks'),dict(season=2023,franchise_id='0016',name='Seattle Seahawks'),dict(season=2024,franchise_id='0015',name='San Francisco 49ers')]
        self.assertEqual(majority_franchise(moved,[]),'Seattle Seahawks')
        renamed=[dict(season=2018,franchise_id='0031',name='Oakland Raiders'),dict(season=2021,franchise_id='0031',name='Las Vegas Raiders'),dict(season=2022,franchise_id='0015',name='Seattle Seahawks')]
        self.assertEqual(majority_franchise(renamed,[]),'Las Vegas Raiders')
        carson=next(o for o in build()['owners'] if o['owner']=='Carson Witte')
        self.assertEqual(carson['franchise'],'Kansas City Chiefs')
        self.assertEqual(carson['history'][-1]['franchise'],'Seattle Seahawks')
    def test_washington_owner_change_preserves_champion_history(self):
        d=build()
        brandon=next(o for o in d['owners'] if o['owner']=='Brandon Owens')
        frank=next(o for o in d['owners'] if o['owner']=='Frank Roberts')
        self.assertFalse(brandon['active'])
        self.assertEqual(brandon['years'],[2025])
        self.assertTrue(frank['active'])
        self.assertEqual(frank['franchise'],'Washington Commanders')
        self.assertEqual(frank['seasons'],0)
        self.assertEqual(next(c for c in d['champions'] if c['year']==2025)['gm'],'Brandon Owens')
    def test_canonical_history_and_prizes(self):
        d=build();h=json.loads((ROOT/'data/gm_career_seasons.json').read_text())
        roster=json.loads((ROOT/'data/current_gms_2026.json').read_text())['profiles']
        for team,current in roster.items():
            for person in people(current['gm']):
                owner=next(o for o in d['owners'] if person in o['members'] and o['active'])
                self.assertEqual(owner['franchise'],team)
        self.assertEqual(len(h),384);self.assertEqual(len(d['champions']),12)
        records=json.loads((ROOT/'data/trophy_room/league_records.json').read_text())
        for r in h:
            source=next(x for x in records if x['season']==r['season'] and x['franchise_id']==r['franchise_id'])
            for k in ['record_wins','record_losses','record_ties']:self.assertEqual(r[k],source[k])
        for o in d['owners']:
            rows=[r for r in h if o['members'][0] in people(r['gm'])]
            self.assertEqual(len(rows),o['seasons'])
            if rows:self.assertAlmostEqual(o['allTimeAllPlay'],sum((r['wins']+.5*r['ties'])/(r['wins']+r['losses']+r['ties']) for r in rows)/len(rows))
            for person in o['members']:
                profile=_profile_from_rows(_career_rows(person,h))
                for k in ['wins','losses','ties']:self.assertEqual(o[k],profile[k],person)
        for p in d['payouts']:
            self.assertEqual(len(p['teams']),32)
            for t in p['teams']:
                west={'LAR':'Rams','SFO':'49ers','SEA':'Seahawks'}
                if t['team'] in west:self.assertTrue(t['franchise'].endswith(west[t['team']]),(p['year'],t))
                self.assertAlmostEqual(t['totalEarnings'],sum(x['amount'] for x in t['earnedBreakdown']))
                self.assertAlmostEqual(t['totalEarnings'],t['earnings'])
        p=next(p for p in d['payouts'] if p['year']==2018)
        self.assertEqual(next(t for t in p['teams'] if t['team']=='NEP')['totalEarnings'],90)
        self.assertEqual(next(t for t in p['teams'] if t['team']=='LVR')['totalEarnings'],0)
        self.assertEqual(next(t for t in d['payouts'][0]['teams'] if t['team']=='LAR')['franchise'],'St. Louis Rams')
if __name__=='__main__':unittest.main()
