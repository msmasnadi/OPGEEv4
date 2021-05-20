import pytest

from opgee import Process
from opgee.config import setParam
from opgee.error import OpgeeException
from opgee.stream import Stream
from .utils_for_tests import load_test_model, path_to_test_file


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
def test_separator(configure_logging_for_tests):
    return load_test_model('test_separator.xml')


# def test_unknown_analysis(test_model2):
#     with pytest.raises(OpgeeException, match=r"Analysis named '.*' is not defined"):
#         test_model2.get_analysis('non-existent-analysis')
#
#
# def test_unknown_field(test_model2):
#     with pytest.raises(OpgeeException, match=r"Field named '.*' is not defined"):
#         test_model2.get_field('non-existent-field')
#
#
# def test_unknown_const(test_model2):
#     with pytest.raises(OpgeeException, match=r"No known constant with name .*"):
#         test_model2.const('non-existent-const')


def test_run(test_separator):
    analysis = test_separator.get_analysis('test_separator')
    field = analysis.get_field('test')
    field.run(analysis)

