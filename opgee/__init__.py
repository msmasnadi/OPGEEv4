#
# Author: Richard Plevin
# See LICENSE.txt for license details.
#
import warnings

# warnings.filterwarnings("ignore", category=DeprecationWarning)
# warnings.filterwarnings("error", category=UserWarning) # turn warning into error to debug
warnings.filterwarnings("ignore", category=UserWarning) # turn warning into error to debug

#
# Try to use the "ureg" from thermosteam to avoid mixing and matching registries. If
# that fails, we create a new pint unit registry. (In tool.main() we load our defs
# and set the ureg to be the application registry.)
#
try:
    from thermosteam.units_of_measure import ureg
except:
    import pint
    ureg = pint.UnitRegistry()  # pragma: no cover
