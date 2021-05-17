import pytest
from opgee.error import CommandlineError

def test_graph_classes(opgee):
    pathname = '/dev/null'
    try:
        opgee.run(None, ['graph', '--classes', 'core', '--classes_output', pathname])
        good = True
    except Exception as e:
        good = False

    assert good

def test_graph_field(opgee):
    pathname = '/tmp/graph.png'
    try:
        opgee.run(None, ['graph', '--field', 'test', '--field_output', pathname])
        good = True
    except Exception as e:
        good = False

    assert good

def test_graph_model(opgee):
    pathname = '/dev/null'
    try:
        opgee.run(None, ['graph', '--hierarchy_output', pathname])
        good = True
    except Exception as e:
        good = False

    assert good

def test_unknown_field(opgee):
    with pytest.raises(CommandlineError, match=r"Field name .* was not found in model"):
        opgee.run(None, ['graph', '--field', 'unknown-field'])
