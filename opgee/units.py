from collections.abc import Callable
from typing import (
    Final,
    Optional,
    TypeVar,
)

import pint
from pint.registry import ApplicationRegistry

from opgee.pkg_utils import resourceStream

FRAC = "frac"
T = TypeVar("T", bound=Callable)


def iif(fn: Callable[[], T]) -> T:
    """
    Simple decorator to define an immediately invoked function. Similar to
    JS/TS `(function () {})()`

    :param fn: Any callable that returns a Callable
    :type fn: Callable[[], T]
    :return: The return value from the passed Callable
    :rtype: T
    """
    return fn()


@iif
def get_ureg() -> Callable[[], ApplicationRegistry]:
    """
    Always return the same instance of OPGEE's `pint.ApplicationRegistry`.

    :return: callable to fetch the ApplicationRegistry instance
    :rtype: Callable[[], ApplicationRegistry]
    """
    _ar: Optional[ApplicationRegistry] = None

    def _ret() -> ApplicationRegistry:
        nonlocal _ar
        if _ar is None:
            _ar = pint.get_application_registry()
            del _ar._units["bbl"]
            stream = resourceStream("etc/units.txt")
            lines = [line.strip() for line in stream.readlines()]
            _ar.load_definitions(lines)
        return _ar

    return _ret


ureg: Final[ApplicationRegistry] = get_ureg()

Qty = ureg.Quantity
