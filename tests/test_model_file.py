import pytest

from opgee.error import OpgeeException
from opgee.model_file import ModelFile, extract_model, fields_for_analysis

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


def test_many_field_comparison():
    from opgee.manager import run_serial

    analysis_name = 'test-fields'
    model_xml_file = path_to_test_file('test-fields-9000.xml')

    field_names = fields_for_analysis(model_xml_file, analysis_name)

    N = 4
    # run the first 4 only
    results = run_serial(model_xml_file, analysis_name, field_names[:N])

    assert len(results) == N

def test_extract_model():
    analysis_name = "test_boundary"
    model_xml = path_to_test_file("test_boundary.xml")
    for field_name, xml_str in extract_model(model_xml=model_xml, analysis_name=analysis_name, field_names=[]):
        mf = ModelFile.from_xml_string(xml_str, add_stream_components=False,
                                       use_class_path=False,
                                       use_default_model=True,
                                       analysis_names=[analysis_name],
                                       field_names=[field_name])
        analysis = mf.model.get_analysis(analysis_name)
        assert analysis.boundary == "Distribution"
        assert analysis.fn_unit == "gas"
    
    analysis_name = "example"
    model_xml = path_to_test_file("gas_lifting_field.xml")
    for fn, xs in extract_model(model_xml, analysis_name, []):
        mf = ModelFile.from_xml_string(xs, add_stream_components=False,
                                       use_class_path=False,
                                       use_default_model=True,
                                       analysis_names=[analysis_name],
                                       field_names=[fn])
        analysis = mf.model.get_analysis(analysis_name)
        assert analysis.boundary == "Production"
        assert analysis.fn_unit == "oil"