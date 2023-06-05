import pint
import warnings

from .pkg_utils import resourceStream

# warnings.filterwarnings("ignore", category=DeprecationWarning)
# warnings.filterwarnings("error", category=UserWarning) # turn warning into error to debug
warnings.filterwarnings("ignore", category=UserWarning) # turn warning into error to debug

ureg = None

if not ureg:
    ureg = pint.get_application_registry()

    # Standard def is 31.5 gal, not 42 gal as in petrochemical world.
    # We redefine this in etc/units.txt and delete the old def first.
    del ureg._units['bbl']

    stream = resourceStream('etc/units.txt')
    lines = [line.strip() for line in stream.readlines()]
    ureg.load_definitions(lines)
