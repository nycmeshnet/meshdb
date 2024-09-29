from typing import Callable

from flags import decorators


def only_run_if_flag_enabled(flag_name: str) -> Callable:
    return decorators.flag_check(flag_name, True, fallback=lambda: None)
