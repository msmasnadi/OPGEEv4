import pytest
from opgee.config import getConfig
from opgee.log import setLogLevels, configureLogs
from opgee.model import ModelFile
from opgee.process import Process
from opgee.pkg_utils import resourceStream
from opgee.tool import Opgee
from .utils_for_tests import load_test_model

class ProcA(Process):
    def run(self, analysis):
        pass

class ProcB(Process):
    def run(self, analysis):
        pass

@pytest.fixture(scope="session")
def configure_logging_for_tests():
    # Don't display routine diagnostic messages during tests
    getConfig()
    setLogLevels('ERROR')
    configureLogs(force=True)
    return None

@pytest.fixture(scope="module")
def opgee_model(configure_logging_for_tests):
    stream = resourceStream('etc/opgee.xml', stream_type='bytes', decode=None)
    mf = ModelFile('[opgee package]/etc/opgee.xml', stream=stream)
    return mf.model

@pytest.fixture(scope="module")
def test_model(configure_logging_for_tests):
    return load_test_model('test_model.xml')

@pytest.fixture(scope='module')
def opgee():
    return Opgee()
