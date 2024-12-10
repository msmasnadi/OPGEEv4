import pytest
from opgee.units import ureg
from opgee.core import magnitude, dict_from_list, validate_unit, XmlInstantiable, A, _undefined_units
from opgee.error import OpgeeException, AbstractMethodError

def test_magnitude_error():
    q = ureg.Quantity(10.0, "tonnes/day")
    with pytest.raises(OpgeeException, match=r"magnitude: value .* units are not .*"):
        magnitude(q, ureg.Unit("tonnes/year"))

def test_dict_from_list():
    foo = XmlInstantiable("foo")
    bar = XmlInstantiable("bar")
    baz = XmlInstantiable("baz")
    items = [foo, bar, baz]
    d = dict_from_list(items)

    assert len(d) == 3 and d['foo'] == foo and d['bar'] == bar and d['baz'] == baz

def test_dict_from_list_error():
    items = [XmlInstantiable("foo"), XmlInstantiable("bar"), XmlInstantiable("foo")]
    with pytest.raises(OpgeeException, match="XmlInstantiable instances must have unique names: foo is not unique."):
        dict_from_list(items)

def test_from_xml_error():
    with pytest.raises(AbstractMethodError, match=f"Abstract method XmlInstantiable.from_xml was called.*"):
        XmlInstantiable("foo").from_xml(None)

def test_find_parent_error():
    assert XmlInstantiable("foo").find_container('Model') is None

def test_validate_unit_error(configure_logging_for_tests):
    unit = 'not_a_unit'
    assert unit not in _undefined_units
    assert validate_unit(unit) is None and unit in _undefined_units

def test_A_set_value_None():
    a = A('foo', value=None)
    assert a.value is None

def test_A_str_rep():
    value = 10
    unit  = 'mmbtu/day'
    a = A('foo', value=value, pytype='float', unit=unit)
    assert str(a).startswith("<A name='foo' type='float'")
    assert a.value == ureg.Quantity(value, unit)


count = 0

def fn1(a, b):
    global count
    count += 1
    return a + b + count
