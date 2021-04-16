'''
.. OPGEE stream support

.. Copyright (c) 2021 Richard Plevin and Adam Brandt
   See the https://opensource.org/licenses/MIT for license details.
'''
import pandas as pd
from .error import OpgeeException
from .log import getLogger

_logger = getLogger(__name__)

# HCs with 1-60 carbon atoms, i.e., C1, C2, ..., C60
_hydrocarbons = [f'C{n+1}' for n in range(60)]

_solids  = ['PC']   # petcoke
_liquids = ['oil']
_gases   = ['N2', 'O2', 'CO2', 'H2O', 'CH4', 'C2H6', 'C3H8', 'C4H10', 'H2', 'H2S', 'SO2', 'air']
_other   = ['Na+', 'Cl-', 'Si-']

# All possible stream components
Components = _solids + _liquids + _gases + _other # or use C1-C60 (_hydrocarbons)?

# constants to use instead of strings
PHASE_SOLID  = 'solid'
PHASE_LIQUID = 'liquid'
PHASE_GAS    = 'gas'

# Phases of matter
Phases = [PHASE_SOLID, PHASE_LIQUID, PHASE_GAS]

def extend_components(names):
    """
    Extend the global `Component` list.
    N.B. This must be called before any streams are instantiated.

    :param names: (iterable of str) the names of new stream components.
    :return: None
    :raises: OpgeeException if any of the names were previously defined stream components.
    """
    # ensure no duplicate names
    bad = set(names).intersection(set(Components))
    if bad:
        raise OpgeeException(f"extend_components: these proposed extensions are already defined: {bad}")

    _logger.info(f"Extended stream components to include {names}")

    Components.extend(names)

def create_component_matrix():
    """
    Create a pandas DataFrame to hold the 3 phases of the known Components.

    :return: (pandas.DataFrame) Zero-filled stream DataFrame
    """
    return pd.DataFrame(data=0.0, index=Components, columns=Phases)
