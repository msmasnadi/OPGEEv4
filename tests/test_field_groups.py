import pytest
from opgee.model import ModelFile
from opgee.process import Process
from .utils_for_tests import path_to_test_file

@pytest.fixture(scope="session")
def field_groups_model(configure_logging_for_tests):
    xml_path = path_to_test_file('field_groups_model.xml')
    mf = ModelFile(xml_path, add_stream_components=False, use_class_path=False)
    return mf.model


class ProcA(Process):
    def run(self, analysis):
        pass


class ProcB(Process):
    def run(self, analysis):
        pass

def test_field_groups(field_groups_model):
    field_groups_model.validate()
    analysis = field_groups_model.get_analysis('test')
    # Pattern should match only fields 'test1' and 'test2', and not 'test3'
    assert analysis.get_field('test1') and analysis.get_field('test2') and not analysis.get_field('test3', raiseError=False)

