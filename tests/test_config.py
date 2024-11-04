import os
import pytest
from opgee.config import (unixPath, getHomeDir, pathjoin, getConfig, getParam,
                          getParamAsBoolean, getParamAsInt, getParamAsFloat,
                          setSection, USR_CONFIG_FILE, stringTrue)
from opgee.error import OpgeeException, ConfigFileError
from .utils_for_tests import load_config_from_string

def test_unixpath():
    assert unixPath(r"\Users\foo\bar") == "/Users/foo/bar"

def test_expanduser():
    if os.environ.get('CI') == 'true':
        home = os.environ['HOME']           # don't use OPGEE_HOME for this test
    else:
        home = getHomeDir()

    assert pathjoin("~", "foo", expanduser=True) == unixPath(f"{home}/foo")

def test_abspath():
    home = getHomeDir()
    os.chdir(home)
    assert pathjoin("foo", "bar", abspath=True) == unixPath(f"{home}/foo/bar")

def test_realpath(tmp_path):    # built-in fixture returns a temporary directory
    foo = tmp_path / 'foo.txt'
    with open(foo, 'w'):   # create an empty file
        pass

    bar = tmp_path / 'bar.txt'
    os.symlink(foo, bar)
    assert pathjoin(bar, realpath=True) == unixPath(str(foo))


def test_reload():
    getConfig()
    getConfig(reload=True) # just making sure it runs

@pytest.fixture(scope="function")
def dummy_config():
    project_name = 'dummy'

    # Create a config section
    cfg_text = f"""
        [DEFAULT]
        OPGEE.DefaultProject = {project_name}
        OPGEE.TextEditor = echo
        
        boolean_param = yes
        int_param = 123
        float_param = 4.5
        
        [{project_name}]
        OPGEE.ProjectName = {project_name}

        X.foo = one
        X.bar = two
        X.baz = three
    """

    # load the config text and make the new section the default
    load_config_from_string(cfg_text)
    setSection(project_name)

    return project_name

def test_config_exact(opgee_main, dummy_config, capsys):
    # capsys is a file like object that captures output to stdout / stderr

    project_name = dummy_config

    opgee_main.run(None, argList=['config', '--exact', 'OPGEE.ProjectName'])
    captured = capsys.readouterr()
    assert captured.out == f"{project_name}\n"

def test_config_cmd(opgee_main, dummy_config, capsys):
    opgee_main.run(None, argList=['config', 'X\\.'])
    captured = capsys.readouterr()
    lines = [line.strip() for line in captured.out.split('\n') if line]
    assert lines == ['[dummy]', 'X.bar = two', 'X.baz = three', 'X.foo = one']

def test_config_edit(opgee_main, dummy_config, capsys):
    opgee_main.run(None, argList=['config', '--edit'])
    captured = capsys.readouterr()
    home = getHomeDir()
    assert captured.out == f"echo {home}/{USR_CONFIG_FILE}\n"

def test_unknown_section(dummy_config):
    with pytest.raises(OpgeeException, match=r"getParam: unknown section .*"):
        getParam('unknown_param', 'unknown_section')

def test_unknown_param(dummy_config):
    with pytest.raises(OpgeeException, match=r"getParam: unknown variable .*"):
        getParam('unknown_param')

def test_string_value():
    assert stringTrue('yes', raiseError=False)
    assert not stringTrue('no')

    assert stringTrue('unknown', raiseError=False) is None

    with pytest.raises(ConfigFileError, match=r"Unrecognized boolean value: .*"):
        stringTrue('unknown', raiseError=True)

def test_getParamAsBoolean(dummy_config):
    with pytest.raises(ConfigFileError, match=r"The value of variable .* could not converted to boolean."):
        getParamAsBoolean('X.foo')

    assert getParamAsBoolean('boolean_param') is True

def test_getParamAsInt(dummy_config):
    with pytest.raises(ValueError):
        getParamAsInt('X.foo')

    assert getParamAsInt('int_param') == 123

def test_getParamAsFloat(dummy_config):
    with pytest.raises(ValueError):
        getParamAsFloat('X.foo')

    assert getParamAsFloat('int_param') == 123.0
    assert getParamAsFloat('float_param') == 4.5
