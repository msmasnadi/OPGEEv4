import pytest

from opgee.analysis import Analysis
from opgee.constants import DETAILED_RESULT
from opgee.error import AbstractMethodError
from opgee.field import Field, FieldResult
from opgee.post_processor import PostProcessor

from .utils_for_tests import load_test_model, path_to_test_file

@pytest.fixture(scope="function")
def test_model2(configure_logging_for_tests):
    # This fixture also serves to test user classpath
    model = load_test_model('test_model2.xml', class_path=path_to_test_file('user_processes.py'))
    return model

DATA = 'dummy_data'

class SimplePostProcessor(PostProcessor):
    results = []
    def __init__(self):
        pass

    @classmethod
    def clear(cls):
        cls.results.clear()

    def run(self, analysis: Analysis, field: Field, result: FieldResult):
        self.results.append((DATA, result))

    def save(self):
        pass

def test_simple_post_processor(test_model2):
    analysis = test_model2.get_analysis('Analysis1')
    field = test_model2.get_field('Field1')
    result = FieldResult(analysis.name, field.name, DETAILED_RESULT)

    instance = SimplePostProcessor()
    instance.run(analysis, field, result)

    assert len(instance.results) == 1

    saved = instance.results[0]
    assert saved[0] == DATA and saved[1] == result

    SimplePostProcessor.clear()
    assert len(SimplePostProcessor.results) == 0


class InvalidPostProcessor(PostProcessor):
    # Doesn't define required run() method
    pass

def test_invalid_post_processor(test_model2):
    analysis = test_model2.get_analysis('Analysis1')
    field = test_model2.get_field('Field1')
    result = FieldResult(analysis.name, field.name, DETAILED_RESULT)

    instance = InvalidPostProcessor()

    with pytest.raises(AbstractMethodError):
        instance.run(analysis, field, result)
