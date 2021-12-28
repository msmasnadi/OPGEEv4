import pytest
from opgee.process import reload_subclass_dict, Process
from .utils_for_tests import load_test_model


class BoundaryBefore(Process):
    def run(self, analysis):
        pass

    def impute(self):
        pass


@pytest.fixture(scope="module")
def test_boundary(configure_logging_for_tests):
    reload_subclass_dict()
    return load_test_model('test_boundary.xml')


def test_gas_trans_boundary(test_boundary):
    analysis = test_boundary.get_analysis('test_boundary')
    field = analysis.get_field('test_gas_transmission_boundary')
    field.run(analysis)
