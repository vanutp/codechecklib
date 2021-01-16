import getpass
from enum import Enum
from types import SimpleNamespace
from typing import List

LANGUAGES = {'cpp': 'C++', 'cs': 'C#', 'c': 'C', 'py': 'Python', 'rb': 'Ruby'}

COMPILE_COMMANDS = {
    'cs': lambda filename: ['mcs', '-optimize', '-nologo', '-out:' + filename + '.o', filename],
    'cpp': lambda filename: ['g++', '-x', 'c++', '-o', filename + '.o', filename],
    'c': lambda filename: ['gcc', '-x', 'c++', '-o', filename + '.o', filename],
    'py': lambda filename: [['pylint', '--disable=R,C', filename], ['cp', filename, filename + '.o']],
    'py_nl': lambda filename: ['cp', filename, filename + '.o'],
    'rb': lambda filename: ['cp', filename, filename + '.o'],
}
EXEC_COMMANDS = {
    'cs': lambda filename: ['mono', filename],
    'cpp': lambda filename: [filename],
    'c': lambda filename: [filename],
    'py': lambda filename: ['python3', filename],
    'py_nl': lambda filename: ['python3', filename],
    'rb': lambda filename: ['ruby', filename],
}
AVAILABLE_BINARIES = {
    'cs': ['env', 'bash', 'sh', 'mono', 'mcs'],
    'cpp': ['env', 'bash', 'sh', 'g++', 'ld', 'as'],
    'c': ['env', 'bash', 'sh', 'gcc', 'ld', 'as'],
    'py': ['env', 'bash', 'sh', 'python', 'python3', 'pylint', 'cp'],
    'py_nl': ['env', 'bash', 'sh', 'python', 'python3', 'cp'],
    'rb': ['env', 'bash', 'sh', 'ruby', 'cp'],
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


__all__ = ['LANGUAGES', 'COMPILE_COMMANDS', 'EXEC_COMMANDS', 'AVAILABLE_BINARIES', 'MY_USER',
           'TestingException', 'CgroupSetupException', 'ExecStatus', 'ExecResult', 'TestResult']
