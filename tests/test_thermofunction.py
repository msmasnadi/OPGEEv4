import pytest
import pandas as pd
import pint
from opgee.processes.thermodynamics import Oil
from opgee.core import ureg
from opgee.stream import Stream

@pytest.fixture
def oil_instance():
    API = pint.Quantity(32.8, ureg["degAPI"])
    gas_comp = pd.Series(data=dict(N2=2.0, CO2=6.0, CH4=84.0, C2H6=4.0,
                                   C3H8=2, C4H10=1, H2S=1))
    gas_oil_ratio = 2429.30
    oil = Oil(API, gas_comp, gas_oil_ratio)

    return oil

def test_API(oil_instance):
    stream = Stream("test_stream",temperature=200.0, pressure=1556.0)
    bubble_p = oil_instance.bubble_point_pressure(stream)
    assert bubble_p == pytest.approx(8951.0)
