import pytest
from opgee.error import OpgeeException
from opgee import Process
from opgee import Stream
from .utils_for_tests import load_test_model

class BoundaryStreamsProcA(Process):
    pass

class BoundaryStreamsProcB(Process):
    pass

class BoundaryStreamsProcC(Process):
    pass

@pytest.fixture(scope="module")
def boundary_model(configure_logging_for_tests):
    return load_test_model('test_boundary_streams.xml')

def test_boundary_streams(boundary_model):
    analysis = boundary_model.get_analysis('test_boundary_streams')
    # field = analysis.get_field('field1')

    boundaries = Stream.boundaries()

    assert set(boundaries) == {'Production', 'Distribution'}

    s = Stream.boundary_stream('Production')
    assert s.name == 'production site boundary'

    s = Stream.boundary_stream('Distribution')
    assert s.name == 'distribution boundary'

    with pytest.raises(OpgeeException, match=r"boundary_stream: boundary '.*' has not been declared."):
        Stream.boundary_stream('unknown-boundary')

    # no need to run the field
    # field.run(analysis)
