from opgee.config import getParam, getConfig
from opgee.model import ModelFile
from opgee.log import getLogger, configureLogs, setLogLevels
from opgee.pkg_utils import resourceStream

_logger = getLogger(__name__)

def init_logging():
    level = getParam('OPGEE.LogLevel')
    setLogLevels(level)
    configureLogs(force=True)


def main():
    getConfig(createDefault=True)
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
    from pint import UnitRegistry

    ureg = UnitRegistry()
    ureg.load_definitions(resourceStream('etc/opgee_units.txt'))

    g = ureg.Quantity(10, ureg.psig)
    a = ureg.Quantity(21, ureg.psia)
    x = g.to(ureg.psia) + a
    print(x)

#test_pint()
main()
