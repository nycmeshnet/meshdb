import inspect
from functools import wraps
from typing import Callable

from flags.state import flag_state


def create_noop(func):
    """Creates a no-op function that conforms to the argument
    specification of the given function."""

    def noop(*args, **kwargs):
        pass

    # Get the argument specification of the original function
    argspec = inspect.getfullargspec(func)

    # Update the noop function's signature to match the original function
    noop.__signature__ = inspect.Signature(
        parameters=[inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD) for name in argspec.args]
        + [
            inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=argspec.defaults[i])
            for i, name in enumerate(argspec.kwonlyargs)
        ],
        return_annotation=argspec.annotations.get("return", None),
    )

    return noop


def skip_if_flag_disabled(flag_name: str) -> Callable:
    """
    Decorator that transforms the annotated function into a noop if the given flag name is disabled
    :param flag_name: the flag to check
    """

    def decorator(func):
        def inner(*args, **kwargs):
            enabled = flag_state(flag_name)

            if enabled:
                return func(*args, **kwargs)

        return wraps(func)(inner)

    return decorator
