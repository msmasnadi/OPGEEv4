import pytest
from opgee.error import CommandlineError
from .utils_for_tests import path_to_test_file

def test_run_builtin(opgee):
    try:
        opgee.run(None, ['run', '-a', 'test'])
        good = True
    except Exception as e:
        print(e)
        good = False

    assert good

def test_unknown_analysis(opgee):
    name = 'unknown-analysis'
    with pytest.raises(CommandlineError, match=r"Specified analyses .* not found in model"):
        opgee.run(None, ['run', '-a', name])

def test_unknown_field(opgee):
    name = 'unknown-field'
    with pytest.raises(CommandlineError, match=r"The model contains no fields matching command line arguments."):
        opgee.run(None, ['run', '-f', name])

def test_run_test_model(opgee):
    xml_path = path_to_test_file('test_model.xml')
    try:
        opgee.run(None, ['run', '-f', 'test', '--no_default_model', '-m', xml_path])
        good = True
    except Exception as e:
        good = False

    assert good

def test_no_model(opgee):
    with pytest.raises(CommandlineError, match=r"No model to run: .*"):
        opgee.run(None, ['run', '-a', 'test', '--no_default_model'])
