import pytest
from opgee import Process
from .utils_for_tests import load_test_model


class BoundaryStreamsProcA(Process):
    pass


class BoundaryStreamsProcB(Process):
    pass


class BoundaryStreamsProcC(Process):
    pass


@pytest.fixture(scope="module")
def boundary_model(configure_logging_for_tests):
    return load_test_model('test_boundary_procs.xml')


def test_boundary_streams(boundary_model):
    analysis = boundary_model.get_analysis('test_boundary_procs')
    field = analysis.get_field('field1')

    boundaries = field.defined_boundaries()

    assert set(boundaries) == {'Production', 'Distribution', 'Transportation'}

    proc = field.boundary_dict['Production']
    assert proc.name == 'ProductionBoundary'

    proc = field.boundary_dict['Distribution']
    assert proc.name == 'DistributionBoundary'

    # no need to run the field
    # field.run(analysis)
