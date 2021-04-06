from opgee.XMLFile import XMLFile
from opgee.core import Attributes, ModelFile
from opgee.utils import resourceStream
from opgee.config import getParam
from opgee.log import getLogger

_logger = getLogger(__name__)

def init_logging():
    from opgee.log import configureLogs, setLogLevels

    level = getParam('OPGEE.LogLevel')
    setLogLevels(level)
    configureLogs(force=True)


def main():
    init_logging()
    _logger.debug("testing")

    attributes = Attributes()
    field_attr = attributes.class_attrs('Field')
    print(field_attr.attribute('downhole_pump'))
    print(field_attr.attribute('ecosystem_richness'))
    print(field_attr.option('ecosystem_C_richness'))

    stream = resourceStream('etc/opgee.xml', stream_type='bytes', decode=None)
    m = ModelFile(stream)
    m.model.run()

def test_pint():
    from pint import UnitRegistry, Quantity

    ureg = UnitRegistry()
    ureg.load_definitions(resourceStream('etc/opgee_units.txt'))

    # c = Quantity(10, ureg.degC)
    # k = Quantity(111, ureg.degK)
    # x = c.to(ureg.degK) + k
    # print(x)

    g = Quantity(10, ureg.psig)
    a = Quantity(21, ureg.psia)
    x = g.to(ureg.psia) + a
    print(x)

#test_pint()
main()
