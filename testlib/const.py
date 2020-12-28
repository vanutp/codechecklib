import getpass
import os
from enum import Enum
from types import SimpleNamespace
from typing import List

LANGUAGES = {'cpp': 'C++', 'cs': 'C#', 'c': 'C', 'py': 'Python'}

COMPILE_COMMANDS = {
    'cs': lambda filename: (['mcs', '-optimize', '-nologo', f'-out:' + filename + '.o', filename], filename + '.o'),
    'cpp': lambda filename: (['g++', '-x', 'c++', '-o', filename + '.o', filename], filename + '.o'),
    'c': lambda filename: (['gcc', '-x', 'c++', '-o', filename + '.o', filename], filename + '.o'),
    'py': lambda filename: (['pylint', '--disable=R,C', filename], filename),
    'py_nl': lambda filename: (['echo'], filename),
}
EXEC_COMMANDS = {
    'cs': lambda filename: ['mono', filename],
    'cpp': lambda filename: [filename],
    'c': lambda filename: [filename],
    'py': lambda filename: ['python3', filename],
    'py_nl': lambda filename: ['python3', filename],
}
AVAILABLE_BINARIES = {
    'cs': ['env', 'bash', 'sh', 'mono', 'mcs'],
    'cpp': ['env', 'bash', 'sh', 'g++', 'ld', 'as'],
    'c': ['env', 'bash', 'sh', 'gcc', 'ld', 'as'],
    'py': ['env', 'bash', 'sh', 'python', 'python3', 'pylint'],
    'py_nl': ['env', 'bash', 'sh', 'python', 'python3', 'echo'],
}

MY_USER = getpass.getuser()


class TestingException(Exception):
    pass


class CgroupSetupException(TestingException):
    pass


class ExecStatus(Enum):
    TL = 'TL'
    ML = 'ML'
    RE = 'RE'
    OK = 'OK'
    WA = 'WA'


class ExecResult(SimpleNamespace):
    status: ExecStatus
    time: float
    stdout: str
    stderr: str


class TestResult(SimpleNamespace):
    success: bool
    results: List[ExecResult]
    first_error_test: int


__all__ = ['LANGUAGES', 'COMPILE_COMMANDS', 'EXEC_COMMANDS', 'AVAILABLE_BINARIES', 'MY_USER',
           'TestingException', 'CgroupSetupException', 'ExecStatus', 'ExecResult', 'TestResult']
