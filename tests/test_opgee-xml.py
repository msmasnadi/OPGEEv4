import pytest
from opgee.model_file import ModelFile

@pytest.fixture(scope="module")
def opgee():
    mf = ModelFile(None, use_default_model=True)
    return mf.model


@pytest.mark.parametrize(
    "field_name", [ # ('gas_lifting_field'),  # TODO: doesn't work yet.
                   ('oil_stab_field'),
                   ('steam_flooding_field')])
def test_gas_lifting_field(opgee, field_name):
    analysis = opgee.get_analysis('test_analysis')
    field = analysis.get_field(field_name)

    # Just testing that we can run the fields without error
    field.run(analysis)
