from opgee.config import getParam
from opgee.model import ModelFile
from opgee.log import getLogger, configureLogs, setLogLevels
from opgee.utils import resourceStream

import opgee.processes     # load pre-defined Process subclasses so the classes can be found by name

_logger = getLogger(__name__)

def init_logging():
    level = getParam('OPGEE.LogLevel')
    setLogLevels(level)
    configureLogs(force=True)


def main():
    init_logging()

    s = resourceStream('etc/opgee.xml', stream_type='bytes', decode=None)
    mf = ModelFile('[opgee package]/etc/opgee.xml', stream=s)
    model = mf.model
    model.validate()

    run_all = False
    if run_all:
        model.run()
    else:
        field_name = 'test'
        field = model.analysis.field_dict[field_name]
        field.run()

    show_streams = False
    if show_streams:
        for field in model.analysis.children():
            for s in field.streams():
                print(f"\n<Stream '{s.name}>'\n{s.components}")

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
