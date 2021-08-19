from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

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

        self.water = self.field.water
        self.water_density = self.water.density()

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

        self.imported_fuel_gas_comp = field.attrs_with_prefix("imported_gas_comp_")
        self.processed_prod_gas_comp = field.attrs_with_prefix("processed_prod_gas_comp_")
        self.inlet_air_comp = field.attrs_with_prefix("air_comp_")

        self.OTSG_frac_import_gas = self.attr("OTSG_frac_import_gas")
        self.OTSG_frac_prod_gas = self.attr("OTSG_frac_prod_gas")
        self.O2_excess_OTSG = self.attr("O2_excess_OTSG")
        self.OTSG_fuel_type = self.attr("OTSG_fuel_type")

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

        # OTSG combustion
        OTSG_gaseous_fuel = (self.imported_fuel_gas_comp * self.OTSG_frac_import_gas +
                             self.processed_prod_gas_comp * self.OTSG_frac_prod_gas)
        prod_gas_reactants_comp = self.get_combustion_comp(self.reaction_combustion_coeff, self.processed_prod_gas_comp)
        prod_gas_products_comp = self.get_combustion_comp(self.prod_combustion_coeff, self.processed_prod_gas_comp)
        import_gas_reactants_comp = self.get_combustion_comp(self.reaction_combustion_coeff, self.imported_fuel_gas_comp)
        import_gas_products_comp = self.get_combustion_comp(self.prod_combustion_coeff,
                                                             self.imported_fuel_gas_comp)

        if self.OTSG_fuel_type == "Gas":
            air_requirement_fuel = (self.OTSG_frac_import_gas * import_gas_reactants_comp + self.OTSG_frac_prod_gas * prod_gas_reactants_comp) * self.O2_excess_OTSG
        else:
            air_requirement_fuel = (self.liquid_fuel_comp["C"] + 0.25*self.liquid_fuel_comp["H"] + self.liquid_fuel_comp["S"]) * self.O2_excess_OTSG / self.inlet_air_comp["O2"] * self.inlet_air_comp

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
