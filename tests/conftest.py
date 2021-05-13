import pytest
from opgee.config import getConfig
from opgee.log import setLogLevels, configureLogs
from opgee.model import ModelFile
from opgee.process import Process
from opgee.pkg_utils import resourceStream

class ProcA(Process): pass
class ProcB(Process): pass

@pytest.fixture(scope="session ")
def configure_logging_for_tests():
    # Don't display routine diagnostic messages during tests
    getConfig()
    setLogLevels('ERROR')
    configureLogs(force=True)
    return None

@pytest.fixture(scope="module")
def opgee_model(configure_logging_for_tests):
    s = resourceStream('etc/opgee.xml', stream_type='bytes', decode=None)
    mf = ModelFile('[opgee package]/etc/opgee.xml', stream=s)
    return mf.model

@pytest.fixture(scope="module")
def test_model(configure_logging_for_tests):
    mf = ModelFile('files/test_model.xml', add_stream_components=False, use_class_path=False)
    return mf.model
