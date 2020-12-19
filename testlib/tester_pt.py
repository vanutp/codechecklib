import os
import random
import string
from typing import List, Tuple

from . import Tester
from .const import ExecStatus, EXEC_STATUS_TO_PT_STATUS, MY_USER, CgroupSetupException


class TesterPtCompatible(Tester):
    def test_one_pt(self, compiled_path: str, timeout: int, has_internet: bool,
                    blacklist_dirs: List[str], language: str, input_file: str, output_file: str,
                    cgroups: List[str], results, test):
        result = self._execute_one(compiled_path, timeout, has_internet, blacklist_dirs, language, input_file,
                                   output_file, test[0], cgroups)
        if result.status == ExecStatus.INTERR:
            raise FileNotFoundError()
        results.append((EXEC_STATUS_TO_PT_STATUS[result.status], result.time if result.time else -1,
                        result.stdout, result.stderr))
        if result.status == ExecStatus.OK and result.stdout != test[1]:
            results[-1][0] = 2

    # Exec_result: 0 - OK
    #              1 - TL
    #              2 - WA
    #              3 - RE
    #              6 - ML
    # Result: (success: bool, List[Tuple[int, str, str]] (exec_result, stdout, stderr), first_error_test: int)
    #
    def run_pt(self, compiled_path: str, tests: List[Tuple[str, str]], timeout: int, memory: int, has_internet: bool,
               blacklist_dirs: List[str], language: str, input_file: str, output_file: str):
        results = []
        success = True
        first_error_test = -1
        cgroup_name = 'ts_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        setup_commands = [
            f'sudo cgcreate -a {MY_USER} -t {MY_USER}:ts_user -g memory:{cgroup_name}',
            f'sudo cgcreate -a {MY_USER} -t {MY_USER}:ts_user -g pids:{cgroup_name}',
            f'sudo chmod 660 /sys/fs/cgroup/memory/{cgroup_name}/tasks',
            f'sudo chmod 660 /sys/fs/cgroup/pids/{cgroup_name}/tasks',
            f'sudo su -c "echo {memory} > /sys/fs/cgroup/memory/{cgroup_name}/memory.limit_in_bytes"',
            f'sudo su -c "echo {memory} > /sys/fs/cgroup/memory/{cgroup_name}/memory.memsw.limit_in_bytes"'
            if os.path.isfile(f'/sys/fs/cgroup/memory/{cgroup_name}/memory.memsw.limit_in_bytes') else '',
            f'sudo su -c "echo 8 > /sys/fs/cgroup/pids/{cgroup_name}/pids.max"'
        ]
        for cmd in setup_commands:
            if code := os.system(cmd):
                raise CgroupSetupException(f'Command "{cmd}" failed with exit code {code}')
        for test_idx in range(len(tests)):
            test = tests[test_idx]
            self.test_one_pt(compiled_path, timeout, has_internet, blacklist_dirs, language, input_file, output_file,
                             [f'memory/{cgroup_name}', f'pids/{cgroup_name}'], results, test)
            if results[-1][0] != 0:
                first_error_test = first_error_test if first_error_test != -1 else test_idx
        os.system(f'sudo cgdelete memory:{cgroup_name}')
        os.system(f'sudo cgdelete pids:{cgroup_name}')
        return success, results, first_error_test


__all__ = ['TesterPtCompatible']
