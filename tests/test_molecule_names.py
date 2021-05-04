import pytest
from opgee.error import OpgeeException
from opgee.stream import molecule_to_carbon, carbon_to_molecule

parameterize_args = ["c_name, m_name", [('C1', 'CH4'), ('C2', 'C2H6'), ('C5', 'C5H12')]]

@pytest.mark.parametrize(*parameterize_args)
def test_m_to_c(c_name, m_name):
    assert carbon_to_molecule(c_name) == m_name

@pytest.mark.parametrize(*parameterize_args)
def test_c_to_m(c_name, m_name):
    assert c_name == molecule_to_carbon(m_name)

def test_bad_molecule():
    with pytest.raises(OpgeeException, match=r".*Expected hydrocarbon molecule name*"):
        molecule_to_carbon('H2O')

def test_bad_carbon():
    with pytest.raises(OpgeeException, match=r".*Expected carbon number name*"):
        carbon_to_molecule('CH4')
