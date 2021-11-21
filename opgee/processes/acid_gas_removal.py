from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID
from ..process import run_corr_eqns
from opgee import ureg
from ..compressor import Compressor
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..emissions import Emissions, EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class AcidGasRemoval(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.type_amine_AGR = field.attr("type_amine_AGR")
        self.ratio_reflux_reboiler_AGR = field.attr("ratio_reflux_reboiler_AGR")
        self.feed_press_AGR = field.attr("feed_press_AGR")
        self.regeneration_AGR_temp = field.attr("regeneration_AGR_temp")
        self.eta_reboiler_AGR = self.attr("eta_reboiler_AGR")
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
        self.eta_compressor_AGR = self.attr("eta_compressor_AGR")
        self.prime_mover_type_AGR = self.attr("prime_mover_type_AGR")

    def run(self, analysis):
        self.print_running_msg()

        if not self.all_streams_ready("gas for AGR"):
            return

        # mass rate
        input = self.find_input_streams("gas for AGR", combine=True)

        if input.is_empty():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        CO2_feed_mass_rate = input.gas_flow_rate("CO2")
        CH4_feed_mass_rate = input.gas_flow_rate("C1")
        CO2_to_demethanizer = min(0.05 * CO2_feed_mass_rate, 0.001 * CH4_feed_mass_rate)

        gas_to_demethanizer = self.find_output_stream("gas for demethanizer", raiseError=None)
        if gas_to_demethanizer is not None:
            gas_to_demethanizer.copy_flow_rates_from(input)
            gas_to_demethanizer.set_gas_flow_rate("CO2", CO2_to_demethanizer)
            gas_to_demethanizer.subtract_gas_rates_from(gas_fugitives)
            gas_to_demethanizer.set_temperature_and_pressure(input.temperature, input.pressure)

        gas_to_CO2_reinjection = self.find_output_stream("gas for CO2 compressor", raiseError=None)
        if gas_to_CO2_reinjection is not None:
            gas_to_CO2_reinjection.copy_flow_rates_from(input)
            gas_to_CO2_reinjection.subtract_gas_rates_from(gas_to_demethanizer)
            gas_to_CO2_reinjection.subtract_gas_rates_from(gas_fugitives)
            gas_to_CO2_reinjection.set_temperature_and_pressure(input.temperature, input.pressure)

        # AGR modeling based on Aspen HYSYS
        feed_gas_mol_fracs = self.gas.component_molar_fractions(input)
        mol_frac_CO2 = min(max(feed_gas_mol_fracs["CO2"].to("frac").m if "CO2" in feed_gas_mol_fracs.index else 0, 0.0),
                           0.2)
        mol_frac_H2S = min(max(feed_gas_mol_fracs["H2S"].to("frac").m if "H2S" in feed_gas_mol_fracs.index else 0, 0.0),
                           0.15)
        reflux_ratio = min(max(self.ratio_reflux_reboiler_AGR.to("frac").m, 1.5), 3.0)
        regen_temp = min(max(self.regeneration_AGR_temp.to("degF").m, 190.0), 220.0)
        feed_gas_press = min(max(self.feed_press_AGR.to("psia").m, 14.7), 514.7)

        gas_volume_rate = self.gas.tot_volume_flow_rate_STP(input)
        gas_multiplier = gas_volume_rate.to("mmscf/day").m / 1.0897  # multiplier for gas load in correlation equation

        x1 = mol_frac_CO2
        x2 = mol_frac_H2S
        x3 = reflux_ratio
        x4 = regen_temp
        x5 = feed_gas_press
        corr_result_df = run_corr_eqns(x1, x2, x3, x4, x5, self.AGR_table.loc[:, self.type_amine_AGR])
        reboiler_heavy_duty = ureg.Quantity(max(0, corr_result_df["Reboiler"] * gas_multiplier), "kW")
        pump_duty = ureg.Quantity(max(0, corr_result_df["Pump"] * gas_multiplier), "kW")
        condenser_thermal_load = ureg.Quantity(max(0, corr_result_df["Condenser"] * gas_multiplier), "kW")
        cooler_thermal_load = ureg.Quantity(max(0, corr_result_df["Cooler"] * gas_multiplier), "kW")
        reboiler_fuel_use = reboiler_heavy_duty * self.eta_reboiler_AGR

        condenser_energy_consumption = self.predict_blower_energy_use(condenser_thermal_load,
                                                                      self.air_cooler_delta_T,
                                                                      self.water_press,
                                                                      self.air_cooler_fan_eff,
                                                                      self.air_cooler_speed_reducer_eff)
        amine_cooler_energy_consumption = self.predict_blower_energy_use(cooler_thermal_load,
                                                                         self.air_cooler_delta_T,
                                                                         self.water_press,
                                                                         self.air_cooler_fan_eff,
                                                                         self.air_cooler_speed_reducer_eff)

        overall_compression_ratio = ureg.Quantity(feed_gas_press, "psia") / input.pressure
        compression_ratio = Compressor.get_compression_ratio(overall_compression_ratio)
        num_stages = Compressor.get_num_of_compression(overall_compression_ratio)
        total_work, _ = Compressor.get_compressor_work_temp(self.field,
                                                            input.temperature,
                                                            input.pressure,
                                                            gas_to_demethanizer,
                                                            compression_ratio,
                                                            num_stages)
        volume_flow_rate_STP = self.gas.tot_volume_flow_rate_STP(gas_to_demethanizer)
        total_energy = total_work * volume_flow_rate_STP
        brake_horse_power = total_energy / self.eta_compressor_AGR
        compressor_energy_consumption = self.get_energy_consumption(self.prime_mover_type_AGR, brake_horse_power)

        # energy-use
        energy_use = self.energy
        if self.prime_mover_type_AGR == "NG_engine" or "NG_turbine":
            energy_carrier = EN_NATURAL_GAS
        elif self.prime_mover_type_AGR == "Electric_motor":
            energy_carrier = EN_ELECTRICITY
        else:
            energy_carrier = EN_DIESEL
        energy_use.set_rate(energy_carrier, compressor_energy_consumption)
        energy_use.add_rate(EN_NATURAL_GAS, reboiler_fuel_use)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)
