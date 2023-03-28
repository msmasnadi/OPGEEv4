import pytest
from opgee.error import CommandlineError
from .utils_for_tests import path_to_test_file


def test_unknown_analysis(opgee):
    name = 'unknown-analysis'
    with pytest.raises(CommandlineError, match=r"Specified analyses .* not found in model"):
        opgee.run(None, ['run', '-a', name])


def test_unknown_field(opgee):
    name = 'unknown-field'
    with pytest.raises(CommandlineError, match=r"Indicated field names .* were not found in model"):
         opgee.run(None, ['run', '-f', name])


def test_run_test_model(opgee):

    # NOT UNUSED! Defines procs referenced by test_model2.xml
    from .files import user_processes

    xml_path = path_to_test_file('test_model2.xml')
    try:
        args = ['run', '-f', 'Field1', '-m', xml_path, '--no-default-model']
        cmd = ' '.join(args)
        #print(f"Running 'opg {cmd}'")
        opgee.run(None, args)
        good = True

    except Exception as e:
        print(f"ERROR: test_run_test_model: {e}")
        good = False

    assert good


def test_no_model(opgee):
    with pytest.raises(CommandlineError, match=r"No model to run: .*"):
        opgee.run(None, ['run', '-a', 'test', '--no-default-model'])
