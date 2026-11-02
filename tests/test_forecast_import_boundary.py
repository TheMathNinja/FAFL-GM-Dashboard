"""Scoring consumers must not inherit dashboard-only solver dependencies."""
import subprocess
import sys
import unittest
from pathlib import Path


class ImportBoundaryTests(unittest.TestCase):
    def test_scoring_helpers_import_without_clinching_solver(self):
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        code = (
            'import sys; '
            f'sys.path.insert(0,{str(scripts)!r}); '
            'sys.modules["exact_clinching"]=None; '
            'sys.modules["z3"]=None; '
            'import build, scoring_engine, quarterly_bonus; '
            'assert callable(build.fit_means); '
            'assert callable(scoring_engine.parameters)'
        )
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__': unittest.main()
