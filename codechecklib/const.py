import getpass
from enum import Enum
from types import SimpleNamespace
from typing import List

LANGUAGES = {'cpp': 'C++', 'cs': 'C#', 'c': 'C', 'py': 'Python', 'rb': 'Ruby', 'js': 'JavaScript'}

COMPILE_COMMANDS = {
    'cs': lambda filename: ['mcs', '-optimize', '-nologo', '-out:' + filename + '.o', filename],
    'cpp': lambda filename: ['g++', '-x', 'c++', '-std=c++20', '-o', filename + '.o', filename],
    'c': lambda filename: ['gcc', '-x', 'c++', '-o', filename + '.o', filename],
    'py': lambda filename: [['pylint', '--disable=R,C', filename], ['cp', filename, filename + '.o']],
    'py_nl': lambda filename: ['cp', filename, filename + '.o'],
    'rb': lambda filename: ['cp', filename, filename + '.o'],
    'js': lambda filename: ['cp', filename, filename + '.o'],
}
EXEC_COMMANDS = {
    'cs': lambda filename: ['mono', filename],
    'cpp': lambda filename: [filename],
    'c': lambda filename: [filename],
    'py': lambda filename: ['python3', filename],
    'py_nl': lambda filename: ['python3', filename],
    'rb': lambda filename: ['ruby', filename],
    'js': lambda filename: ['node', filename],
}
COMMON_AVAILABLE_BINARIES = ['env', 'bash', 'sh']
AVAILABLE_BINARIES = {
    'cs': ['mono', 'mcs'],
    'cpp': ['g++', 'ld', 'as'],
    'c': ['gcc', 'ld', 'as'],
    'py': ['python', 'python3', 'pylint', 'cp'],
    'py_nl': ['python', 'python3', 'cp'],
    'rb': ['ruby', 'cp'],
    'js': ['node', 'cp'],
}

MY_USER = getpass.getuser()


class TestingException(Exception):
    pass


class CgroupSetupException(TestingException):
    pass


class ExecStatus(str, Enum):
    CE = 'CE'
    TL = 'TL'
    ML = 'ML'
    RE = 'RE'
    OK = 'OK'
    WA = 'WA'


class ExecResult(SimpleNamespace):
    status: ExecStatus
    compilation_time: float
    compiler_message: str
    time: float
    stdout: str
    stderr: str


class TestResult(SimpleNamespace):
    success: bool
    compilation_time: float
    compiler_message: str
    compilation_error: bool
    results: List[ExecResult]
    first_error_test: int


__all__ = ['LANGUAGES', 'COMPILE_COMMANDS', 'EXEC_COMMANDS', 'COMMON_AVAILABLE_BINARIES',
           'AVAILABLE_BINARIES', 'MY_USER', 'TestingException', 'CgroupSetupException',
           'ExecStatus', 'ExecResult', 'TestResult']
