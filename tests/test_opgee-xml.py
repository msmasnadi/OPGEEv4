import pytest
from opgee import ureg
from opgee.model_file import ModelFile

@pytest.fixture(scope="module")
def opgee():
    mf = ModelFile(None, use_default_model=True)
    return mf.model


@pytest.mark.parametrize(
    "field_name", [ ('gas_lifting_field')])
def test_gas_lifting_field(opgee, field_name):
    analysis = opgee.get_analysis('example')
    field = analysis.get_field(field_name)

    # Just testing that we can run the fields without error
    field.run(analysis)

# TODO: This is a temporary test just for debugging smart defaults. Delete this test after solving the smart defaults issue.
@pytest.mark.parametrize(
    "field_name", [ ('gas_lifting_field')])
def test_smart_default(opgee, field_name):
    analysis = opgee.get_analysis('example')
    field = analysis.get_field(field_name)
    T = field.attr('prod_water_inlet_temp')

    assert T == ureg.Quantity(340, 'degF')
