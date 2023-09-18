import pytest
from opgee.model_file import ModelFile

@pytest.fixture(scope="module")
def opgee_model():
    mf = ModelFile(None, use_default_model=True)
    return mf.model

def test_gas_lifting_field(opgee_model):
    analysis = opgee_model.get_analysis('example')
    field = analysis.get_field('gas_lifting_field')

    # Just testing that we can run the fields without error
    field.run(analysis)
