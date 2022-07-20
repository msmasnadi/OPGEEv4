import pytest
from opgee.model_file import ModelFile

@pytest.fixture(scope="module")
def opgee():
    mf = ModelFile(None, use_default_model=True)
    return mf.model


def test_gas_lifting_field(opgee):
    analysis = opgee.get_analysis('test_analysis')
    # Just testing that we can run the fields without error
    for field in analysis.fields():
        field.run(analysis)
