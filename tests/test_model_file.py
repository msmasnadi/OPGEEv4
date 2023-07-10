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


def test_many_field_comparison():
    from opgee.mcs.simulation import run_serial

    analysis_name = 'test-fields'
    model_xml_file = path_to_test_file('test-fields-9000.xml')

    field_names = fields_for_analysis(model_xml_file, analysis_name)

    N = 4
    # run the first 4 only
    energy_cols, emissions_cols, errors = run_serial(model_xml_file, analysis_name, field_names[:N])

    assert len(energy_cols) + len(errors) == N
