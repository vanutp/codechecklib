import unittest

from testlib import Tester
from testlib.const import ExecStatus


class TestPython(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tester = Tester()

    async def test_stdin_stdout_ok(self):
        test_program = '[print(int(input()) + 2) for _ in range(int(input()))]'
        res = await self.tester.run(test_program, 'py_nl', '2\n3\n4')
        self.assertEqual(res.status, ExecStatus.OK)
        self.assertEqual(res.stdout, '5\n6')

    async def test_stdin_stdout_re(self):
        test_program = 'print(input())\n1/0'
        res = await self.tester.run(test_program, 'py_nl', '123')
        self.assertEqual(res.status, ExecStatus.RE)
        self.assertEqual(res.stdout, '123')

    async def test_tl(self):
        test_program = 'while True: pass'
        res = await self.tester.run(test_program, 'py_nl')
        self.assertEqual(res.status, ExecStatus.TL)

    async def test_ml(self):
        test_program = 'a = [1]\nwhile True: a += a[:]'
        res = await self.tester.run(test_program, 'py_nl', memory=1024 * 1024 * 1)
        self.assertEqual(res.status, ExecStatus.ML)

    async def test_fork(self):
        test_program = 'import os\nwhile True: os.fork()'
        res = await self.tester.run(test_program, 'py_nl')
        self.assertEqual(res.status, ExecStatus.RE)

    async def test_stdin_stdout_ok_multiple(self):
        test_program = '[print(int(input()) + 2) for _ in range(int(input()))]'
        res = await self.tester.test(test_program, 'py_nl', [('2\n3\n4', '5\n6'),
                                                             ('4\n5\n2\n5\n-1', '7\n4\n7\n1')])
        self.assertTrue(res.success)

    async def test_stdin_stdout_wa_multiple(self):
        test_program = '[print(int(input()) + 2) for _ in range(int(input()))]'
        res = await self.tester.test(test_program, 'py_nl', [('2\n3\n4', '4\n6'),
                                                             ('4\n5\n2\n5\n-1', '7\n4\n7\n1')])
        self.assertFalse(res.success)
        self.assertEqual(res.first_error_test, 0)
        self.assertEqual(res.results[0].stdout, '5\n6')
