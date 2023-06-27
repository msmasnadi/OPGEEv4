import pytest
from opgee.error import OpgeeException
from opgee.stream import Stream
from .utils_for_tests import load_test_model, path_to_test_file

@pytest.fixture(scope="function")
def test_model2(configure_logging_for_tests):
    # This fixture also serves to test user classpath
    model = load_test_model('test_model2.xml', class_path=path_to_test_file('user_processes.py'))
    return model

def test_stream_components(configure_logging_for_tests):
    load_test_model('test_model.xml', stream_components='Foo, Bar')
    comps = Stream.component_names
    assert 'Foo' in comps and 'Bar' in comps


def test_unknown_analysis(test_model2):
    with pytest.raises(OpgeeException, match=r"Analysis named '.*' is not defined"):
        test_model2.get_analysis('non-existent-analysis')


def test_unknown_field(test_model2):
    with pytest.raises(OpgeeException, match=r"Field named '.*' is not defined"):
        test_model2.get_field('non-existent-field')


def test_unknown_const(test_model2):
    with pytest.raises(OpgeeException, match=r"No known constant with name .*"):
        test_model2.const('non-existent-const')


def test_get_analysis(test_model2):
    assert test_model2.get_analysis('Analysis1')


def test_get_analysis_group_regex(test_model):
    assert test_model.get_analysis('test2')


def test_get_analysis_group(test_model):
    assert test_model.get_analysis('test3')


def test_get_field(test_model2):
    assert test_model2.get_field('Field1')


def test_const(test_model2):
    test_model2.const('std-temperature')


def test_model_children(test_model2):
    assert set(test_model2.children()) == set(test_model2.analyses())
