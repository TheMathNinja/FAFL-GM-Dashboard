import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from push_generated import publish


class PublicationTests(unittest.TestCase):
    def test_branch_advance_is_rebased_and_retried_without_force(self):
        run = Mock(side_effect=[SimpleNamespace(returncode=n) for n in [0, 0, 1, 0, 0, 0]])
        sleep = Mock()
        publish(run, sleep)
        self.assertEqual(run.call_count, 6)
        self.assertEqual(run.call_args_list[3].args[0], ['git', 'fetch', 'origin', 'main'])
        self.assertFalse(any('--force' in c.args[0] for c in run.call_args_list))
        sleep.assert_called_once_with(2)

    def test_conflict_aborts_without_push(self):
        run = Mock(side_effect=[SimpleNamespace(returncode=n) for n in [0, 1, 0]])
        with self.assertRaisesRegex(RuntimeError, 'conflicts'):
            publish(run, Mock())
        self.assertEqual(run.call_args.args[0], ['git', 'rebase', '--abort'])

    def test_retries_are_bounded(self):
        run = Mock(side_effect=[SimpleNamespace(returncode=n) for n in [0, 0, 1] * 3])
        with self.assertRaisesRegex(RuntimeError, 'three attempts'):
            publish(run, Mock())
        self.assertEqual(run.call_count, 9)
