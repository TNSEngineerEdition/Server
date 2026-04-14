import time
from typing import Callable, ParamSpec, TypeVar

import overpy

T = TypeVar("T")
P = ParamSpec("P")


def retry_query(times: int) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except overpy.exception.OverPyException:
                    if attempt == times - 1:
                        raise

                    time.sleep(5)

            raise ValueError("Exceeded number of retries")

        return wrapper

    return decorator
