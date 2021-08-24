from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID, Stream
import pandas as pd
from opgee import ureg
from ..error import BalanceError

_logger = getLogger(__name__)


class SteamGeneration(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.steam_flooding_check = field.attr("steam_flooding")

        if self.steam_flooding_check != 1:
            self.enabled = False
            return

        self.frac_steam_cogen = field.attr("fraction_steam_cogen")
        self.frac_steam_solar = field.attr("fraction_steam_solar")
        self.SOR = field.attr("SOR")
        self.oil_volume_rate = field.attr("oil_prod")
        self.steam_quality_outlet = self.attr("steam_quality_outlet")
        self.steam_quality_after_blowdown = self.attr("steam_quality_after_blowdown")
        self.fraction_blowdown_recycled = self.attr("fraction_blowdown_recycled")
        self.waste_water_reinjection_temp = self.attr("waste_water_reinjection_temp")
        self.waste_water_reinjection_press = self.attr("waste_water_reinjection_press")
        self.friction_loss_stream_distr = self.attr("friction_loss_stream_distr")
        self.pressure_loss_choke_wellhead = self.attr("pressure_loss_choke_wellhead")
        self.API = field.attr("API")

        self.water = field.water
        self.water_density = self.water.density()
        self.oil = field.oil
        self.gas = field.gas

        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

        self.res_press = field.attr("res_press")
        self.steam_press_upper = field.model.const("steam-press-upper-limit")
        self.steam_injection_delta_press = self.attr("steam_injection_delta_press")
        self.steam_generator_press_outlet = min((self.res_press + self.steam_injection_delta_press) *
                                                self.friction_loss_stream_distr *
                                                self.pressure_loss_choke_wellhead, self.steam_press_upper)
        self.steam_generator_temp_outlet = self.water.saturated_temperature(self.steam_generator_press_outlet)

        self.fraction_steam_cogen = field.attr("fraction_steam_cogen")
        self.fraction_steam_solar = field.attr("fraction_steam_solar")
        self.fraction_OTSG = 1 - self.fraction_steam_cogen - self.fraction_steam_solar

        self.prod_water_inlet_temp = self.attr("prod_water_inlet_temp")
        self.prod_water_inlet_press = self.attr("prod_water_inlet_press")
        self.makeup_water_inlet_temp = self.attr("makeup_water_inlet_temp")
        self.makeup_water_inlet_press = self.attr("makeup_water_inlet_press")
        self.temperature_inlet_air_OTSG = self.attr("temperature_inlet_air_OTSG")
        self.OTSG_exhaust_temp_outlet_before_economizer = self.attr(
            "OTSG_exhaust_temp_outlet_before_economizer")
        self.OTSG_exhaust_temp_series = self.attrs_with_prefix("OTSG_exhaust_temp_")

        self.imported_fuel_gas_comp = field.attrs_with_prefix("imported_gas_comp_")
        self.processed_prod_gas_comp = field.attrs_with_prefix("processed_prod_gas_comp_")
        self.inlet_air_comp = field.attrs_with_prefix("air_comp_")

        self.OTSG_frac_import_gas = self.attr("OTSG_frac_import_gas")
        self.OTSG_frac_prod_gas = self.attr("OTSG_frac_prod_gas")
        self.HRSG_frac_import_gas = self.attr("HRSG_frac_import_gas")
        self.HRSG_frac_prod_gas = self.attr("HRSG_frac_prod_gas")
        self.O2_excess_OTSG = self.attr("O2_excess_OTSG")
        self.OTSG_fuel_type = self.attr("fuel_input_type_OTSG")
        self.loss_shell_OTSG = self.attr("loss_shell_OTSG")
        self.loss_gaseous_OTSG = self.attr("loss_gaseous_OTSG")
        self.loss_liquid_OTSG = self.attr("loss_liquid_OTSG")

        self.prod_combustion_coeff = field.model.prod_combustion_coeff
        self.reaction_combustion_coeff = field.model.reaction_combustion_coeff
        self.liquid_fuel_comp = field.oil.liquid_fuel_composition(self.API)

        self.blowdown_heat_recovery = self.attr("blowdown_heat_recovery")
        self.eta_blowdown_heat_rec_OTSG = self.attr("eta_blowdown_heat_rec_OTSG")

        self.economizer_OTSG = self.attr("economizer_OTSG")
        self.preheater_OTSG = self.attr("preheater_OTSG")

        self.eta_economizer_heat_rec_OTSG = self.attr("eta_economizer_heat_rec_OTSG")
        self.eta_preheater_heat_rec_OTSG = self.attr("eta_preheater_heat_rec_OTSG")

        # These are needed for balance check
        self.air_requirement_fuel = None
        self.air_requirement_MW = None
        self.fuel_consumption_for_steam_generation = None
        self.exhaust_consump_sum = None
        self.exhaust_consump_MW = None
        self.gas_MW_combust_OTSG = None
        self.prod_water_mass_rate = None
        self.prod_water_enthalpy_rate = None
        self.makeup_water_mass_rate = None
        self.makeup_water_enthalpy_rate = None
        self.OTSG_steam_out_enthalpy_rate = None
        self.gas_LHV_OTSG = None
        self.air_requirement_LHV_stream = None
        self.LHV_stream = None

    def run(self, analysis):
        self.print_running_msg()
        self.set_iteration_value(0)

        # mass rate
        steam_injection_volume_rate = self.SOR * self.oil_volume_rate
        water_mass_rate_for_injection = steam_injection_volume_rate * self.water_density
        blowdown_water_mass_rate = water_mass_rate_for_injection * (
                self.steam_quality_after_blowdown - self.steam_quality_outlet) / self.steam_quality_outlet
        waste_water_from_blowdown = blowdown_water_mass_rate * (1 - self.fraction_blowdown_recycled)
        recycled_blowdown_water = blowdown_water_mass_rate * self.fraction_blowdown_recycled

        output_waster_water = self.find_output_stream("waste water")
        output_waster_water.set_liquid_flow_rate("H2O",
                                                 waste_water_from_blowdown.to("tonne/day"),
                                                 self.waste_water_reinjection_temp,
                                                 self.waste_water_reinjection_press)
        output_recycled_blowdown_water = self.find_output_stream("blowdown water")
        output_recycled_blowdown_water.set_liquid_flow_rate("H2O", recycled_blowdown_water.to("tonne/day"),
                                                            self.waste_water_reinjection_temp,
                                                            self.waste_water_reinjection_press)

        # output_steam_injection = self.find_output_stream("water for steam injection")
        # output_steam_injection.set_liquid_flow_rate("H2O", water_mass_rate_for_injection.to("tonne/day"), self.steam_generator_temp_outlet, self.steam_generator_press_outlet)

        input_prod_water = self.find_input_stream("produced water for steam generation")
        prod_water_mass_rate = input_prod_water.liquid_flow_rate("H2O")
        prod_water_enthalpy_rate = self.water.enthalpy_PT(self.prod_water_inlet_press,
                                                          self.prod_water_inlet_temp,
                                                          prod_water_mass_rate * self.fraction_OTSG)

        input_makeup_water = self.find_input_stream("makeup water for steam generation")
        makeup_water_mass_rate = input_makeup_water.liquid_flow_rate("H2O")
        makeup_water_enthalpy_rate = self.water.enthalpy_PT(self.makeup_water_inlet_press,
                                                            self.makeup_water_inlet_temp,
                                                            makeup_water_mass_rate * self.fraction_OTSG)

        OTSG_desired_steam_mass_rate = water_mass_rate_for_injection * self.fraction_OTSG
        OTSG_desired_steam_enthalpy_rate = self.water.steam_enthalpy(self.steam_generator_press_outlet,
                                                                     self.steam_quality_outlet,
                                                                     OTSG_desired_steam_mass_rate)
        OTSG_blowdown_before_heat_recovery_mass_rate = blowdown_water_mass_rate * self.fraction_OTSG
        OTSG_blowdown_before_heat_recovery_enthalpy_rate = self.water.enthalpy_PT(self.steam_generator_press_outlet,
                                                                                  self.steam_generator_temp_outlet,
                                                                                  OTSG_blowdown_before_heat_recovery_mass_rate)
        OTSG_blowdown_after_heat_recovery_enthalpy_rate = self.water.enthalpy_PT(self.steam_generator_press_outlet,
                                                                                 self.steam_generator_temp_outlet,
                                                                                 OTSG_blowdown_before_heat_recovery_mass_rate)
        recoverable_enthalpy_blowdown_water = self.eta_blowdown_heat_rec_OTSG * (
                OTSG_blowdown_before_heat_recovery_enthalpy_rate - OTSG_blowdown_after_heat_recovery_enthalpy_rate) if self.blowdown_heat_recovery else ureg.Quantity(
            0, "MJ/day")
        blowdown_loss = OTSG_blowdown_before_heat_recovery_enthalpy_rate - OTSG_blowdown_after_heat_recovery_enthalpy_rate - recoverable_enthalpy_blowdown_water
        OTSG_steam_out_enthalpy_rate = OTSG_desired_steam_enthalpy_rate + OTSG_blowdown_before_heat_recovery_enthalpy_rate

        # OTSG combustion
        gas_combusted_in_OTSG = (self.imported_fuel_gas_comp * self.OTSG_frac_import_gas +
                                 self.processed_prod_gas_comp * self.OTSG_frac_prod_gas)
        gas_MW_combust_OTSG = self.gas.molar_weight_from_molar_fracs(gas_combusted_in_OTSG)
        gas_LHV_OTSG = self.gas.mass_energy_density_from_molar_fracs(gas_combusted_in_OTSG)

        prod_gas_reactants_comp = self.get_combustion_comp(self.reaction_combustion_coeff, self.processed_prod_gas_comp)
        prod_gas_products_comp = self.get_combustion_comp(self.prod_combustion_coeff, self.processed_prod_gas_comp)
        import_gas_reactants_comp = self.get_combustion_comp(self.reaction_combustion_coeff,
                                                             self.imported_fuel_gas_comp)
        import_gas_products_comp = self.get_combustion_comp(self.prod_combustion_coeff,
                                                            self.imported_fuel_gas_comp)
        if self.OTSG_fuel_type == "Gas":
            air_requirement_fuel = (self.OTSG_frac_import_gas * import_gas_reactants_comp
                                    + self.OTSG_frac_prod_gas * prod_gas_reactants_comp) * self.O2_excess_OTSG
        else:
            air_requirement_fuel = (self.liquid_fuel_comp["C"] + 0.25 * self.liquid_fuel_comp["H"] +
                                    self.liquid_fuel_comp["S"]) * self.O2_excess_OTSG / self.inlet_air_comp[
                                       "O2"] * self.inlet_air_comp

        air_requirement_fuel_sum = ureg.Quantity(air_requirement_fuel.sum(), "percent")
        air_requirement_fuel["C1"] = 100
        air_requirement_fuel = pd.Series(air_requirement_fuel, dtype="pint[percent]")
        air_requirement_MW = self.gas.molar_weight_from_molar_fracs(
            air_requirement_fuel.drop(labels=["C1"])) / air_requirement_fuel.drop(labels=["C1"]).sum()
        air_requirement_LHV_fuel = (air_requirement_fuel * self.gas.combustion_enthalpy(air_requirement_fuel,
                                                                                        self.temperature_inlet_air_OTSG)).sum() / gas_MW_combust_OTSG
        air_requirement_LHV_stream = (air_requirement_fuel * self.gas.combustion_enthalpy(air_requirement_fuel,
                                                                                          self.temperature_inlet_air_OTSG)).sum() / air_requirement_MW / air_requirement_fuel_sum
        air_requirement_fuel = air_requirement_fuel.drop(labels=["C1"])

        if self.OTSG_fuel_type == "Gas":
            exhaust_consump = (self.OTSG_frac_import_gas * import_gas_products_comp +
                               self.OTSG_frac_prod_gas * prod_gas_products_comp) + (
                                      self.O2_excess_OTSG - 1) / self.O2_excess_OTSG * air_requirement_fuel
        else:
            exhaust_consump = air_requirement_fuel + 0.5 * self.liquid_fuel_comp
            exhaust_consump["O2"] = air_requirement_fuel["O2"] - self.liquid_fuel_comp["C"] - 0.25 * \
                                    self.liquid_fuel_comp["H"] - self.liquid_fuel_comp["S"]
            exhaust_consump["CO2"] = air_requirement_fuel["CO2"] + self.liquid_fuel_comp["C"]
        exhaust_consump_sum = exhaust_consump.sum()
        exhaust_consump["C1"] = ureg.Quantity(100, "percent")
        exhaust_consump = pd.Series(exhaust_consump, dtype="pint[percent]")
        exhaust_consump_MW = self.gas.molar_weight_from_molar_fracs(
            exhaust_consump.drop(labels=["C1"])) / exhaust_consump.drop(labels=["C1"]).sum()

        LHV_fuel, LHV_stream = self.get_LHV_fuel_and_stream_series(exhaust_consump,
                                                                   self.OTSG_exhaust_temp_series,
                                                                   gas_MW_combust_OTSG,
                                                                   exhaust_consump_sum,
                                                                   exhaust_consump_MW)
        exhaust_consump = exhaust_consump.drop(labels=["C1"])
        OTSG_input_enthalpy_per_unit_fuel = (
                gas_LHV_OTSG + air_requirement_LHV_fuel - LHV_fuel["outlet_before_economizer"])
        OTSG_shell_loss_per_unit_fuel = self.loss_shell_OTSG * gas_LHV_OTSG if self.OTSG_fuel_type == "Gas" else self.loss_shell_OTSG * self.oil.mass_energy_density()
        OTSG_other_loss_per_unit_fuel = self.loss_gaseous_OTSG / gas_MW_combust_OTSG if self.OTSG_fuel_type == "Gas" else self.loss_liquid_OTSG
        OTSG_available_enthalpy = max(OTSG_input_enthalpy_per_unit_fuel -
                                      OTSG_shell_loss_per_unit_fuel -
                                      OTSG_other_loss_per_unit_fuel, 0)

        # calculate recoverable heat
        delta_H = OTSG_steam_out_enthalpy_rate - prod_water_enthalpy_rate - makeup_water_enthalpy_rate - recoverable_enthalpy_blowdown_water
        constant_before_economizer = exhaust_consump_sum * exhaust_consump_MW / gas_MW_combust_OTSG * LHV_stream[
            "outlet_before_economizer"]
        constant_before_preheater = exhaust_consump_sum * exhaust_consump_MW / gas_MW_combust_OTSG * LHV_stream[
            "outlet_before_preheater"]
        constant_outlet = exhaust_consump_sum * exhaust_consump_MW / gas_MW_combust_OTSG * LHV_stream["outlet"]
        constant_total = (constant_before_economizer - constant_outlet) / OTSG_available_enthalpy
        total_recoverable_heat = constant_total / (1 + constant_total) * delta_H

        eta_1 = self.eta_economizer_heat_rec_OTSG
        eta_2 = self.eta_preheater_heat_rec_OTSG
        denominator = (1 - eta_1 * eta_2 * (constant_before_preheater - constant_before_economizer) * (
                    constant_outlet - constant_before_preheater) /
                       (
                                   OTSG_available_enthalpy - eta_1 * constant_before_preheater + eta_1 * constant_before_economizer) /
                       (OTSG_available_enthalpy - eta_2 * constant_outlet + eta_2 * constant_before_preheater))
        recoverable_heat_before_economizer = ureg.Quantity(0, "MJ/day") if not self.economizer_OTSG else \
            eta_1 * (constant_before_economizer - constant_before_preheater) * OTSG_available_enthalpy * delta_H / \
            (OTSG_available_enthalpy - eta_1 * constant_before_preheater + eta_1 * constant_before_economizer) / \
            (OTSG_available_enthalpy - eta_2 * constant_outlet + eta_2 * constant_before_preheater) / denominator
        recoverable_heat_before_preheater = ureg.Quantity(0, "MJ/day") if not self.economizer_OTSG else \
            eta_2 * (constant_before_preheater - constant_outlet) * OTSG_available_enthalpy * delta_H / \
            (OTSG_available_enthalpy - eta_1 * constant_before_preheater + eta_1 * constant_before_economizer) / \
            (OTSG_available_enthalpy - eta_2 * constant_outlet + eta_2 * constant_before_preheater) / denominator

        fuel_demand_for_steam_enthalpy_change = delta_H - recoverable_heat_before_economizer - recoverable_heat_before_preheater
        fuel_consumption_for_steam_generation = fuel_demand_for_steam_enthalpy_change / OTSG_available_enthalpy

        self.air_requirement_fuel = air_requirement_fuel
        self.air_requirement_MW = air_requirement_MW
        self.fuel_consumption_for_steam_generation = fuel_consumption_for_steam_generation
        self.exhaust_consump_sum = exhaust_consump_sum
        self.exhaust_consump_MW = exhaust_consump_MW
        self.gas_MW_combust_OTSG = gas_MW_combust_OTSG
        self.prod_water_mass_rate = prod_water_mass_rate
        self.prod_water_enthalpy_rate = prod_water_enthalpy_rate
        self.makeup_water_mass_rate = makeup_water_mass_rate
        self.makeup_water_enthalpy_rate = makeup_water_enthalpy_rate
        self.OTSG_steam_out_enthalpy_rate = OTSG_steam_out_enthalpy_rate
        self.gas_LHV_OTSG = gas_LHV_OTSG
        self.air_requirement_LHV_stream = air_requirement_LHV_stream
        self.LHV_stream = LHV_stream

        # GT + HRSG combustion
        gas_combusted_in_GT = (self.imported_fuel_gas_comp * self.HRSG_frac_import_gas +
                               self.processed_prod_gas_comp * self.HRSG_frac_prod_gas)
        gas_MW_combust_GT = self.gas.molar_weight_from_molar_fracs(gas_combusted_in_GT)
        gas_LHV_GT = self.gas.mass_energy_density_from_molar_fracs(gas_combusted_in_GT)




    def check_balances(self):

        air_in_mass_rate = self.air_requirement_fuel * self.gas.molar_weight_from_molar_fracs(
            self.inlet_air_comp) * self.fuel_consumption_for_steam_generation
        air_in_mass_rate = air_in_mass_rate / self.air_requirement_MW if self.OTSG_fuel_type == "Gas" else air_in_mass_rate

        OTSG_outlet_exhaust_mass = self.exhaust_consump_sum * self.exhaust_consump_MW * self.fuel_consumption_for_steam_generation
        OTSG_outlet_exhaust_mass = OTSG_outlet_exhaust_mass / self.gas_MW_combust_OTSG if self.OTSG_fuel_type == "Gas" else OTSG_outlet_exhaust_mass

        OTSG_prod_water_mass_rate = self.prod_water_mass_rate * self.fraction_OTSG
        OTSG_makup_water_mass_rate = self.makeup_water_mass_rate * self.fraction_OTSG

        OTSG_mass_in = self.fuel_consumption_for_steam_generation + air_in_mass_rate + \
                       OTSG_prod_water_mass_rate + OTSG_makup_water_mass_rate
        OTSG_mass_out = self.OTSG_steam_out_enthalpy_rate + OTSG_outlet_exhaust_mass

        OTSG_energy_in = self.fuel_consumption_for_steam_generation * self.gas_LHV_OTSG + \
                         air_in_mass_rate * self.air_requirement_LHV_stream + \
                         self.prod_water_enthalpy_rate + self.makeup_water_enthalpy_rate
        OTSG_energy_out = OTSG_outlet_exhaust_mass * self.LHV_stream["outlet"]

        # raise BalanceError(self.name, "OTSG_mass")

    @staticmethod
    def get_combustion_comp(coeff_table, gas_comp):
        """
        calculate reaction gas comp using combustion table and gas comp

        :param coeff_table:
        :param gas_comp:
        :return: (float) Pandas Series, reaction gas comp
        """
        table = coeff_table.loc[gas_comp.index, :]
        table = table.transpose()
        result = table.dot(gas_comp)

        return result

    def get_LHV_fuel_and_stream_series(self, comp_series, temp_series, fuel_MW, comp_series_sum, comp_series_MW):
        """
        calculate exhaust LHV fuel and stream using exhaust composition, temperature series and fuel mol_weight

        :param comp_series_MW:
        :param comp_series_sum:
        :param fuel_MW:
        :param comp_series:
        :param temp_series:
        :return: (float) LHV fuel series and LHV stream series
        """

        LHV_fuel = pd.Series()
        LHV_stream = pd.Series()

        for name in temp_series.index:
            temp = (comp_series * self.gas.combustion_enthalpy(comp_series, temp_series[name])).sum()
            LHV_fuel[name] = temp / fuel_MW
            LHV_stream[name] = temp / comp_series_sum / comp_series_MW

        return LHV_fuel, LHV_stream
