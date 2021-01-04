import asyncio
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile
from time import time

from tqdm import tqdm

from testlib import Tester

tester = Tester()


async def timeit(func, cnt):
    real_time_total = 0
    for _ in tqdm(range(cnt)):
        real_time = time()
        await func()
        real_time_total += time() - real_time
    return real_time_total / cnt


async def main():
    code = '[print(i) for i in range(1874)]'
    f = NamedTemporaryFile('w', delete=False)
    f.write(code)
    filename = f.name
    f.close()

    async def func1():
        Popen(['python3', filename], stdin=PIPE, stdout=PIPE, stderr=PIPE).wait()

    async def func2():
        await tester.run(code, 'py_nl', '')

    a1 = await timeit(func1, 100)
    a2 = await timeit(func2, 100)
    print(a1, a2, a2 / a1)


if __name__ == '__main__':
    asyncio.run(main())
