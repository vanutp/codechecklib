import getpass
from enum import Enum
from types import SimpleNamespace

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
    'py_nl': ['env', 'bash', 'sh', 'python', 'python3', 'pylint'],
}

MY_USER = getpass.getuser()


class CgroupSetupException(Exception):
    pass


class ExecStatus(Enum):
    TL = 'TL'
    ML = 'ML'
    RE = 'RE'
    INTERR = 'INTERR'
    OK = 'OK'


EXEC_STATUS_TO_PT_STATUS = {
    ExecStatus.TL: 1,
    ExecStatus.ML: 6,
    ExecStatus.RE: 3,
    ExecStatus.INTERR: -1,
    ExecStatus.OK: 0
}


class ExecResult(SimpleNamespace):
    status: ExecStatus
    time: float
    stdout: str
    stderr: str


__all__ = ['LANGUAGES', 'COMPILE_COMMANDS', 'EXEC_COMMANDS', 'AVAILABLE_BINARIES', 'MY_USER', 'CgroupSetupException',
           'ExecStatus', 'EXEC_STATUS_TO_PT_STATUS', 'ExecResult']
