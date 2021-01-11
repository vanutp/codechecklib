import unittest

from codechecklib import Tester
from codechecklib.const import ExecStatus


class TestCpp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tester = Tester()

    async def test_stdin_stdout_ok(self):
        test_program = '''#include <iostream>
using namespace std;
int main() 
{
    int a;
    cin >> a;
    a++;
    cout << a << endl;
    return 0; 
}'''
        res = await self.tester.run(test_program, 'cpp', '2')
        self.assertEqual(res.status, ExecStatus.OK)
        self.assertEqual(res.stdout, '3')

    async def test_compilation_flood(self):
        test_program = '''#include __FILE__
#include __FILE__'''
        res = await self.tester.run(test_program, 'cpp', '2')
        self.assertEqual(res.status, ExecStatus.CE)
        self.assertEqual(res.compiler_message, 'Compilation timed out')

    async def test_encoding(self):
        test_program = '''#include <iostream>
#include <string>
using namespace std;
int main()
{
  string text;
  cin >> text;
  unsigned char a = text[0];
  cout << int(a) << endl;
}'''
        res = await self.tester.run(test_program, 'cpp', 'а', data_encoding='cp1251')
        self.assertEqual(res.status, ExecStatus.OK)
        self.assertEqual(res.stdout, '224')
