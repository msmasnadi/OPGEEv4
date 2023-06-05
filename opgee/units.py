#
# Author: Richard Plevin
# See LICENSE.txt for license details.
#
import pint

from .pkg_utils import resourceStream

ureg = None

def load_units():
    global ureg

    if ureg:
        return ureg

    ureg = pint.get_application_registry()

    # Standard def is 31.5 gal, not 42 gal as in petrochemical world.
    # We redefine this in etc/units.txt
    del ureg._units['bbl']

    stream = resourceStream('etc/units.txt')
    lines = [line.strip() for line in stream.readlines()]
    ureg.load_definitions(lines)

    return ureg

if ureg is None:
    load_units()
