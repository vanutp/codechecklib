EXAMPLE_CODES = {
    'cs': '''using System;

namespace Example
{
    public class Program
    {
        public static void Main(string[] args)
        {
            Console.WriteLine(Console.ReadLine());
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
   printf("Hello, World!");
   return 0;
}''',
    'py': 'print(\'Hello, World!\')'
}

__all__ = ['EXAMPLE_CODES']
