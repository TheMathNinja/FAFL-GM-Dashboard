"""Publish verified output with bounded regeneration after source advances."""
import subprocess
import sys

GENERATED = (
    'data/clinching', 'docs/bonus-games', 'docs/playoff-picture',
    'data/current_forecast.json', 'data/weekly_sharks_team_means.csv', 'data/playoff_swing.csv',
    'data/fafl_scoring_model.json', 'data/forward_bye_exposure.csv', 'data/forecast_bye_inputs',
)
MAX_REBUILDS = 2


def publish(run=subprocess.run):
    def git(*args, **kwargs):
        return run(['git', *args], **kwargs)

    def output(*args):
        return git(*args, check=True, capture_output=True, text=True).stdout.strip()

    def tip():
        git('fetch', 'origin', '+refs/heads/main:refs/remotes/origin/main', check=True)
        return output('rev-parse', 'origin/main')

    base = output('rev-parse', 'HEAD')
    for attempt in range(MAX_REBUILDS + 1):
        git('add', '--', *GENERATED, check=True)
        changed = git('diff', '--cached', '--quiet').returncode
        if changed == 1:
            git('commit', '-m', 'Rebuild selected Bonus Games dashboard', check=True)
        elif changed:
            raise RuntimeError('Could not inspect staged generated output')
        if output('status', '--porcelain', '--untracked-files=no'):
            raise RuntimeError('Rebuild modified tracked files outside the generated publication paths')
        candidate = output('rev-parse', 'HEAD')
        latest = tip()
        if latest == candidate:
            return  # No change, or this exact verified commit is already published.
        if latest == base:
            pushed = git('push', 'origin', 'HEAD:main')
            if pushed.returncode == 0:
                return
            latest = tip()
            if latest == candidate:
                return  # The server accepted the push despite a failed response.
            if latest == base:
                raise RuntimeError('Generated publication rejected without a branch advance')
        if attempt == MAX_REBUILDS:
            raise RuntimeError('Main advanced again during the regenerated build; no stale output was pushed')
        print(f'Main advanced during the build; regenerating from latest source ({attempt + 1}/{MAX_REBUILDS}).', flush=True)
        requirements_changed = output('diff', '--name-only', base, latest, '--', 'requirements.txt')
        git('switch', '--detach', latest, check=True)
        if requirements_changed:
            run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        base = latest
        run(['bash', 'scripts/rebuild_bonus_games.sh'], check=True)


if __name__ == '__main__':
    publish()
