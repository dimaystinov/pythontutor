# -*- coding: utf-8 -*-

# Online Python Tutor
# https://github.com/pgbovine/OnlinePythonTutor/
# 
# Copyright (C) 2010-2012 Philip J. Guo (philip@pgbovine.net)
# 
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# Runs both 'user_script' and 'expect_script' and returns whether the
# test has passed or failed, along with the FULL trace if the test has
# failed (so that the user can debug it)


import json
import pprint
import re

from evaldontevil import execute_python


EPSILON = 1e-3


class TestResult:
	def __init__(self, test, status, stderr, user_answer, is_correct):
		self.status = status
		self.stderr = stderr

		self.test_input = test.test_input
		self.correct_answer = test.correct_answer
		self.user_answer = user_answer

		self.is_correct = is_correct

	def verdict_status(self):
		if self.status != 'ok':
			return self.status
		elif not self.is_correct:
			return 'wrong_answer'
		else:
			return 'ok'


class Test:
	def __init__(self, test_input, correct_answer):
		self.test_input = test_input
		self.correct_answer = correct_answer


	def _tokens_are_equal(self, x, y):
		res = False

		try:
			res = abs(float(x) - float(y)) < EPSILON
		except ValueError:
			res = (x == y)

		return res

	def _compare_sequences_of_tokens(self, seq1, seq2):
		seq1 = [i for i in seq1.split() if i]
		seq2 = [i for i in seq2.split() if i]
		return (len(seq1) == len(seq2) and all(self._tokens_are_equal(x, y) for x, y in zip(seq1, seq2)))


	def test_code(self, code):
		res = execute_python(code, stdin=self.test_input)
		user_answer = res.stdout.strip()

		is_correct = self._compare_sequences_of_tokens(user_answer, self.correct_answer)

		return TestResult(self, res.result, res.stderr, user_answer, is_correct)


def run_test(user_code, test_input, test_answer):
	test = Test(test_input, test_answer)
	return test.test_code(user_code)
