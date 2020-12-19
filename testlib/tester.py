import os
import random
import string
from queue import Queue
from subprocess import Popen, PIPE
from subprocess import TimeoutExpired as SubprocessTimeoutExpired
from tempfile import NamedTemporaryFile
from time import sleep
from time import time
from typing import List

from .const import COMPILE_COMMANDS, AVAILABLE_BINARIES, ExecResult, EXEC_COMMANDS, ExecStatus, \
    CgroupSetupException, MY_USER
from .killable_thread import KillableThread
from .sandbox import get_sandbox_command


class Tester:
    def __init__(self):
        pass

    def compile(self, code, blacklist_dirs: List[str], language: str):
        file = NamedTemporaryFile('w+b', delete=False)
        filename = file.name
        file.write(code.encode('utf-8'))
        file.close()
        cmd, compiled_filename = COMPILE_COMMANDS[language](filename)
        cmd = get_sandbox_command(False, blacklist_dirs, cmd, AVAILABLE_BINARIES[language], True)
        start_time = time()
        process = Popen(cmd, stdout=PIPE, stderr=PIPE)
        res = process.communicate()
        compiler_message = res[0].decode() + '\n' + res[1].decode()
        compilation_time = time() - start_time
        if process.returncode == 127:
            raise FileNotFoundError()
        is_success = process.returncode == 0
        return is_success, compiled_filename, compilation_time, compiler_message

    def _background_execute(self, queue: Queue, process: Popen, input: str):
        queue.put(process.communicate(input.encode()))

    def _execute_one(self, compiled_path: str, timeout: int, has_internet: bool, blacklist_dirs: List[str],
                     language: str, input_file: str, output_file: str, stdin: str, cgroup: str) -> ExecResult:
        create_user = input_file or output_file
        user = ''
        if create_user:
            user = 'ts_user_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            os.system(f'sudo useradd -m -g ts_user {user}')

        if input_file:
            Popen(['sudo', 'su', '-c' f'echo {stdin.encode()} > /home/{user}/{input_file}']).wait()

        q = Queue()
        cmd = get_sandbox_command(has_internet, blacklist_dirs, EXEC_COMMANDS[language](compiled_path),
                                  AVAILABLE_BINARIES[language], True, timeout, cgroup, user)
        process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        thread = KillableThread(target=self._background_execute,
                                args=(q, process, stdin if not input_file else ''))
        start_time = time()
        thread.start()
        pid = process.pid
        try:
            process.wait(timeout)
        except SubprocessTimeoutExpired:
            pass
        else:
            sleep(0.1)

        def inner():
            if thread.is_alive():
                thread.kill()
                process.kill()
                return ExecResult(status=ExecStatus.TL, time=None, stdout=None, stderr=None)

            if process.returncode == 127:
                return ExecResult(status=ExecStatus.INTERR, time=None, stdout=None, stderr=None)

            run_time = time() - start_time
            result = q.get()
            stdout: str = '\n'.join([x.rstrip(' ') for x in result[0].decode().split('\n')]).rstrip(
                '\r\n').rstrip('\n')
            stderr: str = result[1].decode()

            if process.returncode != 0:
                kernlog = Popen(['sudo', 'tail', '-n', '100', '/var/log/kern.log'],
                                stdout=PIPE, stderr=PIPE).communicate()[0].decode().split('\n')
                for i, line in enumerate(kernlog):
                    if str(pid) in line and 'Tasks state' in kernlog[i - 2]:
                        return ExecResult(status=ExecStatus.ML, time=run_time, stdout=stdout, stderr=stderr)
                return ExecResult(status=ExecStatus.RE, time=run_time, stdout=stdout, stderr=stderr)

            if output_file:
                result = Popen(['sudo', 'cat', f'cat /home/{user}/{output_file}'], stdin=PIPE, stdout=PIPE,
                               stderr=PIPE).communicate()
                stdout = '\n'.join(
                    [x.rstrip(' ') for x in result[0].decode().split('\n')]).rstrip(
                    '\r\n').rstrip('\n')
            return ExecResult(status=ExecStatus.OK, time=run_time, stdout=stdout, stderr=stderr)

        res = inner()
        if create_user:
            os.system(f'sudo userdel {user}')
            os.system(f'sudo rm -rf /home/{user}')
        return res

    def run(self, compiled_path: str, language: str, stdin: str, blacklist_dirs: List[str] = [],
            timeout: int = 2000, memory: int = 268435456, has_internet: bool = False,
            input_file: str = '', output_file: str = '') -> ExecResult:
        cgroup = 'ts_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        r = os.system(f'sudo cgcreate -a {MY_USER} -t {MY_USER}:ts_user -g memory:{cgroup}')
        r0 = os.system(f'sudo chmod 660 /sys/fs/cgroup/memory/{cgroup}/tasks')
        r1 = os.system(f'sudo su -c "echo {memory} > /sys/fs/cgroup/memory/{cgroup}/memory.limit_in_bytes"')
        r2 = 0
        if os.path.isfile(f'/sys/fs/cgroup/memory/{cgroup}/memory.memsw.limit_in_bytes'):
            r2 = os.system(f'sudo su -c "echo {memory} > /sys/fs/cgroup/memory/{cgroup}/memory.memsw.limit_in_bytes"')
        if r or r0 or r1 or r2:
            raise CgroupSetupException()
        res = self._execute_one(compiled_path, timeout, has_internet, blacklist_dirs, language, input_file,
                                output_file, stdin, cgroup)
        os.system(f'sudo cgdelete memory:{cgroup}')
        return res


__all__ = ['Tester']
