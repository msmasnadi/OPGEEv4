import pytest
from opgee import Process
from .utils_for_tests import load_test_model


class Before(Process):
    def run(self, analysis):
        pass

    def impute(self):
        pass


class After(Process):
    def run(self, analysis):
        pass

    def impute(self):
        pass


@pytest.fixture(scope="module")
def test_boundary(configure_logging_for_tests):
    return load_test_model('test_boundary.xml')


def test_gas_trans_boundary(test_boundary):
    analysis = test_boundary.get_analysis('test_boundary')
    field = analysis.get_field('test_gas_transmission_boundary')
    field.resolve_process_choices()
    field.run(analysis)