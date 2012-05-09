
from os.path import expanduser
from unity_lens_vim import VimLens
import unittest

lens = VimLens()

class TestPattern(unittest.TestCase):

    def setUp(self):
        self.user = 'root'
        self.tilde = '~' + self.user
        self.home = expanduser(self.tilde)

    def test_unanchored(self):
        self.assertEqual('*foo*', lens.pattern('foo'))
        self.assertEqual('*f\\oo*', lens.pattern('f\\oo'))

    def test_absolute(self):
        self.assertEqual('/foo*', lens.pattern('/foo'))
        self.assertEqual('/foo/*', lens.pattern('/foo/'))
        self.assertEqual('/^foo*', lens.pattern('/^foo'))
        self.assertEqual('/' + self.tilde + '*', lens.pattern('/' + self.tilde))

    def test_caret_and_dollar(self):
        self.assertEqual('foo*', lens.pattern('^foo'))
        self.assertEqual('*^foo*', lens.pattern('\\^foo'))
        self.assertEqual('*foo', lens.pattern('foo$'))
        self.assertEqual('*foo$*', lens.pattern('foo\\$'))
        self.assertEqual('foo', lens.pattern('^foo$'))
        self.assertEqual('*^foo$*', lens.pattern('\\^foo\\$'))

    def test_tilde(self):
        self.assertEqual('~nonexistent*', lens.pattern('~nonexistent'))
        self.assertEqual(self.home + '*', lens.pattern(self.tilde))
        self.assertEqual(self.home + '/foo*', lens.pattern(self.tilde + '/foo'))
        self.assertEqual('*bar' + self.tilde + '/foo*', lens.pattern('bar' + self.tilde + '/foo'))
        self.assertEqual(self.tilde + '/foo*', lens.pattern('^' + self.tilde + '/foo'))
        self.assertEqual(self.home + '/foo', lens.pattern(self.tilde + '/foo$'))
        self.assertEqual('*' + self.tilde + '*', lens.pattern('\\' + self.tilde))

