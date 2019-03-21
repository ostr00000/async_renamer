import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from queue import Queue
from typing import Callable, Generator, TypeVar, AsyncIterator

A = TypeVar('A')
B = TypeVar('B')


async def threadProducer(fun: Callable[[A], B], gen: Generator[A, None, None],
                         workers: int = 2, name: str = None) -> AsyncIterator[B]:
    with ThreadPoolExecutor(workers, thread_name_prefix=name) as pool:
        loop = asyncio.get_event_loop()
        queue = Queue()
        for val in islice(gen, 0, workers):
            queue.put(loop.run_in_executor(pool, fun, val))

        try:
            while not queue.empty():
                f = queue.get()
                yield await f
                val = next(gen)
                queue.put(loop.run_in_executor(pool, fun, val))
        except StopIteration:
            pass

        while not queue.empty():
            f = queue.get()
            yield await f


async def threadMapper(fun: Callable[[A], B], gen: AsyncIterator[A],
                       workers: int = 2, name: str = None) -> AsyncIterator[B]:
    with ThreadPoolExecutor(workers, thread_name_prefix=name) as pool:
        loop = asyncio.get_event_loop()
        queue = Queue()

        n = 0
        async for val in gen:
            queue.put(loop.run_in_executor(pool, fun, val))
            n += 1
            if n >= workers:
                break

        try:
            while not queue.empty():
                f = queue.get()
                yield await f
                val = await gen.__anext__()
                queue.put(loop.run_in_executor(pool, fun, val))
        except StopAsyncIteration:
            pass

        while not queue.empty():
            f = queue.get()
            yield await f


def test():
    def genFunction(number: int):
        for i in reversed(range(number)):
            yield i

    def mapFun(number: int) -> int:
        time.sleep(number)
        return number ** 2

    def mapFun2(number):
        time.sleep(1)
        return number - 34

    async def reader():
        g = genFunction(10)
        p = threadProducer(mapFun, g, name="PROD")
        m = threadMapper(mapFun2, p, name="MAPPER")
        async for i in m:
            print(i)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(reader())


if __name__ == '__main__':
    test()
