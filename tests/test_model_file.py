import pytest
from opgee.error import OpgeeException
from opgee.model_file import ModelFile
from .utils_for_tests import path_to_test_file # , load_test_model

def test_no_file():
    pathnames = []
    with pytest.raises(OpgeeException, match="ModelFile: no model XML file specified"):
        ModelFile(pathnames, use_default_model=False)  # instantiate_model=True, save_to_path=None)

def test_modifies():
    xml_path = path_to_test_file('test_fields.xml')
    mf = ModelFile(xml_path, use_default_model=True)
