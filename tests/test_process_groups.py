import pytest
from opgee.error import OpgeeException
from .utils_for_tests import load_test_model

@pytest.fixture(scope="module")
def process_groups_model(configure_logging_for_tests):
    return load_test_model('test_process_groups.xml')

@pytest.fixture(scope="module")
def test_field(process_groups_model):
    analysis = process_groups_model.get_analysis('test')
    field = analysis.get_field('test')
    return field

@pytest.fixture(scope="module")
def gas_paths(test_field):
    return list(test_field.process_choice_dict.values())[0]

#TODO: Add a test to procs and streams that are not chosen
def test_parsing(gas_paths):
    groups_names = gas_paths.group_names()
    assert gas_paths.name == 'gas_processing_path' and len(groups_names) == 9

    dry_gas = gas_paths.get_group('Dry Gas')
    proc_names, stream_names = dry_gas.process_and_stream_refs()
    assert set(stream_names) == {'s2'} and set(proc_names) == {'ProductionBoundary'}


def test_missing_group(gas_paths):
    assert gas_paths.get_group('non-existent-group', raiseError=False) is None

    with pytest.raises(OpgeeException, match="Process choice '.*' not found in field '.*'"):
        gas_paths.get_group('non-existent-group')

