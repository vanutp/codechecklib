import unittest

from codechecklib import Tester
from codechecklib.const import ExecStatus


class TestJs(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tester = Tester()

    async def test_stdin_stdout_ok(self):
        test_program = '''const fs = require('fs');
const data = fs.readFileSync(process.stdin.fd, 'utf-8');
console.log(parseInt(data) + 1);
'''
        res = await self.tester.run(test_program, 'js', '2')
        self.assertEqual(res.status, ExecStatus.OK)
        self.assertEqual(res.stdout, '3')
