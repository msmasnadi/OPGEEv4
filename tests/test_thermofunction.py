import pytest
from opgee.thermodynamics import Oil, Gas
from opgee.stream import Stream

num_digits = 3


@pytest.fixture
def oil_instance(test_model):
    field = test_model.get_field("test")
    oil = Oil(field)

    return oil


def test_gas_specific_gravity(oil_instance):
    gas_SG = oil_instance.gas_specific_gravity()
    assert round(gas_SG, num_digits) == pytest.approx(0.581)


def test_bubble_point_solution_GOR(oil_instance):
    gor_bubble = oil_instance.bubble_point_solution_GOR()
    assert round(gor_bubble, num_digits) == pytest.approx(2822.361)


def test_reservoir_solution_GOR(oil_instance):
    res_GOR = oil_instance.reservoir_solution_GOR()
    assert round(res_GOR, num_digits) == pytest.approx(286.983)


def test_bubble_point_pressure(oil_instance):
    p_bubblepoint = oil_instance.bubble_point_pressure()
    assert round(p_bubblepoint.m) == pytest.approx(9337)


def test_bubble_point_formation_volume_factor(oil_instance):
    bubble_oil_FVF = oil_instance.bubble_point_formation_volume_factor()
    assert round(bubble_oil_FVF, num_digits) == pytest.approx(1.194)


def test_solution_gas_oil_ratio(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
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
    assert round(iso_compress_x, num_digits) == pytest.approx(0.0)


def test_isothermal_compressibility(oil_instance):
    iso_compress = oil_instance.isothermal_compressibility()
    assert iso_compress == pytest.approx(3.0528295800365155e-6)


def test_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    fvf = oil_instance.formation_volume_factor(stream)
    assert round(fvf, num_digits) == pytest.approx(1.194)


def test_density(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    density = oil_instance.density(stream)
    assert round(density.m, num_digits) == pytest.approx(46.919)


def test_mass_energy_density(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    mass_energy_density = oil_instance.mass_energy_density()
    assert round(mass_energy_density.m, num_digits) == pytest.approx(18279.816)


def test_volume_energy_density(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    volume_energy_density = oil_instance.volume_energy_density(stream)
    assert round(volume_energy_density.m, num_digits) == pytest.approx(4.815)


def test_energy_flow_rate(oil_instance):
    stream = Stream("test_stream", temperature=200.0, pressure=1556.0)
    stream.set_flow_rate("C10", "liquid", 273.7766 / 2)
    stream.set_flow_rate("C9", "liquid", 273.7766 / 2)
    energy_flow_rate = oil_instance.energy_flow_rate(stream)
    assert round(energy_flow_rate.m, num_digits) == pytest.approx(11033.223)


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
    s.set_flow_rate("C1", "gas", 87.58050)
    s.set_flow_rate("C2", "gas", 9.75715)
    s.set_flow_rate("C3", "gas", 4.37353)
    s.set_flow_rate("C4", "gas", 2.52654)
    s.set_flow_rate("H2S", "gas", 0.02086)
    return s


def test_total_molar_flow_rate(gas_instance, stream):
    total_molar_flow_rate = gas_instance.total_molar_flow_rate(stream)
    assert total_molar_flow_rate.m == pytest.approx(6122349.11)


def test_component_molar_fraction(gas_instance, stream):
    component_molar_fraction = gas_instance.component_molar_fraction("N2", stream)
    assert component_molar_fraction == pytest.approx(0.0286)


def test_component_molar_fraction(gas_instance, stream):
    component_molar_fraction = gas_instance.component_molar_fraction("C1", stream)
    assert component_molar_fraction == pytest.approx(0.8917)


def test_specific_gravity(gas_instance, stream):
    specific_gravity = gas_instance.specific_gravity(stream)
    assert specific_gravity == pytest.approx(0.6277, abs=1e-4)


def test_ratio_of_specific_heat(gas_instance, stream):
    ratio_of_specific_heat = gas_instance.ratio_of_specific_heat(stream)
    assert round(ratio_of_specific_heat, num_digits) == pytest.approx(1.286)


def test_uncorrelated_pseudocritical_temperature(gas_instance, stream):
    pseudocritical_temp = gas_instance.uncorrelated_pseudocritical_temperature_and_pressure(stream)["temperature"]
    assert int(pseudocritical_temp.m) == 361


def test_uncorrelated_pseudocritical_pressure(gas_instance, stream):
    pseudocritical_press = gas_instance.uncorrelated_pseudocritical_temperature_and_pressure(stream)["pressure"]
    assert round(pseudocritical_press.m, ndigits=0) == pytest.approx(670)


def test_correlated_pseudocritical_temperature(gas_instance, stream):
    corr_pseudocritical_temp = gas_instance.correlated_pseudocritical_temperature(stream)
    assert round(corr_pseudocritical_temp.m, num_digits) == pytest.approx(361.312)


def test_correlated_pseudocritical_pressure(gas_instance, stream):
    corr_pseudocritical_press = gas_instance.correlated_pseudocritical_pressure(stream)
    assert round(corr_pseudocritical_press.m, num_digits) == pytest.approx(670.169)


def test_reduced_temperature(gas_instance, stream):
    reduced_temperature = gas_instance.reduced_temperature(stream)
    assert round(reduced_temperature.m, num_digits) == pytest.approx(1.826)


def test_reduced_pressure(gas_instance, stream):
    reduced_press = gas_instance.reduced_pressure(stream)
    assert round(reduced_press.m, num_digits) == pytest.approx(2.322)


def test_Z_factor(gas_instance, stream):
    z_factor = gas_instance.Z_factor(stream)
    assert round(z_factor, num_digits) == pytest.approx(0.913)


def test_volume_factor(gas_instance, stream):
    vol_factor = gas_instance.volume_factor(stream)
    assert round(vol_factor, num_digits) == pytest.approx(0.011)


def test_gas_density(gas_instance, stream):
    density = gas_instance.density(stream)
    assert round(density.m, num_digits) == pytest.approx(0.070)


def test_molar_weight(gas_instance, stream):
    mol_weight = gas_instance.molar_weight(stream)
    assert round(mol_weight.m, num_digits) == pytest.approx(17.976)


def test_volume_flow_rate(gas_instance, stream):
    vol_flow_rate = gas_instance.volume_flow_rate(stream)
    assert round(vol_flow_rate.m, num_digits) == pytest.approx(1575.94)


def test_mass_energy_density(gas_instance, stream):
    mass_energy_density = gas_instance.mass_energy_density(stream)
    assert round(mass_energy_density.m, num_digits) == pytest.approx(46.918)


def test_volume_energy_density(gas_instance, stream):
    volume_energy_density = gas_instance.volume_energy_density(stream)
    assert round(volume_energy_density.m, num_digits) == pytest.approx(959.501)

def test_energy_flow_rate(gas_instance, stream):
    energy_flow_rate = gas_instance.energy_flow_rate(stream)
    assert energy_flow_rate.m == pytest.approx(4894.052, abs=1e-3)

