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
        self.steam_quality_outlet = field.attr("steam_quality_outlet")
        self.steam_quality_after_blowdown = field.attr("steam_quality_after_blowdown")
        self.fraction_blowdown_recycled = field.attr("fraction_blowdown_recycled")
        self.waste_water_reinjection_temp = field.attr("waste_water_reinjection_temp")
        self.waste_water_reinjection_press = field.attr("waste_water_reinjection_press")
        self.friction_loss_stream_distr = field.attr("friction_loss_stream_distr")
        self.pressure_loss_choke_wellhead = field.attr("pressure_loss_choke_wellhead")
        self.API = field.attr("API")

        self.water = field.water
        self.water_density = self.water.density()
        self.oil = field.oil
        self.gas = field.gas

        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

        self.res_press = field.attr("res_press")
        self.steam_press_upper = field.model.const("steam-press-upper-limit")
        self.steam_injection_delta_press = field.attr("steam_injection_delta_press")
        self.steam_generator_press_outlet = min((self.res_press + self.steam_injection_delta_press) *
                                                self.friction_loss_stream_distr *
                                                self.pressure_loss_choke_wellhead, self.steam_press_upper)
        self.steam_generator_temp_outlet = self.water.saturated_temperature(self.steam_generator_press_outlet)

        self.fraction_steam_cogen = field.attr("fraction_steam_cogen")
        self.fraction_steam_solar = field.attr("fraction_steam_solar")
        self.fraction_OTSG = 1 - self.fraction_steam_cogen - self.fraction_steam_solar

        self.prod_water_inlet_temp = field.attr("prod_water_inlet_temp")
        self.prod_water_inlet_press = field.attr("prod_water_inlet_press")
        self.makeup_water_inlet_temp = field.attr("makeup_water_inlet_temp")
        self.makeup_water_inlet_press = field.attr("makeup_water_inlet_press")
        self.temperature_inlet_air_OTSG = field.attr("temperature_inlet_air_OTSG")
        self.OTSG_exhaust_temp_outlet_before_economizer = field.attr(
            "OTSG_exhaust_temp_outlet_before_economizer")
        self.OTSG_exhaust_temp_series = field.attrs_with_prefix("OTSG_exhaust_temp_")
        self.HRSG_exhaust_temp_series = field.attrs_with_prefix("HRSG_exhaust_temp_")

        self.imported_fuel_gas_comp = field.attrs_with_prefix("imported_gas_comp_")
        self.processed_prod_gas_comp = field.attrs_with_prefix("processed_prod_gas_comp_")
        self.inlet_air_comp = field.attrs_with_prefix("air_comp_")

        self.OTSG_frac_import_gas = field.attr("OTSG_frac_import_gas")
        self.OTSG_frac_prod_gas = field.attr("OTSG_frac_prod_gas")
        self.HRSG_frac_import_gas = field.attr("HRSG_frac_import_gas")
        self.HRSG_frac_prod_gas = field.attr("HRSG_frac_prod_gas")
        self.O2_excess_OTSG = field.attr("O2_excess_OTSG")
        self.OTSG_fuel_type = field.attr("fuel_input_type_OTSG")
        self.loss_shell_OTSG = field.attr("loss_shell_OTSG")
        self.loss_shell_HRSG = field.attr("loss_shell_HRSG")
        self.loss_gaseous_OTSG = field.attr("loss_gaseous_OTSG")
        self.loss_liquid_OTSG = field.attr("loss_liquid_OTSG")

        self.prod_combustion_coeff = field.model.prod_combustion_coeff
        self.reaction_combustion_coeff = field.model.reaction_combustion_coeff
        self.gas_turbine_tlb = field.model.gas_turbine_tbl
        self.liquid_fuel_comp = field.oil.liquid_fuel_composition(self.API)

        self.blowdown_heat_recovery = field.attr("blowdown_heat_recovery")
        self.eta_blowdown_heat_rec_OTSG = field.attr("eta_blowdown_heat_rec_OTSG")
        self.eta_blowdown_heat_rec_HRSG = field.attr("eta_blowdown_heat_rec_HRSG")

        self.economizer_OTSG = field.attr("economizer_OTSG")
        self.preheater_OTSG = field.attr("preheater_OTSG")
        self.economizer_HRSG = field.attr("economizer_HRSG")
        self.preheater_HRSG = field.attr("preheater_HRSG")

        self.eta_economizer_heat_rec_OTSG = field.attr("eta_economizer_heat_rec_OTSG")
        self.eta_preheater_heat_rec_OTSG = field.attr("eta_preheater_heat_rec_OTSG")

        self.eta_economizer_heat_rec_HRSG = field.attr("eta_economizer_heat_rec_HRSG")
        self.eta_preheater_heat_rec_HRSG = field.attr("eta_preheater_heat_rec_HRSG")

        self.gas_turbine_type = field.attr("gas_turbine_type")
        self.duct_firing = field.attr("duct_firing")

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
        self.O2_excess_HRSG = None
        self.import_gas_products_comp = None
        self.prod_gas_products_comp = None
        self.exhaust_consump_GT = None
        self.exhaust_consump_GT_LHV_fuel = None
        self.gas_MW_combust_GT = None
        self.gas_LHV_GT = None

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

        input_prod_water = self.find_input_stream("produced water for steam generation")
        prod_water_mass_rate = input_prod_water.liquid_flow_rate("H2O")

        input_makeup_water = self.find_input_stream("makeup water for steam generation")
        makeup_water_mass_rate = input_makeup_water.liquid_flow_rate("H2O")

        pass

    def check_balances(self):
        pass



        # raise BalanceError(self.name, "OTSG_mass")
