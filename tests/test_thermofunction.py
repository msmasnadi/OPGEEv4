import pytest
from opgee.thermodynamics import Oil, Gas
from opgee.stream import Stream
from opgee import ureg


@pytest.fixture(scope="module")
def oil_instance(test_model):
    field = test_model.get_field("test")
    oil = Oil(field)

    return oil


def test_gas_specific_gravity(oil_instance):
    gas_SG = oil_instance.gas_specific_gravity()
    assert gas_SG == ureg.Quantity(pytest.approx(0.627654556), "frac")


def test_bubble_point_solution_GOR(oil_instance):
    gor_bubble = oil_instance.bubble_point_solution_GOR()
    assert gor_bubble == ureg.Quantity(pytest.approx(2822.361), "scf/bbl_oil")


def test_reservoir_solution_GOR(oil_instance):
    res_GOR = oil_instance.reservoir_solution_GOR()
    assert res_GOR == ureg.Quantity(pytest.approx(291.910567), "scf/bbl_oil")


def test_bubble_point_pressure(oil_instance):
    p_bubblepoint = oil_instance.bubble_point_pressure()
    assert p_bubblepoint == ureg.Quantity(pytest.approx(9213.43432), "psia")


def test_bubble_point_formation_volume_factor(oil_instance):
    bubble_oil_FVF = oil_instance.bubble_point_formation_volume_factor()
    assert bubble_oil_FVF == ureg.Quantity(pytest.approx(1.19963034), "frac")


def test_solution_gas_oil_ratio(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    solution_gor = oil_instance.solution_gas_oil_ratio(stream)
    assert solution_gor == ureg.Quantity(pytest.approx(291.767004), "scf/bbl_oil")


def test_saturated_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    sat_fvf = oil_instance.saturated_formation_volume_factor(stream)
    assert sat_fvf == ureg.Quantity(pytest.approx(1.1995558), "frac")


def test_unsat_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    unsat_fvf = oil_instance.unsat_formation_volume_factor(stream)
    assert unsat_fvf == ureg.Quantity(pytest.approx(1.228004), "frac")


def test_isothermal_compressibility_X(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    iso_compress_x = oil_instance.isothermal_compressibility_X(stream)
    assert iso_compress_x == ureg.Quantity(0.0, "pa**-1")


def test_isothermal_compressibility(oil_instance):
    iso_compress = oil_instance.isothermal_compressibility()
    assert iso_compress == ureg.Quantity(pytest.approx(3.0528295800365155e-6), "pa**-1")


def test_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    fvf = oil_instance.formation_volume_factor(stream)
    assert fvf == ureg.Quantity(pytest.approx(1.1995558), "frac")


def test_density(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    density = oil_instance.density(stream)
    assert density == ureg.Quantity(pytest.approx(46.8968187), "lb/ft**3")


def test_mass_energy_density(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    mass_energy_density = oil_instance.mass_energy_density()
    assert mass_energy_density.m == ureg.Quantity(pytest.approx(18279.816), "btu/lb")


def test_volume_energy_density(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    volume_energy_density = oil_instance.volume_energy_density(stream)
    assert volume_energy_density == ureg.Quantity(pytest.approx(4.815), "btu/lb")


def test_energy_flow_rate(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    stream.set_flow_rate("C10", "liquid", 273.831958 / 2)
    stream.set_flow_rate("C9", "liquid", 273.831958 / 2)
    energy_flow_rate = oil_instance.energy_flow_rate(stream)
    assert energy_flow_rate == ureg.Quantity(pytest.approx(11032.33778), "mmbtu/day")


@pytest.fixture
def gas_instance(test_model):
    field = test_model.get_field("test")
    gas = Gas(field)
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
    assert specific_gravity == ureg.Quantity(pytest.approx(0.627655387), "frac")


def test_ratio_of_specific_heat(gas_instance, stream):
    ratio_of_specific_heat = gas_instance.ratio_of_specific_heat(stream)
    assert ratio_of_specific_heat == ureg.Quantity(pytest.approx(1.28553925), "frac")


def test_uncorrelated_pseudocritical_temperature(gas_instance, stream):
    pseudocritical_temp = gas_instance.uncorrelated_pseudocritical_temperature_and_pressure(stream)["temperature"]
    assert pseudocritical_temp == ureg.Quantity(pytest.approx(361.164867), "rankine")


def test_uncorrelated_pseudocritical_pressure(gas_instance, stream):
    pseudocritical_press = gas_instance.uncorrelated_pseudocritical_temperature_and_pressure(stream)["pressure"]
    assert pseudocritical_press == ureg.Quantity(pytest.approx(669.895774), "psia")


def test_correlated_pseudocritical_temperature(gas_instance, stream):
    corr_pseudocritical_temp = gas_instance.correlated_pseudocritical_temperature(stream)
    assert corr_pseudocritical_temp == ureg.Quantity(pytest.approx(361.164867), "rankine")


def test_correlated_pseudocritical_pressure(gas_instance, stream):
    corr_pseudocritical_press = gas_instance.correlated_pseudocritical_pressure(stream)
    assert corr_pseudocritical_press == ureg.Quantity(pytest.approx(669.895774), "psia")


def test_reduced_temperature(gas_instance, stream):
    reduced_temperature = gas_instance.reduced_temperature(stream)
    assert reduced_temperature == ureg.Quantity(pytest.approx(1.82650656), "frac")


def test_reduced_pressure(gas_instance, stream):
    reduced_press = gas_instance.reduced_pressure(stream)
    assert reduced_press == ureg.Quantity(pytest.approx(2.32274939), "frac")


def test_Z_factor(gas_instance, stream):
    z_factor = gas_instance.Z_factor(stream)
    assert z_factor == ureg.Quantity(pytest.approx(0.913575608), "frac")


def test_volume_factor(gas_instance, stream):
    vol_factor = gas_instance.volume_factor(stream)
    assert vol_factor == ureg.Quantity(pytest.approx(0.0109559824), "frac")


def test_gas_density(gas_instance, stream):
    density = gas_instance.density(stream)
    assert density == ureg.Quantity(pytest.approx(0.0698142018), "tonne/m**3")


def test_molar_weight(gas_instance, stream):
    mol_weight = gas_instance.molar_weight(stream)
    assert mol_weight == ureg.Quantity(pytest.approx(17.97378), "g/mol")


def test_volume_flow_rate(gas_instance, stream):
    vol_flow_rate = gas_instance.volume_flow_rate(stream)
    assert vol_flow_rate == ureg.Quantity(pytest.approx(1576.20877), "m**3/day")


def test_mass_energy_density(gas_instance, stream):
    mass_energy_density = gas_instance.mass_energy_density(stream)
    assert mass_energy_density == ureg.Quantity(pytest.approx(46.9246768), "MJ/kg")


def test_volume_energy_density(gas_instance, stream):
    volume_energy_density = gas_instance.volume_energy_density(stream)
    assert volume_energy_density == ureg.Quantity(pytest.approx(959.532995), "btu/ft**3")

def test_energy_flow_rate(gas_instance, stream):
    energy_flow_rate = gas_instance.energy_flow_rate(stream)
    assert energy_flow_rate == ureg.Quantity(pytest.approx(4894.21783), "mmBtu/day")

