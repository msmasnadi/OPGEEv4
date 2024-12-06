from typing import (
    Callable,
    Iterable,
    ParamSpec,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    overload,
)

from pint import Unit
from pint.facets.plain import PlainQuantity

from . import ureg

# TypeVar for `ensure_dimensionless` methods
T_QSeq = TypeVar("T_QSeq", PlainQuantity, Sequence[PlainQuantity])

FRAC = "frac"

_unit_registry = ureg.get()

def ensure_unit(quantity: PlainQuantity, unit: str):
    ...


@overload
def ensure_dimensionless(val: PlainQuantity) -> PlainQuantity: ...


@overload
def ensure_dimensionless(val: Sequence[PlainQuantity]) -> Sequence[PlainQuantity]: ...


def ensure_dimensionless(val: T_QSeq) -> T_QSeq:
    """
    Validate and coerce the passed value or list of values into dimensionless quantities.

    :param val: (PlainQuantity | Sequence[PlainQuantity]) The quantity or sequence of quantities
    :return: (PlainQuantity | Sequence[PlainQuantity]) The same quantity converted to 'frac' units
    :raises: ValueError if any of the passed quantities are not dimensionless
    """
    msg = "Ratios must be dimensionless, %s passed. Dimensionality %s"
    if isinstance(val, PlainQuantity):
        if not val.dimensionless:
            dim = val.dimensionality
            raise ValueError(msg % (repr(val), repr(dim)))
        return val.to("frac")
    else:
        dimless = [r.dimensionless for r in val]
        if not all(dimless):
            bad_val = val[dimless.index(False)]
            dim = bad_val.dimensionality
            raise ValueError(msg % (repr(bad_val), repr(dim)))
        return [r.to("frac") for r in val]



P = ParamSpec('P')
RT = TypeVar('RT')

TUnit = Union[str, Unit, None]
TUnitSpec = Union[TUnit, Iterable[TUnit]]

IntVarArgs = ParamSpec('IntVarArgs')
PreWrappedSig = Callable[IntVarArgs, float]

def wraps(args_units: TUnitSpec, ret_units: TUnitSpec):
    ...
    
def simple(x: float, y: float) -> float:
    return y / x

q_simple = ureg.wraps('m/s', ('hour', 'mile'))(simple)
