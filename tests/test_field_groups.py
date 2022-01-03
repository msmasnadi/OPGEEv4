import pytest
from .utils_for_tests import load_test_model

def test_field_groups():
    field_groups_model = load_test_model('field_groups_model.xml')
    field_groups_model.validate()
    analysis = field_groups_model.get_analysis('test')
    # Pattern should match only fields 'test1' and 'test2', and not 'test3'
    assert analysis.get_field('test1') and analysis.get_field('test2') and not analysis.get_field('test3', raiseError=False)

