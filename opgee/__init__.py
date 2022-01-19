import pint
from .pkg_utils import resourceStream

#
# Try to use the "ureg" from thermosteam to avoid mixing and matching registries.
# If that fails, we create a new pint unit registry. In either case, we load our defs,
# and set it to be the application registry.
#
try:
    from thermosteam.units_of_measure import ureg
except:
    ureg = pint.UnitRegistry()  # pragma: no cover

ureg.load_definitions(resourceStream('etc/units.txt'))
pint.set_application_registry(ureg)

from .processes import *
