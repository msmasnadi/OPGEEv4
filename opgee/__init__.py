import pint
from .pkg_utils import resourceStream

#
# Create a pint registry, load our defs, and make it the application registry.
#
ureg = pint.UnitRegistry()
ureg.load_definitions(resourceStream('etc/units.txt'))
pint.set_application_registry(ureg)

from .processes import *


# class Before(Process):
#     def run(self, analysis):
#         pass
#
#
# class After(Process):
#     def run(self, analysis):
#         pass
