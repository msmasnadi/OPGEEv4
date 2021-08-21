from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID, Stream
import pandas as pd
from opgee import ureg

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
        self.temperature_outlet_exhaust_OTSG_before_economizer = self.attr("temperature_outlet_exhaust_OTSG_before_economizer")

        self.imported_fuel_gas_comp = field.attrs_with_prefix("imported_gas_comp_")
        self.processed_prod_gas_comp = field.attrs_with_prefix("processed_prod_gas_comp_")
        self.inlet_air_comp = field.attrs_with_prefix("air_comp_")

        self.OTSG_frac_import_gas = field.attr("OTSG_frac_import_gas")
        self.OTSG_frac_prod_gas = field.attr("OTSG_frac_prod_gas")
        self.O2_excess_OTSG = self.attr("O2_excess_OTSG")
        self.OTSG_fuel_type = self.attr("fuel_input_type_OTSG")
        self.loss_shell_OTSG = self.attr("loss_shell_OTSG")
        self.loss_gaseous_OTSG = self.attr("loss_gaseous_OTSG")
        self.loss_liquid_OTSG = self.attr("loss_liquid_OTSG")

        self.prod_combustion_coeff = field.model.prod_combustion_coeff
        self.reaction_combustion_coeff = field.model.reaction_combustion_coeff
        self.liquid_fuel_comp = field.oil.liquid_fuel_composition(self.API)

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
        input_makeup_water = self.find_input_stream("makeup water for steam generation")
        makeup_water_mass_rate = input_makeup_water.liquid_flow_rate("H2O")

        OTSG_steam_mass_rate = (water_mass_rate_for_injection + blowdown_water_mass_rate) * (self.fraction_OTSG)
        OTSG_desired_steam_mass_rate = water_mass_rate_for_injection * self.fraction_OTSG

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
        air_requirement_MW = self.gas.molar_weight_from_molar_fracs(air_requirement_fuel) / air_requirement_fuel.sum()
        air_requirement_LHV_fuel = (air_requirement_fuel * self.gas.combustion_enthalpy(air_requirement_fuel, self.temperature_inlet_air_OTSG)).sum() / gas_MW_combust_OTSG
        air_requirement_LHV_stream = (air_requirement_fuel * self.gas.combustion_enthalpy(air_requirement_fuel, self.temperature_inlet_air_OTSG)).sum() / air_requirement_MW / air_requirement_fuel_sum

        if self.OTSG_fuel_type == "Gas":
            exhaust_consump_before_economizer = (self.OTSG_frac_import_gas * import_gas_products_comp + self.OTSG_frac_prod_gas * prod_gas_products_comp
                                                 + (self.O2_excess_OTSG-1)/self.O2_excess_OTSG) * air_requirement_fuel
        else:
            exhaust_consump_before_economizer = air_requirement_fuel + 0.5*self.liquid_fuel_comp
            exhaust_consump_before_economizer["O2"] = air_requirement_fuel["O2"] - self.liquid_fuel_comp["C"] - 0.25*self.liquid_fuel_comp["H"]-self.liquid_fuel_comp["S"]
            exhaust_consump_before_economizer["CO2"] = air_requirement_fuel["CO2"] + self.liquid_fuel_comp["C"]
        exhaust_consump_before_economizer["C1"] = 0
        exhaust_consump_before_economizer_sum = ureg.Quantity(exhaust_consump_before_economizer.sum(), "percent")
        exhaust_consump_before_economizer["C1"] = 100
        exhaust_consump_before_economizer = pd.Series(exhaust_consump_before_economizer, dtype="pint[percent]")
        exhaust_consump_before_economizer_MW = self.gas.molar_weight_from_molar_fracs(exhaust_consump_before_economizer) / exhaust_consump_before_economizer.sum()
        exhaust_consump_before_economizer_LHV_fuel = (exhaust_consump_before_economizer * self.gas.combustion_enthalpy(exhaust_consump_before_economizer,
                                                                                        self.temperature_outlet_exhaust_OTSG_before_economizer)).sum() / gas_MW_combust_OTSG
        exhaust_consump_before_economizer_LHV_stream = (exhaust_consump_before_economizer * self.gas.combustion_enthalpy(exhaust_consump_before_economizer,
                                                                                          self.temperature_outlet_exhaust_OTSG_before_economizer)).sum() / exhaust_consump_before_economizer_MW / exhaust_consump_before_economizer_sum

        OTSG_input_enthalpy_per_unit_fuel = self.oil.mass_energy_density() - air_requirement_LHV_fuel - exhaust_consump_before_economizer_LHV_fuel
        OTSG_shell_loss_per_unit_fuel = self.loss_shell_OTSG * gas_LHV_OTSG if self.OTSG_fuel_type == "Gas" else self.loss_shell_OTSG * self.oil.mass_energy_density()
        OTSG_other_loss_per_unit_fuel = self.loss_gaseous_OTSG / gas_MW_combust_OTSG if self.OTSG_fuel_type == "Gas" else self.loss_liquid_OTSG
        OTSG_available_enthalpy = max(OTSG_input_enthalpy_per_unit_fuel - OTSG_shell_loss_per_unit_fuel - OTSG_other_loss_per_unit_fuel, 0)



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
