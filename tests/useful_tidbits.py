import pytest

# From https://python.plainenglish.io/unit-testing-in-python-structure-57acd51da923
@pytest.mark.parametrize(
    "n,expected", [(0, 0), (1, 1), (2, 1), (3, 2), (4, 3), (5, 5), (6, 8)]
)
def test_route_status(n, expected):
    assert fib(n) == expected

#
# Testing exception handling
#

# From pytest docs
def test_zero_division():
    with pytest.raises(ZeroDivisionError):
        1 / 0

# test the actual exception info
def test_recursion_depth():
    with pytest.raises(RuntimeError) as excinfo:

        def f():
            f()

        f()
    assert "maximum recursion" in str(excinfo.value)

def myfunc():
    raise ValueError("Exception 123 raised")

# test that a regular expression matches on the string representation of an exception
def test_match():
    with pytest.raises(ValueError, match=r".* 123 .*"):
        myfunc()

# There’s an alternate form of the pytest.raises() function where you pass a function
# that will be executed with the given *args and **kwargs and assert that the given
# exception is raised:
# pytest.raises(ExpectedException, func, *args, **kwargs)

