import pytest
import pandas as pd
import pint
from opgee.processes.thermodynamics import Oil
from opgee.core import ureg
from opgee.stream import Stream

@pytest.fixture
def oil_instance():
    API = pint.Quantity(32.8, ureg["degAPI"])
    gas_comp = pd.Series(data=dict(N2=2.0, CO2=6.0, C1=84.0, C2=4.0,
                                   C3=2, C4=1, H2S=1))
    gas_oil_ratio = 2429.30
    res_temp = ureg.Quantity(200, "degF")
    res_press = ureg.Quantity(500, "psi")
    oil = Oil(API, gas_comp, gas_oil_ratio, res_temp, res_press)

    return oil

def test_API(oil_instance):
    stream = Stream("test_stream",temperature=200.0, pressure=1556.0)
    bubble_p = oil_instance.bubble_point_pressure(stream)
    assert bubble_p == pytest.approx(8951.0)

def test_reservoir_solution_GOR(oil_instance):
    oil_instance.reservoir_solution_GOR()