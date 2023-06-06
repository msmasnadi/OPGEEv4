import pandas as pd
import pytest
from opgee.core import TemperaturePressure
from opgee.stream import Stream, PHASE_GAS, PHASE_LIQUID
from opgee import ureg


@pytest.fixture(scope="module")
def oil_instance(test_model):
    field = test_model.get_field("test")
    return field.oil


def test_gas_specific_gravity(oil_instance):
    gas_SG = oil_instance.gas_specific_gravity
    assert gas_SG == ureg.Quantity(pytest.approx(0.620513719), "frac")


def test_bubble_point_solution_GOR(oil_instance):
    GOR = oil_instance.gas_oil_ratio
    gor_bubble = oil_instance.bubble_point_solution_GOR(GOR)
    assert gor_bubble == ureg.Quantity(pytest.approx(2822.361), "scf/bbl_oil")


def test_oil_specific_gravity(oil_instance):
    oil_SG = oil_instance.specific_gravity(oil_instance.API)
    assert oil_SG == ureg.Quantity(pytest.approx(oil_instance.oil_specific_gravity.m), "frac")


def test_oil_API_from_SG(oil_instance):
    oil_SG = oil_instance.specific_gravity(oil_instance.API)
    oil_API = oil_instance.API_from_SG(oil_SG)
    assert oil_API == ureg.Quantity(pytest.approx(oil_instance.API.m), "degAPI")


def test_reservoir_solution_GOR(oil_instance):
    res_GOR = oil_instance.reservoir_solution_GOR()
    assert res_GOR == ureg.Quantity(pytest.approx(291.03397), "scf/bbl_oil")


test_tp = TemperaturePressure(ureg.Quantity(200.0, "degF"), ureg.Quantity(1556.0, "psia"))


def test_bubble_point_pressure(oil_instance):
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    p_bubblepoint = oil_instance.bubble_point_pressure(oil_SG, gas_SG, GOR)
    assert p_bubblepoint == ureg.Quantity(pytest.approx(9235.176121), "psia")


def test_solution_gas_oil_ratio(oil_instance):
    stream = Stream("test_stream", test_tp)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    solution_gor = oil_instance.solution_gas_oil_ratio(stream, oil_SG, gas_SG, GOR)
    assert solution_gor == ureg.Quantity(pytest.approx(290.890838), "scf/bbl_oil")


def test_saturated_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", test_tp)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    sat_fvf = oil_instance.saturated_formation_volume_factor(stream, oil_SG, gas_SG, GOR)
    assert sat_fvf == ureg.Quantity(pytest.approx(1.19867887), "frac")


def test_unsat_formation_volume_factor(oil_instance):
    stream = Stream("test_stream", test_tp)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    unsat_fvf = oil_instance.unsat_formation_volume_factor(stream, oil_SG, gas_SG, GOR)
    assert unsat_fvf == ureg.Quantity(pytest.approx(1.22717505), "frac")


def test_isothermal_compressibility_X(oil_instance):
    stream = Stream("test_stream", test_tp)
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
    stream = Stream("test_stream", test_tp)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    fvf = oil_instance.formation_volume_factor(stream, oil_SG, gas_SG, GOR)
    assert fvf == ureg.Quantity(pytest.approx(1.19867887), "frac")


def test_oil_density(oil_instance):
    stream = Stream("test_stream", test_tp)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    density = oil_instance.density(stream, oil_SG, gas_SG, GOR)
    assert density == ureg.Quantity(pytest.approx(47.0100087, rel=10e-5), "lb/ft**3")


def test_oil_mass_energy_density(oil_instance):
    mass_energy_density = oil_instance.oil_LHV_mass
    assert mass_energy_density == ureg.Quantity(pytest.approx(18279.816), "btu/lb")


def test_oil_volume_flow_rate(oil_instance):
    stream = Stream("test_stream", test_tp)
    stream.set_flow_rate("oil", PHASE_LIQUID, 276.534764)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    volume_flow_rate = oil_instance.volume_flow_rate(stream, oil_SG, gas_SG, GOR)
    assert volume_flow_rate == ureg.Quantity(pytest.approx(2309.80926, rel=10e-5), "bbl_oil/day")


def test_oil_volume_energy_density(oil_instance):
    stream = Stream("test_stream", test_tp)
    oil_SG = oil_instance.oil_specific_gravity
    gas_SG = oil_instance.gas_specific_gravity
    GOR = oil_instance.gas_oil_ratio
    volume_energy_density = oil_instance.volume_energy_density(stream, oil_SG, gas_SG, GOR)
    assert volume_energy_density == ureg.Quantity(pytest.approx(4.82480434, rel=10e-5), "mmBtu/bbl_oil")


def test_oil_energy_flow_rate(oil_instance):
    stream = Stream("test_stream", test_tp)
    stream.set_API(ureg.Quantity(32.8, "degAPI"))
    stream.set_flow_rate("oil", PHASE_LIQUID, 273.831958)
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
    return field.gas


@pytest.fixture
def stream():
    s = Stream("test_stream", test_tp)
    s.set_flow_rate("N2", PHASE_GAS, 4.90497)
    s.set_flow_rate("CO2", PHASE_GAS, 0.889247)
    s.set_flow_rate("C1", PHASE_GAS, 87.59032)
    s.set_flow_rate("C2", PHASE_GAS, 9.75715)
    s.set_flow_rate("C3", PHASE_GAS, 4.37353)
    s.set_flow_rate("C4", PHASE_GAS, 2.52654)
    s.set_API(32.8)
    return s


def test_total_molar_flow_rate(gas_instance, stream):
    total_molar_flow_rate = gas_instance.total_molar_flow_rate(stream)
    assert total_molar_flow_rate == ureg.Quantity(pytest.approx(6122349.16), "mol/day")


def test_molar_flow_rate(gas_instance, stream):
    molar_flow_rate = gas_instance.molar_flow_rate(stream, "C1")
    assert molar_flow_rate == ureg.Quantity(pytest.approx(5459905.78), "mol/day")


def test_component_molar_fraction_N2(gas_instance, stream):
    component_molar_fraction = gas_instance.component_molar_fraction("N2", stream)
    assert component_molar_fraction == ureg.Quantity(pytest.approx(0.0285991048), "frac")


def test_component_molar_fraction_C1(gas_instance, stream):
    component_molar_fraction = gas_instance.component_molar_fraction("C1", stream)
    assert component_molar_fraction == ureg.Quantity(pytest.approx(0.891799149), "frac")


def test_component_mass_fraction(gas_instance, stream):
    molar_fracs = pd.Series([0.004, 0.9666, 0.02, 0.01],
                            index=["N2", "C1", "C2", "C3"], dtype="pint[mol/mol]")
    mass_fracs = gas_instance.component_mass_fractions(molar_fracs)
    assert mass_fracs["C1"] == ureg.Quantity(pytest.approx(0.9307131413113588))


def test_specific_gravity(gas_instance, stream):
    specific_gravity = gas_instance.specific_gravity(stream)
    assert specific_gravity == ureg.Quantity(pytest.approx(0.620514541), "frac")


def test_ratio_of_specific_heat(gas_instance, stream):
    ratio_of_specific_heat = gas_instance.ratio_of_specific_heat(stream)
    assert ratio_of_specific_heat == ureg.Quantity(pytest.approx(1.28972962, rel=10e-4), "frac")


def test_gas_heat_capacity(gas_instance, stream):
    heat_capacity = gas_instance.heat_capacity(stream)
    assert heat_capacity == ureg.Quantity(pytest.approx(132557.175, rel=10e-3), "btu/degF/day")


def test_uncorrected_pseudocritical_temperature(gas_instance, stream):
    pseudocritical_temp = gas_instance.uncorrected_pseudocritical_temperature_and_pressure(stream)["temperature"]
    assert pseudocritical_temp == ureg.Quantity(pytest.approx(361.164867, rel=10e-5), "rankine")


def test_uncorrected_pseudocritical_pressure(gas_instance, stream):
    pseudocritical_press = gas_instance.uncorrected_pseudocritical_temperature_and_pressure(stream)["pressure"]
    assert pseudocritical_press == ureg.Quantity(pytest.approx(669.895774, rel=10e-5), "psia")


def test_corrected_pseudocritical_temperature(gas_instance, stream):
    corr_pseudocritical_temp = gas_instance.corrected_pseudocritical_temperature(stream)
    assert corr_pseudocritical_temp == ureg.Quantity(pytest.approx(361.164867, rel=10e-5), "rankine")


def test_corrected_pseudocritical_pressure(gas_instance, stream):
    corr_pseudocritical_press = gas_instance.corrected_pseudocritical_pressure(stream)
    assert corr_pseudocritical_press == ureg.Quantity(pytest.approx(669.895774, rel=10e-5), "psia")


def test_reduced_temperature(gas_instance, stream):
    reduced_temperature = gas_instance.reduced_temperature(stream)
    assert reduced_temperature == ureg.Quantity(pytest.approx(1.82650656, rel=10e-5), "frac")


def test_reduced_pressure(gas_instance, stream):
    reduced_press = gas_instance.reduced_pressure(stream)
    assert reduced_press == ureg.Quantity(pytest.approx(2.32274939, rel=10e-5), "frac")


def test_Z_factor(gas_instance, stream):
    reduced_temp = gas_instance.reduced_temperature(stream)
    reduced_press = gas_instance.reduced_pressure(stream)
    z_factor = gas_instance.Z_factor(reduced_temp, reduced_press)
    assert z_factor == ureg.Quantity(pytest.approx(0.922374916, rel=10e-5), "frac")


def test_volume_factor(gas_instance, stream):
    vol_factor = gas_instance.volume_factor(stream)
    assert vol_factor == ureg.Quantity(pytest.approx(0.0109559824, abs=0.0005), "frac")


def test_gas_density(gas_instance, stream):
    density = gas_instance.density(stream)
    assert density == ureg.Quantity(pytest.approx(0.0686303423, rel=10e-4), "tonne/m**3")


def test_gas_viscosity(gas_instance, stream):
    viscosity = gas_instance.viscosity(stream)
    assert viscosity == ureg.Quantity(pytest.approx(0.0171786183, rel=10e-5), "centipoise")


def test_molar_weight(gas_instance, stream):
    mol_weight = gas_instance.molar_weight(stream)
    assert mol_weight == ureg.Quantity(pytest.approx(17.97378), "g/mol")


def test_molar_weight_from_molar_fracs(gas_instance, stream):
    molar_fracs = pd.Series([0.004, 0.9666, 0.02, 0.01],
                            index=["N2", "C1", "C2", "C3"], dtype="pint[mol/mol]")
    mol_weight = gas_instance.molar_weight_from_molar_fracs(molar_fracs)
    assert mol_weight == ureg.Quantity(pytest.approx(16.6610324), "g/mol")


def test_gas_volume_flow_rate(gas_instance, stream):
    vol_flow_rate = gas_instance.volume_flow_rate(stream)
    assert vol_flow_rate == ureg.Quantity(pytest.approx(1603.39805, rel=10e-4), "m**3/day")


def test_gas_volume_flow_rate_STP(gas_instance):
    s = Stream("test_stream", test_tp)
    s.set_flow_rate("N2", PHASE_GAS, 1.0638)
    s.set_flow_rate("C1", PHASE_GAS, 147.1241)
    s.set_flow_rate("C2", PHASE_GAS, 5.7095)
    s.set_flow_rate("C3", PHASE_GAS, 4.1863)
    vol_flow_rate_STP = gas_instance.volume_flow_rate_STP(s)
    assert vol_flow_rate_STP == ureg.Quantity(pytest.approx(7.94253339), "mmscf/day")


def test_gas_volume_flow_rate_STP(gas_instance):
    s = Stream("test_stream", test_tp)
    s.set_flow_rate("N2", PHASE_GAS, 1.0638)
    s.set_flow_rate("C1", PHASE_GAS, 147.1241)
    s.set_flow_rate("C2", PHASE_GAS, 5.7095)
    s.set_flow_rate("C3", PHASE_GAS, 4.1863)
    vol_flow_rates_STP = gas_instance.volume_flow_rates_STP(s)
    assert vol_flow_rates_STP["C1"].to("mmscf/day") == ureg.Quantity(pytest.approx(7.66776813, rel=10e-3), "mmscf/day")


def test_gas_mass_energy_density(gas_instance, stream):
    mass_energy_density = gas_instance.mass_energy_density(stream)
    assert mass_energy_density == ureg.Quantity(pytest.approx(46.9246768), "MJ/kg")


def test_gas_mass_energy_density_from_molar_fracs(gas_instance, stream):
    molar_fracs = pd.Series([0.004, 0.9666, 0.02, 0.01],
                            index=["N2", "C1", "C2", "C3"], dtype="pint[mol/mol]")
    mass_energy_density = gas_instance.mass_energy_density_from_molar_fracs(molar_fracs)
    assert mass_energy_density == ureg.Quantity(pytest.approx(49.7703477), "MJ/kg")


def test_combustion_enthalpy(gas_instance, stream):
    molar_fracs = pd.Series([9.2878, 2.4624, 0.0035, 0.2399],
                            index=["N2", "O2", "CO2", "H2O"], dtype="pint[mol/mol]")
    temperature = ureg.Quantity(80.33, "degF")
    enthalpy = gas_instance.combustion_enthalpy(molar_fracs, temperature, PHASE_GAS)
    assert enthalpy["H2O"] == ureg.Quantity(pytest.approx(120.4288942, rel=10e-3), "joule/mole")


def test_volume_energy_density(gas_instance, stream):
    volume_energy_density = gas_instance.volume_energy_density(stream)
    assert volume_energy_density == ureg.Quantity(pytest.approx(957.960214, rel=10e-3), "btu/ft**3")


def test_energy_flow_rate(gas_instance, stream):
    energy_flow_rate = gas_instance.energy_flow_rate(stream)
    assert energy_flow_rate == ureg.Quantity(pytest.approx(4894.21783), "mmBtu/day")


@pytest.fixture
def water_instance(test_model):
    field = test_model.get_field("test")
    return field.water


def test_water_density(water_instance):
    density = water_instance.density()
    assert density == ureg.Quantity(pytest.approx(1002.4871, rel=1e-5), "kg/m**3")


def test_water_volume_rate(water_instance):
    stream = Stream("water stream", test_tp)
    stream.set_flow_rate("H2O", PHASE_LIQUID, 1962.61672)
    volume_flow_rate = water_instance.volume_flow_rate(stream)
    assert volume_flow_rate == ureg.Quantity(pytest.approx(12313.8616, rel=1e-5), "bbl_water/day")


def test_water_specific_heat(water_instance):
    temperature = ureg.Quantity(200, "degF")
    specific_heat = water_instance.specific_heat(temperature)
    assert specific_heat == ureg.Quantity(pytest.approx(0.450496339, rel=10e-4), "btu/lb/degF")


def test_water_heat_capacity(water_instance):
    stream = Stream("water stream", test_tp)
    stream.set_flow_rate("H2O", PHASE_LIQUID, 1962.61672)
    heat_capacity = water_instance.heat_capacity(stream)
    assert heat_capacity == ureg.Quantity(pytest.approx(1949220.72, rel=10e-4), "btu/degF/day")


def test_water_saturated_temperature(water_instance):
    Psat = ureg.Quantity(1122.00, "psia")
    Tsat = water_instance.saturated_temperature(Psat)
    assert Tsat.to("degC") == ureg.Quantity(pytest.approx(292.660571, abs=0.025), "degC")


def test_water_enthalpy_PT(water_instance):
    press = ureg.Quantity(13.7895, "bar")
    temp = ureg.Quantity(60.0, "degC")
    mass_rate = ureg.Quantity(3.94E7, "kg/day")
    enthalpy = water_instance.enthalpy_PT(press, temp, mass_rate)
    assert enthalpy == ureg.Quantity(pytest.approx(9940445.92), "MJ/day")


def test_steam_enthalpy(water_instance):
    press = ureg.Quantity(77.359177, "bar")
    steam_quality = ureg.Quantity(0.7, "frac")
    mass_rate = ureg.Quantity(5.52E7, "kg/day")
    enthalpy = water_instance.steam_enthalpy(press, steam_quality, mass_rate)
    assert enthalpy == ureg.Quantity(pytest.approx(1.28341315e+08), "MJ/day")


def test_check_balance(test_model):
    from opgee.error import BalanceError

    field = test_model.get_field("test")
    proc = field.find_process('SteamGeneration')

    input = ureg.Quantity(100.0, "tonne/day")
    output1 = ureg.Quantity(100.0001, "tonne/day")
    output2 = ureg.Quantity(110, "tonne/day")

    proc.check_balance(input, output1, "test1")

    with pytest.raises(BalanceError, match="test2 is not balanced in SteamGeneration"):
        proc.check_balance(input, output2, "test2")
