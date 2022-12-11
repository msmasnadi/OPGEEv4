import pytest
from opgee import ureg
from opgee.energy import EN_NATURAL_GAS, EN_CRUDE_OIL
from opgee.emissions import EM_FLARING
from opgee.error import OpgeeException, ZeroEnergyFlowError
from opgee.process import Process, _get_subclass, Reservoir


class NotProcess(): pass


def test_subclass_lookup_good(test_model):
    assert _get_subclass(Process, 'ProcA')


def test_subclass_lookup_bad_subclass(test_model):
    with pytest.raises(OpgeeException, match=r'Class .* is not a known subclass of .*'):
        _get_subclass(Process, 'NonExistentProcess')


def test_subclass_lookup_bad_parent(test_model):
    with pytest.raises(OpgeeException, match=r'_get_subclass: cls .* must be one of .*'):
        _get_subclass(NotProcess, 'NonExistentProcess')


def test_set_emission_rates(test_model_with_change):
    analysis = test_model_with_change.get_analysis('test')
    field = analysis.get_field('test')
    procA = field.find_process('ProcA')

    rate_co2 = ureg.Quantity(100.0, 'tonne/day')
    rate_ch4 = ureg.Quantity(30.0, 'tonne/day')
    rate_n2o = ureg.Quantity(6.0, 'tonne/day')

    procA.add_emission_rates(EM_FLARING, CO2=rate_co2, CH4=rate_ch4, N2O=rate_n2o)
    df = procA.get_emission_rates(analysis)
    rates = df[EM_FLARING]

    assert (rates.N2O == rate_n2o and rates.CH4 == rate_ch4 and rates.CO2 == rate_co2)


def test_add_energy_rates(test_model_with_change):
    analysis = test_model_with_change.get_analysis('test')
    field = analysis.get_field('test')
    procA = field.find_process('ProcA')

    unit = ureg.Unit('mmbtu/day')
    ng_rate = ureg.Quantity(123.45, unit)
    oil_rate = ureg.Quantity(4321.0, unit)

    procA.add_energy_rates({EN_NATURAL_GAS: ng_rate, EN_CRUDE_OIL: oil_rate})

    rates = procA.get_energy_rates()

    assert (rates[EN_NATURAL_GAS] == ng_rate and rates[EN_CRUDE_OIL] == oil_rate)


@pytest.fixture(scope='module')
def process(test_model):
    analysis = test_model.get_analysis('test')
    field = analysis.get_field('test')
    proc = field.find_process('ProcA')
    return proc


def test_get_reservoir(process):
    assert isinstance(process.get_reservoir(), Reservoir)


@pytest.fixture(scope='module')
def procB(test_model):
    analysis = test_model.get_analysis('test')
    field = analysis.get_field('test')
    proc = field.find_process('ProcB')
    return proc


def test_find_input_streams_dict(procB):
    obj = procB.find_input_streams("crude oil")
    assert isinstance(obj, dict) and len(obj) == 1


def test_find_input_streams_list(procB):
    obj = procB.find_input_streams("crude oil", as_list=True)
    assert isinstance(obj, list) and len(obj) == 1


def test_find_input_stream(procB):
    procB.find_input_stream("crude oil")


def test_find_output_stream(process):
    process.find_output_stream("crude oil")


def test_find_input_stream_error(procB):
    stream_type = 'unknown_stream_type'
    with pytest.raises(OpgeeException, match=f".* no input streams contain '{stream_type}'"):
        procB.find_input_stream(stream_type)


def test_venting_fugitive_rate(test_model):
    analysis = test_model.get_analysis('test')
    field = analysis.get_field('test')
    procA = field.find_process('ProcA')
    rate = procA.venting_fugitive_rate()

    # mean of 1000 random draws from uniform(0.001, .003) should be ~0.002
    assert rate == pytest.approx(0.002, abs=0.0005)


def test_set_intermediate_value(procB):
    value = 123.456
    unit = 'degF'
    q = ureg.Quantity(value, unit)

    iv = procB.iv
    iv.store('temp', q)
    row = iv.get('temp')

    assert row['value'] == q.m and ureg.Unit(row['unit']) == q.u


def test_bad_intermediate_value(procB):
    iv = procB.iv
    with pytest.raises(OpgeeException, match=f"An intermediate value for '.*' was not found"):
        row = iv.get('non-existent')


foo = 1.0
bar = dict(x=1, y=2)
baz = "a string"


@pytest.mark.parametrize(
    "name, value", [('foo', foo), ('bar', bar), ('baz', baz)])
def test_process_data(procB, name, value):
    field = procB.field
    field.save_process_data(foo=foo, bar=bar, baz=baz)

    assert field.get_process_data(name) == value


def test_bad_process_data(procB):
    with pytest.raises(OpgeeException, match='Process data dictionary does not include .*'):
        procB.field.get_process_data("nonexistent-data-key", raiseError=True)


def approx_equal(a, b, abs=10E-6):
    "Check that two Quantities are approximately equal"
    return a.m == pytest.approx(b.m, abs=abs)


# Test gas processing units
def test_VRUCompressor(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_VRUCompressor')
    field.run(analysis)
    proc = field.find_process('VRUCompressor')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(0.347490006, "mmbtu/day")
    assert approx_equal(total, expected)


def test_VFPartition(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_VFPartition')
    field.run(analysis)
    proc = field.find_process('VFPartition')
    # ensure total energy flow rates
    total = proc.find_output_stream("methane slip").gas_flow_rates().sum()
    expected = ureg.Quantity(76.74077437660227, "tonne/day")
    assert approx_equal(total, expected)


def test_Flaring(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_Flaring')
    field.run(analysis)
    proc = field.find_process('Flaring')
    # ensure total energy flow rates
    total = proc.emissions.rates(analysis.gwp).loc["GHG"].sum()
    expected = ureg.Quantity(5298.998755911673, "tonne/day")
    assert approx_equal(total, expected)


def test_Venting(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_Venting')
    field.run(analysis)
    proc = field.find_process('Venting')
    # ensure total energy flow rates
    total = proc.emissions.rates(analysis.gwp).loc["GHG"].sum()
    expected = ureg.Quantity(1149.7618654739997, "tonne/day")
    assert approx_equal(total, expected)


def test_AcidGasRemoval_Aspen(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_AcidGasRemoval_Aspen')
    field.run(analysis)
    proc = field.find_process('AcidGasRemoval')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(267.794943, "mmbtu/day")
    assert approx_equal(total, expected)


def test_AcidGasRemoval_testbook(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_AcidGasRemoval_testbook')
    field.run(analysis)
    proc = field.find_process('AcidGasRemoval')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(781308.7244344904, "mmbtu/day")
    assert approx_equal(total, expected)


def test_GasDehydration(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_GasDehydration')
    field.run(analysis)
    proc = field.find_process('GasDehydration')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(679.408523, "mmbtu/day")
    assert approx_equal(total, expected)


def test_Demethanizer(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_Demethanizer')
    field.run(analysis)
    proc = field.find_process('Demethanizer')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(37.8165183, "mmbtu/day")
    assert approx_equal(total, expected)


def test_PreMembraneChiller(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_PreMembraneChiller')
    field.run(analysis)
    proc = field.find_process('PreMembraneChiller')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(907.0197708571166, "mmbtu/day")
    assert approx_equal(total, expected)


def test_PreMembraneCompressor(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_PreMembraneCompressor')
    field.run(analysis)
    proc = field.find_process('PreMembraneCompressor')
    # ensure total energy flow rates
    assert proc.energy.data.sum() == ureg.Quantity(0.0, "mmbtu/day")


def test_CO2Membrane(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_CO2Membrane')
    field.run(analysis)
    proc = field.find_process('CO2Membrane')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(4035.23283, "mmbtu/day")
    assert approx_equal(total, expected)


def test_CO2ReinjectionCompressor(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_CO2ReinjectionCompressor')
    field.run(analysis)
    proc = field.find_process('CO2ReinjectionCompressor')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(5274.50039, "mmbtu/day")
    assert approx_equal(total, expected)


def test_CO2InjectionWell(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_CO2InjectionWell')
    field.run(analysis)
    proc = field.find_process('CO2InjectionWell')
    # ensure total energy flow rates
    total = proc.emissions.rates(analysis.gwp).loc["GHG"].sum()
    expected = ureg.Quantity(0.259990500904288, "tonne/day")
    assert approx_equal(total, expected)


def test_RyanHolmes(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_RyanHolmes')
    field.run(analysis)
    proc = field.find_process('RyanHolmes')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(414.763217, "mmbtu/day")
    assert approx_equal(total, expected)


def test_SourGasCompressor(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_SourGasCompressor')
    field.run(analysis)
    proc = field.find_process('SourGasCompressor')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(244.014547, "mmbtu/day")
    assert approx_equal(total, expected)


def test_SourGasInjection(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_SourGasInjection')
    field.run(analysis)
    proc = field.find_process('SourGasInjection')
    # ensure total energy flow rates
    total = proc.emissions.rates(analysis.gwp).loc["GHG"].sum()
    expected = ureg.Quantity(2.8431898600000003, "tonne/day")
    assert approx_equal(total, expected)


def test_GasReinjectionCompressor(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_GasReinjectionCompressor')
    field.run(analysis)
    proc = field.find_process('GasReinjectionCompressor')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(64113.74141179, "mmbtu/day")
    assert approx_equal(total, expected)


def test_N2Flooding(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_N2Flooding')
    field.run(analysis)
    proc = field.find_process('GasPartition')
    # ensure total energy flow rates
    total = proc.find_output_stream("gas for gas reinjection compressor").gas_flow_rates().sum()
    expected = ureg.Quantity(25127.68891663532, "tonne/day")
    assert approx_equal(total, expected)

    total = proc.find_output_stream("gas").gas_flow_rates().sum()
    expected = ureg.Quantity(758.78647, "tonne/day")
    assert approx_equal(total, expected)


def test_CO2Flooding_CO2_reinjection(test_model_with_change):
    analysis = test_model_with_change.get_analysis('test_gas_processes')
    field = analysis.get_field('test_CO2Flooding')
    field.save_process_data(CO2_reinjection_mass_rate=ureg.Quantity(8364.59303, "tonne/day"))
    field.run(analysis)
    proc = field.find_process('GasPartition')
    # ensure total energy flow rates
    total = proc.find_output_stream("gas for gas reinjection compressor").gas_flow_rates().sum()
    expected = ureg.Quantity(1399.5948519637434, "tonne/day")
    assert approx_equal(total, expected)

    total = proc.find_output_stream("gas").gas_flow_rates().sum()
    expected = ureg.Quantity(24885.555110000005, "tonne/day")
    assert approx_equal(total, expected)


def test_CO2Flooding_non_zero(test_model_with_change):
    analysis = test_model_with_change.get_analysis('test_gas_processes')
    field = analysis.get_field('test_CO2Flooding')
    field.save_process_data(CO2_reinjection_mass_rate=ureg.Quantity(100000, "tonne/day"))
    field.run(analysis)
    proc = field.find_process('GasPartition')
    # ensure total energy flow rates
    total = proc.find_output_stream("gas for gas reinjection compressor").gas_flow_rates().sum()
    expected = 0
    assert total == expected

    total = proc.find_output_stream("gas").gas_flow_rates().sum()
    expected = ureg.Quantity(24885.555110000005, "tonne/day")
    assert approx_equal(total, expected)


def test_NGFlooding_onsite(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_NGFlooding_onsite_gas')
    field.run(analysis)
    proc = field.find_process('GasPartition')
    # ensure total energy flow rates
    total = proc.find_output_stream("gas for gas reinjection compressor").gas_flow_rates().sum()
    expected = ureg.Quantity(3824.449990753103, "tonne/day")
    assert approx_equal(total, expected)

    total = proc.find_output_stream("gas").gas_flow_rates().sum()
    expected = ureg.Quantity(22187.2424492469, "tonne/day")
    assert approx_equal(total, expected)


def test_CO2Flooding_sour_gas_reinjection(test_model_with_change):
    analysis = test_model_with_change.get_analysis('test_gas_processes')
    field = analysis.get_field('test_CO2Flooding')
    field.save_process_data(sour_gas_reinjection_mass_rate=ureg.Quantity(8387.50113, "tonne/day"))
    field.run(analysis)
    proc = field.find_process('GasPartition')

    # ensure total energy flow rates
    s = proc.find_output_stream("gas for gas reinjection compressor")
    total = s.gas_flow_rates().sum()
    expected = ureg.Quantity(1375.9995089637432, "tonne/day")
    assert approx_equal(total, expected)

    total = proc.find_output_stream("gas").gas_flow_rates().sum()
    expected = ureg.Quantity(24885.555110000005, "tonne/day")
    assert approx_equal(total, expected)


def test_NGFlooding_offset(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_NGFlooding_offset_gas')
    field.run(analysis)
    proc = field.find_process('GasPartition')
    # ensure total energy flow rates
    total = proc.find_output_stream("gas for gas reinjection compressor").gas_flow_rates().sum()
    expected = ureg.Quantity(382444.9990753103, "tonne/day")
    assert approx_equal(total, expected)

    total = proc.find_output_stream("gas").gas_flow_rates().sum()
    expected = 0.0
    assert total == expected


def test_GasLifting_low_GLIR(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_GasLifting_low_GLIR')
    field.run(analysis)
    proc = field.find_process('GasPartition')
    # ensure total energy flow rates
    total = proc.find_output_stream("lifting gas").gas_flow_rates().sum()
    expected = ureg.Quantity(176.35032820055403, "tonne/day")
    assert approx_equal(total, expected)

    total = proc.find_output_stream("gas").gas_flow_rates().sum()
    expected = ureg.Quantity(1486.1372117994458, "tonne/day")
    assert approx_equal(total, expected)


def test_GasLifting_high_GLIR(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_GasLifting_high_GLIR')
    field.run(analysis)
    proc = field.find_process('GasPartition')
    # ensure total energy flow rates
    total = proc.find_output_stream("lifting gas").gas_flow_rates().sum()
    expected = ureg.Quantity(1662.4875399999996, "tonne/day")
    assert approx_equal(total, expected)

    total = proc.find_output_stream("gas").gas_flow_rates().sum()
    expected = 0.0
    assert total == expected


# Test common processing units
def test_ReservoirWellInterface(test_model):
    analysis = test_model.get_analysis('test_common_processes')
    field = analysis.get_field('test_ReservoirWellInterface')
    field.run(analysis)
    proc = field.find_process('ReservoirWellInterface')
    # ensure output stream pressure
    pressure = proc.find_output_stream("crude oil").tp.P
    expected = ureg.Quantity(1324.1743628149043, "mmbtu/day")
    assert approx_equal(pressure, expected)


def test_ReservoirWellInterface_CO2_flood(test_model):
    analysis = test_model.get_analysis('test_common_processes')
    field = analysis.get_field('test_ReservoirWellInterface_CO2_flood')
    field.save_process_data(CO2_mass_rate=ureg.Quantity(827.74208, "tonne/day"))
    field.run(analysis)
    proc = field.find_process('ReservoirWellInterface')
    # ensure output stream pressure
    pressure = proc.find_output_stream("crude oil").tp.P
    expected = ureg.Quantity(1520.255707996104, "mmbtu/day")
    assert approx_equal(pressure, expected)


def test_DownholePump(test_model):
    analysis = test_model.get_analysis('test_common_processes')
    field = analysis.get_field('test_DownholePump')
    field.run(analysis)
    proc = field.find_process('DownholePump')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(157.26444308607068, "mmbtu/day")
    assert approx_equal(total, expected)


def test_Separation(test_model):
    analysis = test_model.get_analysis('test_gas_processes')
    field = analysis.get_field('test_Separation')
    field.run(analysis)
    proc = field.find_process('Separation')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(0.765118605167738, "mmbtu/day")
    assert approx_equal(total, expected)


def test_CrudeOilDewatering(test_model):
    analysis = test_model.get_analysis('test_common_processes')
    field_stab = analysis.get_field('test_CrudeOilDewatering')
    field_upgrading = analysis.get_field("test_CrudeOilDewatering_Upgrading")
    field_dilution = analysis.get_field("test_CrudeOilDewatering_Dilution")
    field_storage = analysis.get_field("test_CrudeOilDewatering_Storage")
    field_both = analysis.get_field("test_CrudeOilDewatering_DilutionUpgrading")

    field_stab.run(analysis)
    proc = field_stab.find_process('CrudeOilDewatering')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(6474.605161411582, "mmbtu/day")
    assert approx_equal(total, expected)

    field_upgrading.run(analysis)
    proc = field_upgrading.find_process('CrudeOilDewatering')
    output = proc.find_output_stream("oil for upgrading")
    # ensure total mass flow rates
    total = output.total_flow_rate()
    expected = ureg.Quantity(55847.93157, "tonne/day")
    assert approx_equal(total, expected)

    field_dilution.run(analysis)
    proc = field_dilution.find_process('CrudeOilDewatering')
    output = proc.find_output_stream("oil for dilution")
    # ensure total mass flow rates
    total = output.total_flow_rate()
    expected = ureg.Quantity(55847.93157, "tonne/day")
    assert approx_equal(total, expected)

    field_storage.run(analysis)
    proc = field_storage.find_process('CrudeOilDewatering')
    output = proc.find_output_stream("oil for storage")
    # ensure total mass flow rates
    total = output.total_flow_rate()
    expected = ureg.Quantity(55847.93157, "tonne/day")
    assert approx_equal(total, expected)

    field_both.run(analysis)
    proc = field_both.find_process('CrudeOilDewatering')
    output = proc.find_output_stream("oil for dilution")
    # ensure total mass flow rates
    total = output.total_flow_rate()
    expected = ureg.Quantity(55847.93157, "tonne/day")
    assert approx_equal(total, expected)


def test_CrudeOilStabilization(test_model):
    analysis = test_model.get_analysis('test_common_processes')
    field = analysis.get_field('test_CrudeOilStabilization')
    field.run(analysis)
    proc = field.find_process('CrudeOilStabilization')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(16387.96681238, "mmbtu/day")
    assert approx_equal(total, expected)


def test_HeavyOilUpgrading(test_model):
    analysis = test_model.get_analysis('test_oil_processes')
    field = analysis.get_field('test_HeavyOilUpgrading')
    field.run(analysis)
    proc = field.find_process('HeavyOilUpgrading')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(63524.64102838269, "mmbtu/day")
    assert approx_equal(total, expected)


def test_HeavyOilDilution(test_model):
    analysis = test_model.get_analysis('test_oil_processes')
    field = analysis.get_field('test_HeavyOilDilution')
    field.run(analysis)
    proc = field.find_process('HeavyOilDilution')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(2609.1316115952463, "mmbtu/day")
    assert approx_equal(total, expected)


def test_CrudeOilStorage(test_model):
    analysis = test_model.get_analysis('test_oil_processes')
    field = analysis.get_field('test_CrudeOilStorage')
    field.run(analysis)
    proc = field.find_process('CrudeOilStorage')
    # ensure total emission flow rates
    total = proc.emissions.data.loc["GHG"].sum()
    expected = ureg.Quantity(1885.055763739042, "tonne/day")
    assert approx_equal(total, expected)


def test_BitumenMining(test_model):
    analysis = test_model.get_analysis('test_oil_processes')
    field = analysis.get_field('test_BitumenMining')
    field.run(analysis)
    proc = field.find_process('BitumenMining')
    # ensure total energy flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(60717.00400130419, "mmbtu/day")
    assert approx_equal(total, expected)


def test_SteamGeneration_OTSG(test_model):
    analysis = test_model.get_analysis('test_water_processes')
    field = analysis.get_field('test_SteamGeneration_OTSG')

    try:
        field.run(analysis)
    except ZeroEnergyFlowError:
        # we expect zero energy flow at boundary on this test
        pass

    proc = field.find_process('SteamGeneration')
    # ensure total emission flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(67895.96099734664, "mmBtu/day")
    assert approx_equal(total, expected)


def test_SteamGeneration_Cogen(test_model):
    analysis = test_model.get_analysis('test_water_processes')
    field = analysis.get_field('test_SteamGeneration_Cogen')

    try:
        field.run(analysis)
    except ZeroEnergyFlowError:
        # we expect zero energy flow at boundary on this test
        pass

    proc = field.find_process('SteamGeneration')
    # ensure total emission flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(99558.64685355888, "mmBtu/day")
    assert approx_equal(total, expected)


def test_SteamGeneration_Solar(test_model):
    analysis = test_model.get_analysis('test_water_processes')
    field = analysis.get_field('test_SteamGeneration_Solar')

    try:
        field.run(analysis)
    except ZeroEnergyFlowError:
        # we expect zero energy flow at boundary on this test
        pass

    proc = field.find_process('SteamGeneration')
    # ensure total emission flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(1216.7129922580275, "mmBtu/day")
    assert approx_equal(total, expected)


def test_WaterTreatment(test_model):
    analysis = test_model.get_analysis('test_water_processes')
    field = analysis.get_field('test_WaterTreatment')

    try:
        field.run(analysis)
    except ZeroEnergyFlowError:
        # we expect zero energy flow at boundary on this test
        pass

    proc = field.find_process('WaterTreatment')
    # ensure total emission flow rates
    total = proc.energy.data.sum()
    expected = ureg.Quantity(51.107496947788306, "mmBtu/day")
    assert approx_equal(total, expected)

