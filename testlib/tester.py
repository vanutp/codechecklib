import asyncio
import os
import random
import string
from asyncio import Queue
from asyncio.subprocess import create_subprocess_exec, PIPE, DEVNULL, Process
from tempfile import NamedTemporaryFile
from time import time
from typing import List, Tuple

from .const import COMPILE_COMMANDS, AVAILABLE_BINARIES, ExecResult, EXEC_COMMANDS, ExecStatus, \
    CgroupSetupException, TestResult, MY_USER, TestingException
from .sandbox import get_sandbox_command


class Tester:
    def __init__(self):
        pass

    async def compile(self, code, blacklist_dirs: List[str], language: str):
        file = NamedTemporaryFile('w+b', delete=False)
        filename = file.name
        file.write(code.encode('utf-8'))
        file.close()
        cmd, compiled_filename = COMPILE_COMMANDS[language](filename)
        cmd = get_sandbox_command(False, blacklist_dirs, cmd, AVAILABLE_BINARIES[language], True)
        start_time = time()
        process = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        res = await process.communicate()
        compiler_message = res[0].decode() + '\n' + res[1].decode()
        compilation_time = time() - start_time
        if process.returncode == 127:
            raise FileNotFoundError()
        is_success = process.returncode == 0
        return is_success, compiled_filename, compilation_time, compiler_message

    async def _run_commands(self, commands: List[List[str]], exception=TestingException):
        for cmd in commands:
            process = await create_subprocess_exec(*cmd)
            await process.wait()
            if process.returncode:
                raise exception(f'Command "{cmd}" failed with exit code {process.returncode}')

    async def _setup_cgroup(self, memory, pids, user):
        if not os.path.isfile('/sys/fs/cgroup/cgroup.subtree_control'):
            raise CgroupSetupException('cgroups v2 required')
        cgroup_name = user
        cgroup_base_dir = f'/sys/fs/cgroup/ts'
        if not os.path.isdir(cgroup_base_dir):
            commands = [
                f'mkdir {cgroup_base_dir}',
                f'echo +memory +pids > {cgroup_base_dir}/cgroup.subtree_control',
                f'mkdir {cgroup_base_dir}/root'
            ]
            await self._run_commands(list(map(lambda x: ['sudo', 'bash', '-c', x], commands)), CgroupSetupException)
        setup_commands_root = [
            f'echo {os.getpid()} > {cgroup_base_dir}/root/cgroup.procs',
            f'mkdir {cgroup_base_dir}/{cgroup_name}',
            f'chown -R {MY_USER}:ts_user {cgroup_base_dir}',
            f'chmod -R g+w {cgroup_base_dir}',
        ]
        setup_commands = [
            f'echo {memory} > {cgroup_base_dir}/{cgroup_name}/memory.max',
            f'echo 0 > {cgroup_base_dir}/{cgroup_name}/memory.swap.max',
            f'echo {pids} > {cgroup_base_dir}/{cgroup_name}/pids.max',
        ]
        await self._run_commands(list(map(lambda x: ['sudo', 'bash', '-c', x], setup_commands_root)) +
                                 list(map(lambda x: ['sudo', '-i', '-u', user, 'bash', '-c', x], setup_commands)),
                                 CgroupSetupException)
        return f'{cgroup_base_dir}/{cgroup_name}'

    async def _remove_cgroup(self, cgroup_path):
        await self._run_commands([['sudo', 'rmdir', cgroup_path]])

    async def _execute_one(self, compiled_path: str, timeout: int, memory: int,
                           has_internet: bool, blacklist_dirs: List[str], language: str,
                           input_file: str, output_file: str, stdin: str) -> ExecResult:
        await self._run_commands([['chmod', '755', compiled_path]])
        # ВНИМАНИЕ ВНИМАНИЕ ВНИМАНИЕ
        # ПЕРЕД ПОПЫТКОЙ ПОСТАВИТЬ СЮДА ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ,
        # ПРОЙДИ В КОНЕЦ ЭТОЙ ФУНКЦИИ И ПОСМОТРИ НА ВЫПОЛНЯЮЩУЮСЯ КОМАНДУ
        user = 'ts_user_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        await self._run_commands([['sudo', 'useradd', '-m', '-g', 'ts_user', user]])
        cgroup_path = await self._setup_cgroup(memory, 8, user)

        if input_file:
            await self._run_commands([['sudo', 'bash', '-c' f'echo {stdin.encode()} > /home/{user}/{input_file}']])

        cmd = get_sandbox_command(has_internet, blacklist_dirs, EXEC_COMMANDS[language](compiled_path),
                                  AVAILABLE_BINARIES[language], True, cgroup_path, user)
        process = await create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

        async def background_execute(q: Queue, process: Process, stdin: str):
            await q.put(await process.communicate(stdin.encode()))

        q = Queue()
        asyncio.create_task(background_execute(q, process, stdin if not input_file else ''))
        start_time = time()
        try:
            await asyncio.wait_for(process.wait(), timeout / 1000)
        except asyncio.exceptions.TimeoutError:
            pass

        async def inner():
            if process.returncode is None:
                procs = (await (await create_subprocess_exec('cat', f'{cgroup_path}/cgroup.procs',
                                                             stdout=PIPE, stderr=PIPE))
                         .communicate())[0].decode().split('\n')
                for proc in procs:
                    await (await create_subprocess_exec('sudo', 'kill', '-9', proc,
                                                        stdout=DEVNULL, stderr=DEVNULL)).wait()
                assert process.returncode is not None
                return ExecResult(status=ExecStatus.TL, time=None, stdout=None, stderr=None)

            if process.returncode == 127:
                raise FileNotFoundError(process.stderr)

            result = await q.get()
            run_time = time() - start_time
            stdout: str = '\n'.join([x.rstrip(' ') for x in result[0].decode().split('\n')]).rstrip(
                '\r\n').rstrip('\n')
            stderr: str = '\n'.join([x.rstrip(' ') for x in result[1].decode().split('\n')]).rstrip(
                '\r\n').rstrip('\n')

            if process.returncode != 0:
                memory_events = (await (await create_subprocess_exec('cat', f'{cgroup_path}/memory.events',
                                                                     stdout=PIPE, stderr=PIPE))
                                 .communicate())[0].decode().split('\n')
                for line in memory_events:
                    if not line:
                        continue
                    event, value = line.split()
                    value = int(value)
                    if event == 'oom_kill' and value > 0:
                        return ExecResult(status=ExecStatus.ML, time=run_time, stdout=stdout, stderr=stderr)
                return ExecResult(status=ExecStatus.RE, time=run_time, stdout=stdout, stderr=stderr)

            if output_file:
                result = await (await create_subprocess_exec('sudo', 'cat', f'cat /home/{user}/{output_file}',
                                                             stdin=PIPE, stdout=PIPE, stderr=PIPE)).communicate()
                stdout = '\n'.join([x.rstrip(' ') for x in result[0].decode().split('\n')]).rstrip('\r\n').rstrip('\n')
            return ExecResult(status=ExecStatus.OK, time=run_time, stdout=stdout, stderr=stderr)

        res = await inner()
        await self._remove_cgroup(cgroup_path)
        await self._run_commands([['sudo', 'userdel', user], ['sudo', 'rm', '-rf', f'/home/{user}']])
        return res

    async def run(self, compiled_path: str, language: str, stdin: str = '', blacklist_dirs: List[str] = [],
                  timeout: int = 2000, memory: int = 1024 * 1024 * 256, has_internet: bool = False,
                  input_file: str = '', output_file: str = '') -> ExecResult:
        return await self._execute_one(compiled_path, timeout, memory, has_internet, blacklist_dirs, language,
                                       input_file,
                                       output_file, stdin)

    async def test(self, compiled_path: str, language: str, tests: List[Tuple[str, str]],
                   blacklist_dirs: List[str] = [],
                   timeout: int = 2000, memory: int = 1024 * 1024 * 256, has_internet: bool = False,
                   input_file: str = '', output_file: str = '') -> TestResult:
        result = TestResult(results=[], success=True, first_error_test=-1)
        for test_idx in range(len(tests)):
            test = tests[test_idx]
            result_now = await self._execute_one(compiled_path, timeout, memory, has_internet, blacklist_dirs, language,
                                                 input_file, output_file, test[0])
            result.results.append(result_now)
            if result_now.status == ExecStatus.OK and result_now.stdout != test[1]:
                result.results[-1].status = ExecStatus.WA
            if result.results[-1].status != ExecStatus.OK:
                result.success = False
                result.first_error_test = result.first_error_test if result.first_error_test != -1 else test_idx
        return result


__all__ = ['Tester']
