"""Add this year's all-play games to the audited, league-specific GM baseline."""
import json

def gm_profiles(root, season, week, current):
    baseline = json.loads((root / 'data/gm_career_profiles.json').read_text(encoding='utf8'))
    assert baseline['season'] == season and len(baseline['profiles']) == 32
    current_gms = json.loads((root / f'data/current_gms_{season}.json').read_text(encoding='utf8'))
    assert current_gms['season'] == season and len(current_gms['profiles']) == 32
    for team, profile in baseline['profiles'].items():
        expected = current_gms['profiles'][team]
        assert profile['franchise_id'] == expected['franchise_id']
        assert profile['gm'] == expected['gm']
    scores = current[current.week <= week].copy()
    scores.franchise_id = scores.franchise_id.astype(str).str.zfill(4)
    assert len(scores) == 32 * week and not scores.points.isna().any()
    assert not scores.duplicated(['week', 'franchise_id']).any()
    profiles = baseline['profiles']
    for g in profiles.values():
        own = scores[scores.franchise_id == g['franchise_id']]
        assert len(own) == week
        for r in own.itertuples():
            other = scores[(scores.week == r.week) & (scores.franchise_id != g['franchise_id'])].points
            g['wins'] += int((r.points > other).sum())
            g['losses'] += int((r.points < other).sum())
            g['ties'] += int((r.points == other).sum())
    return profiles
