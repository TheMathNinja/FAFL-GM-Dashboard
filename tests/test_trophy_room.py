import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_trophy_room import build,people
from gm_profiles import _career_rows,_profile_from_rows
class TrophyRoomTests(unittest.TestCase):
    def test_canonical_history_and_prizes(self):
        d=build();h=json.loads((ROOT/'data/gm_career_seasons.json').read_text())
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
                self.assertAlmostEqual(t['totalEarnings'],sum(x['amount'] for x in t['earnedBreakdown']))
                self.assertAlmostEqual(t['totalEarnings'],t['earnings'])
        p=next(p for p in d['payouts'] if p['year']==2018)
        self.assertEqual(next(t for t in p['teams'] if t['team']=='NEP')['totalEarnings'],90)
        self.assertEqual(next(t for t in p['teams'] if t['team']=='LVR')['totalEarnings'],0)
        self.assertEqual(next(t for t in d['payouts'][0]['teams'] if t['team']=='LAR')['franchise'],'St. Louis Rams')
if __name__=='__main__':unittest.main()
