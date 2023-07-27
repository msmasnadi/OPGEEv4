import pytest
from opgee.error import OpgeeException
from opgee.mcs.packet import Packet

def test_exceptions():
    analysis = "a1"

    with pytest.raises(OpgeeException, match="Packet must be initialized with trial_nums and field_name, or field_names"):
        Packet(analysis, trial_nums=[1, 2, 3])

    with pytest.raises(OpgeeException, match="Packet must be initialized with either trial_nums or field_names, not both"):
        Packet(analysis, trial_nums=[1, 2, 3], field_name="foo", field_names=['a', 'b'])

def test_mcs_case():
    trial_nums = [1, 2, 4, 5, 10]
    field_name = 'field-1'
    analysis_name = 'a2'
    pkt = Packet(analysis_name, trial_nums=trial_nums, field_name=field_name)

    assert pkt.analysis_name == analysis_name
    assert pkt.is_mcs
    assert pkt.field_names is None
    assert pkt.field_name == field_name
    assert list(n for n in pkt) == trial_nums

def test_non_mcs_case():
    field_names = ['a', 'b', 'c', 'd']
    analysis_name = 'a3'
    pkt = Packet(analysis_name, field_names=field_names)

    assert pkt.analysis_name == analysis_name
    assert not pkt.is_mcs
    assert pkt.field_names == field_names
    assert pkt.field_name is None
    assert list(n for n in pkt) == field_names
