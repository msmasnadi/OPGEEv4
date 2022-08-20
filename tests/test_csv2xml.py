from opgee.tool import opg
from opgee.model_file import ModelFile

def test_csv2xml():
    output_xml = '/tmp/test-fields.xml'
    count = 5
    cmdline = f'csv2xml -n {count} -p -i etc/test-fields.csv -o "{output_xml}" --overwrite'
    opg(cmdline)

    model_file = ModelFile([output_xml],
                           add_stream_components=False,
                           use_class_path=False,
                           use_default_model=True,
                           instantiate_model=True,
                           save_to_path=None)

    # Just check that the output file has the expected number of fields
    m = model_file.model
    analysis = m.get_analysis('test-fields')
    fields = analysis.fields()
    assert len(fields) == count
