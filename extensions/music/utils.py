import asyncio
import time
from functools import partial, wraps
from itertools import chain, islice
from typing import Any, Callable, Coroutine, Generator, Iterable, TypeVar

_T = TypeVar("_T")


def sync_to_thread(
    func: Callable[[...], _T]
) -> Callable[[...], Coroutine[None, None, _T]]:
    @wraps(func)
    async def inner(*args, **kwargs):
        loop = asyncio.get_event_loop()
        internal_function = partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, internal_function)

    return inner


def chunk(
    iterable: Iterable[_T], size: int = 10
) -> Generator[Generator[_T, Any, None], Any, None]:
    iterator = iter(iterable)
    size -= 1

    for first in iterator:
        yield chain([first], islice(iterator, size))


def short_diff_from_unix(then: int) -> str:
    now = time.time() - then
    minutes, seconds = divmod(int(now), 60)
    hours, minutes = divmod(minutes, 60)

    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def short_diff_from_time(diff) -> str:
    minutes, seconds = divmod(int(diff), 60)
    hours, minutes = divmod(minutes, 60)

    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"
