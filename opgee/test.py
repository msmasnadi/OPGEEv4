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

    stream = resourceStream('etc/opgee.xml', stream_type='bytes', decode=None)
    m = ModelFile(stream, schemaPath='etc/opgee.xsd')

    pass

main()
