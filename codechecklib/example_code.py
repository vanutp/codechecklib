EXAMPLE_CODES = {
    'cs': '''using System;

namespace Example
{
    public class Program
    {
        public static void Main(string[] args)
        {
            Console.WriteLine("Hello, world!");
        }
    }
}''',
    'cpp': '''#include <iostream>

using namespace std;

int main() 
{
    cout << "Hello, world!" << endl;
    return 0; 
}''',
    'c': '''#include <stdio.h>
int main() {
   printf("Hello, world!");
   return 0;
}''',
    'py': 'print(\'Hello, world!\')',
    'rb': 'puts \'Hello, world!\'',
    'js': 'console.log(\'Hello, world!\')'
}
EXAMPLE_CODES['py_nl'] = EXAMPLE_CODES['py']

__all__ = ['EXAMPLE_CODES']
