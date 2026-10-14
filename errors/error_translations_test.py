import re
import unittest

from errors import error_translations
from evaldontevil import execute_python


class TestErrorTranslations(unittest.TestCase):
    def test_code_snippets_are_present(self):
        for entry in error_translations.ERROR_TRANSLATIONS:
            self.assertIsNotNone(entry.code, entry.source_regexp)

    def test_code_snippets_cause_errors_that_match(self):
        for entry in error_translations.ERROR_TRANSLATIONS:
            if entry.code:
                execution = execute_python(entry.code)
                self.assertTrue(isinstance(execution.exception, dict),
                                str(type(execution.exception)) + entry.source_regexp)
                exception_str = execution.exception['exception_str']
                self.assertTrue(re.match(entry.regexp, exception_str),
                    'Regexp "{0}" doesn\'t match message {1}'.format(
                        entry.source_regexp, exception_str))

    # TODO(vpavlenko): Add test that every case doens't match by any preceding error translation.

if __name__ == '__main__':
    unittest.main()
