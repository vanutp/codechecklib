import unittest

from codechecklib import Tester
from codechecklib.const import ExecStatus


class TestRs(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tester = Tester()

    async def test_stdin_stdout_ok(self):
        test_program = '''fn main() {
    println!("Hello world!");
}'''
        res = await self.tester.run(test_program, 'rs')
        print(res.compiler_message)
        self.assertEqual(res.status, ExecStatus.OK)
        self.assertEqual(res.stdout, 'Hello world!')
        self.assertEqual(res.stderr, '')
