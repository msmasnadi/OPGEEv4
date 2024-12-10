from collections.abc import Callable
from typing import (
    Final,
    Optional,
    TypeVar,
)

import pint
from pint.registry import ApplicationRegistry

from opgee.error import OpgeeException
from opgee.log import getLogger
from opgee.pkg_utils import resourceStream

FRAC = "frac"
T = TypeVar("T", bound=Callable)

_logger = getLogger(__name__)

def _iif(fn: Callable[[], T]) -> T:
    """
    Simple decorator to define an immediately invoked function. Similar to
    JS/TS `(function () {})()`

    :param fn: Any callable that returns a Callable
    :type fn: Callable[[], T]
    :return: The return value from the passed Callable
    :rtype: T
    """
    return fn()


@_iif
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

# to avoid redundantly reporting bad units
_undefined_units = {}

def validate_unit(unit):
    """
    Return the ``pint.Unit`` associated with the string ``unit``, or ``None``
    if ``unit`` is ``None`` or not in the unit registry.

    :param unit: (str) a string representation of a ``pint.Unit``

    :return: (pint.Unit or None)
    """
    if not unit:
        return None

    if unit in ureg:
        return ureg.Unit(unit)

    if unit not in _undefined_units:
        _logger.warning(f"Unit '{unit}' is not in the UnitRegistry")
        _undefined_units[unit] = 1

    return None


def magnitude(value, units=None):
    """
    Return the magnitude of ``value``. If ``value`` is a ``pint.Quantity`` and
    ``units`` is not None, check that ``value`` has the expected units and
    return the magnitude of ``value``. If ``value`` is not a ``pint.Quantity``,
    just return it.

    :param value: (float or pint.Quantity) the value for which we return the magnitude.
    :param units: (None or pint.Unit) the expected units
    :return: the magnitude of `value`
    """
    if isinstance(value, ureg.Quantity):
        # if optional units are provided, validate them
        if units:
            if not isinstance(units, pint.Unit):
                units = ureg.Unit(units)
            if value.units != units:
                raise OpgeeException(f"magnitude: value {value} units are not {units}")

        return value.m
    else:
        return value
