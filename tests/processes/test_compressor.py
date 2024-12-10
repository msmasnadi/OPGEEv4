import functools

import pytest
from pint import DimensionalityError, Quantity

from opgee.processes.compressor import Compressor
from opgee.units import ureg

Q_ = ureg.Quantity

def test_get_compression_ratio():
    overall_comp_ratio = Q_(25., 'kilopascal') / Q_(0.5, 'psia')
    result = Compressor.get_compression_ratio_and_stage(overall_comp_ratio)
    assert result is not None
    _approx = functools.partial(pytest.approx, rel=10e-3, abs=10e-6)
    comp_ratio, num_stages = result
    assert comp_ratio.m == _approx(2.6929, rel=10E-3, abs=10E-6)
    assert num_stages == 2
    
    # works with pure floats as well
    result = Compressor.get_compression_ratio_and_stage(3 / 2)
    assert result is not None
    comp_ratio, num_stages = result
    assert isinstance(comp_ratio, Quantity)
    assert comp_ratio.m == 1.5
    assert num_stages == 1
    
def test_get_compression_ratio_not_dimensionless():
    overall_compression_ratio = Q_(1., 'kPa') / Q_(1., 'sec')
    
    with pytest.raises(DimensionalityError):
        _ = Compressor.get_compression_ratio_and_stage(overall_compression_ratio)
        
def test_get_compression_ratio_stages_qtys():
    ratios = [1., 1000., 0.558, 100]
    comp_ratios = [Q_(r, "frac") for r in ratios]
    result = Compressor.get_compression_ratio_stages(comp_ratios)
    assert len(result) > 0
    