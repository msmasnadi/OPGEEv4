import os
import pytest
from opgee.error import CommandlineError
from .utils_for_tests import path_to_test_file

def test_graph_classes(opgee):
    pathname = path_to_test_file('classes.png')
    try:
        opgee.run(None, ['graph', '--classes', 'core', '--classes_output', pathname])
        os.remove(pathname)
        good = True
    except Exception as e:
        good = False

    assert good

def test_graph_classes(opgee):
    pathname = path_to_test_file('field.png')
    try:
        opgee.run(None, ['graph', '--field', 'test', '--field_output', pathname])
        os.remove(pathname)
        good = True
    except Exception as e:
        good = False

    assert good

def test_graph_model(opgee):
    pathname = path_to_test_file('model_hierarchy.png')
    try:
        opgee.run(None, ['graph', '--hierarchy_output', pathname])
        os.remove(pathname)
        good = True
    except Exception as e:
        good = False

    assert good

def test_unknown_field(opgee):
    with pytest.raises(CommandlineError, match=r"Field name .* was not found in model"):
        opgee.run(None, ['graph', '--field', 'unknown-field'])
