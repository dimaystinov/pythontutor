"""Client regression tests (never execute submitted code in this process)."""
import unittest
from unittest.mock import patch
from evaldontevil import execute_python


class TestExecutePython(unittest.TestCase):
    def test_missing_runner_fails_closed(self):
        with patch.dict('os.environ', {}, clear=True):
            result = execute_python('[][0]')
        self.assertEqual(result.result, 'internal_error')
        self.assertEqual(result.stdout, '')
