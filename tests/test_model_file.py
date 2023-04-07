import pytest
from opgee.error import OpgeeException
from opgee.model_file import (ModelFile, fields_for_analysis, extracted_model)
from .utils_for_tests import path_to_test_file

def test_no_file():
    pathnames = []
    with pytest.raises(OpgeeException, match="ModelFile: no model XML file or string specified"):
        ModelFile(pathnames, use_default_model=False)  # instantiate_model=True, save_to_path=None)

def test_modifies():
    xml_path = path_to_test_file('test_fields.xml')
    mf = ModelFile(xml_path, use_default_model=True)

def test_many_fields():
    analysis_name = 'test-fields'
    model_xml = path_to_test_file('test-fields-9000.xml')

    field_names = fields_for_analysis(model_xml, analysis_name)
    assert len(field_names) == 8966

    analyses = [analysis_name]

    for field_name, xml_pathname in extracted_model(model_xml, analysis_name, field_names=field_names[:4]):  # extract the first 4 only
        # We just test that the models load
        mf = ModelFile(xml_pathname, add_stream_components=False, use_class_path=False,
                       use_default_model=True, save_to_path=None,
                       analysis_names=analyses,  # may be unnecessary
                       field_names=[field_name])        # may be unnecessary


