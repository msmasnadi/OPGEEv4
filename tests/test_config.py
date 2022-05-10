from opgee.config import *

def test_unixpath():
    assert unixPath(r"\Users\foo\bar") == "/Users/foo/bar"

def test_expanduser():
    if os.environ.get('TRAVIS') == 'true':
        home = os.environ['HOME']           # don't use OPGEE_HOME for this test
    else:
        home = getHomeDir()

    assert pathjoin("~", "foo", expanduser=True) == unixPath(f"{home}/foo")

def test_abspath():
    home = getHomeDir()
    os.chdir(home)
    assert pathjoin("foo", "bar", abspath=True) == unixPath(f"{home}/foo/bar")

def test_reload():
    getConfig()
    getConfig(reload=True) # just making sure it runs
