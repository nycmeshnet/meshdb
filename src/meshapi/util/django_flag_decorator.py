import inspect
from typing import Callable

from flags import decorators


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
    def inner_decorator(func):
        # Create a noop function that matches the signature of the decorated function.
        # We could do this with `lambda *args, **kwargs: None` instead and it would be just fine,
        # but there's a hard coded equality check inside the django-flags code that wants the
        # function signatures to match exactly
        noop_func_matching_signature = create_noop(func)
        return decorators.flag_check(flag_name, True, fallback=noop_func_matching_signature)(func)

    return inner_decorator
