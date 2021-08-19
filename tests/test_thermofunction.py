import pandas as pd
import pytest
from opgee.thermodynamics import Oil, Gas, Water
from opgee.stream import Stream
from opgee import ureg


@pytest.fixture(scope="module")
def oil_instance(test_model):
    field = test_model.get_field("test")
    oil = Oil(field)
    oil._after_init()
    return oil


def test_gas_specific_gravity(oil_instance):
    gas_SG = oil_instance.gas_specific_gravity
    assert gas_SG == ureg.Quantity(pytest.approx(0.622999935), "frac")


def test_bubble_point_solution_GOR(oil_instance):
    GOR = oil_instance.gas_oil_ratio
    gor_bubble = oil_instance.bubble_point_solution_GOR(GOR)
    assert gor_bubble == ureg.Quantity(pytest.approx(2822.361), "scf/bbl_oil")


def test_oil_specific_gravity(oil_instance):
    oil_SG = oil_instance.specific_gravity(oil_instance.API)
    assert oil_SG == ureg.Quantity(pytest.approx(oil_instance.oil_specific_gravity.m), "frac")


def test_reservoir_solution_GOR(oil_instance):
    res_GOR = oil_instance.reservoir_solution_GOR()
    assert res_GOR == ureg.Quantity(pytest.approx(291.334541), "scf/bbl_oil")


def test_bubble_point_pressure(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    p_bubblepoint = oil_instance.bubble_point_pressure(stream, oil_SG, gas_SG, GOR)
    assert p_bubblepoint == ureg.Quantity(pytest.approx(9227.70805), "psia")


def test_solution_gas_oil_ratio(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    solution_gor = oil_instance.solution_gas_oil_ratio(stream, oil_SG, gas_SG, GOR)
    assert solution_gor == ureg.Quantity(pytest.approx(291.191262), "scf/bbl_oil")


def test_saturated_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    sat_fvf = oil_instance.saturated_formation_volume_factor(stream, oil_SG, gas_SG, GOR)
    assert sat_fvf == ureg.Quantity(pytest.approx(1.19898185), "frac")


def test_unsat_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    unsat_fvf = oil_instance.unsat_formation_volume_factor(stream, oil_SG, gas_SG, GOR)
    assert unsat_fvf == ureg.Quantity(pytest.approx(1.22745738), "frac")


def test_isothermal_compressibility_X(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    iso_compress_x = oil_instance.isothermal_compressibility_X(stream, oil_SG, gas_SG, GOR)
    assert iso_compress_x == ureg.Quantity(0.0, "pa**-1")


def test_isothermal_compressibility(oil_instance):
    oil_SG = oil_instance.oil_specific_gravity
    iso_compress = oil_instance.isothermal_compressibility(oil_SG)
    assert iso_compress == ureg.Quantity(pytest.approx(3.0528295800365155e-6), "pa**-1")


def test_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    fvf = oil_instance.formation_volume_factor(stream, oil_SG, gas_SG, GOR)
    assert fvf == ureg.Quantity(pytest.approx(1.19898185), "frac")


def test_oil_density(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    density = oil_instance.density(stream, oil_SG, gas_SG, GOR)
    assert density == ureg.Quantity(pytest.approx(46.8997952), "lb/ft**3")


def test_oil_mass_energy_density(oil_instance):
    mass_energy_density = oil_instance.oil_LHV_mass
    assert mass_energy_density == ureg.Quantity(pytest.approx(18279.816), "btu/lb")


def test_oil_volume_flow_rate(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    stream.set_flow_rate("oil", "liquid", 276.534764)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    volume_flow_rate = oil_instance.volume_flow_rate(stream, oil_SG, gas_SG, GOR)
    assert volume_flow_rate == ureg.Quantity(pytest.approx(2315.23726), "bbl_oil/day")


def test_oil_volume_energy_density(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    volume_energy_density = oil_instance.volume_energy_density(stream, oil_SG, gas_SG, GOR)
    assert volume_energy_density == ureg.Quantity(pytest.approx(4.81349274), "mmBtu/bbl_oil")


def test_oil_energy_flow_rate(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    stream.set_flow_rate("oil", "liquid", 273.831958)
    energy_flow_rate = oil_instance.energy_flow_rate(stream)
    assert energy_flow_rate == ureg.Quantity(pytest.approx(11035.4544), "mmbtu/day")


def test_oil_heat_capacity(oil_instance):
    temp = ureg.Quantity(127.5, "degF")
    API = oil_instance.API
    heat_capacity = oil_instance.specific_heat(API, temp)
    assert heat_capacity == ureg.Quantity(pytest.approx(0.48734862), "btu/lb/degF")


def test_liquid_fuel_comp(oil_instance):
    API = ureg.Quantity(10, "degAPI")
    liquid_fuel_comp = oil_instance.liquid_fuel_composition(API)
    assert liquid_fuel_comp["C"] == ureg.Quantity(pytest.approx(71.432), "mol/kg")


@pytest.fixture
def gas_instance(test_model):
    field = test_model.get_field("test")
    gas = Gas(field)
    gas._after_init()
    return gas


@pytest.fixture
def stream():
    s = Stream("test_stream", temperature=200.0, pressure=1556.0)
    s.set_flow_rate("N2", "gas", 4.90497)
    s.set_flow_rate("CO2", "gas", 0.889247)
    s.set_flow_rate("C1", "gas", 87.59032)
    s.set_flow_rate("C2", "gas", 9.75715)
    s.set_flow_rate("C3", "gas", 4.37353)
    s.set_flow_rate("C4", "gas", 2.52654)
    return s


def test_total_molar_flow_rate(gas_instance, stream):
    total_molar_flow_rate = gas_instance.total_molar_flow_rate(stream)
    assert total_molar_flow_rate == ureg.Quantity(pytest.approx(6122349.16), "mol/day")


def test_component_molar_fraction_N2(gas_instance, stream):
    component_molar_fraction = gas_instance.component_molar_fraction("N2", stream)
    assert component_molar_fraction == ureg.Quantity(pytest.approx(0.0285991048), "frac")


def test_component_molar_fraction_C1(gas_instance, stream):
    component_molar_fraction = gas_instance.component_molar_fraction("C1", stream)
    assert component_molar_fraction == ureg.Quantity(pytest.approx(0.891799149), "frac")


def test_specific_gravity(gas_instance, stream):
    specific_gravity = gas_instance.specific_gravity(stream)
    assert specific_gravity == ureg.Quantity(pytest.approx(0.62300076), "frac")


def test_ratio_of_specific_heat(gas_instance, stream):
    ratio_of_specific_heat = gas_instance.ratio_of_specific_heat(stream)
    assert ratio_of_specific_heat == ureg.Quantity(pytest.approx(1.28972962), "frac")


def test_gas_heat_capacity(gas_instance, stream):
    heat_capacity = gas_instance.heat_capacity(stream)
    assert heat_capacity == ureg.Quantity(pytest.approx(132557.175), "btu/degF/day")


def test_uncorrected_pseudocritical_temperature(gas_instance, stream):
    pseudocritical_temp = gas_instance.uncorrected_pseudocritical_temperature_and_pressure(stream)["temperature"]
    assert pseudocritical_temp == ureg.Quantity(pytest.approx(361.164867), "rankine")


def test_uncorrected_pseudocritical_pressure(gas_instance, stream):
    pseudocritical_press = gas_instance.uncorrected_pseudocritical_temperature_and_pressure(stream)["pressure"]
    assert pseudocritical_press == ureg.Quantity(pytest.approx(669.895774), "psia")


def test_corrected_pseudocritical_temperature(gas_instance, stream):
    corr_pseudocritical_temp = gas_instance.corrected_pseudocritical_temperature(stream)
    assert corr_pseudocritical_temp == ureg.Quantity(pytest.approx(361.164867), "rankine")


def test_corrected_pseudocritical_pressure(gas_instance, stream):
    corr_pseudocritical_press = gas_instance.corrected_pseudocritical_pressure(stream)
    assert corr_pseudocritical_press == ureg.Quantity(pytest.approx(669.895774), "psia")


def test_reduced_temperature(gas_instance, stream):
    reduced_temperature = gas_instance.reduced_temperature(stream)
    assert reduced_temperature == ureg.Quantity(pytest.approx(1.82650656), "frac")


def test_reduced_pressure(gas_instance, stream):
    reduced_press = gas_instance.reduced_pressure(stream)
    assert reduced_press == ureg.Quantity(pytest.approx(2.32274939), "frac")


def test_Z_factor(gas_instance, stream):
    reduced_temp = gas_instance.reduced_temperature(stream)
    reduced_press = gas_instance.reduced_pressure(stream)
    z_factor = gas_instance.Z_factor(reduced_temp, reduced_press)
    assert z_factor == ureg.Quantity(pytest.approx(0.913575608), "frac")


def test_volume_factor(gas_instance, stream):
    vol_factor = gas_instance.volume_factor(stream)
    assert vol_factor == ureg.Quantity(pytest.approx(0.0109559824), "frac")


def test_gas_density(gas_instance, stream):
    density = gas_instance.density(stream)
    assert density == ureg.Quantity(pytest.approx(0.069296467), "tonne/m**3")


def test_gas_viscosity(gas_instance, stream):
    viscosity = gas_instance.viscosity(stream)
    assert viscosity == ureg.Quantity(pytest.approx(0.0172091105), "centipoise")


def test_molar_weight(gas_instance, stream):
    mol_weight = gas_instance.molar_weight(stream)
    assert mol_weight == ureg.Quantity(pytest.approx(17.97378), "g/mol")


def test_gas_volume_flow_rate(gas_instance, stream):
    vol_flow_rate = gas_instance.volume_flow_rate(stream)
    assert vol_flow_rate == ureg.Quantity(pytest.approx(1587.9851), "m**3/day")


def test_gas_mass_energy_density(gas_instance, stream):
    mass_energy_density = gas_instance.mass_energy_density(stream)
    assert mass_energy_density == ureg.Quantity(pytest.approx(46.9246768), "MJ/kg")


def test_volume_energy_density(gas_instance, stream):
    volume_energy_density = gas_instance.volume_energy_density(stream)
    assert volume_energy_density == ureg.Quantity(pytest.approx(959.532995), "btu/ft**3")


def test_energy_flow_rate(gas_instance, stream):
    energy_flow_rate = gas_instance.energy_flow_rate(stream)
    assert energy_flow_rate == ureg.Quantity(pytest.approx(4894.21783), "mmBtu/day")


@pytest.fixture
def water_instance(test_model):
    field = test_model.get_field("test")
    water = Water(field)
    water._after_init()
    return water


def test_water_density(water_instance):
    density = water_instance.density()
    assert density == ureg.Quantity(pytest.approx(1004.12839), "kg/m**3")


def test_water_volume_rate(water_instance):
    stream = Stream("water stream", temperature=200, pressure=1556.6)
    stream.set_flow_rate("H2O", "liquid", 1962.61672)
    volume_flow_rate = water_instance.volume_flow_rate(stream)
    assert volume_flow_rate == ureg.Quantity(pytest.approx(12293.734), "bbl_water/day")


def test_water_specific_heat(water_instance):
    temperature = ureg.Quantity(200, "degF")
    specific_heat = water_instance.specific_heat(temperature)
    assert specific_heat == ureg.Quantity(pytest.approx(0.450496339), "btu/lb/degF")


def test_water_heat_capacity(water_instance):
    stream = Stream("water stream", temperature=200, pressure=1556.6)
    stream.set_flow_rate("H2O", "liquid", 1962.61672)
    heat_capacity = water_instance.heat_capacity(stream)
    assert heat_capacity == ureg.Quantity(pytest.approx(1949220.72), "btu/degF/day")


def test_water_saturated_temperature(water_instance):
    Psat = ureg.Quantity(1122.00, "psia")
    Tsat = water_instance.saturated_temperature(Psat)
    assert Tsat.to("degC") == ureg.Quantity(pytest.approx(292.660571), "degC")
