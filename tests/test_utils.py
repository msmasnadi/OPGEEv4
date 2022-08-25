import os
import pytest

from opgee import ureg
from opgee.error import OpgeeException
from opgee.utils import (getBooleanXML, coercible, mkdirs, loadModuleFromPath,
                         removeTree, parseTrialString, getResource)
from .utils_for_tests import tmpdir

@pytest.mark.parametrize(
    "value, expected", [("true", True), ("yes", True), ("1", True),
                        ("false", False), ("no", False), ("0", False), ("none", False)
                        ]
)
def test_boolean_xml(value, expected):
    assert getBooleanXML(value) == expected


def test_boolean_xml_failure():
    value = "xyz"
    with pytest.raises(OpgeeException, match=f"Can't convert '{value}' to boolean.*"):
        getBooleanXML(value)

@pytest.mark.parametrize(
    "value, pytype, result", [(10, "float", 10.0),
                              ("11.0", "int", 11),
                              (ureg.Quantity(20.9, "tonnes"), "ignored", ureg.Quantity(20.9, "tonnes"))]
)
def test_coercible(value, pytype, result):
    assert coercible(value, pytype) == result


def test_coercible_failure():
    with pytest.raises(OpgeeException, match=f".*is not coercible.*"):
        coercible(10.7, "int")

    with pytest.raises(OpgeeException, match=f".*not a recognized type string.*"):
        coercible(10.7, "blah-blah-blah")

    with pytest.raises(OpgeeException, match=f".*is not coercible.*"):
        coercible("foobar", float)

def test_mkdirs():
    with pytest.raises(TypeError):
        mkdirs(12345)

    d = tmpdir('foo', 'bar', 'baz')
    mkdirs(d)
    assert os.path.isdir(d)

    removeTree(d)
    assert not os.path.isdir(d)

    removeTree(d, ignore_errors=True)

    with pytest.raises(FileNotFoundError):
        removeTree(d, ignore_errors=False)

    from opgee.config import IsWindows
    if not IsWindows:
        with pytest.raises(OSError):
            mkdirs('/not/a/real/path')


def test_load_module_failure():
    with pytest.raises(OpgeeException, match=f".*Can't load module.*"):
        loadModuleFromPath("/not/a/rea/path.py", raiseError=True)

    loadModuleFromPath("/not/a/rea/path.py", raiseError=False)

def test_trial_string():
    s = '1, 41, 3, 7-11'
    nums = parseTrialString(s)
    assert set(nums) == {1, 3, 7, 8, 9, 10, 11, 41}

    with pytest.raises(ValueError):
        parseTrialString(s + 'junk')

def test_getResource():
    x = getResource('etc/units.txt')

    with pytest.raises(OpgeeException):
        getResource('not/a/real/resource')
