from opgee.config import *

def test_unixpath():
    assert unixPath(r"\Users\foo\bar") == "/Users/foo/bar"

def test_expanduser():
    home = os.getenv('HOME')
    assert pathjoin("~", "foo", expanduser=True) == f"{home}/foo"

def test_abspath():
    home = os.getenv('HOME')
    os.chdir(home)
    assert pathjoin("foo", "bar", abspath=True) == f"{home}/foo/bar"

def test_reload():
    getConfig()
    getConfig(reload=True) # just making sure it runs

# @pytest.mark.parametrize(
#     "vers, expected",
#     [('1.2.3', Version(major=1, minor=2, patch=3, prerelease=None, build=None)),
#      ('4.5',   Version(major=4, minor=5, patch=0, prerelease=None, build=None)),
#      ('4.0.0-alpha', Version(major=4, minor=0, patch=0, prerelease='alpha', build=None))]
# )
# def test_parse_version_info(vers, expected):
#     result = parse_version_info(vers)
#     assert result == expected
