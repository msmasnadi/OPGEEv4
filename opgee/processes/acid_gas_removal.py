from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID
from ..process import run_corr_eqns
from opgee import ureg

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
        self.eta_reboiler_AGR = field.attr("eta_reboiler_AGR")
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

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_streams("gas for AGR", combine=True)

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        CO2_feed_mass_rate = input.gas_flow_rate("CO2")
        CH4_feed_mass_rate = input.gas_flow_rate("C1")
        CO2_to_demethanizer = min(0.05 * CO2_feed_mass_rate, 0.001 * CH4_feed_mass_rate)

        gas_to_demethanizer = self.find_output_stream("gas for demethanizer")
        gas_to_demethanizer.copy_flow_rates_from(input)
        gas_to_demethanizer.set_gas_flow_rate("CO2", CO2_to_demethanizer)
        gas_to_demethanizer.set_temperature_and_pressure(input.temperature, input.pressure)

        gas_to_CO2_reinjection = self.find_output_stream("gas for CO2 compressor")
        # TODO: check the following gas path
        gas_to_CO2_reinjection.copy_flow_rates_from(input)
        gas_to_CO2_reinjection.subtract_gas_rates_from(gas_to_demethanizer)
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

        gas_volume_rate = self.gas.volume_flow_rate_STP(input)
        gas_multiplier = gas_volume_rate.to("mmscf/day").m / 1.0897  # multiplier for gas load in correlation equation

        x1 = mol_frac_CO2
        x2 = mol_frac_H2S
        x3 = reflux_ratio
        x4 = regen_temp
        x5 = feed_gas_press
        corr_result_df = run_corr_eqns(x1, x2, x3, x4, x5, self.AGR_table.loc[:, self.type_amine_AGR])
        reboiler_heavy_duty = ureg.Quantity(max(0, corr_result_df["Reboiler"] * gas_multiplier), "kW")
        pump_duty = ureg.Quantity(max(0, corr_result_df["Pump"] * gas_multiplier), "kW")
        condensor_thermal_load = ureg.Quantity(max(0, corr_result_df["Condenser"] * gas_multiplier), "kW")
        cooler_thermal_load = ureg.Quantity(max(0, corr_result_df["Cooler"]), "kW")

        reboiler_fuel_use = reboiler_heavy_duty * self.eta_reboiler_AGR
        blower_air_quantity = condensor_thermal_load / self.air_elevation_const / self.air_cooler_delta_T
        blower_CFM = blower_air_quantity / self.air_density_ratio
        blower_delivered_hp = blower_CFM * self.water_press / self.air_cooler_fan_eff
        blower_fan_motor_hp = blower_delivered_hp / self.air_cooler_speed_reducer_eff
        air_cooler_energy_consumption = self.get_energy_consumption("Electric_motor", blower_fan_motor_hp)
        pass
