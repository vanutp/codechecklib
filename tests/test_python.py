import unittest

from testlib import Tester
from testlib.const import ExecStatus

TEST_PROGRAM = '''n = int(input())
for _ in range(n):
    print(int(input()) + 2)
'''


class TestPython(unittest.TestCase):
    def setUp(self):
        self.tester = Tester()

    def test_stdin_stdout(self):
        is_success, compiled_filename, _, _ = self.tester.compile(TEST_PROGRAM, [], 'py')
        self.assertTrue(is_success)
        res = self.tester.run(compiled_filename, 'py', '2\n3\n4')
        self.assertEqual(res.status, ExecStatus.OK)
        self.assertEqual(res.stdout, '5\n6')
