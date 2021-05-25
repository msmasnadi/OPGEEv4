import pytest
from opgee.error import OpgeeException
from opgee.table_manager import TableManager
from .utils_for_tests import path_to_test_file

def test_add_table():
    table_name = 'test_table'
    csv_path = path_to_test_file(f'{table_name}.csv')
    mgr = TableManager()
    mgr.add_table(csv_path, index_col=0, skiprows=1)
    df = mgr.get_table(table_name)
    assert (df.shape == (3, 2) and df.loc['foo', 'value2'] == 20.6)

def test_bad_table_name():
    mgr = TableManager()
    name = 'non-existent-table'
    with pytest.raises(OpgeeException, match=f"Unknown table '{name}'"):
        mgr.get_table(name)
