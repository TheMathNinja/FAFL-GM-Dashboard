"""Publish a generated commit without force-pushing or resolving conflicts."""
import subprocess
import time


def publish(run=subprocess.run, sleep=time.sleep):
    for attempt in range(3):
        run(['git', 'fetch', 'origin', 'main'], check=True)
        result = run(['git', 'rebase', 'origin/main'])
        if result.returncode:
            run(['git', 'rebase', '--abort'], check=True)
            raise RuntimeError('Generated output conflicts with newer changes; rebuild from current main')
        if run(['git', 'push', 'origin', 'HEAD:main']).returncode == 0:
            return
        if attempt < 2:
            sleep(2 ** (attempt + 1))
    raise RuntimeError('Generated publication still rejected after three attempts')


if __name__ == '__main__':
    publish()
