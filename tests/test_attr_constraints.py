import pytest
from opgee.error import OpgeeException
from .utils_for_tests import load_test_model

@pytest.fixture(scope="module")
def constraint_model(configure_logging_for_tests):
    return

# N.B. The previously mutually exclusive attributes tested here no longer are exclusive
# def test_excludes():
#     with pytest.raises(OpgeeException, match=r".*Exclusive attribute.*"):
#         load_test_model('test_attr_constraints_1.xml')


def test_syncs():
    with pytest.raises(OpgeeException, match=r".*Attributes in synchronized.*"):
        load_test_model('test_attr_constraints_2.xml')

def test_constraints():
    with pytest.raises(OpgeeException, match=r".*Attribute '.*': constraint failed.*"):
        load_test_model('test_attr_constraints_3.xml')



