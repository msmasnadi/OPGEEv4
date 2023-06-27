import pytest
from opgee.config import setParam
from opgee.error import CommandlineError
from .utils_for_tests import path_to_test_file

def test_unknown_analysis(opgee_main):
    name = 'unknown-analysis'
    with pytest.raises(CommandlineError, match=r"Specified analyses .* not found in model"):
        opgee_main.run(None, ['run', '-a', name])


def test_unknown_field(opgee_main):
    name = 'unknown-field'
    with pytest.raises(CommandlineError, match=r"Indicated field names .* were not found in model"):
         opgee_main.run(None, ['run', '-f', name])


def test_run_test_model(opgee_main):
    from opgee.process import decache_subclasses
    from opgee.tool import opg

    decache_subclasses()
    setParam('OPGEE.ClassPath', path_to_test_file('user_processes.py'))

    xml_path = path_to_test_file('test_model2.xml')
    cmd = f"run -f Field1 -m {xml_path} --no-default-model"
    print(f"Running 'opg {cmd}'")

    try:
        opg(cmd)
        good = True

    except Exception as e:
        print(f"ERROR: test_run_test_model: {e}")
        good = False

    setParam('OPGEE.ClassPath', '')  # avoid reloading user_processes.py
    assert good


def test_no_model(opgee_main):
    with pytest.raises(CommandlineError, match=r"No model to run: .*"):
        opgee_main.run(None, ['run', '-a', 'test', '--no-default-model'])
