"""Capture and report user-visible effects of an official FAFL score correction."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).parents[1]
BEFORE = ROOT / '.correction_impact_before.json'
BASELINE = ROOT / 'data/official_score_output_baseline.json'
OUTPUT = ROOT / 'data/correction_impact.json'
STATE_FILES = ('data/processed_player_scores.json', 'data/current_weekly.csv', 'data/bonus_games.csv')


def rows(path):
    return list(csv.DictReader(path.open(encoding='utf-8-sig'))) if path.exists() else []


def num(value):
    return float(value)


def score_map(path, week):
    value = json.loads(path.read_text()) if path.exists() else {}
    if 'scores' in value and int(value.get('week', -1)) == week:
        return {str(k): num(v) for k, v in value['scores'].items()}
    item = value.get('weeks', {}).get(str(week), {})
    return {str(k): num(v) for k, v in item.get('scores', {}).items()}


def all_play(weekly, week, root=ROOT):
    selected = [r for r in weekly if int(r['week']) == week]
    scores = {r['franchise_id'].zfill(4): num(r['points']) for r in selected}
    names = {r['franchise_id'].zfill(4): r['franchise_name'] for r in rows(root / 'data/bonus_games.csv')}
    return {fid: {'name': names.get(fid, fid), 'wins': sum(
        1 if value > other else .5 if value == other else 0
        for other_id, other in scores.items() if other_id != fid)} for fid, value in scores.items()}


def bonus(root=ROOT):
    return {r['event'] + ':' + r['franchise_id'].zfill(4):
            {'name': r['franchise_name'], 'event': r['event'],
             'result': 'W' if num(r['bonus_result']) == 1 else 'T' if num(r['bonus_result']) == .5 else 'L'}
            for r in rows(root / 'data/bonus_games.csv')}


def state(week, current=False, root=ROOT):
    score_path = BEFORE.parent / '.refresh_player_scores.json' if current else root / 'data/processed_player_scores.json'
    return {'season': int(os.environ.get('CURRENT_SEASON', '2026')), 'week': week,
            'player_scores': score_map(score_path, week), 'ext': {},
            'all_play': all_play(rows(root / 'data/current_weekly.csv'), week, root), 'bonus': bonus(root)}


def official_git_state(week):
    candidates = []
    for process in ('preliminary', 'corrections'):
        path = ROOT / f'data/refresh_receipts/{process}.json'
        if path.exists():
            receipt = json.loads(path.read_text())
            if receipt.get('status') == 'success' and receipt.get('week') == week:
                candidates.append(receipt)
    if not candidates:
        return None
    receipt = max(candidates, key=lambda value: value.get('completed_at', ''))
    path = f'data/refresh_receipts/{receipt["process"]}.json'
    ref = subprocess.check_output(
        ['git', 'log', '-S', f'"run_id": "{receipt["run_id"]}"', '--format=%H', '--', path],
        cwd=ROOT, text=True).splitlines()
    if not ref:
        return None
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for relative in STATE_FILES:
            content = subprocess.check_output(['git', 'show', f'{ref[0]}:{relative}'], cwd=ROOT)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return state(week, root=root)


def changes(before, after):
    result = {'league': 'FAFL', 'season': after['season'], 'week': after['week'],
              'run_id': os.environ.get('GITHUB_RUN_ID', ''), 'ext_pr': [], 'all_play': [], 'bonus_games': []}
    for fid in sorted(set(before['all_play']) & set(after['all_play'])):
        old, new = before['all_play'][fid], after['all_play'][fid]
        if old['wins'] != new['wins']:
            result['all_play'].append({'franchise_id': fid, 'franchise': new['name'],
                                       'old_wins': old['wins'], 'new_wins': new['wins']})
    for key in sorted(set(before['bonus']) & set(after['bonus'])):
        old, new = before['bonus'][key], after['bonus'][key]
        if old['result'] != new['result']:
            result['bonus_games'].append({'franchise': new['name'], 'event': new['event'],
                                          'old_result': old['result'], 'new_result': new['result']})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('capture', 'compare', 'promote'))
    parser.add_argument('--league', choices=('FAFL',), required=True)
    parser.add_argument('--week', type=int, required=True)
    args = parser.parse_args()
    if args.action == 'capture':
        value = json.loads(BASELINE.read_text()) if BASELINE.exists() else None
        if not value or value.get('week') != args.week:
            value = official_git_state(args.week) or state(args.week)
        BEFORE.write_text(json.dumps(value, indent=2) + '\n')
    elif args.action == 'compare':
        OUTPUT.write_text(json.dumps(changes(json.loads(BEFORE.read_text()), state(args.week, True)), indent=2) + '\n')
    else:
        BASELINE.write_text(json.dumps(state(args.week, True), indent=2) + '\n')


if __name__ == '__main__':
    main()
