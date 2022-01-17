import pytest
from .utils_for_tests import load_test_model


@pytest.fixture(scope="module")
def test_gas_branch(configure_logging_for_tests):
    return load_test_model('test_gas_flooding.xml')


def test_gas_flooding(test_gas_branch):
    analysis = test_gas_branch.get_analysis('test_gas_flooding')
    field = analysis.get_field('test_gas_flooding')
    field.run(analysis)
