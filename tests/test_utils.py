import pytest

from opgee import ureg
from opgee.error import OpgeeException
from opgee.utils import getBooleanXML, coercible, mkdirs, loadModuleFromPath

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

def test_load_module_failure():
    with pytest.raises(OpgeeException, match=f".*Can't load module.*"):
        loadModuleFromPath("/not/a/rea/path.py", raiseError=True)

    loadModuleFromPath("/not/a/rea/path.py", raiseError=False)
