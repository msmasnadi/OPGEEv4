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
def test_gas_branch(configure_logging_for_tests):
    return load_test_model('test_gas_branch.xml')


# def test_gas_path_1(test_gas_branch):
#     analysis = test_gas_branch.get_analysis('test_gas_path_1')
#     field = analysis.get_field('test_gas_path_1')
#     field.run(analysis)

def test_gas_path_2(test_gas_branch):
    analysis = test_gas_branch.get_analysis('test_gas_path_2')
    field = analysis.get_field('test_gas_path_2')
    field.resolve_process_choices()
    field.run(analysis)
