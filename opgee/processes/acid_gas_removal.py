#
# AcidGasRemoval class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from opgee.processes.compressor import Compressor
from .shared import get_energy_carrier, predict_blower_energy_use, get_bounded_value
from .. import ureg
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process, run_corr_eqns
from ..error import OpgeeException

_logger = getLogger(__name__)

# Input values for variable getting from HYSYS
variable_bound_dict = {"mol_frac_CO2": [0.0, 0.2],
                       "mol_frac_H2S": [0.0, 0.15],
                       "reflux_ratio": [1.5, 3.0],
                       "regen_temp": [190.0, 220.0], # unit in degree F
                       "feed_gas_press": [14.7, 514.7]} # unit in psia


class AcidGasRemoval(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.type_amine = self.attr("type_amine")
        self.ratio_reflux_reboiler = self.attr("ratio_reflux_reboiler")
        self.feed_pressure = self.attr("feed_press")
        self.regeneration_temp = self.attr("regeneration_temp")
        self.eta_reboiler = self.attr("eta_reboiler")
        self.air_cooler_delta_T = self.attr("air_cooler_delta_T")
        self.air_cooler_press_drop = self.attr("air_cooler_press_drop")
        self.air_elevation_const = field.model.const("air-elevation-corr")
        self.air_density_ratio = field.model.const("air-density-ratio")
        self.water_press = field.water.density() * \
                           self.air_cooler_press_drop * \
                           field.model.const("gravitational-acceleration")
        self.air_cooler_fan_eff = self.attr("air_cooler_fan_eff")
        self.air_cooler_speed_reducer_eff = self.attr("air_cooler_speed_reducer_eff")
        self.AGR_table = field.model.AGR_tbl
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")

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

        # AGR modeling based on Aspen HYSYS
        feed_gas_mol_frac = self.gas.component_molar_fractions(input)
        if "CO2" not in feed_gas_mol_frac.index:
            mol_frac_CO2 = 0
        else:
            mol_frac_CO2 = get_bounded_value(feed_gas_mol_frac["CO2"].to("frac").m, "mol_frac_CO2", variable_bound_dict)

        if "H2S" not in feed_gas_mol_frac.index:
            if mol_frac_CO2 == 0:
                _logger.warning(f"Feed gas does not contain H2S and CO2, please consider use non-AGR gas processing path")
            mol_frac_H2S = 0
        else:
            mol_frac_H2S = get_bounded_value(feed_gas_mol_frac["H2S"].to("frac").m, "mol_frac_H2S", variable_bound_dict)

        if mol_frac_H2S > 0.01:
            self.type_amine = "MDEA"
            variable_bound_dict["reflux_ratio"] = [6.5, 8.0]

        reflux_ratio = get_bounded_value(self.ratio_reflux_reboiler.to("frac").m, "reflux_ratio", variable_bound_dict)
        regen_temp = get_bounded_value(self.regeneration_temp.to("degF").m, "regen_temp", variable_bound_dict)
        feed_gas_press = get_bounded_value(self.feed_pressure.to("psia").m, "feed_gas_press", variable_bound_dict)

        gas_volume_rate = self.gas.tot_volume_flow_rate_STP(input)
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

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, compressor_energy_consumption + reboiler_fuel_use)
        energy_use.set_rate("Electricity", pump_duty_elec + condenser_elec_consumption + amine_cooler_elec_consumption)

        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
