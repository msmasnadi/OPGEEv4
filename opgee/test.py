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
    _logger.debug("testing")

    s = resourceStream('etc/opgee.xml', stream_type='bytes', decode=None)
    mf = ModelFile('[opgee package]/etc/opgee.xml', stream=s)
    model = mf.model
    model.validate()
    model.run()

    from opgee.graph import write_model_diagram, write_class_diagram
    write_model_diagram(model, "/tmp/model_diagram.png")
    write_class_diagram("/tmp/class_diagram.png")

    # Show streams
    for field in model.analysis.fields:
        for s in field.streams:
            print(f"\nStream {s.number} ({s.name}), src='{s.src}', dst='{s.dst}'\n{s.components}")

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
