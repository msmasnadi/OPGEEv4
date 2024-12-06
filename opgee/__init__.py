import warnings
from typing import Callable, Final, Optional, TypeVar

import pint
from pint.registry import ApplicationRegistry

from .pkg_utils import resourceStream

# warnings.filterwarnings("ignore", category=DeprecationWarning)
# warnings.filterwarnings("error", category=UserWarning) # turn warning into error to debug
warnings.filterwarnings("ignore", category=UserWarning) # turn warning into error to debug

T = TypeVar('T', bound=Callable)
def iif(fn: Callable[[], T]) -> T:
    """
    Simple decorator to define an immediately invoked function.

    :param fn: Any callable that returns a Callable
    :type fn: Callable[[], T]
    :return: The return value from the passed Callable
    :rtype: T
    """
    return fn()

@iif
def get_ureg() -> Callable[[], ApplicationRegistry]:
    _ar: Optional[ApplicationRegistry] = None
    def _ret() -> ApplicationRegistry:
        nonlocal _ar
        if _ar is None:
            _ar = pint.get_application_registry()
            del _ar._units['bbl']
            stream = resourceStream('etc/units.txt')
            lines = [line.strip() for line in stream.readlines()]
            _ar.load_definitions(lines)
        return _ar
    return _ret

# get_ureg: Callable[[], ApplicationRegistry] = _get_ureg()

ureg: Final[ApplicationRegistry] = get_ureg()

Qty = ureg.Quantity

# if not ureg:
#     ureg = pint.get_application_registry()

#     # Standard def is 31.5 gal, not 42 gal as in petrochemical world.
#     # We redefine this in etc/units.txt and delete the old def first.
#     del ureg._units['bbl']

#     stream = resourceStream('etc/units.txt')
#     lines = [line.strip() for line in stream.readlines()]
#     ureg.load_definitions(lines)