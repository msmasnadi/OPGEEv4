import pytest
import pandas as pd
import pint
from opgee.processes.thermodynamics import Oil
from opgee.core import ureg
from opgee.stream import Stream

num_digits = 3

@pytest.fixture
def oil_instance():
    API = pint.Quantity(32.8, ureg["degAPI"])
    # gas_comp = pd.Series(data=dict(N2=2.0, CO2=6.0, C1=84.0, C2=4.0,
    #                                C3=2, C4=1, H2S=1))/100
    gas_comp = pd.Series(data=dict(N2=0.004, CO2=0.0, C1=0.966, C2=0.02,
                                   C3=0.01, C4=0.0, H2S=0))
    gas_oil_ratio = 2429.30
    res_temp = ureg.Quantity(200, "degF")
    res_press = ureg.Quantity(1556.6, "psi")
    oil = Oil(API, gas_comp, gas_oil_ratio, res_temp, res_press)

    return oil

def test_gas_specific_gravity(oil_instance):
    gas_SG = oil_instance.gas_specific_gravity()

    # stream = Stream("test_stream",temperature=200.0, pressure=1556.0)
    # bubble_p = oil_instance.bubble_point_pressure()
    assert round(gas_SG, num_digits) == pytest.approx(0.581)

def test_bubble_point_solution_GOR(oil_instance):
    gor_bubble = oil_instance.bubble_point_solution_GOR()
    assert round(gor_bubble, num_digits) == pytest.approx(2822.361)

def test_reservoir_solution_GOR(oil_instance):
    res_GOR = oil_instance.reservoir_solution_GOR()
    assert round(res_GOR, num_digits) == pytest.approx(286.983)

def test_bubble_point_pressure(oil_instance):
    p_bubblepoint = oil_instance.bubble_point_pressure()
    assert round(p_bubblepoint) == pytest.approx(9337)

def test_bubble_point_formation_volume_factor(oil_instance):
    bubble_oil_FVF = oil_instance.bubble_point_formation_volume_factor()
    assert round(bubble_oil_FVF, num_digits) == pytest.approx(1.194)

def test_solution_gas_oil_ratio(oil_instance):
    stream = Stream("test_stream",temperature=200.0, pressure=1556.0)
    solution_gor = oil_instance.solution_gas_oil_ratio(stream)
    assert round(solution_gor, 1) == pytest.approx(286.8)

def test_saturated_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    sat_fvf = oil_instance.saturated_formation_volume_factor(stream)
    assert round(sat_fvf, num_digits) == pytest.approx(1.194)

def test_unsat_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    unsat_fvf = oil_instance.unsat_formation_volume_factor(stream)
    assert round(unsat_fvf, num_digits) == pytest.approx(1.223)

def test_isothermal_compressibility_X(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    iso_compress_x = oil_instance.isothermal_compressibility_X(stream)
    assert round(iso_compress_x, num_digits) == pytest.approx(-0.032)

def test_isothermal_compressibility(oil_instance):
    iso_compress = oil_instance.isothermal_compressibility()
    assert round(iso_compress, num_digits) == pytest.approx(3.05e-6)