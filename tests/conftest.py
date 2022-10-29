import pytest

from opgee.config import getConfig
from opgee.log import setLogLevels, configureLogs
from opgee.model_file import ModelFile
from opgee.tool import Opgee
from .utils_for_tests import load_test_model


@pytest.fixture(scope="session")
def configure_logging_for_tests():
    # Don't display routine diagnostic messages during tests
    getConfig()
    setLogLevels('ERROR')
    configureLogs(force=True)
    return None


@pytest.fixture(scope="function")
def opgee_model(configure_logging_for_tests):
    mf = ModelFile(None, use_default_model=True)
    return mf.model


@pytest.fixture(scope="module")
def test_model(configure_logging_for_tests):
    return load_test_model('test_model.xml')


@pytest.fixture(scope="function")
def test_model_with_change(configure_logging_for_tests):
    """
    The same as test_model, only with "function" scope, for use on
    tests that alter the model, to avoid creating state changes that
    confuse tests.
    """
    return load_test_model('test_model.xml')


@pytest.fixture(scope='function')
def opgee():
    return Opgee()
