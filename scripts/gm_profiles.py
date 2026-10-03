"""Build current GM cards from 2026 ownership plus completed-season history."""
import json
from copy import deepcopy
import re


GM_ALIASES = {
    'Chase Marak': {'Chase'},
    'Sid Narayanan': {'Siddhartha Narayanan'},
}


def _normalized(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


def _career_rows(gm, rows):
    aliases = {_normalized(gm), *(_normalized(x) for x in GM_ALIASES.get(gm, set()))}
    is_group = ',' in gm
    matched = []
    for row in rows:
        historical = row['gm']
        if is_group:
            include = _normalized(historical) in aliases
        else:
            include = bool(aliases.intersection(_normalized(x.strip()) for x in historical.split(',')))
        if include:
            matched.append(row)
    return matched


def _current_profiles(root, season):
    """Join current ownership to history by GM, never by last year's franchise."""
    baseline = json.loads((root / 'data/gm_career_profiles.json').read_text(encoding='utf8'))
    current = json.loads((root / f'data/current_gms_{season}.json').read_text(encoding='utf8'))
    seasons = json.loads((root / 'data/gm_career_seasons.json').read_text(encoding='utf8'))
    assert baseline['season'] == season and baseline['completedThrough'] < season
    assert len(baseline['profiles']) == 32
    assert current['season'] == season and len(current['profiles']) == 32

    history_by_gm = {profile['gm']: profile for profile in baseline['profiles'].values()}
    assert len(history_by_gm) == len(baseline['profiles'])
    profiles = {}
    for team, owner in current['profiles'].items():
        gm = owner['gm']
        historical = deepcopy(history_by_gm.get(gm, {
            'experience': 0, 'wins': 0, 'losses': 0, 'ties': 0,
            'best': None, 'bestYears': [], 'worst': None, 'worstYears': [],
        }))
        historical['franchise_id'] = owner['franchise_id']
        historical['gm'] = gm
        career_rows = _career_rows(gm, seasons)
        assert len(career_rows) == historical['experience']
        assert sum(r['wins'] for r in career_rows) == historical['wins']
        assert sum(r['losses'] for r in career_rows) == historical['losses']
        assert sum(r['ties'] for r in career_rows) == historical['ties']
        historical['completedSeasonApPcts'] = [
            (r['wins'] + .5 * r['ties']) / (r['wins'] + r['losses'] + r['ties'])
            for r in career_rows
        ]
        profiles[team] = historical
    assert len({p['franchise_id'] for p in profiles.values()}) == 32
    return profiles

def gm_profiles(root, season, week, current):
    scores = current[current.week <= week].copy()
    scores.franchise_id = scores.franchise_id.astype(str).str.zfill(4)
    assert len(scores) == 32 * week and not scores.points.isna().any()
    assert not scores.duplicated(['week', 'franchise_id']).any()
    profiles = _current_profiles(root, season)
    for g in profiles.values():
        own = scores[scores.franchise_id == g['franchise_id']]
        assert len(own) == week
        for r in own.itertuples():
            other = scores[(scores.week == r.week) & (scores.franchise_id != g['franchise_id'])].points
            g['wins'] += int((r.points > other).sum())
            g['losses'] += int((r.points < other).sum())
            g['ties'] += int((r.points == other).sum())
        current_games = 31 * week
        current_pct = sum(
            (r.points > scores[(scores.week == r.week) & (scores.franchise_id != g['franchise_id'])].points).sum()
            + .5 * (r.points == scores[(scores.week == r.week) & (scores.franchise_id != g['franchise_id'])].points).sum()
            for r in own.itertuples()
        ) / current_games if current_games else 0
        current_weight = min(week, 17) / 17
        completed = g.pop('completedSeasonApPcts')
        g['careerApPct'] = (sum(completed) + current_weight * current_pct) / (len(completed) + current_weight)
    return profiles
