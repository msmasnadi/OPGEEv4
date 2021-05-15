from opgee.config import *
from semver import Version

def test_unixpath():
    assert unixPath(r"\Users\foo\bar") == "/Users/foo/bar"

# @pytest.mark.parametrize(
#     "vers, expected",
#     [('1.2.3', Version(major=1, minor=2, patch=3, prerelease=None, build=None)),
#      ('4.5',   Version(major=4, minor=5, patch=0, prerelease=None, build=None)),
#      ('4.0.0-alpha', Version(major=4, minor=0, patch=0, prerelease='alpha', build=None))]
# )
# def test_parse_version_info(vers, expected):
#     result = parse_version_info(vers)
#     assert result == expected
