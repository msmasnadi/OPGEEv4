import pytest
from opgee import ureg
from opgee.model_file import ModelFile

@pytest.fixture(scope="module")
def opgee_model():
    mf = ModelFile(None, use_default_model=True)
    return mf.model


@pytest.mark.parametrize(
    "field_name", [ ('gas_lifting_field')])
def test_gas_lifting_field(opgee_model, field_name):
    analysis = opgee_model.get_analysis('example')
    field = analysis.get_field(field_name)

    # Just testing that we can run the fields without error
    field.run(analysis)
