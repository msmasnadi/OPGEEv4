import pytest
from opgee import ureg
from opgee.core import magnitude, dict_from_list, validate_unit, XmlInstantiable, A, _undefined_units, cached
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
    with pytest.raises(AbstractMethodError, match=f"Abstract method XmlInstantiable.from_xml was called. A subclass of XmlInstantiable must implement this method."):
        XmlInstantiable("foo").from_xml(None)

def test_find_parent_error():
    assert XmlInstantiable("foo").find_parent('Model') is None

def test_validate_unit_error(configure_logging_for_tests):
    unit = 'not_a_unit'
    assert unit not in _undefined_units
    assert validate_unit(unit) is None and unit in _undefined_units

def test_A_set_value_None():
    a = A('foo', value=None)
    assert a.value is None

def test_A_str_rep():
    a = A('foo', value=10, pytype='float', unit='mmbtu/day')
    assert str(a) == "<A name='foo' type='float' value='10.0 mmbtu/d'>"


count = 0

def fn1(a, b):
    global count
    count += 1
    return a + b + count

@cached
def fn2(a, b):
    global count
    count += 1
    return a + b + count

def test_cached():
    global count

    count = 0
    assert fn1(1, 2) + fn1(1, 2) == 9

    count = 0
    assert fn2(1, 2) + fn2(1, 2) == 8
