#
# AcidGasRemoval class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..processes.compressor import Compressor
from .. import ureg
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process, run_corr_eqns
from .shared import get_energy_carrier, predict_blower_energy_use, get_bounded_value, get_energy_consumption

_logger = getLogger(__name__)

amine_solution_K_value_dict = { "conv DEA" : 1.45,
                                "high DEA": 0.95,
                                "MEA" : 2.05,
                                "DGA" : 1.28,
                                "MDEA" : 1.25}


class AcidGasRemoval(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        m = field.model

        self.gas = field.gas
        self.type_amine = self.attr("type_amine")
        self.ratio_reflux_reboiler = self.attr("ratio_reflux_reboiler")
        self.AGR_feedin_press = field.attr("AGR_feedin_press")
        self.regeneration_temp = self.attr("regeneration_temp")
        self.eta_reboiler = self.attr("eta_reboiler")
        self.air_cooler_delta_T = self.attr("air_cooler_delta_T")
        self.air_cooler_press_drop = self.attr("air_cooler_press_drop")
        self.air_elevation_const = m.const("air-elevation-corr")
        self.air_density_ratio = m.const("air-density-ratio")
        self.water_press = field.water.density() * \
                           self.air_cooler_press_drop * \
                           m.const("gravitational-acceleration")
        self.air_cooler_fan_eff = self.attr("air_cooler_fan_eff")
        self.air_cooler_speed_reducer_eff = self.attr("air_cooler_speed_reducer_eff")
        self.AGR_table = m.AGR_tbl
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.amine_solution_K_value =\
            ureg.Quantity(amine_solution_K_value_dict[self.type_amine]*100, "gallon*day/minutes/mmscf")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        if not self.all_streams_ready("gas for AGR"):
            return

        # mass rate
        input = self.find_input_streams("gas for AGR", combine=True)
        if input.is_uninitialized():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        CO2_feed_mass_rate = input.gas_flow_rate("CO2")
        CH4_feed_mass_rate = input.gas_flow_rate("C1")
        CO2_to_demethanizer = min(0.05 * CO2_feed_mass_rate, 0.001 * CH4_feed_mass_rate)

        output_gas = self.find_output_stream("gas for demethanizer", raiseError=False)
        if output_gas is None:
            output_gas = self.find_output_stream("gas for gas partition")
        output_gas.copy_flow_rates_from(input)
        output_gas.set_gas_flow_rate("CO2", CO2_to_demethanizer)
        output_gas.subtract_rates_from(gas_fugitives)
        self.set_iteration_value(output_gas.total_flow_rate())

        gas_to_CO2_reinjection = self.find_output_stream("gas for CO2 compressor", raiseError=False)
        if gas_to_CO2_reinjection is not None:
            gas_to_CO2_reinjection.copy_flow_rates_from(input)
            gas_to_CO2_reinjection.subtract_rates_from(output_gas)
            gas_to_CO2_reinjection.subtract_rates_from(gas_fugitives)

        feed_gas_mol_frac = self.gas.component_molar_fractions(input)
        mol_frac_H2S = feed_gas_mol_frac["H2S"] if "H2S" in feed_gas_mol_frac else ureg.Quantity(0, "frac")
        mol_frac_CO2 = feed_gas_mol_frac["CO2"] if "CO2" in feed_gas_mol_frac else ureg.Quantity(0, "frac")

        if mol_frac_H2S.m == 0.0 and mol_frac_CO2 == 0.0:
            _logger.warning(f"Feed gas does not contain H2S and CO2, please consider using non-AGR gas processing path")
            return

        if mol_frac_H2S.m <= 0.2 and mol_frac_CO2 <= 0.15:
            compressor_energy_consumption, reboiler_fuel_use, electricity_consump =\
                self.calculate_energy_consumption_from_Aspen(input, output_gas, mol_frac_CO2, mol_frac_H2S)
        else:
            compressor_energy_consumption, reboiler_fuel_use, electricity_consump = \
                self.calculate_energy_consumption_from_textbook(input, mol_frac_CO2, mol_frac_H2S)

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, compressor_energy_consumption + reboiler_fuel_use)
        energy_use.add_rate("Electricity", electricity_consump) \
            if energy_carrier == "Electricty" else energy_use.set_rate("Electricity", electricity_consump)


        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)


    def calculate_energy_consumption_from_Aspen(self, input, output_gas, mol_frac_CO2, mol_frac_H2S):

        # Input values for variable getting from HYSYS
        variable_bound_dict = {"mol_frac_CO2": [0.0, 0.2],
                               "mol_frac_H2S": [0.0, 0.15],
                               "reflux_ratio": [1.5, 3.0],
                               "regen_temp": [190.0, 220.0],  # unit in degree F
                               "feed_gas_press": [14.7, 514.7]}  # unit in psia

        mol_frac_CO2 = get_bounded_value(mol_frac_CO2.to("frac").m, "mol_frac_CO2", variable_bound_dict)
        mol_frac_H2S = get_bounded_value(mol_frac_H2S.to("frac").m, "mol_frac_H2S", variable_bound_dict)

        if mol_frac_H2S > 0.01:
            self.type_amine = "MDEA"
            variable_bound_dict["reflux_ratio"] = [6.5, 8.0]

        reflux_ratio = get_bounded_value(self.ratio_reflux_reboiler.to("frac").m, "reflux_ratio", variable_bound_dict)
        regen_temp = get_bounded_value(self.regeneration_temp.to("degF").m, "regen_temp", variable_bound_dict)
        feed_gas_press = get_bounded_value(self.AGR_feedin_press.to("psia").m, "feed_gas_press", variable_bound_dict)

        gas_volume_rate = self.gas.volume_flow_rate_STP(input)
        gas_multiplier = gas_volume_rate.to("mmscf/day").m / 1.0897  # multiplier for gas load in correlation equation

        x1 = mol_frac_CO2
        x2 = mol_frac_H2S
        x3 = reflux_ratio
        x4 = regen_temp
        x5 = feed_gas_press
        corr_result_df = run_corr_eqns(x1, x2, x3, x4, x5, self.AGR_table.loc[:, self.type_amine])
        reboiler_heavy_duty = ureg.Quantity(max(0.0, corr_result_df["Reboiler"] * gas_multiplier), "kW")
        condenser_thermal_load = ureg.Quantity(max(0.0, corr_result_df["Condenser"] * gas_multiplier), "kW")
        cooler_thermal_load = ureg.Quantity(max(0.0, corr_result_df["Cooler"] * gas_multiplier), "kW")

        reboiler_fuel_use = reboiler_heavy_duty * self.eta_reboiler
        pump_duty_elec = ureg.Quantity(max(0.0, corr_result_df["Pump"] * gas_multiplier), "kW")
        condenser_elec_consumption = predict_blower_energy_use(self, condenser_thermal_load)
        amine_cooler_elec_consumption = predict_blower_energy_use(self, cooler_thermal_load)

        overall_compression_ratio = ureg.Quantity(feed_gas_press, "psia") / input.tp.P
        compressor_energy_consumption, temp, _ = \
            Compressor.get_compressor_energy_consumption(self.field,
                                                         self.prime_mover_type,
                                                         self.eta_compressor,
                                                         overall_compression_ratio,
                                                         output_gas,
                                                         inlet_tp=input.tp)

        electricity_consump = pump_duty_elec + condenser_elec_consumption + amine_cooler_elec_consumption
        return compressor_energy_consumption, reboiler_fuel_use, electricity_consump

    def calculate_energy_consumption_from_textbook(self, input, mol_frac_CO2, mol_frac_H2S):
        feedin_gas_volume_rate_STP = self.gas.volume_flow_rates_STP(input)

        CO2_volume_rate =\
            feedin_gas_volume_rate_STP["CO2"] if mol_frac_CO2.m != 0 else ureg.Quantity(0, "mmscf/day")
        H2S_volume_rate =\
            feedin_gas_volume_rate_STP["H2S"] if mol_frac_H2S.m != 0 else ureg.Quantity(0, "mmscf/day")
        amine_circulation_rate = self.amine_solution_K_value * (CO2_volume_rate + H2S_volume_rate)

        # Pumps energy consumption
        circulation_pump_HP =\
            ureg.Quantity(amine_circulation_rate.to("gallon / minute").m * (input.tp.P.m + 50) * 0.00065, "horsepower")
        booster_pump_HP = ureg.Quantity(amine_circulation_rate.to("gallon / minute").m * 0.06, "horsepower")
        reflux_pump_HP = booster_pump_HP
        total_pump_HP = circulation_pump_HP + booster_pump_HP + reflux_pump_HP
        total_pump_energy_consump = get_energy_consumption("Electric_motor", total_pump_HP)

        # Air coolers energy consumption
        amine_cooler_HP = ureg.Quantity(amine_circulation_rate.to("gallon / minute").m * 0.36, "horsepower")
        reflux_condenser_HP = amine_cooler_HP * 2
        total_cooling_HP = amine_cooler_HP + reflux_condenser_HP
        total_coolers_energy_consump = get_energy_consumption("Electric_motor", total_cooling_HP)

        # Reboiler energy consumption
        reboiler_heat_duty = amine_circulation_rate * ureg.Quantity(72000, "btu*minute/gallon/hr") * 1.15
        total_reboiler_erergy_consump = self.eta_reboiler * reboiler_heat_duty

        return ureg.Quantity(0, "mmbtu/day"), total_reboiler_erergy_consump, total_coolers_energy_consump + total_pump_energy_consump






