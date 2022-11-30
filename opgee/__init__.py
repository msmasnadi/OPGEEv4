#
# Author: Richard Plevin
# See LICENSE.txt for license details.
#
import pint
import pint_pandas
from .pkg_utils import resourceStream

import warnings

#warnings.filterwarnings("ignore", category=DeprecationWarning)
#warnings.filterwarnings("error", category=UserWarning) # turn warning into error to debug
warnings.filterwarnings("ignore", category=UserWarning)

#
# Try to use the "ureg" from thermosteam to avoid mixing and matching registries.
# If that fails, we create a new pint unit registry. In either case, we load our defs,
# and set it to be the application registry.
#
try:
    from thermosteam.units_of_measure import ureg
except:
    ureg = pint.UnitRegistry()  # pragma: no cover

stream = resourceStream('etc/units.txt')
lines = [line.strip() for line in stream.readlines()]
ureg.load_definitions(lines)

pint.set_application_registry(ureg)
