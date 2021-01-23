import asyncio
import os
import random
import string
from asyncio import Queue
from asyncio.subprocess import create_subprocess_exec, PIPE, DEVNULL, Process
from tempfile import mkdtemp
from time import time
from typing import List, Tuple

from .const import COMPILE_COMMANDS, AVAILABLE_BINARIES, ExecResult, EXEC_COMMANDS, ExecStatus, \
    CgroupSetupException, TestResult, MY_USER, TestingException, COMMON_AVAILABLE_BINARIES
from .sandbox import get_sandbox_command


class Tester:
    def __init__(self):
        pass

    async def _run_commands(self, commands: List[List[str]], exception=TestingException):
        for cmd in commands:
            process = await create_subprocess_exec(*cmd, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
            await process.wait()
            if process.returncode:
                raise exception(f'Command "{cmd}" failed with exit code {process.returncode}')

    async def _setup_cgroup(self, memory, pids, user):
        if not os.path.isfile('/sys/fs/cgroup/cgroup.subtree_control'):
            raise CgroupSetupException('cgroups v2 required')
        cgroup_name = user
        cgroup_base_dir = '/sys/fs/cgroup/ts'
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

    async def _get_temp_dir(self):
        if not os.path.isdir('/ts_tmp'):
            await self._run_commands([['sudo', 'mkdir', '/ts_tmp'],
                                      ['sudo', 'chown', f'{MY_USER}:ts_user', '/ts_tmp'],
                                      ['sudo', 'chmod', '755', '/ts_tmp']])
        res = mkdtemp(dir='/ts_tmp')
        await self._run_commands([['sudo', 'mount', '-t', 'tmpfs', '-o', 'size=100m,nodev,nosuid', 'tmpfs', res],
                                  ['sudo', 'chown', f'{MY_USER}:ts_user', res],
                                  ['sudo', 'chmod', '750', res]])
        return res

    async def _remove_temp_dir(self, name):
        await self._run_commands([['sudo', 'umount', name],
                                  ['sudo', 'rm', '-rf', name]])

    async def _compile(self, code, blacklist_dirs: List[str], language: str, tmpdir: str, timeout: int, memory: int,
                       encoding: str, max_proc: int):
        filename = os.path.join(tmpdir, 'code')
        file = open(filename, 'wb')
        file.write(code.encode(encoding))
        file.close()
        cmds = COMPILE_COMMANDS[language](filename)
        compilation_time = 0
        compiler_message = ''
        if len(cmds) == 0 or not isinstance(cmds[0], list):
            cmds = [cmds]

        # ВНИМАНИЕ ВНИМАНИЕ ВНИМАНИЕ
        # ПЕРЕД ПОПЫТКОЙ ПОСТАВИТЬ СЮДА ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ,
        # ПРОЙДИ В КОНЕЦ ЭТОЙ ФУНКЦИИ И ПОСМОТРИ НА ВЫПОЛНЯЮЩУЮСЯ КОМАНДУ
        user = 'ts_user_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        await self._run_commands([['sudo', 'useradd', '-m', '-g', 'ts_user', user],
                                  ['sudo', 'chown', '-R', user, tmpdir]])
        cgroup_path = await self._setup_cgroup(memory, max_proc, user)

        try:
            for cmd in cmds:
                cmd = get_sandbox_command(False, blacklist_dirs, cmd,
                                          COMMON_AVAILABLE_BINARIES + AVAILABLE_BINARIES[language],
                                          True, cgroup_path, user)
                process = await create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

                async def background_execute(q: Queue, process: Process):
                    await q.put(await process.communicate())

                q = Queue()
                asyncio.create_task(background_execute(q, process))
                start_time = time()
                try:
                    await asyncio.wait_for(process.wait(), timeout / 1000)
                except asyncio.exceptions.TimeoutError:
                    pass

                if process.returncode is None:
                    procs = (await (await create_subprocess_exec('cat', f'{cgroup_path}/cgroup.procs',
                                                                 stdout=PIPE, stderr=PIPE))
                             .communicate())[0].decode(encoding, errors='replace').split('\n')
                    for proc in procs:
                        await (await create_subprocess_exec('sudo', 'kill', '-9', proc,
                                                            stdout=DEVNULL, stderr=DEVNULL)).wait()
                    assert process.returncode is not None
                    return False, timeout / 1000, 'Compilation timed out'

                result = await q.get()
                compilation_time += time() - start_time
                compiler_message = (compiler_message + '\n' + result[0].decode(encoding, errors='replace') + '\n' +
                                    result[1].decode(encoding, errors='replace')).strip()

                if process.returncode != 0:
                    memory_events = (await (await create_subprocess_exec('cat', f'{cgroup_path}/memory.events',
                                                                         stdout=PIPE, stderr=PIPE))
                                     .communicate())[0].decode(encoding, errors='replace').split('\n')
                    for line in memory_events:
                        if not line:
                            continue
                        event, value = line.split()
                        value = int(value)
                        if event == 'oom_kill' and value > 0:
                            return False, compilation_time, 'Compilation out of memory'
                    return False, compilation_time, compiler_message
            return True, compilation_time, compiler_message
        finally:
            await self._remove_cgroup(cgroup_path)
            await self._run_commands([['sudo', 'userdel', user], ['sudo', 'rm', '-rf', f'/home/{user}']])

    async def _execute_one(self, tmpdir: str, timeout: int, memory: int,
                           has_internet: bool, blacklist_dirs: List[str], language: str,
                           input_file: str, output_file: str, stdin: str, encoding: str, max_proc: int) -> ExecResult:
        # ВНИМАНИЕ ВНИМАНИЕ ВНИМАНИЕ
        # ПЕРЕД ПОПЫТКОЙ ПОСТАВИТЬ СЮДА ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ,
        # ПРОЙДИ В КОНЕЦ ЭТОЙ ФУНКЦИИ И ПОСМОТРИ НА ВЫПОЛНЯЮЩУЮСЯ КОМАНДУ
        user = 'ts_user_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        await self._run_commands([['sudo', 'useradd', '-m', '-g', 'ts_user', user],
                                  ['sudo', 'chown', '-R', user, tmpdir]])
        cgroup_path = await self._setup_cgroup(memory, max_proc, user)

        try:
            if input_file:
                proc = await create_subprocess_exec('sudo', 'tee', f'/home/{user}/{input_file}',
                                                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
                stdout, stderr = map(lambda x: x.decode(encoding, errors='replace'),
                                     await proc.communicate(stdin.encode(encoding)))
                if proc.returncode:
                    raise TestingException(f'Failed to write to input_file, {stderr}')

            cmd = get_sandbox_command(has_internet, blacklist_dirs,
                                      EXEC_COMMANDS[language](os.path.join(tmpdir, 'code.o')),
                                      COMMON_AVAILABLE_BINARIES + AVAILABLE_BINARIES[language],
                                      True, cgroup_path, user)
            process = await create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

            async def background_execute(q: Queue, process: Process, stdin: str):
                await q.put(await process.communicate(stdin.encode(encoding)))

            q = Queue()
            asyncio.create_task(background_execute(q, process, stdin if not input_file else ''))
            start_time = time()
            try:
                await asyncio.wait_for(process.wait(), timeout / 1000)
            except asyncio.exceptions.TimeoutError:
                pass

            if process.returncode is None:
                procs = (await (await create_subprocess_exec('cat', f'{cgroup_path}/cgroup.procs',
                                                             stdout=PIPE, stderr=PIPE))
                         .communicate())[0].decode(encoding, errors='replace').split('\n')
                for proc in procs:
                    await (await create_subprocess_exec('sudo', 'kill', '-9', proc,
                                                        stdout=DEVNULL, stderr=DEVNULL)).wait()
                assert process.returncode is not None
                return ExecResult(status=ExecStatus.TL, time=None, stdout=None, stderr=None)

            result = await q.get()
            run_time = time() - start_time
            stdout: str = '\n'.join([x.rstrip(' ') for x in result[0].decode(encoding, errors='replace').
                                    split('\n')]).rstrip('\r\n').rstrip('\n')
            stderr: str = '\n'.join([x.rstrip(' ') for x in result[1].decode(encoding, errors='replace').
                                    split('\n')]).rstrip('\r\n').rstrip('\n')

            if process.returncode != 0:
                memory_events = (await (await create_subprocess_exec('cat', f'{cgroup_path}/memory.events',
                                                                     stdout=PIPE, stderr=PIPE))
                                 .communicate())[0].decode(encoding, errors='replace').split('\n')
                for line in memory_events:
                    if not line:
                        continue
                    event, value = line.split()
                    value = int(value)
                    if event == 'oom_kill' and value > 0:
                        return ExecResult(status=ExecStatus.ML, time=run_time, stdout=stdout, stderr=stderr)
                return ExecResult(status=ExecStatus.RE, time=run_time, stdout=stdout, stderr=stderr)

            if output_file:
                result = await (await create_subprocess_exec('sudo', 'cat', f'/home/{user}/{output_file}',
                                                             stdin=PIPE, stdout=PIPE, stderr=PIPE)).communicate()
                stdout = '\n'.join([x.rstrip(' ') for x in result[0].decode(encoding, errors='replace').
                                   split('\n')]).rstrip('\r\n').rstrip('\n')
            return ExecResult(status=ExecStatus.OK, time=run_time, stdout=stdout, stderr=stderr)

        finally:
            await self._remove_cgroup(cgroup_path)
            await self._run_commands([['sudo', 'userdel', user], ['sudo', 'rm', '-rf', f'/home/{user}']])

    async def run(self, code: str, language: str, stdin: str = '', blacklist_dirs: List[str] = [],
                  # pylint: disable=W0102
                  timeout: int = 2000, memory: int = 1024 * 1024 * 256, has_internet: bool = False,
                  input_file: str = '', output_file: str = '',
                  compilation_timeout: int = 4000, compilation_memory: int = 1024 * 1024 * 256,
                  data_encoding: str = 'utf-8', source_encoding: str = 'utf-8',
                  max_proc: int = 10, compilation_max_proc: int = 10) -> ExecResult:
        tmpdir = await self._get_temp_dir()
        try:
            is_success, compilation_time, compiler_message = await self._compile(code, blacklist_dirs, language, tmpdir,
                                                                                 compilation_timeout,
                                                                                 compilation_memory, source_encoding,
                                                                                 compilation_max_proc)
            if is_success:
                res = await self._execute_one(tmpdir, timeout, memory, has_internet, blacklist_dirs, language,
                                              input_file, output_file, stdin, data_encoding, max_proc)
            else:
                res = ExecResult(status=ExecStatus.CE, time=None, stdout=None, stderr=None)
            res.compilation_time = compilation_time
            res.compiler_message = compiler_message
            return res
        finally:
            await self._remove_temp_dir(tmpdir)

    async def test(self, code: str, language: str, tests: List[Tuple[str, str]], blacklist_dirs: List[str] = [],
                   # pylint: disable=W0102
                   timeout: int = 2000, memory: int = 1024 * 1024 * 256, has_internet: bool = False,
                   input_file: str = '', output_file: str = '',
                   compilation_timeout: int = 4000, compilation_memory: int = 1024 * 1024 * 256,
                   data_encoding: str = 'utf-8', source_encoding: str = 'utf-8',
                   max_proc: int = 10, compilation_max_proc: int = 10) -> TestResult:
        tmpdir = await self._get_temp_dir()
        try:
            is_success, compilation_time, compiler_message = await self._compile(code, blacklist_dirs, language, tmpdir,
                                                                                 compilation_timeout,
                                                                                 compilation_memory, source_encoding,
                                                                                 compilation_max_proc)
            if is_success:
                result = TestResult(results=[], success=True, first_error_test=-1, compilation_error=False)
                for test_idx, test in enumerate(tests):
                    result_now = await self._execute_one(tmpdir, timeout, memory, has_internet, blacklist_dirs,
                                                         language, input_file, output_file, test[0], data_encoding,
                                                         max_proc)
                    result.results.append(result_now)
                    if result_now.status == ExecStatus.OK and result_now.stdout != test[1]:
                        result.results[-1].status = ExecStatus.WA
                    if result.results[-1].status != ExecStatus.OK:
                        result.success = False
                        result.first_error_test = result.first_error_test if result.first_error_test != -1 else test_idx
            else:
                result = TestResult(success=False, compilation_error=True)
            result.compilation_time = compilation_time
            result.compiler_message = compiler_message
            return result
        finally:
            await self._remove_temp_dir(tmpdir)


__all__ = ['Tester']
