import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from push_generated import publish


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.origin = root / 'origin.git'
        self.writer = root / 'writer'
        self.editor = root / 'editor'
        self.git(root, 'init', '--bare', '--initial-branch=main', str(self.origin))
        self.git(root, 'clone', '--no-hardlinks', 'origin.git', 'editor')
        self.configure(self.editor)
        self.advance('original', 'original generated page')
        self.git(root, 'clone', '--no-hardlinks', 'origin.git', 'writer')
        self.configure(self.writer)
        self.commands = []
        self.rebuild = Mock()

    def git(self, cwd, *args):
        result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def configure(self, cwd):
        self.git(cwd, 'config', 'user.name', 'Publication Test')
        self.git(cwd, 'config', 'user.email', 'publication@example.invalid')

    def advance(self, source, page):
        (self.editor / 'source.txt').write_text(source, encoding='utf-8')
        (self.editor / 'page.txt').write_text(page, encoding='utf-8')
        self.git(self.editor, 'add', '.')
        self.git(self.editor, 'commit', '-m', source)
        self.git(self.editor, 'push', 'origin', 'HEAD:main')

    def run_command(self, args, **kwargs):
        self.commands.append(args)
        if args[0] == 'bash':
            self.rebuild()
            source = (self.writer / 'source.txt').read_text(encoding='utf-8')
            (self.writer / 'page.txt').write_text('generated from ' + source, encoding='utf-8')
            return
        if args[0] == 'git':
            kwargs.setdefault('capture_output', True)
        return subprocess.run(args, cwd=self.writer, **kwargs)

    def publish(self):
        with patch('push_generated.GENERATED', ('page.txt',)):
            publish(self.run_command)

    def test_overlapping_branch_change_regenerates_and_preserves_newer_changes(self):
        (self.writer / 'page.txt').write_text('generated from obsolete source', encoding='utf-8')
        self.advance('new source', 'conflicting page edit')
        self.publish()
        self.rebuild.assert_called_once()
        self.assertEqual(self.git(self.origin, 'show', 'main:source.txt'), 'new source')
        self.assertEqual(self.git(self.origin, 'show', 'main:page.txt'), 'generated from new source')
        self.assertFalse(any('rebase' in c or any(arg.startswith('--force') for arg in c) for c in self.commands))

    def test_branch_advances_during_push_then_rebuilds(self):
        (self.writer / 'page.txt').write_text('first build', encoding='utf-8')
        original = self.run_command
        race = True

        def run(args, **kwargs):
            nonlocal race
            if race and args[:2] == ['git', 'push']:
                race = False
                self.advance('raced source', 'raced page')
            return original(args, **kwargs)

        self.run_command = run
        self.publish()
        self.rebuild.assert_called_once()
        self.assertEqual(self.git(self.origin, 'show', 'main:page.txt'), 'generated from raced source')

    def test_second_advance_stops_without_pushing_stale_output(self):
        self.advance('new source', 'new page')
        self.rebuild.side_effect = lambda: self.advance('newest source', 'newest page')
        with self.assertRaisesRegex(RuntimeError, 'advanced again'):
            self.publish()
        self.rebuild.assert_called_once()
        self.assertEqual(self.git(self.origin, 'show', 'main:page.txt'), 'newest page')

    def test_validation_failure_makes_no_publication(self):
        self.advance('new source', 'new page')
        self.rebuild.side_effect = subprocess.CalledProcessError(1, ['bash'])
        with self.assertRaises(subprocess.CalledProcessError):
            self.publish()
        self.assertEqual(self.git(self.origin, 'show', 'main:page.txt'), 'new page')
