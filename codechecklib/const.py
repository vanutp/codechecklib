import getpass
from enum import Enum
from types import SimpleNamespace
from typing import List

LANGUAGES = {
    'cpp': 'C++',
    'cs': 'C#',
    'c': 'C',
    'py': 'Python',
    'rb': 'Ruby',
    'js': 'JavaScript',
    'rs': 'Rust',
    'hs': 'Haskell',
}

COMPILE_COMMANDS = {
    'cs': lambda filename: ['mcs', '-optimize', '-nologo', '-out:' + filename + '.out', filename],
    'cpp': lambda filename: ['g++', '-x', 'c++', '-std=c++20', '-o', filename + '.out', filename],
    'c': lambda filename: ['gcc', '-x', 'c++', '-o', filename + '.out', filename],
    'py': lambda filename: [['pylint', '--disable=R,C', filename], ['cp', filename, filename + '.out']],
    'py_nl': lambda filename: ['cp', filename, filename + '.out'],
    'rb': lambda filename: ['cp', filename, filename + '.out'],
    'js': lambda filename: ['cp', filename, filename + '.out'],
    'rs': lambda filename: ['rustc', filename, '-o', filename + '.out'],
    'hs': lambda filename: ['ghc', '-x', 'hs', filename, '-o', filename + '.out'],
}
EXEC_COMMANDS = {
    'cs': lambda filename: ['mono', filename],
    'cpp': lambda filename: [filename],
    'c': lambda filename: [filename],
    'py': lambda filename: ['python3', filename],
    'py_nl': lambda filename: ['python3', filename],
    'rb': lambda filename: ['ruby', filename],
    'js': lambda filename: ['node', filename],
    'rs': lambda filename: [filename],
    'hs': lambda filename: [filename],
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
    'rs': ['rustc', 'cc', 'ld'],
    'hs': ['ghc', 'cc', 'as', 'ld', 'ld.gold']
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
