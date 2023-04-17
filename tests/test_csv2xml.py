import os
from opgee.tool import opg
from opgee.model_file import ModelFile
from .utils_for_tests import tmpdir, path_to_test_file

def test_csv2xml():
    output_xml = tmpdir('test-fields.xml')
    input_csv = path_to_test_file('test-fields.csv')

    count = 5
    cmdline = f'csv2xml -n {count} -i "{input_csv}" -o "{output_xml}" --overwrite'
    opg(cmdline)

    model_file = ModelFile([output_xml],
                           add_stream_components=False,
                           use_class_path=False,
                           use_default_model=True,
                           instantiate_model=True,
                           save_to_path=None)

    os.remove(output_xml)

    # Just check that the output file has the expected number of fields
    m = model_file.model
    analysis = m.get_analysis('test-fields')
    fields = analysis.fields()
    assert len(fields) == count

