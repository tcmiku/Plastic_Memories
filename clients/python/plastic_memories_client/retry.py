import time
from typing import Callable


def retry_call(fn: Callable[[], object], retries: int = 2, delays: tuple[float, float] = (0.2, 0.5)):
    attempts = 0
    while True:
        try:
            return fn()
        except Exception:
            if attempts >= retries:
                raise
            delay = delays[min(attempts, len(delays) - 1)]
            time.sleep(delay)
            attempts += 1
