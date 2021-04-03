'''
.. OPGEE stream support

.. Copyright (c) 2021 Richard Plevin and Adam Brandt
   See the https://opensource.org/licenses/MIT for license details.
'''
import numpy as np
from .error import OpgeeException

# HCs with 1-60 carbon atoms, i.e., C1, C2, ..., C60
_hydrocarbons = [f'C{n+1}' for n in range(60)]

# All possible stream components
Components = _hydrocarbons + ['H2S', 'H2O', 'Na+', 'Cl-', 'Si-', 'H']

# Dictionary mapping name to index in component matrix
ComponentDict = {name : idx for (idx, name) in enumerate(Components)}

# Similarly for phases
Phases = ['gas', 'liquid', 'solid']
PhaseDict = {name : idx for (idx, name) in enumerate(Phases)}

# May be handy, since new phases of matter are not going to be created
GAS_PHASE    = 0
LIQUID_PHASE = 1
SOLID_PHASE  = 2

def extend_components(names):
    """
    Extend the global `Component` list and update the global `ComponentDict`.
    N.B. This must be called before any streams are instantiated.

    :param names: (iterable of str) the names of new stream components.
    :return: None
    :raises: OpgeeException if any of the names were previously defined stream components.
    """
    # ensure no duplicate names
    bad = [name for name in names if ComponentDict.get(name) is not None]
    if bad:
        raise OpgeeException(f"extend_components: proposed extensions already defined: {bad}")

    Components.extend(names)

    count = len(ComponentDict)
    for i, name in enumerate(names):
        ComponentDict[name] = count + i

def get_component_matrix():
    """
    Create an appropriately sized component matrix.

    :return: (numpy.array) Zero-filled stream component array
    """
    matrix = np.zeros((len(Components), len(Phases)))
    return matrix

def get_component(matrix, name, phase=None):
    """
    Return the stream component row (all phases) or just the value
    for the given `phase`.

    :param matrix: (numpy.array) a stream component matrix
    :param name: (str) the name of a stream component
    :param phase: (str) one of {'gas', 'liquid', 'solid'}, or None
    :return: if `phase` is None, the entire row of the matrix for
        component `name`, otherwise the value in that row for `phase`.
    :raises: OpgeeException if `name` or `phase` are unknown
    """
    try:
        row = ComponentDict[name]
    except KeyError:
        raise OpgeeException(f"'{name}' is not a known stream component")

    # return the whole row
    if phase:
        try:
            col = PhaseDict[phase]
            result = matrix[row, col]
        except KeyError:
            raise OpgeeException(f"{phase} is not a known phase of matter: {Phases}")
    else:
        result = matrix[row, :]

    return result

def set_component(matrix, name, phase, value):
    """
    Set the value of stream component `name` and `phase`.

    :param matrix: (numpy.array) a stream component matrix
    :param name: (str) the name of a stream component
    :param phase: (str) one of {'gas', 'liquid', 'solid'}
    :
    :return: None
    :raises: OpgeeException if `name` or `phase` are unknown
    """
    try:
        row = ComponentDict[name]
    except KeyError:
        raise OpgeeException(f"'{name}' is not a known stream component")

    try:
        col = PhaseDict[phase]
    except KeyError:
        raise OpgeeException(f"{phase} is not a known phase of matter: {Phases}")

    matrix[row, col] = value

#
# It's unclear whether we'll switch to pandas for convenience (if performance is
# not an issue) or if we'll use this just to make viewing stream components more
# convenient as the dataframe provides labeling and ability to use "query".
#
def get_component_dataframe(matrix=None):
    """
    Get a component DataFrame, either zeroes or created from the given `matrix`.

    :param matrix: (numpy.array) Optional numpy array to use.
      If provided, it must be of the expected dimensions, defined
      by the global variables Components and Phases in the module
      opgee.stream.
    :return: (pandas.DataFrame) If `matrix` is None, returns a
      DataFrame with all zeroes, otherwise, the given `matrix`
      is used.
    """
    import pandas as pd

    matrix = get_component_matrix() if matrix is None else matrix
    df = pd.DataFrame(data=matrix, index=Components, columns=Phases)
    return df
