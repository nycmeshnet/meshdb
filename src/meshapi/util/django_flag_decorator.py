from functools import wraps
from typing import Any, Callable

from flags.state import flag_state


def skip_if_flag_disabled(flag_name: str) -> Callable:
    """
    Decorator that transforms the annotated function into a noop if the given flag name is disabled
    :param flag_name: the flag to check
    """

    def decorator(func: Callable) -> Callable:
        def inner(*args: list, **kwargs: dict) -> Any:
            enabled = flag_state(flag_name)

            if enabled:
                return func(*args, **kwargs)

        return wraps(func)(inner)

    return decorator
