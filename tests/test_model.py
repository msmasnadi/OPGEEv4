import pytest
from opgee.config import setParam
from opgee.error import OpgeeException
from opgee.stream import Stream
from .utils_for_tests import load_test_model, path_to_test_file

@pytest.fixture(scope="module")
def test_model2(configure_logging_for_tests):
    # This fixture also serves to test user classpath
    setParam('OPGEE.ClassPath', path_to_test_file('user_processes.py'))
    return load_test_model('test_model2.xml', use_class_path=True)

def test_stream_components(configure_logging_for_tests):
    setParam('OPGEE.StreamComponents', 'Foo, Bar')
    load_test_model('test_model.xml', add_stream_components=True)

    comps = Stream.components
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

def test_get_field(test_model2):
    assert test_model2.get_field('Field1')

def test_const(test_model2):
    test_model2.const('std-temperature')

def test_model_children(test_model2):
    assert set(test_model2.children()) == set(test_model2.analyses())

