import pytest
from opgee.model import ModelFile
from opgee.pkg_utils import resourceStream
import opgee.processes

@pytest.fixture
def model_instance():
    s = resourceStream('etc/opgee.xml', stream_type='bytes', decode=None)
    mf = ModelFile('[opgee package]/etc/opgee.xml', stream=s)
    return mf.model
