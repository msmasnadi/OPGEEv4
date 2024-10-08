import os
from opgee.tool import opg
from opgee.model_file import ModelFile
from .utils_for_tests import tmpdir, path_to_test_file, tempdir

def test_csv2xml():
    with tempdir() as output_dir:
        output_xml = os.path.join(output_dir, 'test-fields.xml')
        input_csv = path_to_test_file('test-fields.csv')

        count = 5
        cmdline = f'csv2xml -n {count} -i "{input_csv}" -o "{output_xml}" --overwrite'
        opg(cmdline)
        analysis_name = 'test-fields'

        model_file = ModelFile([output_xml],
                               analysis_names=[analysis_name],
                               add_stream_components=False,
                               use_class_path=False,
                               use_default_model=True,
                               instantiate_model=True,
                               save_to_path=None)

    # Just check that the output file has the expected number of fields
    m = model_file.model
    analysis = m.get_analysis(analysis_name)
    fields = analysis.fields()
    assert len(fields) == count
