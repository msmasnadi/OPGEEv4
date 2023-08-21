import pytest
from packet import FieldPacket, TrialPacket, _batched

def test_batched():
    with pytest.raises(ValueError, match="_batched: length must be > 0"):
        list(_batched([1, 2, 3], 0))

def test_trial_packet():
    trial_nums = [1, 2, 4, 5, 10]
    field_name = 'field-1'
    sim_dir = '/foo/bar/baz'
    pkt = TrialPacket(sim_dir, field_name, trial_nums)

    assert pkt.sim_dir == sim_dir
    assert pkt.items == trial_nums
    assert pkt.field_name == field_name
    assert list(n for n in pkt) == trial_nums

def test_field_packet():
    field_names = ['a', 'b', 'c', 'd']
    analysis_name = 'a3'
    pkt = FieldPacket(analysis_name, field_names)

    assert pkt.analysis_name == analysis_name
    assert pkt.items == field_names
    assert list(n for n in pkt) == field_names
