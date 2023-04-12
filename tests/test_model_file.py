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
    import pandas as pd
    from opgee.core import magnitude
    from opgee.config import getParam, pathjoin

    analysis_name = 'test-fields'
    model_xml = path_to_test_file('test-fields-9000.xml')

    field_names = fields_for_analysis(model_xml, analysis_name)

    energy_cols = []
    emission_cols = []

    def total_emissions(proc, gwp):
        rates = proc.emissions.rates(gwp)
        total = rates.loc["GHG"].sum()
        return magnitude(total)

    # Extract and run the first 3 Fields only since we're just testing the extraction mechanism
    for field_name, xml_pathname in extracted_model(model_xml, analysis_name, field_names=field_names):
        mf = ModelFile(xml_pathname, add_stream_components=False, use_class_path=False,
                       use_default_model=True, save_to_path=None,
                       analysis_names=[analysis_name],   # may be unnecessary
                       field_names=[field_name])         # may be unnecessary

        model = mf.model
        analysis = model.get_analysis(analysis_name)
        field = analysis.get_field(field_name)
        field.run(analysis)

        procs = field.processes()
        energy_by_proc = {proc.name: magnitude(proc.energy.rates().sum()) for proc in procs}
        s = pd.Series(energy_by_proc, name=field.name)
        energy_cols.append(s)

        emissions_by_proc = {proc.name: total_emissions(proc, analysis.gwp) for proc in procs}
        s = pd.Series(emissions_by_proc, name=field.name)
        emission_cols.append(s)

    def _save(columns, csvpath):
        df = pd.concat(columns, axis='columns')
        df.index.name = 'process'
        df.sort_index(axis='rows', inplace=True)

        print(f"Writing '{csvpath}'")
        df.to_csv(csvpath)

    temp_dir = getParam('OPGEE.TempDir')
    basename = "test-comparison.csv"
    _save(energy_cols,   pathjoin(temp_dir, "energy-" + basename))
    _save(emission_cols, pathjoin(temp_dir, "emissions-" + basename))

