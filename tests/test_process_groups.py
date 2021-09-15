import pytest
from opgee.error import OpgeeException
from .utils_for_tests import load_test_model

@pytest.fixture(scope="module")
def process_groups_model(configure_logging_for_tests):
    return load_test_model('test_process_groups.xml')

@pytest.fixture(scope="module")
def gas_paths(process_groups_model):
    analysis = process_groups_model.get_analysis('test')
    field = analysis.get_field('test')
    return field.process_choices[0]


def test_parsing(gas_paths):
    groups_names = gas_paths.group_names()
    assert gas_paths.name == 'Gas processing path' and len(groups_names) == 9

    dry_gas = gas_paths.get_group('Dry Gas')
    procs, streams = dry_gas.processes_and_streams()
    assert set(streams) == {'s4', 's5'} and set(procs) == {'uuu', 'www', 'zzz'}


def test_missing_group(gas_paths):
    assert gas_paths.get_group('non-existent-group', raiseError=False) is None

    with pytest.raises(OpgeeException, match="Process choice '.*' not found in field '.*'"):
        gas_paths.get_group('non-existent-group')
