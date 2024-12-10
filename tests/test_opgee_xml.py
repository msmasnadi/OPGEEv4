import pytest

from opgee.units import ureg
from opgee.model_file import ModelFile
from tests.utils_for_tests import path_to_test_file


@pytest.fixture(scope="module")
def opgee_model():
    glf_xml_path = path_to_test_file("gas_lifting_field.xml")
    mf = ModelFile(glf_xml_path, use_default_model=True)
    return mf.model

def test_gas_lifting_field(opgee_model):
    analysis = opgee_model.get_analysis('example')
    field = analysis.get_field('gas_lifting_field')

    # Just testing that we can run the fields without error
    field.run(analysis)